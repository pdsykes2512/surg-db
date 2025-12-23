# NBOCA COSD Data Items Mapping for Bowel Cancer

## Overview
This directive maps the National Bowel Cancer Audit (NBOCA) Key COSD (Cancer Outcomes and Services Dataset) data items to our cancer episode system. These are the standardized NHS data collection requirements for bowel cancer cases in England.

**Source Document:** NBOCA Key COSD Data Items V2.0 - January 2025

## Data Categories

### 1. Demographics

| COSD Code | COSD Field Name | Required For | Current System | Implementation Notes |
|-----------|----------------|--------------|----------------|---------------------|
| CR0010 | NHS NUMBER | All | ✅ `patient.nhs_number` | **Already exists with validation** |
| CR0100 | PERSON BIRTH DATE | All | ✅ `patient.demographics.date_of_birth` | **Already exists** |
| CR0080 | POSTCODE OF USUAL ADDRESS (AT DIAGNOSIS) | All | ✅ `patient.demographics.postcode` | **Already exists** - may need "at diagnosis" tracking |
| CR3170 | PERSON STATED GENDER CODE | All | ✅ `patient.demographics.gender` | **Already exists** |
| CR0150 | ETHNIC CATEGORY | All | ✅ `patient.demographics.ethnicity` | **Already exists** |

**Deprivation Index:** Calculated from postcode - needs integration with IMD lookup service

### 2. Patient Fitness

| COSD Code | COSD Field Name | Required For | Current System | Implementation Notes |
|-----------|----------------|--------------|----------------|---------------------|
| CR0510 | PERFORMANCE STATUS (ADULT) | All | `PerformanceStatus.ecog_score` | Already in episode model |
| CR6010 | ASA SCORE | Surgical patients | Missing | Add to SurgeryTreatment |

**Action:** Add ASA score to surgical treatment classification

### 3. Process Metrics

| COSD Code | COSD Field Name | Required For | Current System | Implementation Notes |
|-----------|----------------|--------------|----------------|---------------------|
| CR1410 | ORGANISATION SITE IDENTIFIER (PROVIDER FIRST SEEN) | All | Missing | Add to episode |
| CR1600 | SOURCE OF REFERRAL FOR OUT-PATIENTS | All | Missing | Add to episode |
| CR2050 | CLINICAL NURSE SPECIALIST INDICATION CODE | All | Missing | Add to episode |
| CR3190 | MULTIDISCIPLINARY TEAM MEETING TYPE | All | `episode.mdt_discussion_date` | Expand to include type |

**Action:** Add referral pathway tracking to episode model

### 4. Diagnosis Details

| COSD Code | COSD Field Name | Required For | Current System | Implementation Notes |
|-----------|----------------|--------------|----------------|---------------------|
| CR2030 | DATE OF PRIMARY DIAGNOSIS (CLINICALLY AGREED) | All | `BowelCancerData.diagnosis_date` | Add to cancer data |
| CR0370 | PRIMARY DIAGNOSIS (ICD) | All | `BowelCancerData.icd10_code` | Add ICD-10 code |
| CO5160 | TUMOUR HEIGHT ABOVE ANAL VERGE | Rectal (C20) only | `BowelCancerData.distance_from_anal_verge_cm` | Already exists |
| CR2070 | TNM VERSION NUMBER (STAGING) | All | `TNMStaging.version` | Add version field |
| CR0520 | T CATEGORY (FINAL PRETREATMENT) | All | `TNMStaging.clinical_t` | Already exists |
| CR0540 | N CATEGORY (FINAL PRETREATMENT) | All | `TNMStaging.clinical_n` | Already exists |
| CR0560 | M CATEGORY (FINAL PRETREATMENT) | All | `TNMStaging.clinical_m` | Already exists |
| CR6400 | MORPHOLOGY (SNOMED) DIAGNOSIS | All | `BowelCancerData.snomed_code` | Add SNOMED code |

**Action:** Add ICD-10 and SNOMED codes to diagnosis tracking

### 5. Treatment Planning

| COSD Code | COSD Field Name | Required For | Current System | Implementation Notes |
|-----------|----------------|--------------|----------------|---------------------|
| CR0460 | CANCER CARE PLAN INTENT | All | `TreatmentBase.treatment_intent` | Already exists |
| CR0470 | PLANNED CANCER TREATMENT TYPE | All | `TreatmentBase.treatment_type` | Already exists |
| CR0490 | NO CANCER TREATMENT REASON | All | Missing | Add to episode |
| CR0680 | CANCER TREATMENT INTENT | All | `TreatmentBase.treatment_intent` | Already exists |
| CR1450 | ORGANISATION SITE IDENTIFIER (OF PROVIDER) | All | Missing | Add to treatment |

