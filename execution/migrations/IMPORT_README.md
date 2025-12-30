# Access DB → IMPACT MongoDB Import Scripts

## Overview

The import process has been completely redesigned based on comprehensive field-by-field mappings documented in `execution/mappings/*.yaml`.

## File Structure

```
execution/
├── mappings/                           # Field-by-field mapping documentation
│   ├── README.md                       # Comprehensive mapping overview
│   ├── patients_mapping.yaml           # Patient data mappings
│   ├── episodes_mapping.yaml           # Episode data mappings
│   ├── tumours_mapping.yaml            # Tumour data mappings
│   ├── treatments_mapping.yaml         # Surgical treatment mappings
│   ├── investigations_mapping.yaml     # Investigation mappings
│   ├── pathology_mapping.yaml          # Pathology update mappings
│   ├── oncology_mapping.yaml           # RT/Chemo treatment mappings
│   └── followup_mapping.yaml           # Follow-up update mappings
│
└── migrations/
    ├── import_from_access_mapped.py    # New clean import script (PART 1)
    ├── export_access_to_csv.sh         # Export Access DB to CSV
    └── IMPORT_README.md                # This file
```

## Prerequisites

### 1. Access Database
- Location: `/root/impact/data/acpdata_v3_db.mdb`
- Original Access database with all patient data

### 2. Export Access DB to CSV

First, export the Access database tables to CSV format:

```bash
bash execution/migrations/export_access_to_csv.sh
```

This creates CSV files in `~/.tmp/access_export_mapped/`:
- `patients.csv` (from Table1)
- `tumours.csv` (from tblTumour)
- `treatments_surgery.csv` (from tblSurgery)
- `pathology.csv` (from tblPathology)
- `oncology.csv` (from tblOncology)
- `followup.csv` (from tblFollowUp)

### 3. Environment Variables

Ensure MongoDB connection is configured:

```bash
# In /etc/impact/secrets.env or .env
MONGODB_URI=mongodb://localhost:27017
```

## Import Process

### Quick Start

The import script is currently INCOMPLETE. Here's the current status:

**✅ COMPLETED:**
- All helper functions for data transformation
- `import_patients()` - Patient import
- `import_episodes()` - Episode import
- `import_tumours()` - Tumour import

**❌ TODO:**
- `import_treatments_surgery()` - Surgical treatments
- `import_investigations()` - Investigations
- `import_pathology()` - Pathology updates
- `import_oncology()` - RT/Chemo treatments
- `import_followup()` - Follow-up data
- `populate_mortality_flags()` - Mortality calculations
- `run_import()` - Main orchestration function
- CSV export script

### Import Sequence

The import MUST be executed in this specific order due to dependencies:

```
1. Patients       → creates patient_id mapping
2. Episodes       → creates episode_id mapping (needs patient_id)
3. Tumours        → creates tumour_id mapping (needs episode_id)
4. Treatments     → creates treatment records (needs episode_id)
                  → updates episodes (lead_clinician, no_treatment)
5. Investigations → creates investigation records (needs episode_id, tumour_id)
6. Pathology      → updates tumours (needs tumour_id)
7. Oncology       → creates RT/chemo treatments (needs episode_id)
8. Follow-up      → updates episodes (needs episode_id)
9. Mortality      → updates treatments (needs deceased_date from patients)
```

## Critical Data Quality Fixes

The import implements all critical fixes documented in the mappings:

### 1. NHS Number Decimal Removal
**Problem:** Access DB stores NHS_No as Double, adding .0
**Fix:** `str(int(float(nhs_number)))`
**Mapping:** `patients_mapping.yaml - nhs_number`

### 2. Surgical Approach Priority Logic
**Problem:** Must check robotic FIRST, then conversion, then laparoscopic
**Fix:** `determine_surgical_approach()` with priority order
**Mapping:** `treatments_mapping.yaml - classification.approach`

### 3. Stoma Type Field
**Problem:** Wrong field used (StomType instead of StomDone)
**Fix:** Use `StomDone` (what was actually done)
**Mapping:** `treatments_mapping.yaml - intraoperative.stoma_type`

