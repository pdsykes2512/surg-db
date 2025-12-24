# Access Database to MongoDB Field Mapping

This document provides the complete field mapping from the original Microsoft Access database (acpdata_v3_db.mdb) to the new MongoDB database (surgdb). Use this as the authoritative reference for any future data imports.

**Last Updated**: December 24, 2025

---

## Overview

The Access database contains 4 main tables that have been migrated:
- **tblPatient** → `patients` collection
- **tblSurgery** → `treatments` collection (surgery treatments)
- **tblTumour** → `episodes` collection (tumour/diagnosis data)
- **tblWaitingTimes** → `episodes` collection (referral and MDT data)

---

## Table 1: tblPatient → patients collection

**Source**: `~/.tmp/patient_export.csv`  
**Export Command**: `mdb-export acpdata_v3_db.mdb tblPatient > patient_export.csv`

| Access Field | MongoDB Field | Collection | Notes |
|-------------|---------------|------------|-------|
| `PAS_No` | `mrn` | patients | Primary identifier - used for matching |
| `Hosp_No` | *(not stored)* | - | Intermediate lookup field only |
| *Other fields* | *(not imported)* | - | Demographics imported separately from hospital systems |

**Usage**: The `PAS_No` (PAS number) becomes the `mrn` field in MongoDB. The `Hosp_No` is used as an intermediate lookup between Access tables but is not stored in MongoDB.

**Matching Strategy**: 
1. Access `tblSurgery.Hosp_No` → lookup → Access `tblPatient.Hosp_No` 
2. Get `tblPatient.PAS_No`
3. Match to MongoDB `patients.mrn`

---

## Table 2: tblSurgery → treatments collection

**Source**: `~/.tmp/surgery_mdt_referral_export.csv`  
**Export Command**: `mdb-export acpdata_v3_db.mdb tblSurgery > surgery_mdt_referral_export.csv`  
**Records**: 7,957 surgery records

| Access Field | MongoDB Field | Collection | Data Type | Notes |
|-------------|---------------|------------|-----------|-------|
| `Hosp_No` | *(lookup only)* | - | String | Used to match patient via tblPatient |
| `Surgery` | `treatment_date` | treatments | Date | Primary surgery date (76.6% populated) - **AUTHORITATIVE** |
| `Date_Th` | *(deprecated)* | - | Date | Alternative date field (33% populated) - DO NOT USE |
| `CNS_date` | `cns_involved` | episodes | Date | CNS nurse involvement date (1,158 records) |
| `Urgency` | `urgency` | treatments | String | Elective/Emergency/Urgent - based on Surgery date timing |
| `Surgeon` | `surgeon` | treatments | String | Surgeon surname or full name |
| *(other fields)* | *(not imported)* | - | - | Other surgical details not yet migrated |

**Important Notes**:
- **Always use `Surgery` field**, not `Date_Th` - Surgery is 2.3x more complete
- `CNS_date` migrates to episodes, not treatments (applies to all patient episodes)
- `Urgency` is recalculated based on Surgery date timing, not stored urgency values
- 1,158 records have CNS dates (14.55% of episodes)

**Urgency Calculation** (from Surgery date):
- **Elective**: Admission ≥ 24 hours before surgery (63.6%)
- **Urgent**: Admission < 24 hours before surgery (7.7%)
- **Emergency**: Admission on same day as surgery (28.7%)

---

## Table 3: tblTumour → episodes collection

**Source**: `~/.tmp/tumour_export.csv`  
**Export Command**: `mdb-export acpdata_v3_db.mdb tblTumour > tumour_export.csv`  
**Records**: 8,088 tumour records

| Access Field | MongoDB Field | Collection | Data Type | Notes |
|-------------|---------------|------------|-----------|-------|
| `Hosp_No` | *(lookup only)* | - | String | Used to match patient via tblPatient |
| `Dt_Diag` | `first_seen_date` | episodes | Date | Diagnosis date → First seen date (7,031 updated, 94.46% completeness) |
| `Tumour_Site` | `primary_diagnosis` | episodes | String | Tumour location/site |
| *(other fields)* | *(not imported yet)* | - | - | Additional tumour characteristics available |

