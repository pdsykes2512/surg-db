# Database Backup System

## Goal
Implement automated MongoDB backups with retention policies, verification, and easy restoration to prevent data loss and enable disaster recovery.

## Inputs
- MongoDB connection details from `.env`
- Backup schedule (daily automatic, on-demand manual)
- Retention policy (keep last 30 days, weekly for 3 months, monthly for 1 year)

## Tools/Scripts
- `execution/backup_database.py` - Creates MongoDB dumps with compression
- `execution/restore_database.py` - Restores from backup files
- `execution/verify_backup.py` - Validates backup integrity
- `execution/cleanup_old_backups.py` - Applies retention policy
- Cron job for automatic daily backups at 2 AM

## Outputs
- Compressed backup files in `~/.tmp/backups/` (not in git)
- Backup manifest file with metadata (timestamp, size, collections, documents)
- Verification report confirming backup integrity
- Restoration log when backups are restored

## Process

### 1. Backup Creation
```bash
python execution/backup_database.py [--manual]
```
- Connects to MongoDB using credentials from `.env`
- Creates timestamped backup directory: `~/.tmp/backups/YYYY-MM-DD_HH-MM-SS/`
- Dumps all collections with `mongodump` (or pymongo if tools unavailable)
- Compresses backup with gzip
- Generates manifest file with:
  - Timestamp
  - Database name
  - Collections backed up
  - Document counts per collection
  - Backup size
  - Backup type (automatic/manual)
- Stores in `~/.tmp/backups/YYYY-MM-DD_HH-MM-SS/`

### 2. Backup Verification
```bash
python execution/verify_backup.py <backup_dir>
```
- Checks backup directory exists
- Validates all expected files present
- Verifies manifest matches actual backup contents
- Checks compression integrity
- Outputs verification report

### 3. Backup Restoration
```bash
python execution/restore_database.py <backup_dir> [--confirm]
```
- Lists available backups if no directory specified
- Shows backup manifest for confirmation
- Requires `--confirm` flag to proceed
- Stops backend service (prevents writes during restore)
- Creates pre-restoration backup automatically
- Decompresses backup files
- Restores to MongoDB using `mongorestore` (or pymongo)
- Restarts backend service
- Outputs restoration log

### 4. Backup Cleanup (Retention Policy)
```bash
python execution/cleanup_old_backups.py
```
Applies retention policy:
- **Daily backups**: Keep last 30 days
- **Weekly backups**: Keep one per week for 3 months (marked as weekly on Sundays)
- **Monthly backups**: Keep one per month for 1 year (marked as monthly on 1st)
- **Manual backups**: Never auto-delete (user must delete manually)

Runs automatically after each backup creation.

### 5. Automatic Scheduling
Create cron job:
```bash
# Daily backup at 2 AM
0 2 * * * cd /root/surg-db && /usr/bin/python3 execution/backup_database.py >> ~/.tmp/backup.log 2>&1
```

## Edge Cases

### MongoDB Tools Not Installed
- Falls back to pymongo-based backup
- Exports each collection to JSON
- Slower but reliable
- Install tools with: `sudo apt-get install mongodb-database-tools`

### Disk Space Issues
- Check available space before backup
- If < 10GB free, send warning but proceed
- If < 5GB free, abort and send alert
- Cleanup old backups to free space

### Backup Corruption
- Verification catches corruption immediately
- Re-run backup if verification fails
- Keep previous successful backup

### Restoration Failures
- Pre-restoration backup protects against restore failures
- Can rollback to pre-restoration state
- Detailed error logging for troubleshooting

### Large Database Size
- Use compression to reduce storage (typically 80-90% reduction)
- Consider incremental backups if database > 10GB
- Stream data to avoid memory issues

## Security Considerations
- Backup files contain sensitive patient data
- Store in `~/.tmp/backups/` (not in git, in .gitignore)
- Set appropriate file permissions (600 - owner only)
- Consider encrypting backups for production
- Never commit backups to version control

## Testing
```bash
# Create test backup
python execution/backup_database.py --manual

# Verify backup
python execution/verify_backup.py ~/.tmp/backups/<latest>

# Test restoration (on test instance only!)
python execution/restore_database.py ~/.tmp/backups/<latest> --confirm

# Test cleanup
python execution/cleanup_old_backups.py --dry-run
```

## Monitoring
- Check `~/.tmp/backup.log` for automatic backup results
- Verify backups exist: `ls -lh ~/.tmp/backups/`
- Check backup sizes are reasonable (should be consistent)
- Test restoration quarterly on test environment

## Manual Backup (Before Major Changes)
Before database migrations, schema changes, or bulk data operations:
```bash
python execution/backup_database.py --manual --note "Before migration X"
```
Manual backups are marked and never auto-deleted.

## Success Criteria
- Daily automatic backups running
- Retention policy working (30 days visible)
- Verification confirms integrity
- Restoration tested and documented
- Backup size reasonable and consistent
- Old backups cleaned up automatically
