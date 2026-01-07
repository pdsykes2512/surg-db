# Environment Setup Guide

This guide explains how to configure the IMPACT application environment variables and settings.

## Table of Contents
- [Quick Start](#quick-start)
- [Environment Files](#environment-files)
- [Configuration Variables](#configuration-variables)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)

## Quick Start

1. **Copy the template:**
   ```bash
   cp .env.example .env
   ```

2. **Generate secure keys:**
   ```bash
   # Generate SECRET_KEY
   python -c 'import secrets; print(secrets.token_urlsafe(32))'

   # Generate ENCRYPTION_KEY
   python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
   ```

3. **Edit `.env` file:**
   - Set `SECRET_KEY` to the generated value
   - Set `ENCRYPTION_KEY` to the generated value
   - Update `MONGODB_URI` if using remote MongoDB
   - Update `CORS_ORIGINS` with your frontend URL

4. **Start the application:**
   ```bash
   sudo systemctl restart impact-backend
   sudo systemctl restart impact-frontend
   ```

## Environment Files

The IMPACT application uses multiple environment files for configuration:

### 1. `.env` (Root Directory)
**Location:** `/root/impact/.env`
**Purpose:** Non-secret configuration that can be shared
**Loaded by:** Backend service (via systemd)

### 2. `secrets.env` (System Config)
**Location:** `/etc/impact/secrets.env`
**Purpose:** Secret values (passwords, API keys, tokens)
**Loaded by:** Backend service (loaded first, takes precedence)

**Note:** The backend service loads `secrets.env` first, then `.env`. This allows you to override non-secret values in `.env` while keeping secrets secure.

## Configuration Variables

### Required Variables

#### Database Configuration
```bash
MONGODB_URI=mongodb://username:password@host:port/database?authSource=admin
MONGODB_DB_NAME=impact
MONGODB_SYSTEM_DB_NAME=impact_system
```

- **MONGODB_URI:** Full MongoDB connection string with authentication
  - Format: `mongodb://[username:password@]host[:port][/database][?options]`
  - Must start with `mongodb://` or `mongodb+srv://`
  - Validated on startup

- **MONGODB_DB_NAME:** Clinical data database (patients, episodes, treatments)
- **MONGODB_SYSTEM_DB_NAME:** System database (users, clinicians, audit logs)

#### Security Configuration
```bash
SECRET_KEY=<generate-with-secrets-module>
ENCRYPTION_KEY=<generate-with-fernet>
```

- **SECRET_KEY:** JWT token signing key
  - **CRITICAL:** Must be changed from default
  - Minimum 32 characters (enforced)
  - Generate with: `python -c 'import secrets; print(secrets.token_urlsafe(32))'`
  - Validation: Startup fails if default key detected

- **ENCRYPTION_KEY:** Fernet key for encrypting sensitive data (NHS numbers, MRNs)
  - Generate with: `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`
  - **WARNING:** Losing this key means losing access to encrypted data

### Optional Variables

#### API Configuration
```bash
API_HOST=0.0.0.0
API_PORT=8000
API_TITLE=IMPACT API
API_VERSION=1.1.0
```

#### CORS Configuration
```bash
CORS_ORIGINS=http://localhost:3000,http://impact.vps:3000
CORS_ORIGIN_REGEX=http://192\.168\.(10|11)\.\d{1,3}:\d+
```

- **CORS_ORIGINS:** Comma-separated list of allowed frontend URLs
- **CORS_ORIGIN_REGEX:** Regex pattern for dynamic origins (e.g., network ranges)

#### Environment Type
```bash
ENVIRONMENT=development
```
Options: `development`, `staging`, `production`

#### Logging
```bash
LOG_LEVEL=INFO
```
Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## Security Best Practices

### 1. Protect Secret Keys
```bash
# Set proper permissions on secrets file
sudo chmod 600 /etc/impact/secrets.env
sudo chown root:root /etc/impact/secrets.env

# Never commit .env to version control
echo ".env" >> .gitignore
```

### 2. Rotate Keys Regularly
- **SECRET_KEY:** Rotate every 90 days (invalidates existing JWTs)
- **ENCRYPTION_KEY:** Cannot be rotated without re-encrypting all data

### 3. Use Strong Keys
- Minimum 32 characters for SECRET_KEY
- Use cryptographically secure random generators
- Never use predictable values (e.g., "password123")

### 4. Environment-Specific Configuration
```bash
# Development
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# Production
ENVIRONMENT=production
LOG_LEVEL=WARNING
```

## Validation

The application performs startup validation on critical configuration:

### Secret Key Validation
```
❌ Startup fails if:
- Default secret key detected
- Secret key < 32 characters

✅ Provides helpful error messages with fix instructions
```

### MongoDB URI Validation
```
❌ Startup fails if:
- URI doesn't start with mongodb:// or mongodb+srv://
- URI is malformed

✅ Shows example valid URI format
```

### Example Error Message
```
🚨 SECURITY ERROR: Default secret key detected!
Set SECRET_KEY environment variable to a secure random key.
Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

## Systemd Service Configuration

The backend service loads environment files in this order:

```ini
# /etc/systemd/system/impact-backend.service
[Service]
EnvironmentFile=/etc/impact/secrets.env  # Loaded first
EnvironmentFile=/root/impact/.env        # Loaded second (can override)
```

**Reload after changes:**
```bash
sudo systemctl daemon-reload
sudo systemctl restart impact-backend
```

## Troubleshooting

### Backend won't start

**Check startup logs:**
```bash
sudo systemctl status impact-backend
tail -50 ~/.tmp/backend.log
```

**Common issues:**
1. **Default secret key:**
   ```
   Solution: Set SECRET_KEY in /etc/impact/secrets.env
   ```

2. **MongoDB connection failed:**
   ```
   Solution: Verify MONGODB_URI is correct and MongoDB is running
   ```

3. **Permission denied:**
   ```
   Solution: Check file permissions on .env and secrets.env
   ```

### Environment variables not loading

**Verify systemd loads them:**
```bash
# Check service environment
systemctl show impact-backend --property=Environment
systemctl show impact-backend --property=EnvironmentFiles
```

**Test configuration:**
```bash
# Temporarily run with debug logging
LOG_LEVEL=DEBUG sudo systemctl restart impact-backend
tail -f ~/.tmp/backend.log
```

### Key rotation

**Rotating SECRET_KEY:**
```bash
# 1. Generate new key
python -c 'import secrets; print(secrets.token_urlsafe(32))'

# 2. Update /etc/impact/secrets.env
sudo nano /etc/impact/secrets.env

# 3. Restart service
sudo systemctl restart impact-backend

# Note: All users will need to log in again
```

**ENCRYPTION_KEY cannot be rotated** without:
1. Decrypting all existing data with old key
2. Re-encrypting with new key
3. Updating database with re-encrypted values

## Backup Encryption

Database backups use a separate encryption key stored at:
```
/root/.backup-encryption-key
/root/.backup-encryption-salt
```

**Backup these files securely!** Losing them means losing access to encrypted backups.

## Quick Reference

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| SECRET_KEY | **Yes** | *None* | Min 32 chars, validated |
| ENCRYPTION_KEY | **Yes** | *None* | Fernet key format |
| MONGODB_URI | **Yes** | `mongodb://impact.vps:27017` | Validated format |
| MONGODB_DB_NAME | No | `impact` | Clinical database |
| MONGODB_SYSTEM_DB_NAME | No | `impact_system` | System database |
| API_HOST | No | `0.0.0.0` | Listen address |
| API_PORT | No | `8000` | Listen port |
| CORS_ORIGINS | No | `http://localhost:3000,...` | Comma-separated |
| ENVIRONMENT | No | `development` | Environment type |
| LOG_LEVEL | No | `INFO` | Logging verbosity |

## Support

For issues with environment configuration:
1. Check startup logs: `tail -50 ~/.tmp/backend.log`
2. Verify validation errors are addressed
3. Ensure all required variables are set
4. Check file permissions on .env files

**Remember:** The application will fail fast on startup if configuration is invalid, with clear error messages explaining what needs to be fixed.
