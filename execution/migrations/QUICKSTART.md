# IMPACT Database Import - Quick Start Guide

This guide provides step-by-step instructions for running the complete database import.

## Prerequisites

✅ Access database at `/root/impact/data/acpdata_v3_db.mdb`
✅ MongoDB running on `localhost:27017`
✅ Python 3 with pandas and pymongo installed
✅ mdb-tools installed (`sudo apt-get install mdb-tools`)

## Step 1: Export Access DB to CSV

```bash
cd /root/impact
bash execution/migrations/export_access_to_csv.sh
```

**Expected output:**
- Creates `~/.tmp/access_export_mapped/` directory
- Exports 7 CSV files:
  - `tblPatient.csv` (7,973 patients)
  - `Table1.csv` (7,250 patients - fallback)
  - `tblTumour.csv` (~8,000 records)
  - `tblSurgery.csv` (~6,000 surgeries)
  - `tblPathology.csv` (~6,000 records)
  - `tblOncology.csv` (RT/Chemo - if exists)
  - `tblFollowUp.csv` (~15,000+ records)

## Step 2: Verify CSV Files

```bash
ls -lh ~/.tmp/access_export_mapped/
```

Check that all required files exist and have reasonable sizes.

## Step 3: Run Import (Development Test)

**RECOMMENDED:** Test on development database first!

```bash
# Set environment for test database
export MONGODB_DB_NAME=impact_test

# Run import
python3 execution/migrations/import_from_access_mapped.py
```

When prompted "Proceed with import? (yes/no):", type `yes`

**Import sequence:**
1. ✅ Patients (with encryption) - ~7,973 records
2. ✅ Episodes - ~8,000 records
3. ✅ Tumours - ~8,000 records
4. ✅ Treatments (surgery) - ~6,000 records
5. ✅ Investigations (4 types) - ~20,000+ records
6. ✅ Pathology updates - ~6,000 tumours
7. ✅ Follow-up data - ~15,000+ records
8. ✅ Mortality flags - All surgical treatments

**Expected duration:** 5-10 minutes

## Step 4: Verify Import

```bash
# Connect to test database
mongosh impact_test

# Check record counts
db.patients.countDocuments({})           // Should be ~7,973
db.episodes.countDocuments({})           // Should be ~8,000
db.tumours.countDocuments({})            // Should be ~8,000
db.treatments.countDocuments({})         // Should be ~6,000
db.investigations.countDocuments({})     // Should be ~20,000+

# Verify encryption (NHS numbers should start with "ENC:")
db.patients.findOne({}, {nhs_number: 1, "demographics.first_name": 1})

# Check pathology data
db.tumours.countDocuments({pathological_t: {$ne: null}})

# Check follow-up data
db.episodes.countDocuments({"follow_up.0": {$exists: true}})

# Check mortality flags
db.treatments.countDocuments({"outcomes.mortality_30day": "yes"})
db.treatments.countDocuments({"outcomes.mortality_90day": "yes"})

# Exit mongosh
exit
```

## Step 5: Verify in Frontend

```bash
# Restart backend to connect to test database
sudo systemctl restart surg-db-backend

# Check backend logs
tail -f ~/.tmp/backend.log
```

Open browser to: http://localhost:3000

**Check:**
- ✅ Patients list loads
- ✅ Patient names/NHS numbers are **NOT** visible (encrypted)
- ✅ Patient IDs are random (e.g., "A3K7M2", not sequential)
- ✅ Episodes show correct data
- ✅ Treatments display properly
- ✅ Investigations appear in patient records
- ✅ Follow-up data visible

## Step 6: Production Import

**ONLY after successful testing!**

### Backup Existing Database

```bash
# Create backup directory
mkdir -p ~/.tmp/impact_backups

# Backup current database
mongodump --db=impact --out=~/.tmp/impact_backups/before_reimport_$(date +%Y%m%d_%H%M%S)
```

### Run Production Import

```bash
# Set environment for production database
export MONGODB_DB_NAME=impact

# Run import
python3 execution/migrations/import_from_access_mapped.py
```

