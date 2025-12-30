# Data Import Mapping Documentation

This directory contains comprehensive field-by-field mappings from the Access database (`acpdata_v3_db.mdb`) to the IMPACT MongoDB database, based on the working surgdb data structure.

## Purpose

These mapping files document exactly how each field in the IMPACT database is populated from the Access database, including:

- **Source fields** from Access DB tables
- **Transformation algorithms** (data cleaning, standardization)
- **Data types** and requirements
- **Function references** for complex mappings
- **Fields not currently mapped** with explanations

## Mapping Files

### 1. [patients_mapping.yaml](patients_mapping.yaml)
**Source:** `Table1` (primary patient demographics)
**Target:** `patients` collection
**Operation:** INSERT

Maps patient identifiers, demographics, contact information, and medical history.

**Key mappings:**
- `patient_id` ← Random 6-character alphanumeric ID, uppercase
- `nhs_number` ← `NHS_No` (with decimal removal)
- `demographics` ← `Forename`, `Surname`, `P_DOB`, `Sex`, etc.
- `contact.postcode` ← `Postcode`
- `medical_history` ← `Fam_Hist`, `Fam_Hist_positive`

**Important notes:**
- NHS number stored as Double in Access, requires `str(int(float(value)))` conversion
- Ethnicity not in Access DB, defaults to "Z" (Not stated)

---

### 2. [episodes_mapping.yaml](episodes_mapping.yaml)
**Source:** `tblTumour` (referral and MDT data portion)
**Target:** `episodes` collection
**Operation:** INSERT (then updated by treatments and follow-ups)

Maps care pathway/episode data including referral, MDT, and treatment planning.

**Key mappings:**
- `episode_id` ← `E-{patient_id}-{sequence:02d}`
- `referral_source` ← `RefType` (standardized to COSD values)
- `first_seen_date` ← `Dt_Visit` (fallback to `Dt_Diag`)
- `treatment_intent` ← `careplan` (curative/palliative)
- `treatment_plan` ← `plan_treat`
- `lead_clinician` ← populated later from `tblSurgery.Surgeon`

**Important notes:**
- Created before tumours and treatments (they reference episode_id)
- Later updated with `lead_clinician`, `no_treatment`, and `follow_up` data
- Mapping key: `(patient_id, TumSeqno) → episode_id`

---

### 3. [tumours_mapping.yaml](tumours_mapping.yaml)
**Source:** `tblTumour` (diagnosis and staging portion)
**Target:** `tumours` collection
**Operation:** INSERT (then updated by pathology)

Maps tumour diagnosis, clinical staging, imaging results, and metastases.

**Key mappings:**
- `tumour_id` ← `TUM-{patient_id}-{sequence:02d}`
- `diagnosis_date` ← `Dt_Diag`
- `site` ← `TumSite` (standardized)
- `clinical_t/n/m` ← `preTNM_T/N/M` (pre-treatment staging)
- `pathological_t/n/m` ← populated later from `tblPathology`
- `imaging_results` ← CT, MRI data from various fields
- `distant_metastases` ← `DM_Liver`, `DM_Lung`, etc.

**Important notes:**
- `tblTumour` serves dual purpose (episode + tumour data)
- Pathological staging initially null, updated by pathology import
- After creation, `tumour_id` pushed to `episode.tumour_ids` array

---

### 4. [treatments_mapping.yaml](treatments_mapping.yaml)
**Source:** `tblSurgery` (surgical treatment data)
**Target:** `treatments` collection
**Operation:** INSERT

Maps surgical treatments with comprehensive perioperative and outcome data.

**Key mappings:**
- `treatment_id` ← `T-{patient_id}-{sequence:02d}`
- `treatment_date` ← `Surgery`
- `opcs4_code`, `asa_score` ← COSD mandatory fields
- `classification.urgency` ← `ModeOp`
- `classification.approach` ← **Priority logic:** Robotic → Conversion → Laparoscopic
- `procedure.stoma_type` ← `StomDone` (**NOT** `StomType`)
- `procedure.defunctioning_stoma` ← `Anastom AND Stoma` (both must be true)
- `outcomes.readmission_30day` ← `Post_IP` (**NOT** `Major_C`)
- `team.primary_surgeon` ← `Surgeon` (matched to clinicians)

**Important notes:**
- Surgical approach has complex priority logic (robotic first!)
- Use `StomDone` (what was done) not `StomType` (what was planned)
- Defunctioning stoma only if BOTH anastomosis AND stoma created
- After creation, updates `episode.lead_clinician` and `episode.no_treatment`

---

### 5. [investigations_mapping.yaml](investigations_mapping.yaml)
**Source:** `tblTumour` (imaging dates and results)
**Target:** `investigations` collection
**Operation:** INSERT

Extracts imaging investigations from tumour table into separate investigation records.

