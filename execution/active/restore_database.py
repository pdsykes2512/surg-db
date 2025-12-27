#!/usr/bin/env python3
"""
Database Restoration Script

Restores MongoDB database from backup with safety checks.

Usage:
    python restore_database.py                    # List available backups
    python restore_database.py <backup_dir>       # Show backup details
    python restore_database.py <backup_dir> --confirm  # Actually restore
"""

import os
import sys
import json
import gzip
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('MONGODB_DB_NAME', 'surgdb')
BACKUP_BASE_DIR = Path.home() / '.tmp' / 'backups'


def list_available_backups():
    """List all available backups"""
    if not BACKUP_BASE_DIR.exists():
        print("No backups directory found.")
        return []
    
    backups = []
    for backup_dir in sorted(BACKUP_BASE_DIR.iterdir(), reverse=True):
        if not backup_dir.is_dir():
            continue
        
        manifest_file = backup_dir / 'manifest.json'
        if manifest_file.exists():
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
            backups.append((backup_dir, manifest))
    
    return backups


def show_backup_details(backup_dir):
    """Show details of a specific backup"""
    manifest_file = backup_dir / 'manifest.json'
    if not manifest_file.exists():
        print(f"❌ No manifest found in {backup_dir}")
        return None
    
    with open(manifest_file, 'r') as f:
        manifest = json.load(f)
    
    print("\n" + "=" * 60)
    print("Backup Details")
    print("=" * 60)
    print(f"📁 Location: {backup_dir}")
    print(f"📅 Timestamp: {manifest['timestamp']}")
    print(f"🏷️  Type: {manifest['backup_type']}")
    print(f"🗄️  Database: {manifest['database']}")
    print(f"📊 Collections: {len(manifest['collections'])}")
    print(f"📄 Total documents: {manifest['total_documents']}")
    if 'backup_size_mb' in manifest:
        print(f"💾 Size: {manifest['backup_size_mb']:.1f} MB")
    if manifest.get('note'):
        print(f"📝 Note: {manifest['note']}")
    
    print("\nCollections:")
    for coll, count in manifest['collections'].items():
        print(f"  - {coll}: {count} documents")
    
    print("=" * 60)
    return manifest


