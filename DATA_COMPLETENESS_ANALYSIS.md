# Data Completeness Analysis

**Date:** December 24, 2025  
**Current Database Status:** 31.35% overall completeness

## Executive Summary

Based on the Access database structure (`acpdata_v3_db.mdb`) and current MongoDB data quality report, significant data exists in the Access database that has not been migrated to the new system.

## Critical Missing Data

### 1. **Oncology Treatments (0% in MongoDB)**
**Access Table:** `tblOncology`  
**Fields Available in Access:**
- **Radiotherapy:**
  - `RadioTh` (Boolean) - Whether patient had radiotherapy
  - `RT_when` (Text) - Timing: Pre-op/Post-op/Palliative
  - `RT_Start` (DateTime) - Start date
  - `RT_Finish` (DateTime) - End date
  - `RT_Type` (Text) - Type of radiotherapy
  - `RT_Trial` (Boolean) - Whether part of trial

- **Chemotherapy:**
  - `ChemoTh` (Boolean) - Whether patient had chemotherapy
  - `Ch_When` (Text) - Timing: Pre-op (neoadjuvant)/Post-op (adjuvant)
  - `Ch_Start` (DateTime) - Start date
  - `Ch_Type` (Text) - Type of chemotherapy
  - `Ch_Trial` (Boolean) - Whether part of trial
  - `Ch_Trial_name` (Text) - Trial name

- **Other:**
  - `ref_onc` (Boolean) - Referred to oncology
  - `misc_info` (Text) - Additional information

**Records:** ~7,957 records (one per tumour/surgery)

**Impact:** HIGH - Oncology section on HomePage shows "No oncology treatments yet"

---

### 2. **MDT (Multidisciplinary Team) Data (0% in MongoDB)**
**Access Table:** `tblWaitingTimes`  
**Fields Available:**
- `MDT_Rev` (Boolean) - Whether MDT review occurred
- `MDT_Date` (DateTime) - Date of MDT meeting
- `Status` (Text) - Patient status code

**MongoDB Expected Fields (Currently Empty):**
- `mdt_discussion_date` - 0% complete (0/7957)
- `mdt_meeting_type` - 0% complete (0/7957)
- `mdt_team` - 0% complete (0/7957)

**Impact:** HIGH - MDT discussion is critical for cancer care pathways

---

### 3. **Follow-Up Data (Not in Current Schema)**
**Access Table:** `tblFollowUp`  
**Available Data:**
- **Recurrence Tracking:**
  - `Local` - Local recurrence
  - `LocalDat` - Date of local recurrence
  - `Distant` - Distant metastases
  - `DistDate` - Date of distant metastases
  - `DS_Liver`, `DS_Lung`, `DS_Bone`, `DS_Other` - Sites of metastases

- **Post-operative Complications:**
  - `WoundRec` - Wound recurrence
  - `PortRec` - Port-site recurrence

- **Further Treatments:**
  - `Ref_Pall` - Referred for palliative care
  - `Ref_livres` - Referred for liver resection
  - `Liv_res` - Had liver resection
  - `DateLivres` - Date of liver resection

- **Follow-up Mode:**
  - `CT_FU` - CT follow-up
  - `Col_FU` - Colonoscopy follow-up
  - `virtual_FU` - Virtual follow-up

**Impact:** HIGH - Essential for long-term outcomes tracking

---

### 4. **Referral & First Seen Data (Partially Complete)**
**Access Table:** `tblWaitingTimes`  
**Fields Available:**
- `Source` (Text) - Referral source code
- `GP_RDate` (DateTime) - GP referral date
- `Received` (DateTime) - Date received by hospital
- `RefType` (Text) - Type of referral
- `FS_Date` (DateTime) - First seen date
- `FS_Org` (Text) - First seen organization
- `RefOrg` (Text) - Referring organization

**Current MongoDB Status:**
- `referral_source`: 33.64% complete (2677/7957)
- `first_seen_date`: 14.68% complete (1168/7957)

**Impact:** MEDIUM - Affects waiting times reporting

---

