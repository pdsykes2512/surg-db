#!/usr/bin/env python3
"""
Database Backup Script

Creates timestamped MongoDB backups with compression and verification.
Supports both mongodump (if available) and pymongo fallback.

Usage:
    python backup_database.py [--manual] [--note "Description"]
"""

import os
import sys
import json
import gzip
import shutil
import argparse
from datetime import datetime
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('MONGODB_DB_NAME', 'surgdb')
BACKUP_BASE_DIR = Path.home() / '.tmp' / 'backups'


def check_disk_space():
    """Check available disk space"""
    stat = shutil.disk_usage(BACKUP_BASE_DIR.parent)
    free_gb = stat.free / (1024**3)
    
    if free_gb < 5:
        print(f"❌ ERROR: Only {free_gb:.1f}GB free. Need at least 5GB. Aborting.")
        sys.exit(1)
    elif free_gb < 10:
        print(f"⚠️  WARNING: Only {free_gb:.1f}GB free. Consider cleanup.")
    else:
        print(f"✓ Disk space OK: {free_gb:.1f}GB available")
    
    return free_gb


def get_database_stats(client):
    """Get database statistics for manifest"""
    db = client[DB_NAME]
    collections = db.list_collection_names()
    
    stats = {
        'database': DB_NAME,
        'collections': {},
        'total_documents': 0
    }
    
    for coll_name in collections:
        count = db[coll_name].count_documents({})
        stats['collections'][coll_name] = count
        stats['total_documents'] += count
    
    return stats


def backup_with_mongodump(backup_dir):
    """Backup using mongodump if available"""
    import subprocess
    
    # Check if mongodump is available
    try:
        subprocess.run(['mongodump', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    
    print("Using mongodump for backup...")
    dump_dir = backup_dir / 'dump'
    
    cmd = [
        'mongodump',
        '--uri', MONGODB_URI,
        '--out', str(dump_dir),
        '--gzip'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✓ mongodump completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ mongodump failed: {e}")
        print(f"stderr: {e.stderr}")
        return False


def backup_with_pymongo(client, backup_dir):
    """Fallback: Backup using pymongo (slower but reliable)"""
    print("Using pymongo for backup (mongodump not available)...")
    db = client[DB_NAME]
    collections = db.list_collection_names()
    
    dump_dir = backup_dir / 'dump' / DB_NAME
    dump_dir.mkdir(parents=True, exist_ok=True)
    
    for coll_name in collections:
        print(f"  Backing up {coll_name}...", end=' ')
        collection = db[coll_name]
        documents = list(collection.find())
        
        # Convert ObjectId to string for JSON serialization
        for doc in documents:
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
        
        # Write compressed JSON
        output_file = dump_dir / f"{coll_name}.json.gz"
        with gzip.open(output_file, 'wt', encoding='utf-8') as f:
            json.dump(documents, f, default=str, indent=2)
        
        print(f"✓ ({len(documents)} documents)")
    
    return True


def create_manifest(backup_dir, stats, backup_type, note=None):
    """Create backup manifest file"""
    manifest = {
        'timestamp': datetime.now().isoformat(),
        'backup_type': backup_type,
        'database': stats['database'],
        'collections': stats['collections'],
        'total_documents': stats['total_documents'],
        'backup_dir': str(backup_dir),
        'note': note
    }
    
    manifest_file = backup_dir / 'manifest.json'
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    return manifest


def calculate_backup_size(backup_dir):
    """Calculate total size of backup"""
    total_size = 0
    for path in backup_dir.rglob('*'):
        if path.is_file():
            total_size += path.stat().st_size
    return total_size


def main():
    parser = argparse.ArgumentParser(description='Backup MongoDB database')
    parser.add_argument('--manual', action='store_true', 
                       help='Mark as manual backup (never auto-deleted)')
    parser.add_argument('--note', type=str, 
                       help='Add note to backup manifest')
    args = parser.parse_args()
    
    print("=" * 60)
    print("MongoDB Backup System")
    print("=" * 60)
    
    # Create backup directory
    BACKUP_BASE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check disk space
    check_disk_space()
    
    # Create timestamped backup directory
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    backup_dir = BACKUP_BASE_DIR / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📦 Backup directory: {backup_dir}")
    
    # Connect to MongoDB
    print(f"\n🔌 Connecting to MongoDB...")
    try:
        client = MongoClient(MONGODB_URI)
        client.admin.command('ping')
        print(f"✓ Connected to {DB_NAME}")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        sys.exit(1)
    
    # Get database stats
    print("\n📊 Gathering database statistics...")
    stats = get_database_stats(client)
    print(f"✓ Database: {stats['database']}")
    print(f"✓ Collections: {len(stats['collections'])}")
    print(f"✓ Total documents: {stats['total_documents']}")
    
    # Perform backup
    print("\n💾 Starting backup...")
    backup_type = 'manual' if args.manual else 'automatic'
    
    success = backup_with_mongodump(backup_dir)
    if not success:
        print("Falling back to pymongo backup...")
        success = backup_with_pymongo(client, backup_dir)
    
    if not success:
        print("❌ Backup failed")
        sys.exit(1)
    
    # Create manifest
    print("\n📝 Creating manifest...")
    manifest = create_manifest(backup_dir, stats, backup_type, args.note)
    
    # Calculate backup size
    backup_size = calculate_backup_size(backup_dir)
    backup_size_mb = backup_size / (1024**2)
    print(f"✓ Backup size: {backup_size_mb:.1f} MB")
    
    # Update manifest with size
    manifest['backup_size_bytes'] = backup_size
    manifest['backup_size_mb'] = backup_size_mb
    with open(backup_dir / 'manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print("\n" + "=" * 60)
    print(f"✅ Backup completed successfully!")
    print(f"📁 Location: {backup_dir}")
    print(f"📊 Collections: {len(stats['collections'])}")
    print(f"📄 Documents: {stats['total_documents']}")
    print(f"💾 Size: {backup_size_mb:.1f} MB")
    print(f"🏷️  Type: {backup_type}")
    if args.note:
        print(f"📝 Note: {args.note}")
    print("=" * 60)
    
    # Run cleanup (applies retention policy)
    print("\n🧹 Running cleanup (retention policy)...")
    cleanup_script = Path(__file__).parent / 'cleanup_old_backups.py'
    if cleanup_script.exists():
        import subprocess
        subprocess.run([sys.executable, str(cleanup_script)])
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
