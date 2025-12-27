# Backup System Quick Reference

## Daily Operations

### Check Backup Status
```bash
# List all backups
python3 /root/surg-db/execution/restore_database.py

# Check backup log
tail -20 ~/.tmp/backup.log

# Check disk usage
du -sh ~/.tmp/backups/
```

### Manual Backup (Before Risky Operations)
```bash
# Before migrations, schema changes, bulk operations
cd /root/surg-db
python3 execution/backup_database.py --manual --note "Before migration X"
```

### View Backup Details
```bash
python3 /root/surg-db/execution/restore_database.py ~/.tmp/backups/<backup_name>
```

## Disaster Recovery

### Restore from Backup
⚠️ **WARNING:** This will ERASE current database!

```bash
# 1. List available backups
python3 /root/surg-db/execution/restore_database.py

# 2. View backup details
python3 /root/surg-db/execution/restore_database.py ~/.tmp/backups/<backup_name>

# 3. Restore (requires confirmation)
python3 /root/surg-db/execution/restore_database.py ~/.tmp/backups/<backup_name> --confirm
# You'll need to type "RESTORE" to confirm
```

**The restore process will:**
1. Create automatic pre-restoration backup
2. Stop backend service
3. Drop all existing collections
4. Restore from backup
5. Restart backend service

## Maintenance

### Test Cleanup (Dry Run)
```bash
python3 /root/surg-db/execution/cleanup_old_backups.py --dry-run
```

### Manual Cleanup
```bash
# Remove old backups (follows retention policy)
python3 /root/surg-db/execution/cleanup_old_backups.py

# Manually delete specific backup
rm -rf ~/.tmp/backups/<backup_name>
```

### Check Cron Job
```bash
# View current cron jobs
crontab -l

# Edit cron jobs
crontab -e
```

## Backup Details

### Automatic Schedule
- **Time:** 2:00 AM daily
- **Type:** automatic
- **Log:** `~/.tmp/backup.log`
- **Retention:** 30 days (then moves to weekly)

### Retention Policy
- **Daily:** Last 30 days (all backups)
- **Weekly:** 3 months (Sundays only)
- **Monthly:** 1 year (1st of month only)
- **Manual:** Never deleted automatically

### Current Status
```bash
# Current database stats
Database: surgdb
Collections: 11
Documents: ~67,367
Backup size: ~2.2 MB compressed
```

## Troubleshooting

### Backup Failed
1. Check disk space: `df -h ~/.tmp`
2. Check MongoDB connection: `mongosh $MONGODB_URI --eval "db.adminCommand('ping')"`
3. Check backup log: `tail -50 ~/.tmp/backup.log`

### Restoration Failed
1. Pre-restoration backup was created automatically
2. Check error in output
3. Backend service may need manual restart: `sudo systemctl restart surg-db-backend`

### Low Disk Space
```bash
# Check space
df -h ~/.tmp

# Free space by removing old backups
python3 /root/surg-db/execution/cleanup_old_backups.py

# Or manually remove oldest automatic backups
ls -lt ~/.tmp/backups/ | tail -10
```

## Best Practices

1. **Before migrations:** Always create manual backup with descriptive note
2. **Test restores:** Quarterly on test environment
3. **Monitor logs:** Check `~/.tmp/backup.log` weekly
4. **Verify backups:** Occasionally check backup sizes are reasonable
5. **Manual backups:** Use for important milestones (never auto-deleted)

## Emergency Contacts

If backup system fails and data is lost:
1. Check `~/.tmp/backups/` for any available backups
2. Look for pre-restoration backups (created automatically before restores)
3. Contact system administrator

## Files

- **Directive:** `directives/database_backup_system.md`
- **Backup script:** `execution/backup_database.py`
- **Restore script:** `execution/restore_database.py`
- **Cleanup script:** `execution/cleanup_old_backups.py`
- **Backup location:** `~/.tmp/backups/`
- **Backup log:** `~/.tmp/backup.log`
- **Cron job:** `crontab -l`