Type `yes` when prompted.

### Verify Production

Follow Step 4 and Step 5 verification steps, but use `impact` database instead of `impact_test`.

## Troubleshooting

### Import fails with "CSV directory not found"

Run the export script first:
```bash
bash execution/migrations/export_access_to_csv.sh
```

### Import fails with "Missing required CSV files"

Check which files are missing:
```bash
ls ~/.tmp/access_export_mapped/
```

Re-run export script if files are missing.

### Encryption keys not found

Keys should be automatically generated on first run. Check:
```bash
ls -la /root/.field-encryption-key
ls -la /root/.field-encryption-salt
```

**IMPORTANT:** Backup these files immediately!

### MongoDB connection failed

Check MongoDB is running:
```bash
sudo systemctl status mongod
```

Check connection string in environment:
```bash
echo $MONGODB_URI  # Should be mongodb://localhost:27017
```

### Duplicate records on re-run

The script uses INSERT-ONLY mode - duplicates are automatically skipped. This is safe behavior.

### Performance is slow

- Ensure MongoDB has enough RAM
- Check disk I/O
- Import runs single-threaded (by design for data integrity)

## Data Quality Checks

After import, verify these critical fixes are working:

### 1. NHS Number Decimal Removal
```javascript
// Should NOT see any decimals
db.patients.find({nhs_number: /\./}).count()  // Should be 0
```

### 2. Surgical Approach Priority Logic
```javascript
// Should see robotic approaches
db.treatments.countDocuments({"classification.approach": "robotic"})

// Should see conversions
db.treatments.countDocuments({"classification.approach": "converted_to_open"})
```

### 3. Stoma Type Field (StomDone, not StomType)
```javascript
db.treatments.distinct("intraoperative.stoma_type")
// Should include: ileostomy, colostomy, other
```

### 4. Defunctioning Stoma Logic
```javascript
// All defunctioning stomas should have anastomosis
db.treatments.find({
  "intraoperative.defunctioning_stoma": "yes",
  "intraoperative.anastomosis_performed": {$ne: "yes"}
}).count()  // Should be 0
```

### 5. Investigation Result Cleaning
```javascript
// Should NOT see leading numbers like "1 Normal"
db.investigations.find({result: /^\d+\s/}).count()  // Should be 0
```

## Encryption Key Backup

**CRITICAL:** Backup encryption keys to secure offline storage!

```bash
# Create secure backup
sudo mkdir -p /root/secure_backups
sudo cp /root/.field-encryption-key /root/secure_backups/
sudo cp /root/.field-encryption-salt /root/secure_backups/
sudo chmod 600 /root/secure_backups/*

# Copy to external storage
# (Follow your organization's key management procedures)
```

**Without these keys, encrypted data cannot be decrypted!**

## Support

For issues or questions:
1. Check [RECENT_CHANGES.md](../../RECENT_CHANGES.md) for latest updates
2. Review mapping files in `execution/mappings/`
3. Check [IMPORT_README.md](IMPORT_README.md) for detailed documentation
4. Review import script logs for error messages

## Quick Reference

| Command | Purpose |
|---------|---------|
| `bash execution/migrations/export_access_to_csv.sh` | Export Access DB to CSV |
| `python3 execution/migrations/import_from_access_mapped.py` | Run full import |
| `mongosh impact --eval "db.patients.countDocuments({})"` | Check patient count |
| `sudo systemctl restart surg-db-backend` | Restart backend |
| `tail -f ~/.tmp/backend.log` | View backend logs |

## Summary

✅ Complete import script with **all 8 import functions**
✅ Full UK GDPR + Caldicott encryption compliance
✅ Random patient IDs (de-identified)
✅ NHS/PAS number linking (more reliable)
✅ Dual-source import (tblPatient + Table1 fallback)
✅ All critical data quality fixes implemented
✅ Production-ready with comprehensive error handling

**Total lines of code:** 2,306
**Import duration:** 5-10 minutes
**Insert mode:** INSERT-ONLY (safe to re-run)
