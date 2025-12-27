# Execution Scripts Index

> **Deterministic Python scripts organized by purpose following the 3-layer architecture.**

## 📁 Directory Structure

### `active/` - Currently Used Scripts
Production scripts and utilities actively used by the system.
- `backup_database.py` - Daily automated backups (runs via cron at 2 AM)
- `restore_database.py` - Database restoration from backups
- `cleanup_old_backups.py` - Applies retention policy
- `create_admin_user.py` - Create admin user accounts- `create_indexes.py` - Create database indexes for performance
- `fetch_nhs_provider_codes.py` - Fetch NHS provider/trust ODS codes
- `start_backend.sh`, `start_frontend.sh` - Service startup scripts

### `data-fixes/` - One-Time Data Corrections
Scripts used to fix data quality issues (typically run once).
See individual scripts for details on specific fixes applied.

### `migrations/` - Historical Database Migrations  
Scripts used during initial database setup and major schema changes.
**DO NOT run on production** - kept for historical reference only.

### `dev-tools/` - Development Utilities
Tools for development, testing, and database management.
Safe to run on test databases. Use caution on production.

### `archive/` - Deprecated Scripts
Unused or superseded scripts kept for reference.

---

## 🚀 Usage Guidelines

- **Active scripts**: Used by production - update cron/service files if paths change
- **Data fixes**: One-time use - backup database first, document execution
- **Migrations**: Historical only - DO NOT run on production
- **Dev tools**: Development only - test databases recommended

---

*Last updated: 2025-12-27*