### 4. Defunctioning Stoma Logic
**Problem:** Requires BOTH anastomosis AND stoma
**Fix:** `is_defunctioning_stoma()` checks both fields
**Mapping:** `treatments_mapping.yaml - intraoperative.defunctioning_stoma`

### 5. Readmission Field
**Problem:** Wrong field used (Major_C instead of Post_IP)
**Fix:** Use `Post_IP` (in-patient readmission)
**Mapping:** `treatments_mapping.yaml - outcomes.readmission_30day`

### 6. Lead Clinician Matching
**Problem:** Case-sensitive matching missing clinicians
**Fix:** Case-insensitive match, fallback to free text
**Mapping:** `treatments_mapping.yaml - team.primary_surgeon`

### 7. Investigation Result Cleaning
**Problem:** Access DB codes like "1 Normal", "2 Abnormal"
**Fix:** `clean_result_text()` removes leading numbers
**Mapping:** `investigations_mapping.yaml - result`

### 8. TumSeqno Type
**Problem:** String vs number mismatch in mapping lookups
**Fix:** Use `row.get('TumSeqno', 0)` as number
**Mapping:** All mappings using episode/tumour lookups

## Data Validation

After import, verify data quality:

```python
# Check patient NHS numbers (no decimals)
db.patients.find_one({'nhs_number': /\./})  # Should be none

# Check surgical approaches
db.treatments.distinct('classification.approach')
# Should include: open, laparoscopic, robotic, converted_to_open

# Check stoma types
db.treatments.distinct('intraoperative.stoma_type')
# Should include: ileostomy, colostomy, other

# Check defunctioning stomas logic
db.treatments.find({
    'intraoperative.defunctioning_stoma': 'yes',
    'intraoperative.anastomosis_performed': {$ne: 'yes'}
})  # Should be empty

# Check investigations result cleaning
db.investigations.find({'result': /^\d+\s/})  # Should be none
```

## Mapping References

Each import function references its corresponding mapping file:

| Function | Mapping File | Description |
|----------|--------------|-------------|
| `import_patients()` | `patients_mapping.yaml` | Patient demographics |
| `import_episodes()` | `episodes_mapping.yaml` | Care pathways |
| `import_tumours()` | `tumours_mapping.yaml` | Diagnosis/staging |
| `import_treatments_surgery()` | `treatments_mapping.yaml` | Surgical treatments |
| `import_investigations()` | `investigations_mapping.yaml` | Imaging/tests |
| `import_pathology()` | `pathology_mapping.yaml` | Histopathology |
| `import_oncology()` | `oncology_mapping.yaml` | RT/Chemotherapy |
| `import_followup()` | `followup_mapping.yaml` | Follow-up data |

## Next Steps

To complete the import script:

1. **Create CSV export script** (`export_access_to_csv.sh`)
   - Export Table1 → patients.csv
   - Export tblTumour → tumours.csv
   - Export tblSurgery → treatments_surgery.csv
   - Export tblPathology → pathology.csv
   - Export tblOncology → oncology.csv
   - Export tblFollowUp → followup.csv

2. **Complete remaining import functions**
   - Copy logic from `import_comprehensive.py`
   - Update to follow mapping files exactly
   - Add mapping file references in comments

3. **Add main orchestration function**
   - Connect to MongoDB
   - Run imports in correct sequence
   - Track statistics
   - Handle errors gracefully

4. **Test on development database**
   - Use `impact_test` database
   - Verify all data quality fixes
   - Check counts match expectations

5. **Run on production**
   - Backup existing `impact` database
   - Drop collections
   - Run clean import
   - Verify in frontend

## Troubleshooting

### Import fails with "patient_id not found"
- Check that CSV files were exported correctly
- Verify Hosp_No field is populated
- Ensure patients import ran successfully

### Mappings don't match data
- Check Access DB schema with `mdb-schema`
- Verify CSV export includes all fields
- Review mapping files for field names

### Performance is slow
- Add indexes after import completes
- Use batch operations where possible
- Monitor MongoDB performance

## References

- Mapping Documentation: `execution/mappings/README.md`
- Original Import: `execution/migrations/import_comprehensive.py`
- COSD Standards: NHS Cancer Outcomes and Services Dataset
