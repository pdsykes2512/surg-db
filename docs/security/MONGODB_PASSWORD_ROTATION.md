# MongoDB Password Rotation Guide

## Overview

This guide explains how to securely rotate the MongoDB database password using the automated script.

## Why Rotate Passwords?

Regular password rotation is a security best practice that:
- Reduces risk of compromised credentials
- Limits damage from credential exposure
- Meets compliance requirements (GDPR, NHS Data Security Toolkit)
- Should be done quarterly or after suspected compromise

## Automated Script

**Location:** `execution/active/rotate_mongodb_password.py`

### Features

- ✅ Generates cryptographically secure 32-character passwords
- ✅ Backs up `.env` file before making changes
- ✅ Updates MongoDB user password
- ✅ Updates `.env` file with new credentials
- ✅ Restarts backend service automatically
- ✅ Verifies new password works
- ✅ Dry-run mode for testing

### Usage

#### Basic Usage (Auto-Generate Password)

```bash
# From project root
cd /root/impact

# Run script (will generate random strong password)
python3 execution/active/rotate_mongodb_password.py
```

#### Dry Run (Test Without Changes)

```bash
# See what would happen without making changes
python3 execution/active/rotate_mongodb_password.py --dry-run
```

#### Use Specific Password

```bash
# Provide your own password (must be strong!)
python3 execution/active/rotate_mongodb_password.py --password "YourStrongPassword123!@#"
```

### What the Script Does

1. **Reads current configuration** from `.env` file
2. **Generates new password** (32 chars: letters, digits, special chars)
3. **Backs up `.env`** to `.tmp/.env.backup_TIMESTAMP`
4. **Updates MongoDB** user password via admin connection
5. **Updates `.env`** file with new connection URI
6. **Restarts backend** service
7. **Verifies** new password works

### Output Example

```
======================================================================
MongoDB Password Rotation Script
======================================================================

📋 Step 1: Reading current configuration...
   Current host: impact.vps:27017
   Current user: admin
   Current database: surgdb
   Auth source: admin

🔑 Step 2: Generating new password...
   Generated strong password (32 characters)

💾 Step 3: Backing up .env file...
   Backup created: /root/impact/.tmp/.env.backup_20251228_233045

🔐 Step 4: Updating MongoDB password...
✅ MongoDB password updated for user 'admin'
✅ New password verified - connection successful

📝 Step 5: Updating .env file...
   .env file updated with new credentials

🔄 Step 6: Restarting backend service...
🔄 Restarting backend service...
✅ Backend service restarted
✅ Backend service is active

======================================================================
✅ PASSWORD ROTATION COMPLETE
======================================================================

📌 Summary:
   - Old .env backed up to: /root/impact/.tmp/.env.backup_20251228_233045
   - MongoDB password updated
   - .env file updated
   - Backend service restarted

🔒 New password: aB3$xY9#mNp2@qR7!vW5&kL8^sT4%hJ1

⚠️  IMPORTANT:
   - Store this password securely (password manager recommended)
   - Delete this terminal output after saving password
   - Test application login to verify everything works
   - Keep backup file secure: /root/impact/.tmp/.env.backup_20251228_233045
```

## Post-Rotation Checklist

After rotating the password, verify:

1. **Backend service is running**
   ```bash
   sudo systemctl status surg-db-backend
   ```

2. **Application login works**
   - Open browser: http://impact.vps:3000
   - Log in with your user credentials
   - Navigate to a few pages to ensure database connectivity