**Action:** Add treatment refusal/non-treatment reason tracking

### 6. Surgery Details (Primary Focus)

| COSD Code | COSD Field Name | Required For | Current System | Implementation Notes |
|-----------|----------------|--------------|----------------|---------------------|
| CR0710 | PROCEDURE DATE | Surgical patients | `SurgeryTreatment.treatment_date` | Already exists |
| CR0720 | PRIMARY PROCEDURE (OPCS) | Surgical patients | `Procedure.opcs_code` | Add OPCS-4 code |
| CR6310 | SURGICAL ACCESS TYPE | Surgical patients | `Procedure.approach` | Already exists (open/laparoscopic/robotic) |
| CO6000 | SURGICAL URGENCY TYPE | Surgical patients | `Classification.urgency` | Already exists |
| pCR1150 | EXCISION MARGIN (CIRCUMFERENTIAL) | Resection patients | Missing | Add to Pathology |

**Action:** Add OPCS-4 procedure codes and circumferential resection margin status

### 7. Pathology Details (Post-Surgery)

| COSD Code | COSD Field Name | Required For | Current System | Implementation Notes |
|-----------|----------------|--------------|----------------|---------------------|
| pCR6820 | TNM VERSION NUMBER (PATHOLOGICAL) | Resection patients | `TNMStaging.version` | Add version field |
| pCR0910 | T CATEGORY (PATHOLOGICAL) | Resection patients | `TNMStaging.pathological_t` | Already exists |
| pCR0920 | N CATEGORY (PATHOLOGICAL) | Resection patients | `TNMStaging.pathological_n` | Already exists |
| pCR0930 | M CATEGORY (PATHOLOGICAL) | Resection patients | `TNMStaging.pathological_m` | Already exists |
| pCR0890 | NUMBER OF NODES EXAMINED | Resection patients | `BowelCancerData.lymph_nodes_examined` | Already exists |
| pCR0900 | NUMBER OF NODES POSITIVE | Resection patients | `BowelCancerData.lymph_nodes_positive` | Already exists |

**Action:** Ensure TNM version is captured for both clinical and pathological staging

## Implementation Priority

### Phase 1: Critical Fields (Required for NBOCA submission)
1. **Patient Demographics** ✅ COMPLETE
   - ✅ NHS Number (CR0010) - already implemented with validation
   - ✅ Postcode (CR0080) - already implemented
   - ✅ Ethnicity (CR0150) - already implemented
   - Note: May need "postcode at diagnosis" vs current postcode distinction

2. **Diagnosis**
   - ICD-10 primary diagnosis code (CR0370)
   - TNM version number (CR2070)
   - Date of diagnosis (CR2030)

3. **Surgery**
   - OPCS-4 primary procedure code (CR0720)
   - ASA score (CR6010)
   - Circumferential resection margin status (pCR1150)

### Phase 2: Process & Quality Metrics
1. Referral source (CR1600)
2. Organisation identifiers (CR1410, CR1450)
3. MDT meeting type (CR3190)
4. CNS involvement (CR2050)

### Phase 3: Enhanced Data
1. No treatment reason tracking (CR0490)
2. SNOMED morphology codes (CR6400)
3. Deprivation index calculation

## Data Validation Rules

### Mandatory Fields by Patient Group
- **All Patients:** Demographics, diagnosis date, TNM staging (clinical), ICD-10 code
- **Surgical Patients:** ASA score, procedure date, OPCS code, surgical access, urgency
- **Resection Patients:** CRM status, pathological TNM, node counts

### TNM Version Compliance
- As of January 1, 2018: TNMv8 should be submitted
- System must support TNMv7 for historical data
- Version field mandatory for all staging submissions

### Rectal Cancer Specific
- Tumour height above anal verge (CO5160) - mandatory for ICD-10 C20 (rectum)
- Should be recorded in cm

## Technical Implementation Notes

### Database Schema Updates Required

**Patient Model (backend/app/models/patient.py):**
```python
# ✅ Already implemented:
# nhs_number: str (required, validated)  # CR0010
# demographics.ethnicity: Optional[str]   # CR0150
# demographics.postcode: Optional[str]    # CR0080
# demographics.date_of_birth: str         # CR0100
# demographics.gender: str                # CR3170

# Potential enhancement:
# postcode_at_diagnosis: Optional[str]    # CR0080 - if different from current
```