**Four investigation types created per tumour:**
1. **CT Abdomen** (`ct_abdomen`) ← `Dt_CT_Abdo`
2. **CT Colonography** (`ct_colonography`) ← `Dt_CT_pneumo`
3. **Colonoscopy** (`colonoscopy`) ← `Date_Col`
4. **MRI Primary** (`mri_primary`) ← `Dt_MRI1` with TNM findings

**Key mappings:**
- `investigation_id` ← `INV-{patient_id}-{type}-{seq:02d}`
- `result` ← cleaned via `clean_result_text()` (removes "1 Normal" → "normal")
- `findings` ← structured MRI data (T/N stage, CRM, EMVI)

**Important notes:**
- Investigations only created if date field is not null
- Result text cleaning removes leading numbers from Access DB codes
- MRI findings stored as structured object, others as simple text
- Bug fix: TumSeqno must be number not string for mapping lookup

---

### 6. [pathology_mapping.yaml](pathology_mapping.yaml)
**Source:** `tblPathology` (histopathology results)
**Target:** `tumours` collection
**Operation:** UPDATE

Updates existing tumour records with pathological staging and histology.

**Key mappings:**
- `pathological_t/n/m` ← `TNM_Tumr/Nods/Mets` (post-surgery staging)
- `grade` ← `HistGrad` (g1/g2/g3/g4)
- `histology_type` ← `HistType` (standardized)
- `lymph_nodes_examined/positive` ← `NoLyNoF/NoLyNoP` (COSD quality metrics)
- `lymphovascular_invasion` ← `VasInv` (present/absent/uncertain)
- `crm_status` ← `Mar_Cir` (critical for rectal cancer)
- `resection_grade` ← `resect_grade` (R0/R1/R2)

**Important notes:**
- UPDATE operation, not INSERT (finds existing tumour via `tumour_mapping`)
- Matching: `(patient_id, TumSeqNo) → tumour_id`
- All invasion fields use enum: present/absent/uncertain
- CRM ≤1mm = involved (critical prognostic factor)

---

### 7. [oncology_mapping.yaml](oncology_mapping.yaml)
**Source:** `tblOncology` (radiotherapy and chemotherapy)
**Target:** `treatments` collection
**Operation:** INSERT

Creates radiotherapy and chemotherapy treatment records.

**Each oncology record can create TWO treatments:**
1. **Radiotherapy** (if `RadioTh = true` and `RT_Start` not null)
2. **Chemotherapy** (if `ChemoTh = true` and `Ch_Start` not null)

**Key mappings:**

**Radiotherapy:**
- `treatment_id` ← `T-{patient_id}-{1000+seq}` (uses 1000+ to avoid collision)
- `timing` ← `RT_when` (neoadjuvant/adjuvant/palliative)
- `technique` ← `RT_Type` (long_course/short_course/contact)
- `start_date`, `end_date` ← `RT_Start`, `RT_Finish`
- `trial_enrollment` ← `RT_Trial`

**Chemotherapy:**
- `treatment_id` ← `T-{patient_id}-{1000+seq}`
- `timing` ← `Ch_When`
- `regimen.regimen_name` ← `Ch_Type` (FOLFOX, CAPOX, etc.)
- `trial_enrollment` ← `Ch_Trial`
- `trial_name` ← `Ch_Trial_name`

**Important notes:**
- One tblOncology record can create 2 treatment records
- Treatment IDs use 1000+ sequence to avoid surgery ID collisions
- Both treatments linked to same episode via `treatment_ids` array

---

### 8. [followup_mapping.yaml](followup_mapping.yaml)
**Source:** `tblFollowUp` (post-treatment follow-up)
**Target:** `episodes` collection
**Operation:** UPDATE (append to `follow_up` array)

Appends follow-up records to episode's `follow_up` array.

**Key mappings:**
- `follow_up_date` ← `Date_FU`
- `modality` ← `ModeFol` (clinic/telephone/other)
- `local_recurrence` ← `Local`, `LocalDat`, `LocalDia`
- `distant_recurrence.sites` ← `DS_Liver`, `DS_Lung`, `DS_Bone`, `DS_Other`
- `investigations.ct` ← `CT_FU`, `CT_date`
- `investigations.colonoscopy` ← `Col_FU`, `Col_Date`
- `palliative_referral` ← `Ref_Pall`, `Dat_Pall`

**Important notes:**
- Multiple follow-up records per episode (array of objects)
- Recurrence data critical for outcomes tracking
- Follow-up investigations separate from diagnostic investigations
- Palliative referral indicates shift from curative to palliative care

---

## Import Sequence

The mappings must be executed in this specific order due to dependencies:

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

## Key Mapping Tables

### Patient Mapping
- **Purpose:** Link Access DB hospital numbers to IMPACT patient IDs
- **Format:** `hosp_no_to_patient_id[hosp_no] = patient_id`
- **Used by:** All subsequent imports

### Episode Mapping
- **Purpose:** Link Access DB tumour records to IMPACT episodes
- **Format:** `episode_mapping[(patient_id, tum_seqno)] = episode_id`
- **Used by:** Tumours, Treatments, Oncology, Investigations, Follow-up