### 5. **Enhanced Pathology Data (Partially in CSV)**
**Access Table:** `tblPathology`  
**Additional Fields Not in Current CSV:**
- `Haggit_level` - Haggitt level for polyp cancers
- `SM_polyp` - Submucosal invasion depth in polyps
- `Venous`, `Lymphatic`, `Perineural` - Invasion types (text descriptions)
- `BeyondMP` - Extension beyond muscularis propria
- `TNM_edition` - TNM staging edition used

**Current Status:** Pathology CSV has 7,614 records but may be missing these fields

**Impact:** MEDIUM - Important for staging and prognosis

---

### 6. **Performance Status (Nearly Empty)**
**MongoDB Field:** `performance_status`  
**Current Status:** 1.31% complete (104/7957)  
**Likely Source:** Not clearly identified in Access DB (may be in comments or notes)

**Impact:** LOW - Nice to have for surgical risk assessment

---

## Recommended Actions

### Priority 1 (Immediate - HIGH Impact)
1. **Migrate Oncology Data from `tblOncology`**
   - Create script to import chemotherapy and radiotherapy treatments
   - Add to treatments collection with `treatment_type: 'chemotherapy'` or `'radiotherapy'`
   - Will populate Oncology section on HomePage

2. **Migrate MDT Data from `tblWaitingTimes`**
   - Import `MDT_Date` → `mdt_discussion_date`
   - Parse `Status` codes to determine `mdt_meeting_type`
   - Populate MDT fields in episodes

3. **Migrate Follow-Up Data**
   - Create new `follow_ups` collection
   - Import recurrence, metastases, and subsequent treatment data
   - Link to episodes via `Hosp_No` and `TumSeqNo`

### Priority 2 (Soon - MEDIUM Impact)
4. **Complete Referral Data from `tblWaitingTimes`**
   - Import `Source` → `referral_source`
   - Import `FS_Date` → `first_seen_date`
   - Map referral source codes to readable descriptions

5. **Enhance Pathology Data**
   - Check if enhanced pathology fields should be added to current schema
   - Re-import pathology data with additional fields

### Priority 3 (Later - LOW Impact)
6. **Performance Status**
   - Manual data entry or ask clinicians for retrospective assessment
   - Consider making it prospective only

---

## Data Mapping Reference

### Access DB → MongoDB Field Mapping

| Access Table | Access Field | MongoDB Collection | MongoDB Field | Status |
|--------------|--------------|-------------------|---------------|--------|
| tblOncology | RadioTh, RT_* | treatments | treatment_type='radiotherapy', treatment_date, etc. | ❌ Not migrated |
| tblOncology | ChemoTh, Ch_* | treatments | treatment_type='chemotherapy', treatment_date, etc. | ❌ Not migrated |
| tblWaitingTimes | MDT_Date | episodes | mdt_discussion_date | ❌ Not migrated |
| tblWaitingTimes | Source | episodes | referral_source | ⚠️ 33.64% complete |
| tblWaitingTimes | FS_Date | episodes | first_seen_date | ⚠️ 14.68% complete |
| tblFollowUp | * | (new collection needed) | follow_ups | ❌ Not in schema |
| tblPathology | Enhanced fields | tumours | (enhance schema) | ⚠️ Partial |

---

## Next Steps

1. **Create migration scripts** for Priority 1 items
2. **Test** on subset of data (100-500 records)
3. **Validate** data integrity and mappings
4. **Run full migration** with backup
5. **Update data quality report** to verify improvements
6. **Update UI** to display new data (Oncology section, MDT info, Follow-up page)

---

## Expected Outcomes

After completing these migrations:
- **Overall Completeness:** Expected to increase from 31.35% to >70%
- **Oncology Section:** Will show actual chemotherapy/radiotherapy counts
- **MDT Category:** Will increase from 0% to ~95%+
- **Clinical Category:** Will improve with follow-up recurrence data
- **Enhanced Analytics:** Can track complete cancer care pathway

---

## Technical Notes

- All Access tables use `Hosp_No` (Hospital Number) as primary patient identifier
- `TumSeqNo` links to specific tumour records
- `Unit_ID` identifies the hospital unit (may be useful for multi-site analysis)
- DateTime fields in Access are in local time (no timezone)
- Boolean fields in Access are stored as TRUE/FALSE
- Many text fields use codes that need lookup tables for interpretation