3. **API health check passes**
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status":"healthy"}
   ```

4. **Store new password securely**
   - Save in password manager (e.g., 1Password, Bitwarden, LastPass)
   - **Do not email or share via unencrypted channels**
   - **Do not commit to version control**

5. **Clear terminal history** (password was displayed)
   ```bash
   history -c
   ```

6. **Secure backup file**
   ```bash
   # The backup .env is stored in .tmp/ directory
   # Ensure only root can read it
   chmod 600 /root/impact/.tmp/.env.backup_*
   ```

## Troubleshooting

### Error: "Connection failed"

**Cause:** Cannot connect to MongoDB with current credentials

**Solutions:**
1. Check MongoDB is running: `sudo systemctl status mongod`
2. Verify network connectivity: `ping impact.vps`
3. Check firewall rules allow port 27017
4. Verify current password in `.env` is correct

### Error: "Operation failed: not authorized"

**Cause:** Current user lacks permission to change passwords

**Solutions:**
1. Ensure connecting as `admin` user
2. Verify admin has `changePassword` privilege
3. Check MongoDB version supports `updateUser` command

### Error: "Failed to restart service"

**Cause:** systemd service failed to restart

**Solutions:**
1. Check service logs: `sudo journalctl -u surg-db-backend -n 50`
2. Verify new password in `.env` is correct
3. Try manual restart: `sudo systemctl restart surg-db-backend`
4. If needed, restore backup:
   ```bash
   cp /root/impact/.tmp/.env.backup_YYYYMMDD_HHMMSS /root/impact/.env
   sudo systemctl restart surg-db-backend
   ```

### Password Changed But .env Not Updated

**CRITICAL:** If MongoDB password changed but `.env` update failed:

```bash
# 1. Find the backup .env file
ls -lt /root/impact/.tmp/.env.backup_*

# 2. Restore from most recent backup
cp /root/impact/.tmp/.env.backup_YYYYMMDD_HHMMSS /root/impact/.env

# 3. Manually change MongoDB password back using mongosh
mongosh mongodb://admin:NEW_PASSWORD@impact.vps:27017/admin
> db.changeUserPassword("admin", "OLD_PASSWORD_FROM_BACKUP")

# 4. Restart backend
sudo systemctl restart surg-db-backend
```

## Security Recommendations

### Rotation Schedule

- **Quarterly:** Rotate every 3 months as routine maintenance
- **Immediate:** Rotate immediately if:
  - Credential exposure suspected
  - Team member with access leaves
  - Security audit recommendation
  - After security incident

### Password Requirements

If providing custom password with `--password`, ensure:
- Minimum 24 characters (32+ recommended)
- Mix of uppercase, lowercase, digits, special chars
- No dictionary words or common patterns
- Not reused from other systems
- Generated by password manager

### Access Control

Restrict script execution:
```bash
# Only root should run this
chmod 700 /root/impact/execution/active/rotate_mongodb_password.py

# Ensure .env is secure
chmod 600 /root/impact/.env
```

## Integration with Backup Strategy

When rotating passwords:

1. **Before rotation:** Create manual database backup
   ```bash
   python3 execution/active/backup_database.py --manual --note "Pre-password-rotation backup"
   ```

2. **Run rotation script**

3. **After rotation:** Verify backup encryption keys still work
   - Backup encryption uses separate keys in `/root/.backup-encryption-key`
   - These are NOT affected by MongoDB password rotation

## Automated Rotation (Optional)

For automated quarterly rotation, create a cron job:

```bash
# Edit root crontab
sudo crontab -e

# Add line to rotate every 90 days at 2 AM
# Logs output to /root/.tmp/password-rotation.log
0 2 1 */3 * /usr/bin/python3 /root/impact/execution/active/rotate_mongodb_password.py >> /root/.tmp/password-rotation.log 2>&1
```

**⚠️ Warning:** Automated rotation means:
- New password won't be immediately known
- Check logs regularly to retrieve new password
- Store new password in password manager ASAP
- Consider email notification when rotation completes

## Related Documentation

- [Security Enhancements Summary](../implementation/SECURITY_ENHANCEMENTS_SUMMARY.md)
- [Encryption Compliance](../implementation/ENCRYPTION_COMPLIANCE.md)
- [Backup System](../../execution/active/backup_database.py)

## Support

For issues or questions:
- Check logs: `sudo journalctl -u surg-db-backend -n 100`
- Review RECENT_CHANGES.md for context
- Test connection: `mongosh "mongodb://admin:PASSWORD@impact.vps:27017/admin"`
