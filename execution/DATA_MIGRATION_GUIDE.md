# Data Migration Guide - ACP Database Import

This document outlines all data quality fixes and migrations applied after importing data from the ACP database. Follow these steps in order if re-importing data.

## Overview

The ACP database export contains historical surgical data with various data quality issues. This guide documents the systematic fixes applied to ensure data consistency and accuracy.

## Prerequisites

- MongoDB running with surgdb database
- CSV exports: `surgeries_export_new.csv`, `patients_export_new.csv`
- Python environment with pymongo and pandas installed

---

## Step 1: Initial Database Setup

```bash
# Initialize database collections
python3 execution/init_database.py

# Create indexes for performance
python3 execution/create_indexes.py
```

---

## Step 2: Import CSV Data

Import the base data from CSV files:

```bash
# Import patients
python3 execution/import_patients.py  # (if exists)

# Import surgeries/treatments
python3 execution/import_surgeries.py  # (if exists)
```

---

## Step 3: Surgeon Data Fixes

### 3.1 Fix Surgeon ObjectIds to Names

**Problem**: ~3,000 treatments have ObjectId strings (e.g., '694ac3ca4536cc3ca6577775') instead of surgeon names.

**Solution**: Map ObjectIds to actual clinician full names.

```bash
python3 execution/fix_surgeon_ids_to_names.py
```

