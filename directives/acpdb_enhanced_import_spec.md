# ACPDB Enhanced Import Specification

## Overview
This specification documents the enhanced fields and mappings for importing legacy ACPDB data into the new cancer episode structure.

## Data Sources
- **tblSurgery** (surgeries_export_new.csv): Surgery and treatment data
- **tblTumour** (tumours_export_new.csv): Tumour and referral pathway data
- **tblPatient** (patients_export_new.csv): Patient demographics

## Field Mappings

### 1. Lead Clinician
**Source**: `tblSurgery.Surgeon`  
**Target**: Episode-level `lead_clinician` field  
**Implementation**:
- Map surgeon name to legacy surgeon ID from `legacy_surgeons.json`
- Store as: `{surgeon_id: "LEGACY_XXX", surgeon_name: "Name"}`
- If surgeon not in mapping, use name directly with warning

### 2. Surgery Performed Flag
**Source**: `tblSurgery.SurgPerf`  
**Target**: Episode-level `surgery_performed` (boolean)  
**Mapping**:
- `1` = `true` (surgery performed)
- `0` or empty = `false` (no surgery)

### 3. No Treatment Reason
**Source**: `tblSurgery.NoSurg`  
**Target**: Episode-level `no_treatment_reason`  
**Mapping**:
- `1` or starts with `1` = "Patient refused treatment"
- `2` or starts with `2` = "Patient unfit"
- `3` or starts with `3` = "Advanced disease"
- `4` or starts with `4` = "Other"
- If empty/null and surgery_performed=false, set to null

### 4. No Treatment Reason (Other Detail)
**Source**: `tblSurgery.NoSurgS`  
**Target**: Episode-level `no_treatment_reason_detail`  
**Mapping**:
- Only populate if `no_treatment_reason` = "Other"
- Free text field
- If NoSurg=4 but NoSurgS is empty, set to null with warning

### 5. Referral Type
**Source**: `tblTumour.RefType`  
**Target**: Episode-level `referral_type`  
**Mapping**:
- Extract from format like "1 Elective", "5 Other"
- Strip number prefix, store clean text
- If empty, set to null

### 6. Referral Date
**Source**: `tblTumour.DtRef`  
**Target**: Episode-level `referral_date`  
**Format**: YYYY-MM-DD (existing parse_date function)

### 7. First Seen Date
**Source**: `tblTumour.Dt_Visit`  
**Target**: Episode-level `first_seen_date`  
**Format**: YYYY-MM-DD

### 8. MDT Discussion Date
**Source**: `tblTumour.Dt_Visit` (same as First Seen Date)  
**Target**: Episode-level `mdt_discussion_date`  
**Format**: YYYY-MM-DD
**Note**: Old system didn't distinguish between first seen and MDT date

### 9. MDT Meeting Type
**Source**: Hardcoded for bowel cancer import  
**Target**: Episode-level `mdt_meeting_type`  
**Value**: `"Colorectal MDT"` (constant for all records)

### 10. Treatment Intent
**Source**: `tblTumour.careplan`  
**Target**: Episode-level `mdt_outcome.treatment_intent`  
**Mapping**:
- Extract from format like "C curative"
- Strip prefix, capitalize properly
- Common values: "Curative", "Palliative", "Watch and Wait"

### 11. Treatment Plan
**Source**: `tblTumour.plan_treat`  
**Target**: Episode-level `mdt_outcome.treatment_plan`  
**Mapping**:
- Extract from format like "01 surgery"
- Strip number prefix
- Common values: "Surgery", "Chemotherapy", "Radiotherapy", "Combined"

### 12. Performance Status
**Source**: `tblTumour.performance`  
**Target**: Episode-level `performance_status`  
**Type**: Integer (0-4, ECOG scale)
**Validation**: Must be 0, 1, 2, 3, 4, or null

### 13. Referral Source
**Source**: `tblTumour.other` (free text)  
**Target**: Episode-level `referral_source`  
**Pattern Matching**:
- `BCSP` or `BOWEL SCREEN` → "Bowel Cancer Screening Programme"
- `GP2WW` or `2WW` or `TWO WEEK` → "2 Week Wait Referral"
- `EMERGENCY` or `A&E` → "Emergency"
- `GP` → "GP Referral"
- `SURVEILLANCE` → "Surveillance"
- Otherwise → Original text (trimmed)