**Episode Model (backend/app/models/episode.py):**
```python
# Process metrics
provider_first_seen: Optional[str]  # CR1410
referral_source: Optional[str]      # CR1600
cns_involved: Optional[bool]        # CR2050
mdt_meeting_type: Optional[str]     # CR3190
no_treatment_reason: Optional[str]  # CR0490
```

**BowelCancerData Model:**
```python
diagnosis_date: Optional[date]           # CR2030
icd10_code: Optional[str]                # CR0370
snomed_morphology_code: Optional[str]    # CR6400
```

**TNMStaging Model:**
```python
tnm_version: str = "8"  # CR2070, pCR6820 - default to v8
```

**SurgeryTreatment Model:**
```python
asa_score: Optional[int]  # CR6010 (1-5)
provider_organisation: Optional[str]  # CR1450
```

**Procedure Model (within surgery):**
```python
opcs_code: Optional[str]  # CR0720 - OPCS-4 procedure code
```

**Pathology Model:**
```python
circumferential_resection_margin: Optional[str]  # pCR1150 - clear/involved/uncertain
crm_distance_mm: Optional[float]  # Distance from tumor to CRM
```

### API Endpoints to Update

1. **POST /api/v2/episodes** - Add validation for NBOCA required fields
2. **GET /api/reports/nboca-export** - New endpoint for COSD export format
3. **GET /api/v2/episodes/{id}/cosd-completeness** - Data completeness checker

### Frontend Form Updates

1. **Patient Registration Form:**
   - Add NHS Number field
   - Add Ethnicity dropdown (use NHS Data Dictionary codes)
   - Add Postcode at diagnosis

2. **Episode Creation Form:**
   - Add referral source dropdown
   - Add provider organisation selector
   - Add MDT meeting type

3. **Bowel Cancer Diagnosis Form:**
   - Add ICD-10 code selector (C18.x, C19.x, C20.x)
   - Add TNM version dropdown (v7/v8)
   - Add diagnosis date

4. **Surgery Form:**
   - Add ASA score (1-5) dropdown
   - Add OPCS-4 procedure code search
   - Add CRM status for resections

5. **Pathology Results Form:**
   - Add CRM assessment fields
   - Ensure pathological TNM with version

## COSD Code Reference

### Common Procedure Codes (OPCS-4)
- H06: Right hemicolectomy
- H07: Left hemicolectomy
- H08: Sigmoid colectomy
- H09: Total colectomy
- H33: Anterior resection
- H40: Hartmann's procedure
- H60: Stoma formation

### ICD-10 Codes for Bowel Cancer
- C18.0-C18.9: Colon cancer (by site)
- C19: Rectosigmoid junction
- C20: Rectum

### ASA Grades
- 1: Normal healthy patient
- 2: Mild systemic disease
- 3: Severe systemic disease
- 4: Severe disease that is constant threat to life
- 5: Moribund patient not expected to survive without surgery

## Export Format

NBOCA submissions require XML format following COSD v9/v10 schema.

### Implementation Status: ✅ COMPLETE

**Backend:** `/root/backend/app/routes/exports.py`
- `GET /api/admin/exports/nboca-xml` - Generate COSD XML export
  - Query params: `start_date`, `end_date` (filter by diagnosis date)
  - Returns: XML file formatted to COSD v9/v10 standard
  - Downloads as: `nboca_export_YYYYMMDD_HHMMSS.xml`

- `GET /api/admin/exports/data-completeness` - Check data quality
  - Returns: Completeness metrics for mandatory COSD fields
  - Breakdown by: patient demographics, diagnosis, surgery

**Frontend:** Admin Page → Exports Tab
- Date range filter (diagnosis date)
- "Download NBOCA XML Export" button - generates XML file
- "Check Data Completeness" button - displays completeness report

### XML Structure
The export includes:
- **SubmissionMetadata:** Organisation code, extract date, record count
- **Patient Records:** For each bowel cancer episode:
  - **Patient Demographics:** NHS number, DOB, gender, ethnicity, postcode
  - **Episode Details:** Provider first seen, referral source, CNS involved, MDT meeting type, performance status
  - **Diagnosis:** ICD-10 code, SNOMED morphology, diagnosis date, TNM staging (clinical & pathological), tumour height, lymph nodes
  - **Treatments:** For each treatment in episode:
    - Surgery: OPCS-4 code, ASA score, approach, urgency, CRM status
    - Chemotherapy: Regimen, cycles planned
    - Radiotherapy: Total dose, fractions