### Tumour Mapping
- **Purpose:** Link Access DB tumour records to IMPACT tumour IDs
- **Format:** `tumour_mapping[(patient_id, tum_seqno)] = tumour_id`
- **Used by:** Pathology, Investigations

### Clinician Mapping
- **Purpose:** Match surgeon names to clinician IDs
- **Format:** `clinician_mapping[name.lower()] = clinician_id`
- **Used by:** Treatments (surgeon matching)

## Data Transformation Functions

These mapping files reference standard transformation functions:

### Date Functions
- `parse_date()` - Convert various date formats to YYYY-MM-DD
- `parse_dob()` - Parse date of birth specifically
- `calculate_age()` - Calculate age from DOB

### Gender/Demographics
- `parse_gender()` - Map M/F to male/female

### COSD Standardization
- `map_referral_source()` - gp/consultant/screening/emergency/other
- `map_referral_priority()` - routine/urgent/two_week_wait
- `map_urgency()` - elective/urgent/emergency
- `map_tumour_site()` - sigmoid_colon, rectum, etc.
- `map_tnm_stage()` - Clean TNM values ("3", "4a", etc.)
- `map_grade()` - g1/g2/g3/g4
- `map_histology_type()` - adenocarcinoma, mucinous_adenocarcinoma, etc.

### Yes/No Standardization
- `map_yes_no()` - Convert booleans to "yes"/"no" strings
- `map_crm_status()` - yes/no/uncertain
- `map_invasion_status()` - present/absent/uncertain

### Treatment Mappings
- `map_treatment_intent()` - curative/palliative
- `map_asa()` - ASA score 1-5
- `determine_surgical_approach()` - **Priority logic:** robotic → converted → laparoscopic
- `map_surgeon_grade()` - consultant/specialist_registrar/other
- `map_stoma_type()` - ileostomy/colostomy/other
- `is_defunctioning_stoma()` - yes if BOTH anastomosis AND stoma
- `map_resection_grade()` - r0/r1/r2

### Oncology Mappings
- `map_treatment_timing()` - neoadjuvant/adjuvant/palliative
- `map_rt_technique()` - long_course/short_course/contact

### Follow-up Mappings
- `map_followup_modality()` - clinic/telephone/other

## Critical User-Requested Fixes

These fixes were identified through data quality review:

1. **NHS Number Decimal Removal**
   - Access stores as Double (adds .0)
   - Fix: `str(int(float(nhs_number)))`

2. **Surgical Approach Priority Logic**
   - Must check Robotic field FIRST
   - Then check for "converted to open" in LapType
   - Finally use LapProc mapping
   - Function: `determine_surgical_approach()`

3. **Stoma Type Field**
   - Use `StomDone` (what was actually done)
   - NOT `StomType` (what was planned)

4. **Defunctioning Stoma Logic**
   - Only return 'yes' if BOTH `Anastom` AND `Stoma` are true
   - Function: `is_defunctioning_stoma()`

5. **Readmission Field**
   - Use `Post_IP` (in-patient readmission)
   - NOT `Major_C` (major complication)

6. **Lead Clinician Matching**
   - Case-insensitive match to active clinicians
   - Fallback to free text if no match
   - Store clinician ID if matched, text name if not

7. **Investigation Result Cleaning**
   - Remove leading numbers from Access DB codes
   - Example: "1 Normal" → "normal"
   - Function: `clean_result_text()`

8. **TumSeqno Type**
   - Use as number: `row.get('TumSeqno', 0)`
   - NOT as string: `str(row.get('TumSeqno', ''))`
   - Critical for mapping lookups

## Files Not Used

These Access DB tables are NOT currently imported:

- `tblPossum` - POSSUM score (physiological scoring system)
- `tblWaitingTimes` - Waiting times data (partially in episodes)
- `tblHospNo` - Foreign hospital numbers (not relevant for single-site)
- `tblUnitDetails` - Unit details (single-site database)
- `tlkpUsers` - User lookup (not relevant for IMPACT)
- `Switchboard Items` - Access UI navigation (irrelevant)

## Usage

These mapping files serve as:

1. **Import Script Reference** - Guides implementation of import logic
2. **Data Dictionary** - Documents field meanings and sources
3. **Quality Assurance** - Verifies correct field mappings
4. **Troubleshooting** - Explains transformation algorithms
5. **Continuity** - Maintains knowledge across AI sessions

When creating a new import script, follow these mappings exactly to ensure:
- Correct field sources
- Proper data transformations
- COSD compliance
- Data quality standards
- Compatibility with surgdb structure

## Next Steps

With these mappings complete, you can now:

1. Create a new clean import script based on these mappings
2. Validate each mapping against the Access DB
3. Test imports on a development database
4. Verify data quality at each stage
5. Run production import with confidence

All transformations are documented - no guesswork needed!
