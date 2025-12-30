"""
Backup Management Routes
Handles database backup and restore operations
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..auth import require_admin
from ..database import Database

router = APIRouter(prefix="/api/admin/backups", tags=["admin", "backups"])

BACKUP_BASE_DIR = Path.home() / '.tmp' / 'backups'
BACKUP_SCRIPT = Path(__file__).parent.parent.parent.parent / 'execution' / 'active' / 'backup_database.py'
RESTORE_SCRIPT = Path(__file__).parent.parent.parent.parent / 'execution' / 'active' / 'restore_database.py'
CLEANUP_SCRIPT = Path(__file__).parent.parent.parent.parent / 'execution' / 'active' / 'cleanup_old_backups.py'


class BackupCreate(BaseModel):
    note: Optional[str] = None


class BackupInfo(BaseModel):
    name: str
    timestamp: str
    backup_type: str
    database: str
    total_documents: int
    backup_size_mb: float
    note: Optional[str] = None
    collections: dict


class BackupRestore(BaseModel):
    backup_name: str
    confirm: bool = False


def get_all_backups() -> List[BackupInfo]:
    """Get list of all available backups (both encrypted and unencrypted)"""
    if not BACKUP_BASE_DIR.exists():
        return []

    backups = []
    for item in sorted(BACKUP_BASE_DIR.iterdir(), reverse=True):
        # Handle unencrypted backups (directories with manifest.json)
        if item.is_dir():
            manifest_file = item / 'manifest.json'
            if not manifest_file.exists():
                continue

            try:
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)

                backups.append(BackupInfo(
                    name=item.name,
                    timestamp=manifest.get('timestamp', ''),
                    backup_type=manifest.get('backup_type', 'unknown'),
                    database=manifest.get('database', ''),
                    total_documents=manifest.get('total_documents', 0),
                    backup_size_mb=manifest.get('backup_size_mb', 0),
                    note=manifest.get('note'),
                    collections=manifest.get('collections', {})
                ))
            except Exception as e:
                print(f"Error reading backup {item}: {e}")
                continue

        # Handle encrypted backups (.tar.gz.enc files)
        elif item.is_file() and item.name.endswith('.tar.gz.enc'):
            try:
                # Get backup name from filename (remove .tar.gz.enc extension)
                backup_name = item.name.replace('.tar.gz.enc', '')

                # Get file size
                file_size_mb = item.stat().st_size / (1024**2)

                # Try to read manifest metadata file if it exists
                metadata_file = BACKUP_BASE_DIR / f"{backup_name}.manifest.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        manifest = json.load(f)

                    # Update size to reflect encrypted size
                    manifest['backup_size_mb'] = round(file_size_mb, 2)
                    manifest['encrypted'] = True
                    if manifest.get('note'):
                        manifest['note'] = f"🔒 {manifest['note']}"
                    else:
                        manifest['note'] = '🔒 Encrypted backup'

                    backups.append(BackupInfo(
                        name=backup_name,
                        timestamp=manifest.get('timestamp', ''),
                        backup_type=manifest.get('backup_type', 'manual'),
                        database=manifest.get('database', 'surgical_outcomes'),
                        total_documents=manifest.get('total_documents', 0),
                        backup_size_mb=manifest['backup_size_mb'],
                        note=manifest['note'],
                        collections=manifest.get('collections', {})
                    ))
                else:
                    # Fallback: parse info from filename
                    from datetime import datetime
                    try:
                        timestamp_str = backup_name
                        dt = datetime.strptime(timestamp_str, '%Y-%m-%d_%H-%M-%S')
                        timestamp = dt.isoformat()
                    except:
                        timestamp = backup_name

                    backups.append(BackupInfo(
                        name=backup_name,
                        timestamp=timestamp,
                        backup_type='manual',
                        database='surgical_outcomes',
                        total_documents=0,  # Unknown without metadata
                        backup_size_mb=round(file_size_mb, 2),
                        note='🔒 Encrypted backup (no metadata)',
                        collections={}
                    ))
            except Exception as e:
                print(f"Error reading encrypted backup {item}: {e}")
                continue

    return backups


@router.get("/", response_model=List[BackupInfo])
async def list_backups(current_user=Depends(require_admin)):
    """List all available backups"""
    return get_all_backups()


@router.get("/status")
async def get_backup_status(current_user=Depends(require_admin)):
    """Get backup system status"""
    backups = get_all_backups()
    
    # Calculate totals
    total_size_mb = sum(b.backup_size_mb for b in backups)
    total_docs = backups[0].total_documents if backups else 0
    
    # Get latest backup
    latest_backup = backups[0] if backups else None
    
    # Check disk space
    import shutil
    stat = shutil.disk_usage(BACKUP_BASE_DIR.parent)
    free_gb = stat.free / (1024**3)
    
    return {
        "total_backups": len(backups),
        "total_size_mb": round(total_size_mb, 2),
        "free_space_gb": round(free_gb, 2),
        "latest_backup": {
            "name": latest_backup.name,
            "timestamp": latest_backup.timestamp,
            "type": latest_backup.backup_type,
            "size_mb": latest_backup.backup_size_mb,
            "note": latest_backup.note
        } if latest_backup else None,
        "database": {
            "name": latest_backup.database if latest_backup else "impact",
            "total_documents": total_docs
        }
    }


async def run_backup_script(note: Optional[str] = None):
    """Run backup script in background"""
    cmd = [sys.executable, str(BACKUP_SCRIPT), '--manual']
    if note:
        cmd.extend(['--note', note])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"Backup completed: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Backup failed: {e.stderr}")
        return False


@router.post("/create")
async def create_backup(
    backup: BackupCreate,
    background_tasks: BackgroundTasks,
    current_user=Depends(require_admin)
):
    """Create a new manual backup"""
    if not BACKUP_SCRIPT.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Backup script not found"
        )
    
    # Run backup in background
    background_tasks.add_task(run_backup_script, backup.note)
    
    return {
        "message": "Backup started",
        "note": backup.note,
        "status": "in_progress"
    }


@router.get("/{backup_name}")
async def get_backup_details(
    backup_name: str,
    current_user=Depends(require_admin)
):
    """Get details of a specific backup"""
    backup_dir = BACKUP_BASE_DIR / backup_name
    manifest_file = backup_dir / 'manifest.json'
    
    if not manifest_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup not found"
        )
    
    with open(manifest_file, 'r') as f:
        manifest = json.load(f)
    
    return manifest


@router.delete("/{backup_name}")
async def delete_backup(
    backup_name: str,
    current_user=Depends(require_admin)
):
    """Delete a specific backup"""
    backup_dir = BACKUP_BASE_DIR / backup_name
    
    if not backup_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup not found"
        )
    
    # Check if it's a manual backup
    manifest_file = backup_dir / 'manifest.json'
    if manifest_file.exists():
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
        
        backup_type = manifest.get('backup_type', 'automatic')
    else:
        backup_type = 'unknown'
    
    # Delete the backup directory
    import shutil
    shutil.rmtree(backup_dir)
    
    return {
        "message": f"Backup {backup_name} deleted successfully",
        "backup_type": backup_type
    }


@router.post("/restore")
async def restore_backup(
    restore: BackupRestore,
    current_user=Depends(require_admin)
):
    """Restore database from backup (DANGEROUS - requires confirmation)"""
    if not restore.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Restoration requires explicit confirmation. Set 'confirm' to true."
        )
    
    backup_dir = BACKUP_BASE_DIR / restore.backup_name
    
    if not backup_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup not found"
        )
    
    if not RESTORE_SCRIPT.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Restore script not found"
        )
    
    # This is intentionally NOT run in background because:
    # 1. It's a critical operation that should block
    # 2. User needs to wait for result
    # 3. Backend service will be restarted anyway
    
    return {
        "message": "Restoration requires manual execution via SSH due to service restart requirements",
        "command": f"python3 {RESTORE_SCRIPT} {backup_dir} --confirm",
        "warning": "This operation will stop the backend service and erase the current database. Run the command via SSH terminal."
    }


@router.post("/cleanup")
async def cleanup_old_backups(
    background_tasks: BackgroundTasks,
    current_user=Depends(require_admin)
):
    """Run backup cleanup (applies retention policy)"""
    if not CLEANUP_SCRIPT.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cleanup script not found"
        )
    
    # Run cleanup in background
    async def run_cleanup():
        try:
            result = subprocess.run(
                [sys.executable, str(CLEANUP_SCRIPT)],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"Cleanup completed: {result.stdout}")
        except subprocess.CalledProcessError as e:
            print(f"Cleanup failed: {e.stderr}")
    
    background_tasks.add_task(run_cleanup)
    
    return {
        "message": "Cleanup started",
        "status": "in_progress"
    }


@router.get("/logs/latest")
async def get_latest_backup_log(current_user=Depends(require_admin)):
    """Get latest backup log entries"""
    log_file = Path.home() / '.tmp' / 'backup.log'
    
    if not log_file.exists():
        return {"lines": [], "message": "No backup log found"}
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            # Get last 50 lines
            latest_lines = lines[-50:] if len(lines) > 50 else lines
        
        return {
            "lines": [line.strip() for line in latest_lines],
            "total_lines": len(lines)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read log file: {str(e)}"
        )