### 14. Provider First Seen
**Source**: Hardcoded  
**Target**: Episode-level `provider_first_seen`  
**Value**: `"RHU"` (Portsmouth Hospitals University NHS Trust)  
**Note**: Changed from RYR to RHU per user correction

## Database Schema Changes

### Episode Collection Structure
```json
{
  "episode_id": "E-{patient_id}-{seq}",
  "patient_id": "{6-char-hash}",
  "condition_type": "cancer",
  "cancer_type": "bowel",
  
  // Existing fields...
  "referral_date": "YYYY-MM-DD",
  
  // NEW FIELDS
  "lead_clinician": {
    "clinician_id": "LEGACY_XXX",
    "name": "Surgeon Name"
  },
  "surgery_performed": true|false,
  "no_treatment_reason": "Patient refused treatment"|"Patient unfit"|"Advanced disease"|"Other"|null,
  "no_treatment_reason_detail": "free text"|null,
  "referral_type": "Elective"|"Emergency"|"Other"|null,
  "first_seen_date": "YYYY-MM-DD"|null,
  "mdt_discussion_date": "YYYY-MM-DD"|null,
  "mdt_meeting_type": "Colorectal MDT",
  "performance_status": 0-4|null,
  "referral_source": "parsed value"|null,
  "provider_first_seen": "RHU",
  
  "mdt_outcome": {
    "treatment_intent": "Curative"|"Palliative"|etc|null,
    "treatment_plan": "Surgery"|"Chemotherapy"|etc|null
  },
  
  "treatment_ids": ["SUR-{patient_id}-{seq}"],
  "tumour_ids": ["TUM-{patient_id}-{seq}"]
}
```

## Implementation Steps

### Phase 1: Data Preparation
1. ✅ Create `legacy_surgeons.json` mapping file (DONE)
2. Load legacy surgeon mappings in migrator __init__
3. Add new helper methods for value parsing

### Phase 2: Migration Script Updates
1. Update `migrate_tumours()` to store full tumour data in `self.tumour_data`
2. Update `migrate_surgeries()` to:
   - Look up tumour data by TumSeqNo
   - Extract all new fields from surgery and tumour rows
   - Build enriched episode document
3. Test with small dataset (10 records)

### Phase 3: Validation
1. Verify all 14 new fields populate correctly
2. Check null handling for missing data
3. Validate pattern matching for referral_source
4. Confirm MDT outcome structure

### Phase 4: Full Migration
1. Run complete migration on all 7,957 episodes
2. Verify data quality
3. Update API/frontend to display new fields

## Edge Cases & Validation Rules

1. **Missing Surgeon**: Warn but continue, set lead_clinician to {"clinician_id": null, "name": "Unknown"}
2. **NoSurg=4 but NoSurgS empty**: Warn, set no_treatment_reason_detail to null
3. **Invalid performance status**: Warn and set to null if not 0-4
4. **Dt_Visit null**: Both first_seen_date and mdt_discussion_date become null
5. **Tumour data missing for surgery**: Error - skip episode creation

## Testing Checklist

- [ ] Surgeon mapping works for common names (Howell, Watson, Aly)
- [ ] Surgery performed flag correctly identifies no-surgery cases
- [ ] No treatment reasons map to correct values (1-4)
- [ ] "Other" reason pulls NoSurgS detail text
- [ ] Referral source pattern matching catches BCSP, GP2WW, etc.
- [ ] Treatment intent/plan strip number prefixes correctly
- [ ] MDT meeting type always "Colorectal MDT"
- [ ] Provider first seen always "RHU"
- [ ] Null values handled gracefully throughout

## Migration Command
```bash
cd /root/surg-db
python3 execution/migrate_acpdb_to_mongodb_v4.py
```

## Rollback Plan
If migration fails:
1. Collections are cleared at start (existing behavior)
2. Re-run previous v3 migration if needed
3. Check `~/.tmp/migration_log_v4_*.json` for errors
