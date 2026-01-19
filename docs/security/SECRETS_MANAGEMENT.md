# Secrets Management

## Overview

IMPACT uses a two-tier environment variable system to separate sensitive credentials from non-secret configuration. This prevents accidental commits of secrets to version control while maintaining ease of configuration management.

## Architecture

### Two Environment Files

1. **`/etc/impact/secrets.env`** - Sensitive credentials (NOT in git)
   - Location: System-level (`/etc/impact/`)
   - Permissions: `600` (root read/write only)
   - Contains: Passwords, API tokens, JWT secrets
   - Backed up to: `/etc/impact/backups/`

2. **`/root/impact/.env`** - Non-secret configuration (CAN be in git)
   - Location: Project directory
   - Permissions: `644` (world-readable)
   - Contains: Hostnames, ports, usernames, database names
   - Version controlled: Safe to commit

### Load Order

systemd services load environment files in this order:
```ini
EnvironmentFile=/etc/impact/secrets.env  # Loaded first
EnvironmentFile=/root/impact/.env         # Loaded second (can override)
```

Later files can override earlier values if needed for local development.

## Secrets File Contents

**`/etc/impact/secrets.env`** contains:

```bash
# MongoDB Database Credentials
MONGODB_URI=mongodb://admin:STRONG_PASSWORD_HERE@impact.vps:27017/surgdb?authSource=admin

# GitHub API Credentials
GITHUB_TOKEN=ghp_YOUR_GITHUB_PAT_HERE

# JWT Authentication Secret (HS256)
SECRET_KEY=YOUR_LONG_RANDOM_SECRET_HERE
```

## Configuration File Contents

**`/root/impact/.env`** contains:

```bash
# MongoDB Configuration (non-secret)
MONGODB_DB_NAME=surgdb

# GitHub Configuration (non-secret)
GITHUB_USERNAME=pdsykes2512

# Backend API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

## Setup on New Environments

When deploying to a new server:

```bash
# 1. Create secrets directory
sudo mkdir -p /etc/impact
sudo chmod 700 /etc/impact

# 2. Create secrets file
sudo touch /etc/impact/secrets.env
sudo chmod 600 /etc/impact/secrets.env

# 3. Add secrets to file
sudo nano /etc/impact/secrets.env
# (Add MONGODB_URI, GITHUB_TOKEN, SECRET_KEY)

# 4. Clone project repository
git clone https://github.com/YOUR_REPO/impact.git
cd impact

# 5. .env file already contains non-secret config (from git)

# 6. Start services
sudo systemctl start surg-db-backend
sudo systemctl start surg-db-frontend
```

## Password Rotation

The password rotation script automatically updates `/etc/impact/secrets.env`:

```bash
# Rotate MongoDB password
python3 execution/active/rotate_mongodb_password.py

# Or with specific password
python3 execution/active/rotate_mongodb_password.py --password "NewStrongPassword123!"
```

The script will:
1. Backup current secrets to `/etc/impact/backups/`
2. Update MongoDB user password
3. Update `/etc/impact/secrets.env` with new password
4. Restart backend service
5. Verify connection

## Security Best Practices

### File Permissions

Always maintain strict permissions:

```bash
# Secrets file - root only
sudo chmod 600 /etc/impact/secrets.env
sudo chown root:root /etc/impact/secrets.env

# Backup directory - root only
sudo chmod 700 /etc/impact/backups
sudo chown -R root:root /etc/impact/backups
```

### Backup Strategy

Secrets should be backed up separately:

```bash
# Create encrypted backup
sudo tar -czf - /etc/impact/secrets.env | \
  gpg --symmetric --cipher-algo AES256 > \
  ~/secrets-backup-$(date +%Y%m%d).tar.gz.gpg

# Restore from encrypted backup
gpg --decrypt secrets-backup-20250129.tar.gz.gpg | \
  sudo tar -xzf - -C /
```

### Version Control

**Never commit secrets to git:**

```bash
# .gitignore already excludes:
/etc/
*.env  # Generic .env files
!.env  # But ALLOWS project .env (which has no secrets)

# Verify .env has no secrets before committing
cat .env  # Should only show non-secret config
git add .env
git commit -m "Update API configuration"
```

### Rotating Secrets

**MongoDB Password:** Use automated script (see above)

**GitHub Token:**
```bash
# 1. Generate new token at github.com/settings/tokens
# 2. Update secrets file
sudo nano /etc/impact/secrets.env
# 3. Restart services
sudo systemctl restart surg-db-backend surg-db-frontend
```

**JWT Secret:**
```bash
# 1. Generate new secret
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# 2. Update secrets file
sudo nano /etc/impact/secrets.env

# 3. Restart backend (invalidates all current tokens)
sudo systemctl restart surg-db-backend

# 4. Users must re-login
```

## Troubleshooting

### Services won't start

```bash
# Check if secrets file exists and is readable
sudo ls -la /etc/impact/secrets.env

# Check if secrets file has valid syntax
sudo grep -E "^[A-Z_]+=.+" /etc/impact/secrets.env

# Check service logs
sudo journalctl -u surg-db-backend -n 50
```

### Secrets not loading

```bash
# Verify process has environment variables
PID=$(pgrep -f "uvicorn backend.app.main:app")
sudo cat /proc/$PID/environ | tr '\0' '\n' | grep -E "MONGODB_URI|SECRET_KEY"

# Should show secrets from /etc/impact/secrets.env
```

### Lost secrets file

```bash
# Restore from backup
ls -la /etc/impact/backups/

# Copy most recent backup
sudo cp /etc/impact/backups/secrets.env.backup_YYYYMMDD_HHMMSS \
       /etc/impact/secrets.env

# Restart services
sudo systemctl restart surg-db-backend surg-db-frontend
```

## Migration from Old System

If upgrading from the old `.env`-only system:

```bash
# 1. Backup current .env
cp .env .env.old

# 2. Create secrets directory
sudo mkdir -p /etc/impact
sudo chmod 700 /etc/impact

# 3. Extract secrets to new file
sudo grep -E "^(MONGODB_URI|GITHUB_TOKEN|SECRET_KEY)=" .env | \
  sudo tee /etc/impact/secrets.env
sudo chmod 600 /etc/impact/secrets.env

# 4. Remove secrets from .env
sed -i '/^MONGODB_URI=/d' .env
sed -i '/^GITHUB_TOKEN=/d' .env
sed -i '/^SECRET_KEY=/d' .env

# 5. Add header to .env
cat > .env.tmp << 'EOF'
# Environment variables - NON-SECRET configuration only
# IMPORTANT: Secrets are stored in /etc/impact/secrets.env (not in version control)
# This file contains only non-sensitive configuration values

EOF
cat .env >> .env.tmp
mv .env.tmp .env

# 6. Update systemd service files (see RECENT_CHANGES.md)

# 7. Restart services
sudo systemctl daemon-reload
sudo systemctl restart surg-db-backend surg-db-frontend
```

## Related Documentation

- [MongoDB Password Rotation](MONGODB_PASSWORD_ROTATION.md)
- [Security Enhancements Summary](../implementation/SECURITY_ENHANCEMENTS_SUMMARY.md)
- [Encryption Compliance](../implementation/ENCRYPTION_COMPLIANCE.md)

## Support

For issues with secrets management:
- Check RECENT_CHANGES.md for recent modifications
- Review systemd service files: `/etc/systemd/system/surg-db-*.service`
- Check service logs: `sudo journalctl -u surg-db-backend -n 100`
