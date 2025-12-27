# File Organization Plan

> **Purpose**: Restructure the surg-db codebase to improve navigability and maintainability

## Current State Analysis

### Root Folder Issues
- **24 documentation files** (various .md files) cluttering root directory
- **15 loose files** (Python scripts, CSVs, JSONs) that should be organized
- Mixed purposes: active code, archived data, temporary exports, documentation

### Execution Folder Issues
- **65 Python scripts** + **4 shell scripts** with no categorization
- Scripts serve different purposes:
  - Database migrations (historical, one-time use)
  - Data fixes (one-time corrections)
  - Active utilities (backups, admin tasks)
  - Sample data generators (development/testing)
  - Startup scripts (production services)

## Proposed Structure

```
/root/surg-db/
├── README.md                          # Main project overview
├── TODO.md                            # Development roadmap
├── RECENT_CHANGES.md                  # Session log
├── STYLE_GUIDE.md                     # UI/UX patterns
├── AGENTS.md                          # AI agent instructions
├── CLAUDE.md                          # Symlink to AGENTS.md
├── .gitignore
├── .env
├── root.code-workspace
│
├── docs/                              # 📚 All documentation
│   ├── README.md                      # Documentation index
│   ├── setup/                         # Setup and deployment
│   │   ├── QUICK_START.md
│   │   ├── DEVELOPMENT.md
│   │   ├── DEPLOYMENT.md
│   │   └── SERVICE_MANAGEMENT.md
│   ├── api/                           # API documentation
│   │   └── API_DOCUMENTATION.md
│   ├── guides/                        # User and feature guides
│   │   ├── USER_GUIDE.md
│   │   ├── BACKUP_QUICK_REFERENCE.md
│   │   └── MIGRATION_HELPERS.md
│   ├── implementation/                # Implementation summaries
│   │   ├── AUDIT_LOGGING_SUMMARY.md
│   │   ├── CODE_OPTIMIZATION_SUMMARY.md
│   │   ├── DATABASE_MIGRATION_SUMMARY.md
│   │   ├── DATA_COMPLETENESS_ANALYSIS.md
│   │   ├── IMPLEMENTATION_SUMMARY.md
│   │   ├── NBOCA_FIELDS_STATUS.md
│   │   ├── NBOCA_IMPLEMENTATION_STATUS.md
│   │   └── SECURITY_ENHANCEMENTS_SUMMARY.md
│   └── archive/                       # Historical documentation
│       ├── README_OLD.md
│       └── SESSION_SUMMARY_2025-12-23.md
│
├── execution/                         # 🛠️ Deterministic Python scripts
│   ├── README.md                      # Scripts index and usage guide
│   ├── active/                        # Currently used scripts
│   │   ├── backup_database.py         # Daily backups (cron job)
│   │   ├── restore_database.py        # Database restoration
│   │   ├── cleanup_old_backups.py     # Backup retention
│   │   ├── create_admin_user.py       # Admin user creation
│   │   ├── create_indexes.py          # Database indexing
│   │   ├── fetch_nhs_provider_codes.py # NHS provider lookup
│   │   ├── start_backend.sh           # Backend startup
│   │   ├── start_frontend.sh          # Frontend startup
│   │   └── test_*.sh                  # Test scripts
│   ├── data-fixes/                    # One-time data corrections
│   │   ├── README.md                  # Fix scripts documentation
│   │   ├── fix_complications_from_csv.py
│   │   ├── fix_future_dobs.py
│   │   ├── fix_patient_ages.py
│   │   ├── fix_patient_validation.py
│   │   ├── fix_rtt_from_csv.py
│   │   ├── fix_surgeon_gmc_index.py
│   │   ├── fix_surgeon_ids_to_names.py
│   │   ├── fix_treatment_dates_from_csv.py
│   │   ├── fix_urgency_from_csv.py
│   │   ├── fix_urgency_with_nhs_match.py
│   │   ├── fix_no_surgery_records.py
│   │   ├── normalize_treatment_intent.py
│   │   ├── normalize_treatment_plan.py
│   │   ├── populate_lead_clinician_from_csv.py
│   │   ├── populate_missing_lead_clinicians.py
│   │   ├── populate_mortality_flags.py
│   │   ├── update_admission_dates.py
│   │   ├── update_deceased_dates.py
│   │   ├── update_mri_rectum_records.py
│   │   └── map_tumour_anatomical_sites.py
│   ├── migrations/                    # Historical database migrations
│   │   ├── README.md                  # Migration history
│   │   ├── migrate_access_to_mongodb.py
│   │   ├── migrate_acpdb_to_mongodb.py
│   │   ├── migrate_acpdb_to_mongodb_v2.py
│   │   ├── migrate_acpdb_to_mongodb_v3.py
│   │   ├── migrate_acpdb_to_mongodb_v4.py
│   │   ├── migrate_add_consultant_flag.py
│   │   ├── migrate_episode_data.py
│   │   ├── migrate_episode_waiting_times.py
│   │   ├── migrate_ids.py
│   │   ├── migrate_investigations.py
│   │   ├── migrate_outcomes_data.py
│   │   ├── migrate_patient_demographics.py
│   │   ├── migrate_surgeon_data.py
│   │   ├── migrate_surgeon_names_to_full.py
│   │   ├── migrate_surgery_data.py
│   │   ├── migrate_to_separate_collections.py
│   │   ├── init_database.py
│   │   ├── init_episodes_collection.py
│   │   ├── init_surgeons.py
│   │   ├── link_surgeons_to_clinicians.py
│   │   ├── restructure_tumour_data.py
│   │   ├── update_surgery_schema.py
│   │   ├── update_tumour_data.py
│   │   └── import_fresh_with_improvements.py
│   ├── dev-tools/                     # Development utilities
│   │   ├── README.md                  # Dev tools documentation
│   │   ├── create_sample_data.py
│   │   ├── create_sample_cancer_episodes.py
│   │   ├── debug_data_structure.py
│   │   ├── test_cosd_export.py
│   │   ├── check_negative_ages.py
│   │   ├── calculate_length_of_stay.py
│   │   ├── clean_surgery_data.py
│   │   ├── compare_databases.py
│   │   ├── enhance_current_database.py
│   │   ├── enhance_current_database_aggressive.py
│   │   ├── export_access_selective.py
│   │   ├── export_missing_lead_clinician.py
│   │   ├── import_surgery_data.py
│   │   ├── optimize_database_queries.py
│   │   └── reset_and_populate_bowel_cancer.py
│   └── archive/                       # Deprecated/unused scripts
│       └── README.md                  # Archive notes
│
├── data/                              # 📊 Data files (NOT in git)
│   ├── exports/                       # CSV exports
│   │   ├── patients_export.csv
│   │   ├── surgeries_export.csv
│   │   ├── pathology_export.csv
│   │   ├── pathology_export_new.csv
│   │   ├── tumours_export.csv
│   │   └── tumours_export_new.csv
│   └── reference/                     # Reference data
│       └── legacy_surgeons.json
│
├── scripts/                           # 🔧 Standalone utility scripts
│   ├── check_investigation_data.py    # (from root)
│   ├── check_surgeon_data.py          # (from root)
│   ├── check_treatment_fields.py      # (from root)
│   ├── find_patients_without_episodes.py # (from root)
│   └── fix_investigation_dates.py     # (from root)
│
├── backend/                           # (unchanged)
├── frontend/                          # (unchanged)
├── directives/                        # (unchanged)
└── .tmp/                              # (unchanged)
```