**Result**: 3,021 treatments updated with proper names (e.g., 'Dan O'Leary', 'Paul Sykes').

### 3.2 Link Surgeons to Clinicians

**Problem**: Treatments have surgeon names (surnames or full names) that need to be linked to the clinicians table.

```bash
python3 execution/link_surgeons_to_clinicians.py
```

**Result**: Maps historical surgeon names to current clinician records.

---

## Step 4: Date and Urgency Fixes

### 4.1 Fix Treatment Dates

**Problem**: Treatment dates don't match the authoritative Surgery field from CSV.

**Key Finding**: Surgery field is 76.6% populated vs Date_Th at 33%.

```bash
python3 execution/fix_treatment_dates_from_csv.py
```

**Result**: 6,087 treatment dates updated to match Surgery field.

### 4.2 Fix Urgency Data

**Problem**: Urgency shows 98.7% emergency when should be ~64% elective.

**Root Cause**: Original script used Date_Th field (33% populated) instead of Surgery field (77% populated).

```bash
python3 execution/fix_urgency_from_csv.py
```

**Expected Result**:
- Elective: 63.6% (5,068 treatments)
- Emergency: 28.7% (2,288 treatments)  
- Urgent: 7.7% (616 treatments)

---

## Step 5: Clinical Data Corrections

### 5.1 Fix Complications

**Problem**: Complication rate of 15.2% includes readmissions incorrectly.

**True Complications**: Only MJ_Leak, MI_Leak, Cardio, MJ_Bleed, MI_Bleed from CSV.

```bash
python3 execution/fix_complications_from_csv.py
```

**Result**: Complication rate corrected to 2.6% (207 cases).

### 5.2 Set Provider Organisation

**Problem**: Provider organisation field needs to be standardized.

```bash
# Set all treatments to Portsmouth Hospitals University NHS Trust (ODS: RHU)
python3 << 'EOF'
from pymongo import MongoClient

client = MongoClient('mongodb://admin:admin123@localhost:27017')
db = client.surgdb

result = db.treatments.update_many(
    {},
    {"$set": {"provider_organisation": "RHU"}}
)
print(f"Updated {result.modified_count} treatments")
EOF
```

**Result**: All 7,957 treatments set to RHU.

### 5.3 Fix Return to Theatre (RTT) Data

**Problem**: Return to theatre data needs to be imported from CSV `re_op` field.

**Expected**: 1.6% RTT rate (126 cases based on CSV).

**Key Details**:
- CSV field: `re_op` (0 = no RTT, 1 = yes RTT)
- Matching strategy: Join surgeries_export_new.csv with patients_export_new.csv on Hosp_No to get NHS_No, then match to treatments using patient_id and treatment_date

```bash
cd /root/surg-db/execution/data-fixes
python3 fix_rtt_from_csv.py
```

**Process**:
1. Loads surgeries_export_new.csv and patients_export_new.csv
2. Joins CSVs on Hosp_No to get NHS_No for each surgery
3. Builds NHS number → patient_id lookup from database
4. For each CSV record:
   - Cleans NHS number (handles float conversion)
   - Looks up patient_id from NHS number
   - Parses surgery date to match treatment_date format (YYYY-MM-DD)
   - Finds matching treatment by patient_id + treatment_date
   - Sets `return_to_theatre` field to True/False based on re_op value
5. Verifies results against CSV totals

**Result**: ~126 treatments (1.6%) marked with return_to_theatre = True.

**Verification Output**:
```
MongoDB RTT = True:  126 (1.6%)
MongoDB RTT = False: 7,831 (98.4%)
✓ MATCH: MongoDB RTT count matches CSV
```

**Notes**:
- Matching relies on accurate NHS numbers in both CSV and database
- Treatment dates must match exactly (YYYY-MM-DD format)
- Records without NHS number or surgery date are skipped
- Script shows first 5 RTT cases for verification

---

## Step 6: Episode Lead Clinician Linking

**Problem**: Episodes have lead_clinician as names (strings like "Howell", "Khan") that need to be linked to clinician IDs for reporting.

**Note**: The backend reports endpoint handles this via name-based matching in the aggregation pipeline. No migration script needed - this is handled at query time.

---

## Data Quality Verification

After completing all migrations, verify the results:

```bash
python3 << 'EOF'
from pymongo import MongoClient

client = MongoClient('mongodb://admin:admin123@localhost:27017')
db = client.surgdb

print("DATA QUALITY CHECK")
print("="*80)

# Check urgency distribution
urgency_dist = {}
for urgency in ['elective', 'emergency', 'urgent']:
    count = db.treatments.count_documents({"urgency": urgency})
    total = db.treatments.count_documents({})
    pct = (count / total * 100) if total > 0 else 0
    urgency_dist[urgency] = {'count': count, 'pct': pct}
    print(f"Urgency - {urgency}: {count} ({pct:.1f}%)")

# Check complication rate
comp_count = db.treatments.count_documents({"complications": True})
total = db.treatments.count_documents({})
comp_pct = (comp_count / total * 100) if total > 0 else 0
print(f"\nComplications: {comp_count} ({comp_pct:.1f}%)")

# Check treatments with dates
date_count = db.treatments.count_documents({"treatment_date": {"$ne": None, "$exists": True}})
date_pct = (date_count / total * 100) if total > 0 else 0
print(f"Treatments with dates: {date_count} ({date_pct:.1f}%)")

# Check surgeon data quality
objectid_pattern = r'^[a-f0-9]{24}$'
objectid_count = db.treatments.count_documents({
    "surgeon": {"$regex": objectid_pattern, "$options": "i"}
})
print(f"Treatments with ObjectId strings: {objectid_count} (should be 0)")

print("\n" + "="*80)
EOF
```

**Expected Results**:
- ✅ Elective: ~64%
- ✅ Complications: ~2.6%
- ✅ Treatments with dates: ~77%
- ✅ ObjectId strings: 0

---

## Frontend Configuration

### Environment Variables

Ensure `.env` file in frontend directory has:

```
VITE_API_URL=http://192.168.11.238:8000/api
```

This ensures the frontend uses the remote backend URL instead of hardcoded localhost.

---

## Key CSV Fields Reference

### Surgery Date Source
- **Field**: `Surgery`
- **Population**: 76.6%
- **Format**: Date string
- **Usage**: Authoritative source for treatment_date

### Urgency Source  
- **Field**: `ModeOp`
- **Values**: 
  - 1 = Elective
  - 2 = Urgent  
  - 3 = Emergency
- **Population**: 75.6% (when matched with Surgery field)

### True Complication Indicators
- **MJ_Leak**: Major anastomotic leak
- **MI_Leak**: Minor anastomotic leak
- **Cardio**: Cardiovascular complications
- **MJ_Bleed**: Major bleeding
- **MI_Bleed**: Minor bleeding

**Note**: Do NOT use `Comp` field or readmission flags for complication rate.

### Return to Theatre Source
- **Field**: `re_op`
- **Values**:
  - 0 = No RTT
  - 1 = Yes RTT
- **Population**: 100% (all records)
- **Expected Rate**: 1.6% (126 cases)
- **Usage**: Authoritative source for return_to_theatre field

---

## Migration Scripts Summary

| Script | Purpose | Records Affected |
|--------|---------|-----------------|
| `fix_surgeon_ids_to_names.py` | Convert ObjectId strings to names | 3,021 |
| `link_surgeons_to_clinicians.py` | Link surgeon names to clinician IDs | 3,023 |
| `fix_treatment_dates_from_csv.py` | Update dates from Surgery field | 6,087 |
| `fix_urgency_from_csv.py` | Correct urgency using ModeOp | 6,013 |
| `fix_complications_from_csv.py` | Fix complications (exclude readmissions) | 7,756 |
| `fix_rtt_from_csv.py` | Fix return to theatre using re_op field | ~7,957 (126 RTT) |

---

## Common Issues and Solutions

### Issue: Surgeon field shows ObjectId
**Cause**: Historical data imported with clinician IDs instead of names  
**Fix**: Run `fix_surgeon_ids_to_names.py`

### Issue: Urgency shows too many emergency cases
**Cause**: Using Date_Th field which is only 33% populated  
**Fix**: Run `fix_urgency_from_csv.py` which uses Surgery field (77% populated)

### Issue: High complication rate
**Cause**: Including readmissions in complication count  
**Fix**: Run `fix_complications_from_csv.py` to use only true complication indicators

### Issue: Treatment dates don't match CSV
**Cause**: Dates imported from Date_Th instead of Surgery field  
**Fix**: Run `fix_treatment_dates_from_csv.py`

### Issue: Frontend shows blank surgeon field when editing
**Cause**: Legacy surgeon names (surnames only like "Howell") don't match current clinician full names  
**Solution**: SearchableSelect component updated to display raw value if no match found

---

## Validation Queries

### Check surgeon data quality
```javascript
// In MongoDB shell
db.treatments.aggregate([
  { $group: {
    _id: "$surgeon",
    count: { $sum: 1 }
  }},
  { $sort: { count: -1 }},
  { $limit: 20 }
])
```

### Check urgency distribution by year
```javascript
db.treatments.aggregate([
  { $match: { treatment_date: { $ne: null }}},
  { $group: {
    _id: { 
      year: { $year: "$treatment_date" },
      urgency: "$urgency"
    },
    count: { $sum: 1 }
  }},
  { $sort: { "_id.year": 1, "_id.urgency": 1 }}
])
```

---

## Notes

1. **Order Matters**: Run scripts in the order listed above. Some scripts depend on previous fixes.

2. **Idempotency**: Most scripts can be safely re-run. They check existing data before updating.

3. **Backup First**: Always backup the database before running migration scripts:
   ```bash
   mongodump --db surgdb --out /backup/surgdb_$(date +%Y%m%d)
   ```

4. **CSV Authority**: The `surgeries_export_new.csv` file is the authoritative source for dates, urgency, complications, and return to theatre data. Always reference it when fixing data quality issues.

5. **Legacy Data**: Some treatments retain legacy surgeon names (surnames only) that don't match current clinicians. This is expected and the UI handles it gracefully.

---

## Last Updated
December 27, 2025