def create_pre_restore_backup():
    """Create automatic backup before restoration"""
    print("\n🔄 Creating pre-restoration backup...")
    backup_script = Path(__file__).parent / 'backup_database.py'
    
    result = subprocess.run(
        [sys.executable, str(backup_script), '--manual', '--note', 'Pre-restoration backup'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Failed to create pre-restoration backup")
        print(result.stderr)
        return False
    
    print("✓ Pre-restoration backup created")
    return True


def restore_with_mongorestore(backup_dir):
    """Restore using mongorestore if available"""
    # Check if mongorestore is available
    try:
        subprocess.run(['mongorestore', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    
    print("Using mongorestore for restoration...")
    dump_dir = backup_dir / 'dump'
    
    if not dump_dir.exists():
        print(f"❌ Dump directory not found: {dump_dir}")
        return False
    
    cmd = [
        'mongorestore',
        '--uri', MONGODB_URI,
        '--drop',  # Drop existing collections before restore
        '--gzip',
        str(dump_dir)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✓ mongorestore completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ mongorestore failed: {e}")
        print(f"stderr: {e.stderr}")
        return False


def restore_with_pymongo(client, backup_dir):
    """Fallback: Restore using pymongo"""
    print("Using pymongo for restoration...")
    db = client[DB_NAME]
    dump_dir = backup_dir / 'dump' / DB_NAME
    
    if not dump_dir.exists():
        print(f"❌ Dump directory not found: {dump_dir}")
        return False
    
    for json_file in dump_dir.glob('*.json.gz'):
        coll_name = json_file.stem.replace('.json', '')
        print(f"  Restoring {coll_name}...", end=' ')
        
        # Drop existing collection
        db[coll_name].drop()
        
        # Read and restore documents
        with gzip.open(json_file, 'rt', encoding='utf-8') as f:
            documents = json.load(f)
        
        if documents:
            # Convert string IDs back to ObjectId if needed
            from bson import ObjectId
            for doc in documents:
                if '_id' in doc and isinstance(doc['_id'], str):
                    try:
                        doc['_id'] = ObjectId(doc['_id'])
                    except:
                        pass  # Keep as string if conversion fails
            
            db[coll_name].insert_many(documents)
        
        print(f"✓ ({len(documents)} documents)")
    
    return True


def stop_backend_service():
    """Stop backend service to prevent writes during restore"""
    print("\n🛑 Stopping backend service...")
    try:
        subprocess.run(['sudo', 'systemctl', 'stop', 'surg-db-backend'], check=True)
        print("✓ Backend service stopped")
        return True
    except subprocess.CalledProcessError:
        print("⚠️  Could not stop backend service (may not be running)")
        return False


def start_backend_service():
    """Start backend service after restore"""
    print("\n▶️  Starting backend service...")
    try:
        subprocess.run(['sudo', 'systemctl', 'start', 'surg-db-backend'], check=True)
        print("✓ Backend service started")
        return True
    except subprocess.CalledProcessError:
        print("❌ Could not start backend service")
        return False


def main():
    parser = argparse.ArgumentParser(description='Restore MongoDB database from backup')
    parser.add_argument('backup_dir', nargs='?', help='Backup directory to restore')
    parser.add_argument('--confirm', action='store_true', 
                       help='Actually perform the restoration (required for safety)')
    args = parser.parse_args()
    
    print("=" * 60)
    print("MongoDB Restoration System")
    print("=" * 60)
    
    # If no backup directory specified, list available backups
    if not args.backup_dir:
        print("\n📋 Available backups:\n")
        backups = list_available_backups()
        
        if not backups:
            print("No backups found.")
            return 0
        
        for backup_dir, manifest in backups:
            backup_type = manifest.get('backup_type', 'unknown')
            timestamp = manifest.get('timestamp', 'unknown')
            docs = manifest.get('total_documents', 0)
            size_mb = manifest.get('backup_size_mb', 0)
            note = manifest.get('note', '')
            
            print(f"📁 {backup_dir.name}")
            print(f"   {timestamp} | {backup_type} | {docs} docs | {size_mb:.1f} MB")
            if note:
                print(f"   Note: {note}")
            print()
        
        print("\nTo restore a backup:")
        print(f"  python {Path(__file__).name} <backup_dir>")
        return 0
    
    # Parse backup directory
    backup_dir = Path(args.backup_dir)
    if not backup_dir.is_absolute():
        backup_dir = BACKUP_BASE_DIR / backup_dir
    
    if not backup_dir.exists():
        print(f"❌ Backup directory not found: {backup_dir}")
        return 1
    
    # Show backup details
    manifest = show_backup_details(backup_dir)
    if not manifest:
        return 1
    
    # If --confirm not provided, show warning and exit
    if not args.confirm:
        print("\n⚠️  WARNING: This will OVERWRITE your current database!")
        print("⚠️  All current data will be LOST!")
        print("\nTo proceed with restoration, add --confirm flag:")
        print(f"  python {Path(__file__).name} {backup_dir} --confirm")
        return 0
    
    # Confirm restoration
    print("\n" + "!" * 60)
    print("⚠️  FINAL WARNING: This will ERASE your current database!")
    print("!" * 60)
    response = input("\nType 'RESTORE' to proceed: ")
    if response != 'RESTORE':
        print("❌ Restoration cancelled")
        return 0
    
    # Create pre-restoration backup
    if not create_pre_restore_backup():
        response = input("\n⚠️  Pre-restoration backup failed. Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("❌ Restoration cancelled")
            return 1
    
    # Stop backend service
    service_was_running = stop_backend_service()
    
    # Connect to MongoDB
    print("\n🔌 Connecting to MongoDB...")
    try:
        client = MongoClient(MONGODB_URI)
        client.admin.command('ping')
        print(f"✓ Connected to {DB_NAME}")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        if service_was_running:
            start_backend_service()
        return 1
    
    # Perform restoration
    print("\n🔄 Starting restoration...")
    print("⚠️  This will drop all existing collections!")
    
    success = restore_with_mongorestore(backup_dir)
    if not success:
        print("Falling back to pymongo restoration...")
        success = restore_with_pymongo(client, backup_dir)
    
    if not success:
        print("\n❌ Restoration failed!")
        if service_was_running:
            start_backend_service()
        return 1
    
    # Restart backend service
    if service_was_running:
        start_backend_service()
    
    print("\n" + "=" * 60)
    print("✅ Database restored successfully!")
    print(f"📁 From: {backup_dir}")
    print(f"📊 Collections: {len(manifest['collections'])}")
    print(f"📄 Documents: {manifest['total_documents']}")
    print("=" * 60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