## Migration Steps

### Step 1: Create new directory structure
```bash
mkdir -p docs/{setup,api,guides,implementation,archive}
mkdir -p execution/{active,data-fixes,migrations,dev-tools,archive}
mkdir -p data/{exports,reference}
mkdir -p scripts
```

### Step 2: Move documentation files
```bash
# Setup documentation
mv QUICK_START.md docs/setup/
mv DEVELOPMENT.md docs/setup/
mv DEPLOYMENT.md docs/setup/
mv SERVICE_MANAGEMENT.md docs/setup/

# API documentation
mv API_DOCUMENTATION.md docs/api/

# User guides
mv USER_GUIDE.md docs/guides/
mv BACKUP_QUICK_REFERENCE.md docs/guides/
mv MIGRATION_HELPERS.md docs/guides/

# Implementation summaries
mv AUDIT_LOGGING_SUMMARY.md docs/implementation/
mv CODE_OPTIMIZATION_SUMMARY.md docs/implementation/
mv DATABASE_MIGRATION_SUMMARY.md docs/implementation/
mv DATA_COMPLETENESS_ANALYSIS.md docs/implementation/
mv IMPLEMENTATION_SUMMARY.md docs/implementation/
mv NBOCA_FIELDS_STATUS.md docs/implementation/
mv NBOCA_IMPLEMENTATION_STATUS.md docs/implementation/
mv SECURITY_ENHANCEMENTS_SUMMARY.md docs/implementation/

# Archive
mv README_OLD.md docs/archive/
mv SESSION_SUMMARY_2025-12-23.md docs/archive/
```