**Important Notes**:
- `Dt_Diag` (diagnosis date) is used as proxy for `first_seen_date` 
- 7,031 out of 7,957 episodes updated (88.4% match rate)
- All episodes for a patient get the same first_seen_date (patient-level, not tumour-level)

---

## Table 4: tblWaitingTimes → episodes collection

**Source**: `~/.tmp/waiting_times_export.csv`  
**Export Command**: `mdb-export acpdata_v3_db.mdb tblWaitingTimes > waiting_times_export.csv`  
**Records**: Only 4 records total (minimal data)

| Access Field | MongoDB Field | Collection | Data Type | Notes |
|-------------|---------------|------------|-----------|-------|
| `Hosp_No` | *(lookup only)* | - | String | Used to match patient via tblPatient |
| `MDT_date` | `mdt_discussion_date` | episodes | Date | MDT discussion date (only 4 records - 0.05%) |
| `MDT_date` | `mdt_meeting_type` | episodes | String | Set to "colorectal mdt" if MDT_date exists |
| `Source` | `referral_source` | episodes | String | Referral source code (0-9) |
| `Date_Ref` | `referral_date` | episodes | Date | Referral date (if available) |

**Referral Source Code Mapping**:
```
01 → "GP"
02 → "Consultant"
03 → "GP"
04 → "Other"
05 → "Self"
06 → "Emergency"
07 → "Screening"
08 → "Other"
09 → "Other"
10 → "Transfer"
99 → "Unknown"
```

**Important Notes**:
- Only 4 records exist in tblWaitingTimes - very incomplete
- MDT dates only 0.05% populated (4 out of 7,957 episodes)
- Referral source only available for these 4 records
- This table has limited value for migration

---

## Migration Statistics

### Episode-Level Data (from migrate_episode_data.py)

| Field | Source Table | Records Available | Episodes Updated | Completeness |
|-------|-------------|-------------------|------------------|--------------|
| `first_seen_date` | tblTumour.Dt_Diag | 8,085 | 7,031 | 94.46% |
| `cns_involved` | tblSurgery.CNS_date | 1,127 | 1,158 | 14.55% |
| `mdt_discussion_date` | tblWaitingTimes.MDT_date | 4 | 4 | 0.05% |
| `referral_source` | tblWaitingTimes.Source | 4 | 4 | 0.05% |

### Treatment-Level Data

| Field | Source | Records Updated | Notes |
|-------|--------|----------------|-------|
| `treatment_date` | tblSurgery.Surgery | 6,087 | From Surgery field (authoritative) |
| `surgeon` | tblSurgery.Surgeon | ~5,000 | After ObjectId → name conversion |
| `urgency` | Calculated from dates | ~7,000 | Recalculated, not direct import |

---

## Data Quality Notes

### High Quality Fields (>90% populated)
- ✅ `first_seen_date` from tblTumour.Dt_Diag (94.46%)

### Medium Quality Fields (10-90% populated)
- ⚠️ `treatment_date` from tblSurgery.Surgery (76.6%)
- ⚠️ `cns_involved` from tblSurgery.CNS_date (14.55%)

### Low Quality Fields (<10% populated)
- ❌ `mdt_discussion_date` from tblWaitingTimes.MDT_date (0.05%)
- ❌ `referral_source` from tblWaitingTimes.Source (0.05%)

### Derived Fields
These are calculated, not directly imported:
- `urgency`: Calculated from admission vs surgery date timing
- `episode_id`: Generated in new format (E-XXXXXX-01)
- `treatment_id`: Generated in new format (SUR-XXXXXXXXXX-01)

---

## Key Matching Strategy

**Patient Matching Flow**:
```
Access tblSurgery/tblTumour/tblWaitingTimes
    └─> Hosp_No field
        └─> Lookup in tblPatient by Hosp_No
            └─> Get PAS_No field
                └─> Match to MongoDB patients.mrn
                    └─> Get patient_id
                        └─> Update all episodes for that patient
```

**Why this multi-step approach?**
- Access uses `Hosp_No` (hospital number) as identifier
- MongoDB uses `mrn` (MRN/PAS number) as identifier  
- `tblPatient` provides the mapping: `Hosp_No` → `PAS_No` (MRN)
- All episodes for a patient receive the same episode-level data

