#!/usr/bin/env python3
"""
Backup Cleanup Script

Applies retention policy to automatically delete old backups.

Retention Policy:
- Daily backups: Keep last 30 days
- Weekly backups: Keep one per week for 3 months (Sundays)
- Monthly backups: Keep one per month for 1 year (1st of month)
- Manual backups: Never auto-delete

Usage:
    python cleanup_old_backups.py [--dry-run]
"""

import os
import sys
import json
import shutil
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

BACKUP_BASE_DIR = Path.home() / '.tmp' / 'backups'


def parse_backup_timestamp(backup_name):
    """Parse backup directory name to datetime"""
    try:
        return datetime.strptime(backup_name, '%Y-%m-%d_%H-%M-%S')
    except ValueError:
        return None


def get_all_backups():
    """Get all backups with their metadata"""
    if not BACKUP_BASE_DIR.exists():
        return []
    
    backups = []
    for backup_dir in BACKUP_BASE_DIR.iterdir():
        if not backup_dir.is_dir():
            continue
        
        manifest_file = backup_dir / 'manifest.json'
        if not manifest_file.exists():
            continue
        
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
        
        timestamp = parse_backup_timestamp(backup_dir.name)
        if not timestamp:
            continue
        
        backups.append({
            'dir': backup_dir,
            'name': backup_dir.name,
            'timestamp': timestamp,
            'type': manifest.get('backup_type', 'automatic'),
            'size_mb': manifest.get('backup_size_mb', 0),
            'manifest': manifest
        })
    
    return sorted(backups, key=lambda x: x['timestamp'], reverse=True)


def calculate_backup_size(backup):
    """Calculate size of backup directory"""
    total_size = 0
    for path in backup['dir'].rglob('*'):
        if path.is_file():
            total_size += path.stat().st_size
    return total_size / (1024**2)  # MB


def apply_retention_policy(backups, dry_run=False):
    """Apply retention policy and return backups to delete"""
    now = datetime.now()
    
    # Organize backups by date
    daily_cutoff = now - timedelta(days=30)
    weekly_cutoff = now - timedelta(days=90)  # 3 months
    monthly_cutoff = now - timedelta(days=365)  # 1 year
    
    to_keep = set()
    to_delete = []
    
    # Track weekly and monthly backups
    weekly_backups = defaultdict(list)  # week -> backups
    monthly_backups = defaultdict(list)  # month -> backups
    
    for backup in backups:
        backup_ts = backup['timestamp']
        
        # Always keep manual backups
        if backup['type'] == 'manual':
            to_keep.add(backup['name'])
            continue
        
        # Keep all backups within 30 days
        if backup_ts >= daily_cutoff:
            to_keep.add(backup['name'])
            continue
        
        # For older backups, organize by week/month
        week_key = backup_ts.strftime('%Y-W%U')
        month_key = backup_ts.strftime('%Y-%m')
        
        weekly_backups[week_key].append(backup)
        monthly_backups[month_key].append(backup)
    
    # Keep one backup per week for 3 months (prefer Sundays)
    for week_key, week_backups in weekly_backups.items():
        if not week_backups:
            continue
        
        # Check if any backup is within weekly retention
        if any(b['timestamp'] >= weekly_cutoff for b in week_backups):
            # Prefer Sunday backups (weekday == 6)
            sunday_backups = [b for b in week_backups if b['timestamp'].weekday() == 6]
            if sunday_backups:
                to_keep.add(sunday_backups[0]['name'])
            else:
                # Keep the first backup of the week
                to_keep.add(week_backups[0]['name'])
    
    # Keep one backup per month for 1 year (prefer 1st of month)
    for month_key, month_backups in monthly_backups.items():
        if not month_backups:
            continue
        
        # Check if any backup is within monthly retention
        if any(b['timestamp'] >= monthly_cutoff for b in month_backups):
            # Prefer 1st of month
            first_day_backups = [b for b in month_backups if b['timestamp'].day == 1]
            if first_day_backups:
                to_keep.add(first_day_backups[0]['name'])
            else:
                # Keep the first backup of the month
                to_keep.add(month_backups[0]['name'])
    
    # Identify backups to delete
    for backup in backups:
        if backup['name'] not in to_keep:
            to_delete.append(backup)
    
    return to_delete


def main():
    parser = argparse.ArgumentParser(description='Cleanup old backups')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be deleted without actually deleting')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Backup Cleanup (Retention Policy)")
    print("=" * 60)
    
    if not BACKUP_BASE_DIR.exists():
        print("No backups directory found.")
        return 0
    
    # Get all backups
    print("\n📊 Analyzing backups...")
    backups = get_all_backups()
    
    if not backups:
        print("No backups found.")
        return 0
    
    print(f"Found {len(backups)} backup(s)")
    
    # Calculate total size
    total_size = sum(b['size_mb'] for b in backups)
    print(f"Total size: {total_size:.1f} MB")
    
    # Apply retention policy
    print("\n🔍 Applying retention policy...")
    to_delete = apply_retention_policy(backups, dry_run=args.dry_run)
    
    if not to_delete:
        print("✓ No backups to delete (all within retention policy)")
        return 0
    
    print(f"\n📋 {len(to_delete)} backup(s) to delete:")
    total_freed_mb = 0
    
    for backup in to_delete:
        print(f"  ❌ {backup['name']}")
        print(f"     {backup['timestamp'].strftime('%Y-%m-%d %H:%M')} | "
              f"{backup['type']} | {backup['size_mb']:.1f} MB")
        total_freed_mb += backup['size_mb']
    
    print(f"\n💾 Space to free: {total_freed_mb:.1f} MB")
    
    if args.dry_run:
        print("\n🔍 DRY RUN - No backups were deleted")
        return 0
    
    # Delete backups
    print("\n🗑️  Deleting old backups...")
    deleted_count = 0
    
    for backup in to_delete:
        try:
            shutil.rmtree(backup['dir'])
            print(f"  ✓ Deleted {backup['name']}")
            deleted_count += 1
        except Exception as e:
            print(f"  ❌ Failed to delete {backup['name']}: {e}")
    
    print("\n" + "=" * 60)
    print(f"✅ Cleanup complete!")
    print(f"🗑️  Deleted: {deleted_count} backup(s)")
    print(f"💾 Freed: {total_freed_mb:.1f} MB")
    print(f"📁 Remaining: {len(backups) - deleted_count} backup(s)")
    print("=" * 60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