### Step 3: Move execution scripts
```bash
# Active scripts (stay in execution/active/)
mv execution/backup_database.py execution/active/
mv execution/restore_database.py execution/active/
mv execution/cleanup_old_backups.py execution/active/
mv execution/create_admin_user.py execution/active/
mv execution/create_indexes.py execution/active/
mv execution/fetch_nhs_provider_codes.py execution/active/
mv execution/*.sh execution/active/

# Data fixes
mv execution/fix_*.py execution/data-fixes/
mv execution/normalize_*.py execution/data-fixes/
mv execution/populate_*.py execution/data-fixes/
mv execution/update_*.py execution/data-fixes/
mv execution/map_tumour_anatomical_sites.py execution/data-fixes/

# Migrations
mv execution/migrate_*.py execution/migrations/
mv execution/init_*.py execution/migrations/
mv execution/link_surgeons_to_clinicians.py execution/migrations/
mv execution/restructure_tumour_data.py execution/migrations/
mv execution/import_fresh_with_improvements.py execution/migrations/

# Dev tools
mv execution/create_sample_*.py execution/dev-tools/
mv execution/debug_*.py execution/dev-tools/
mv execution/test_*.py execution/dev-tools/
mv execution/check_*.py execution/dev-tools/
mv execution/calculate_*.py execution/dev-tools/
mv execution/clean_*.py execution/dev-tools/
mv execution/compare_*.py execution/dev-tools/
mv execution/enhance_*.py execution/dev-tools/
mv execution/export_*.py execution/dev-tools/
mv execution/import_surgery_data.py execution/dev-tools/
mv execution/optimize_database_queries.py execution/dev-tools/
mv execution/reset_and_populate_bowel_cancer.py execution/dev-tools/
```

### Step 4: Move data files
```bash
# CSV exports
mv *.csv data/exports/ 2>/dev/null || true
mv pathology_export*.csv data/exports/ 2>/dev/null || true
mv tumours_export*.csv data/exports/ 2>/dev/null || true

# Reference data
mv legacy_surgeons.json data/reference/
```

### Step 5: Move standalone scripts
```bash
mv check_investigation_data.py scripts/
mv check_surgeon_data.py scripts/
mv check_treatment_fields.py scripts/
mv find_patients_without_episodes.py scripts/
mv fix_investigation_dates.py scripts/
mv test_audit_logging.py scripts/
```

### Step 6: Update .gitignore
Add data/ directory to .gitignore to avoid committing exports

### Step 7: Create README files
- `docs/README.md` - Documentation index
- `execution/README.md` - Scripts index
- `execution/data-fixes/README.md` - Fix scripts guide
- `execution/migrations/README.md` - Migration history
- `execution/dev-tools/README.md` - Dev tools guide
- `data/README.md` - Data directory purpose

## Benefits

### 📁 **Better Organization**
- Clear separation of documentation, scripts, and data
- Easy to find relevant files
- Logical grouping by purpose

### 🧭 **Improved Navigation**
- New developers can quickly understand structure
- README files guide users to correct locations
- Less clutter in root directory

### 🔒 **Better Git Hygiene**
- Data exports excluded from version control
- Clear distinction between code and data
- Easier to write .gitignore rules

### 📚 **Documentation Discovery**
- All docs in one place with clear hierarchy
- Setup guides separate from implementation notes
- Archive preserves historical context

### 🛠️ **Script Management**
- Active scripts clearly separated from historical ones
- Migration history preserved but organized
- Development tools isolated from production scripts

## Backwards Compatibility

### Potential Issues
1. **Cron jobs** - May reference `execution/backup_database.py`
2. **Service files** - May reference `execution/start_*.sh` scripts
3. **Documentation links** - May break internal references
4. **Import paths** - Scripts may import from `execution/`

### Solutions
1. Update cron job paths to `execution/active/backup_database.py`
2. Update systemd service files to point to `execution/active/`
3. Use symlinks for critical files if needed
4. Update Python import paths if scripts depend on each other

## Rollback Plan

If issues arise:
```bash
# All moves are reversible
# Git will show all file movements
git status
git diff --name-status

# Can revert with:
git checkout -- .
```

## Success Criteria

✅ Root directory has ≤10 files (README, TODO, AGENTS, STYLE_GUIDE, RECENT_CHANGES, config files)
✅ All documentation in `docs/` with clear hierarchy
✅ Execution scripts categorized by purpose
✅ Data files excluded from git
✅ Services still function after migration
✅ README files provide clear navigation
✅ .gitignore updated appropriately

## Timeline

- **Planning**: 30 minutes (this document)
- **Execution**: 1-2 hours (careful file movements, testing)
- **Documentation**: 30 minutes (README files)
- **Testing**: 30 minutes (verify services work)
- **Total**: 2.5-3 hours

---

**Status**: READY FOR APPROVAL
**Created**: 2025-12-27
**Author**: AI Agent