---

## Migration Scripts Reference

### Episode Data Migration
**Script**: `execution/migrate_episode_data.py`
**Purpose**: Migrate episode-level data (CNS dates, first seen dates, MDT dates, referral sources)
**Usage**:
```bash
# Dry run (preview changes)
python3 execution/migrate_episode_data.py --dry-run

# Execute migration
python3 execution/migrate_episode_data.py --confirm
```

### CSV Exports Required
Before running migrations, export these tables:
```bash
# From Access database location
cd /root/surg-db/acpdb/

# Export tblPatient (for Hosp_No → PAS_No mapping)
mdb-export acpdata_v3_db.mdb tblPatient > ~/.tmp/patient_export.csv

# Export tblSurgery (for CNS dates and surgery dates)
mdb-export acpdata_v3_db.mdb tblSurgery > ~/.tmp/surgery_mdt_referral_export.csv

# Export tblTumour (for diagnosis/first seen dates)
mdb-export acpdata_v3_db.mdb tblTumour > ~/.tmp/tumour_export.csv

# Export tblWaitingTimes (for MDT and referral data)
mdb-export acpdata_v3_db.mdb tblWaitingTimes > ~/.tmp/waiting_times_export.csv
```

---

## Future Import Checklist

If you need to re-import data from the Access database:

1. ✅ Export all 4 CSV files (see commands above)
2. ✅ Verify CSV files exist in `~/.tmp/`
3. ✅ Use `Surgery` field for treatment dates (NOT `Date_Th`)
4. ✅ Use `Dt_Diag` from tblTumour for first_seen_date (NOT tblWaitingTimes)
5. ✅ Map via `tblPatient`: `Hosp_No` → `PAS_No` → `patients.mrn`
6. ✅ Update ALL episodes for each patient (not just one episode)
7. ✅ Run with `--dry-run` first to verify mappings
8. ✅ Check completeness statistics match expected values
9. ✅ Verify surgeon names are full names, not ObjectIds
10. ✅ Recalculate urgency from date timing (don't use stored values)

---

## Common Pitfalls to Avoid

### ❌ DON'T:
1. Use `Date_Th` instead of `Surgery` for treatment dates (33% vs 77% populated)
2. Use `tblWaitingTimes` for first_seen_date (only 4 records vs 8,085 in tblTumour)
3. Import urgency values directly (they're incorrect - recalculate from dates)
4. Match directly by Hosp_No to MongoDB (use PAS_No/mrn via tblPatient)
5. Update only the first episode per patient (update all episodes)
6. Skip the `--dry-run` step (always preview first)

### ✅ DO:
1. Use `Surgery` field for all treatment dates (authoritative source)
2. Use `tblTumour.Dt_Diag` for first_seen_date (94% completeness)
3. Calculate urgency from admission/surgery date timing
4. Use 3-step matching: `Hosp_No` → `tblPatient` → `PAS_No` → `mrn`
5. Update all episodes for each matched patient
6. Always run `--dry-run` before `--confirm`
7. Verify statistics match expected completeness percentages

---

## Oncology & Follow-up Data (NOT YET MIGRATED)

### tblOncology (7,552 records available)
**Fields to migrate in future**:
- `RadioTh` → `treatment_type='radiotherapy'` 
- `RT_Start` → radiotherapy start date
- `RT_Finish` → radiotherapy end date
- `ChemoTh` → `treatment_type='chemotherapy'`
- `Ch_Start` → chemotherapy start date
- `Ch_Type` → chemotherapy regimen

### tblFollowUp (7,186 records available)
**Fields to migrate in future**:
- Recurrence data (local/distant)
- Metastases sites
- Subsequent treatments
- Long-term outcomes

These tables have high completeness and should be priority for next migration phase.

---

## Contact & Maintenance

**Script Location**: `/root/surg-db/execution/migrate_episode_data.py`  
**Documentation**: `/root/surg-db/execution/ACCESS_TO_MONGODB_FIELD_MAPPING.md`  
**Data Location**: `/root/surg-db/acpdb/acpdata_v3_db.mdb`  
**CSV Exports**: `~/.tmp/*.csv`

For questions or issues with field mappings, refer to this document first.