### Field Mappings (XML → Database)
- Gender codes: male=1, female=2, other=9
- Approach codes: open=01, laparoscopic=02, laparoscopic_converted=03, robotic=04
- Urgency codes: elective=01, urgent=02, emergency=03
- CRM status: R0 (clear), R1 (involved)
- Dates: All formatted as YYYY-MM-DD

### Known Limitations
1. Organisation code defaults to "SYSTEM" - should be configured per trust
2. Type annotations for dict parameters generate warnings (non-blocking)
3. Requires authentication (admin role only)

### Usage Example
```typescript
// Frontend export call
const response = await axios.get(
  `${API_URL}/api/admin/exports/nboca-xml?start_date=2024-01-01&end_date=2024-12-31`,
  { headers: { Authorization: `Bearer ${token}` }, responseType: 'blob' }
)
```

### Testing Checklist
- ✅ Backend endpoint registered in main.py
- ✅ Frontend exports tab added to AdminPage
- ✅ Admin authentication required
- ✅ Date filtering functional
- ✅ XML generation includes all COSD mandatory fields
- ✅ Data completeness checker implemented

### Self-Annealing Notes
- **2024-12-23:** Initial implementation complete. XML structure follows COSD v9/v10 spec based on NBOCA mapping directive. All mandatory fields for bowel cancer episodes included. Data completeness checker provides pre-submission validation.

### Export Completeness Issues
If export shows incomplete data, check that your episodes have these mandatory fields populated:

**Demographics (All patients):**
- `patient.nhs_number` (CR0010)
- `patient.demographics.date_of_birth` (CR0100)
- `patient.demographics.gender` (CR3170)
- `patient.demographics.ethnicity` (CR0150)
- `patient.demographics.postcode` (CR0080)

**Diagnosis (All patients):**
- `episode.cancer_data.diagnosis_date` (CR2030)
- `episode.cancer_data.icd10_code` (CR0370) - e.g., C18.0, C19, C20
- `episode.cancer_data.tnm_staging.version` (CR2070) - "7" or "8"
- `episode.cancer_data.tnm_staging.clinical_t` (CR0520)
- `episode.cancer_data.tnm_staging.clinical_n` (CR0540)
- `episode.cancer_data.tnm_staging.clinical_m` (CR0560)

**Surgery (Surgical patients):**
- `treatment.treatment_date` (CR0710)
- `treatment.opcs4_code` (CR0720) - e.g., H06, H33
- `treatment.asa_score` (CR6010) - 1 to 5
- `treatment.approach` (CR6310) - open/laparoscopic/robotic
- `treatment.urgency` (CO6000) - elective/urgent/emergency

**Optional but Recommended:**
- `episode.provider_first_seen` (CR1410) - Organisation code
- `episode.referral_source` (CR1600)
- `episode.cns_involved` (CR2050)
- `episode.mdt_meeting_type` (CR3190)
- `episode.performance_status` (CR0510)
- `treatment.provider_organisation` (CR1450)
- `episode.cancer_data.snomed_morphology_code` (CR6400)
- `treatment.circumferential_resection_margin` (pCR1150) - for resections

**Pathology (Resection patients):**
- `episode.cancer_data.tnm_staging.pathological_t` (pCR0910)
- `episode.cancer_data.tnm_staging.pathological_n` (pCR0920)
- `episode.cancer_data.tnm_staging.pathological_m` (pCR0930)
- `episode.cancer_data.lymph_nodes_examined` (pCR0890)
- `episode.cancer_data.lymph_nodes_positive` (pCR0900)

## Data Quality Monitoring

### Completeness Metrics
- % episodes with NHS number
- % surgical patients with ASA score
- % resections with CRM status
- % episodes with complete TNM staging
- % episodes with ICD-10 codes

### Validation Alerts
- Missing mandatory fields
- Invalid code formats
- Date inconsistencies (e.g., surgery before diagnosis)
- TNM version mismatches

## Testing Requirements

1. **Unit Tests:** Validate COSD code formats
2. **Integration Tests:** XML export generation
3. **Data Quality Tests:** Completeness calculations
4. **Regression Tests:** Ensure existing surgery data preserved

## References

- NBOCA Key COSD Data Items V2.0 (January 2025)
- NHS Data Dictionary
- COSD v9/v10 Technical Output Specification
- TNM Classification 8th Edition

## Review Schedule

- **Next Review:** January 2026 (per NBOCA schedule)
- **Trigger Reviews:** COSD version updates, NHS Data Dictionary changes

---

**Status:** Draft - awaiting implementation
**Last Updated:** December 22, 2025
**Author:** System Analysis based on NBOCA COSD V2.0
