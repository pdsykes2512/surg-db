# COSD Export Functionality Documentation

**Version:** 1.6.2
**Last Updated:** January 2026
**Document Status:** Production
**COSD Version:** v9 / v10 Compatible

---

## Table of Contents

1. [Overview](#overview)
2. [COSD Data Structure](#cosd-data-structure)
3. [NBOCA Field Mapping](#nboca-field-mapping)
4. [Export Functionality](#export-functionality)
5. [Data Validation](#data-validation)
6. [XML Schema Reference](#xml-schema-reference)
7. [Export Process](#export-process)
8. [Troubleshooting](#troubleshooting)
9. [NBOCA Submission Checklist](#nboca-submission-checklist)

---

## Overview

### What is COSD?

**COSD** (Cancer Outcomes and Services Dataset) is the NHS national standard for collecting and reporting cancer data in England. COSD data is submitted to the National Cancer Registration and Analysis Service (NCRAS) for:

- National cancer registration
- Cancer outcomes analysis
- Clinical audit (e.g., National Bowel Cancer Audit - NBOCA)
- Quality improvement
- Commissioning and planning

### NBOCA Compliance

The National Bowel Cancer Audit (NBOCA) is a mandated clinical audit for all NHS Trusts treating bowel cancer patients. IMPACT provides full NBOCA COSD v9/v10 compliance with all 59 mandatory fields implemented.

**Legal Requirement:** NHS Act 2006 Section 13Z requires all NHS Trusts to participate in national clinical audits including NBOCA.

### COSD Versions Supported

- **COSD v9.0** - Primary support
- **COSD v10.0** - Compatible (minor differences handled automatically)

---

## COSD Data Structure

### Data Hierarchy

```xml
<COSDSubmission version="9.0">
  <SubmissionMetadata>
    <OrganisationCode>RHU</OrganisationCode>
    <ExtractDate>2026-01-07</ExtractDate>
    <RecordCount>1250</RecordCount>
  </SubmissionMetadata>

  <Records>
    <CancerRecord>
      <!-- Patient Demographics -->
      <Patient>
        <NHSNumber>1234567890</NHSNumber>
        <PersonBirthDate>1965-03-15</PersonBirthDate>
        <PersonStatedGenderCode>1</PersonStatedGenderCode>
        <EthnicCategory>A</EthnicCategory>
        <PostcodeOfUsualAddress>PO1 3LY</PostcodeOfUsualAddress>
      </Patient>

      <!-- Clinical Episode -->
      <Episode>
        <LocalPatientIdentifier>E-ABC123-01</LocalPatientIdentifier>
        <ProviderFirstSeen>RHU</ProviderFirstSeen>
        <SourceOfReferral>gp</SourceOfReferral>
        <CNSIndicationCode>01</CNSIndicationCode>
        <MDTMeetingType>colorectal</MDTMeetingType>
        <PerformanceStatusAdult>1</PerformanceStatusAdult>

        <!-- Diagnosis and Staging -->
        <Diagnosis>
          <PrimaryDiagnosisDate>2025-06-15</PrimaryDiagnosisDate>
          <PrimaryDiagnosisICD>C18.7</PrimaryDiagnosisICD>
          <MorphologySNOMED>81403</MorphologySNOMED>
          <TumourSite>sigmoid_colon</TumourSite>

          <!-- TNM Staging -->
          <TNMStaging>
            <TNMVersionNumber>8</TNMVersionNumber>
            <TCategoryFinalPretreatment>3</TCategoryFinalPretreatment>
            <NCategoryFinalPretreatment>1a</NCategoryFinalPretreatment>
            <MCategoryFinalPretreatment>0</MCategoryFinalPretreatment>
            <TCategoryPathological>3</TCategoryPathological>
            <NCategoryPathological>1a</NCategoryPathological>
            <MCategoryPathological>0</MCategoryPathological>
          </TNMStaging>

          <!-- Pathology -->
          <Pathology>
            <DifferentiationGrade>moderate</DifferentiationGrade>
            <NumberOfNodesExamined>18</NumberOfNodesExamined>
            <NumberOfNodesPositive>2</NumberOfNodesPositive>
            <CircumferentialResectionMargin>clear</CircumferentialResectionMargin>
            <LymphovascularInvasion>absent</LymphovascularInvasion>
            <PerineuralInvasion>present</PerineuralInvasion>
            <KRASStatus>wild_type</KRASStatus>
            <BRAFStatus>mutant</BRAFStatus>
            <MismatchRepairStatus>proficient</MismatchRepairStatus>
          </Pathology>
        </Diagnosis>

        <!-- Treatments -->
        <Treatments>
          <Treatment>
            <TreatmentType>SURGERY</TreatmentType>
            <TreatmentDate>2025-07-20</TreatmentDate>
            <TreatmentIntent>curative</TreatmentIntent>
            <ProviderOrganisation>RHU</ProviderOrganisation>

            <Surgery>
              <PrimaryProcedureOPCS>H08</PrimaryProcedureOPCS>
              <ASAScore>2</ASAScore>
              <SurgicalAccessType>02</SurgicalAccessType>
              <SurgicalUrgencyType>01</SurgicalUrgencyType>
            </Surgery>
          </Treatment>
        </Treatments>
      </Episode>
    </CancerRecord>
  </Records>
</COSDSubmission>
```

---

## NBOCA Field Mapping

### Patient Demographics Fields

| COSD Code | Field Name | IMPACT Field | Required | Data Type | Example |
|-----------|-----------|--------------|----------|-----------|---------|
| **CR0010** | NHS Number | `patients.nhs_number` | ✅ Mandatory | String (10 digits) | 1234567890 |
| **CR0100** | Date of Birth | `patients.demographics.date_of_birth` | ✅ Mandatory | Date (YYYY-MM-DD) | 1965-03-15 |
| **CR3170** | Gender | `patients.demographics.gender` | ✅ Mandatory | Code (1/2/9) | 1=Male, 2=Female, 9=Other |
| **CR0150** | Ethnicity | `patients.demographics.ethnicity` | ✅ Mandatory | Code (A-S) | A=White British |
| **CR0080** | Postcode | `patients.demographics.postcode` | ✅ Mandatory | String | PO1 3LY |

### Referral Pathway Fields

| COSD Code | Field Name | IMPACT Field | Required | Data Type | Example |
|-----------|-----------|--------------|----------|-----------|---------|
| **CR1600** | Referral Source | `episodes.referral_source` | 🟡 Recommended | Enum | gp/consultant/screening/two_week_wait/emergency |
| **CR1410** | Provider First Seen | `episodes.provider_first_seen` | 🟡 Recommended | NHS Code | RHU (Royal Hospital for Neurodisability) |
| **CR2050** | CNS Involved | `episodes.cns_involved` | 🟡 Recommended | Code (01/02/99) | 01=Yes, 02=No, 99=Unknown |
| **CR3190** | MDT Meeting Type | `episodes.mdt_meeting_type` | 🟡 Recommended | Enum | colorectal/upper_gi/lower_gi/combined |
| **CR0510** | Performance Status | `episodes.performance_status` | 🟡 Recommended | ECOG (0-5) | 1 (Ambulatory, light work) |
| **CR0490** | No Treatment Reason | `episodes.no_treatment_reason` | ⚪ Optional | Text | Patient declined/Unfit for treatment |

### Diagnosis Fields

| COSD Code | Field Name | IMPACT Field | Required | Data Type | Example |
|-----------|-----------|--------------|----------|-----------|---------|
| **CR2030** | Diagnosis Date | `tumours.diagnosis_date` | ✅ Mandatory | Date (YYYY-MM-DD) | 2025-06-15 |
| **CR0370** | ICD-10 Code | `tumours.icd10_code` | ✅ Mandatory | ICD-10 | C18.7 (Sigmoid colon) |
| **CR6400** | SNOMED Morphology | `tumours.snomed_morphology` | 🟡 Recommended | SNOMED Code | 81403 (Adenocarcinoma NOS) |

### TNM Staging Fields

| COSD Code | Field Name | IMPACT Field | Required | Data Type | Example |
|-----------|-----------|--------------|----------|-----------|---------|
| **CR2070** | TNM Version | `tumours.tnm_version` | ✅ Mandatory | Integer (7 or 8) | 8 |
| **CR0520** | Clinical T Stage | `tumours.clinical_t` | ✅ Mandatory | TNM Code | T3 → stored as "3" |
| **CR0540** | Clinical N Stage | `tumours.clinical_n` | ✅ Mandatory | TNM Code | N1a → stored as "1a" |
| **CR0560** | Clinical M Stage | `tumours.clinical_m` | ✅ Mandatory | TNM Code | M0 → stored as "0" |
| **pCR6820** | Pathological T | `tumours.pathological_t` | 🟡 Recommended | TNM Code | pT3 → stored as "3" |
| **pCR0910** | Pathological N | `tumours.pathological_n` | 🟡 Recommended | TNM Code | pN1a → stored as "1a" |
| **pCR0920** | Pathological M | `tumours.pathological_m` | 🟡 Recommended | TNM Code | pM0 → stored as "0" |

**Note:** IMPACT stores TNM stages as simple numbers/letters (e.g., "3", "1a", "0"). The frontend and export add prefixes (T, N, M, p) for display and COSD compliance.

### Pathology Fields

| COSD Code | Field Name | IMPACT Field | Required | Data Type | Example |
|-----------|-----------|--------------|----------|-----------|---------|
| **pCR0930** | Grade/Differentiation | `tumours.grade` | ✅ Mandatory | Enum | well/moderate/poor/undifferentiated |
| **pCR0890** | Nodes Examined | `tumours.lymph_nodes_examined` | 🟡 Recommended | Integer | 18 |
| **pCR0900** | Nodes Positive | `tumours.lymph_nodes_positive` | 🟡 Recommended | Integer | 2 |
| **pCR1150** | CRM Status | `tumours.crm_status` | ✅ Mandatory (rectal) | Enum | clear/involved/close |
| | CRM Distance | `tumours.crm_distance_mm` | 🟡 Recommended | Float (mm) | 5.2 |
| | LVI | `tumours.lymphovascular_invasion` | ⚪ Optional | Enum | present/absent/uncertain |
| | PNI | `tumours.perineural_invasion` | ⚪ Optional | Enum | present/absent/uncertain |
| | KRAS Status | `tumours.kras_status` | ⚪ Optional | Enum | wild_type/mutant/unknown |
| | BRAF Status | `tumours.braf_status` | ⚪ Optional | Enum | wild_type/mutant/unknown |
| | MMR Status | `tumours.mismatch_repair_status` | ⚪ Optional | Enum | proficient/deficient/unknown |

**CRM Status Note:** Circumferential Resection Margin (CRM) is **mandatory for rectal cancer** (ICD-10 codes C19, C20). The validator will flag missing CRM for rectal cancers as an error.

### Treatment Fields (Surgery)

| COSD Code | Field Name | IMPACT Field | Required | Data Type | Example |
|-----------|-----------|--------------|----------|-----------|---------|
| **CR0710** | Surgery Date | `treatments.treatment_date` | ✅ Mandatory (surgery) | Date (YYYY-MM-DD) | 2025-07-20 |
| **CR0720** | OPCS-4 Code | `treatments.procedure.opcs_codes[0]` | ✅ Mandatory (surgery) | OPCS-4 | H08 (Laparoscopic sigmoid colectomy) |
| **CR6010** | ASA Score | `treatments.intraoperative.asa_score` | ✅ Mandatory (surgery) | Integer (1-5) | 2 |
| **CR6310** | Surgical Approach | `treatments.procedure.approach` | 🟡 Recommended | Code (01-04) | 02=Laparoscopic |
| **CO6000** | Urgency | `treatments.classification.urgency` | 🟡 Recommended | Code (01-03) | 01=Elective |
| **CR1450** | Provider Organisation | `treatments.provider_organisation` | 🟡 Recommended | NHS Code | RHU |

**Surgical Approach Codes:**
- `01` = Open
- `02` = Laparoscopic
- `03` = Laparoscopic converted to open
- `04` = Robotic

**Urgency Codes:**
- `01` = Elective
- `02` = Urgent
- `03` = Emergency

### Surgery Type Normalization for COSD Export

IMPACT uses internal surgery types (`surgery_primary`, `surgery_rtt`, `surgery_reversal`) for relationship tracking. These are **normalized to "SURGERY"** during COSD export:

```typescript
// Internal types (IMPACT database)
treatment_type: "surgery_primary" | "surgery_rtt" | "surgery_reversal"

// COSD export (normalized)
<TreatmentType>SURGERY</TreatmentType>
```

**Reason:** COSD standard does not distinguish between primary surgeries, return to theatre, or stoma reversals—all are reported as "SURGERY" with OPCS-4 codes differentiating procedures.

---

## Export Functionality

### NBOCA XML Export Endpoint

**Endpoint:** `GET /api/admin/exports/nboca-xml`

**Authentication:** Admin role required

**Query Parameters:**
- `start_date` (optional): Filter episodes from this date (YYYY-MM-DD)
- `end_date` (optional): Filter episodes until this date (YYYY-MM-DD)

**Response:** XML file download (COSD v9/v10 format)

**Filename Format:** `nboca_export_YYYYMMDD_HHMMSS.xml`

### Export Logic

#### Episode Selection

```python
# Base query: Cancer episodes only
query = {"condition_type": "cancer"}

# Prefer bowel cancer if available
bowel_count = await db.episodes.count_documents({
    "condition_type": "cancer",
    "cancer_type": "bowel"
})
if bowel_count > 0:
    query["cancer_type"] = "bowel"

# Date filtering (if specified)
if start_date or end_date:
    query["$or"] = [
        {"referral_date": date_range},      # String comparison
        {"first_seen_date": date_range},
        {"diagnosis_date": date_range},
        {"created_at": datetime_range}       # Datetime comparison
    ]
```

**Date Filtering Note:** Most date fields in IMPACT are stored as ISO strings (e.g., "2025-06-15"), but `created_at` is stored as datetime objects. The export logic handles both formats.

#### Treatment Filtering

Only treatments with valid OPCS-4 codes are included in the export:

```python
treatments_cursor = db.treatments.find({
    "episode_id": episode_id,
    "opcs4_code": {"$exists": True, "$ne": ""}
})
```

**Reason:** OPCS-4 code is **mandatory** for all surgical treatments in COSD submissions. Treatments without OPCS-4 codes (e.g., incomplete data entry) are excluded to prevent validation errors.

#### Data Decryption

Patient identifiers (NHS number, MRN, postcode, DOB) are **encrypted at rest** using AES-256. These fields are **decrypted during export**:

```python
# Decrypt sensitive fields for export
patient = decrypt_document(patient)
```

The decrypted data is used only for XML generation and is not stored in plaintext.

### XML Generation Process

1. **Fetch Episodes**: Query cancer episodes (with optional date filter)
2. **Fetch Related Data**: For each episode, fetch:
   - Patient demographics (with decryption)
   - Tumours (TNM staging, pathology)
   - Treatments (with valid OPCS-4 codes only)
3. **Generate XML Structure**:
   - Create root `<COSDSubmission>` element
   - Add submission metadata (org code, date, count)
   - For each episode, create `<CancerRecord>` with:
     - Patient demographics
     - Episode referral pathway
     - Diagnosis and TNM staging (from tumours)
     - Pathology results
     - Treatment details (surgery/chemo/radio)
4. **Pretty Print XML**: Format with indentation for readability
5. **Return Response**: XML file download with appropriate headers

---

## Data Validation

### Pre-Export Validation

Before generating COSD XML, use the **NBOCA Validator** to identify errors and warnings:

**Endpoint:** `GET /api/admin/exports/nboca-validator`

**Authentication:** Admin role required

**Response:**
```json
{
  "summary": {
    "total_episodes": 1250,
    "valid_episodes": 1150,
    "episodes_with_errors": 50,
    "episodes_with_warnings": 50,
    "valid_percentage": 92.0,
    "submission_ready": false
  },
  "episodes": [
    {
      "episode_id": "E-ABC123-01",
      "patient_id": "ABC123",
      "errors": [
        "NHS Number missing",
        "Clinical T stage missing",
        "OPCS-4 code missing"
      ],
      "warnings": [
        "Ethnicity missing (recommended)",
        "Low lymph node yield: 8 (minimum 12 recommended)"
      ]
    }
  ]
}
```

### Validation Rules

#### Mandatory Fields (Errors)

**Patient Demographics:**
- NHS Number (10 digits, no spaces)
- Date of Birth (valid date format)
- Gender (male/female/other)
- Postcode (valid UK postcode format)

**Diagnosis:**
- Diagnosis Date (valid date, before treatment)
- ICD-10 Code (valid colorectal cancer code: C18.x-C20)
- TNM Version (7 or 8)
- Clinical T, N, M stages (all three required)
- Grade/Differentiation

**Surgery (if surgical treatment):**
- Surgery Date
- OPCS-4 Code (valid procedure code)
- ASA Score (1-5)

**Rectal Cancer Specific:**
- CRM Status (mandatory for ICD-10 codes C19, C20)

#### Recommended Fields (Warnings)

**Referral Pathway:**
- Referral Source
- Provider First Seen
- MDT Discussion Date
- MDT Meeting Type
- Performance Status

**Staging:**
- Pathological T, N, M stages (recommended after surgery)

**Pathology:**
- Lymph Nodes Examined (minimum 12 recommended)
- Lymph Nodes Positive
- CRM Distance (if CRM clear)

#### Date Logic Validation

- **Treatment Date ≥ Diagnosis Date**: Treatment cannot be before diagnosis
- **Surgery Date ≥ Admission Date**: Surgery on or after admission
- **Discharge Date ≥ Surgery Date**: Discharge after surgery

#### Code Validation

**Valid ICD-10 Codes for Bowel Cancer:**
```
C18.0 - Caecum
C18.1 - Appendix
C18.2 - Ascending colon
C18.3 - Hepatic flexure
C18.4 - Transverse colon
C18.5 - Splenic flexure
C18.6 - Descending colon
C18.7 - Sigmoid colon
C18.8 - Overlapping lesion of colon
C18.9 - Colon, unspecified
C19   - Rectosigmoid junction
C20   - Rectum
```

**Valid OPCS-4 Codes (Common Colorectal Procedures):**
```
H01 - Total excision of colon
H02 - Extended excision of colon
H04 - Total excision of colon and rectum
H05 - Excision of caecum
H06 - Excision of right hemicolon
H07 - Excision of transverse colon
H08 - Excision of left hemicolon
H09 - Excision of sigmoid colon
H10 - Excision of rectosigmoid
H11 - Excision of rectum
H33 - Excision of rectum and anastomosis
H34 - Anterior resection of rectum
...
```

### Data Completeness Check

**Endpoint:** `GET /api/admin/exports/data-completeness`

**Authentication:** Admin role required

**Response:**
```json
{
  "total_episodes": 1250,
  "patient_demographics": {
    "nhs_number": { "count": 1248, "percentage": 99.8 },
    "date_of_birth": { "count": 1250, "percentage": 100.0 },
    "gender": { "count": 1250, "percentage": 100.0 },
    "ethnicity": { "count": 1180, "percentage": 94.4 },
    "postcode": { "count": 1245, "percentage": 99.6 }
  },
  "diagnosis": {
    "diagnosis_date": { "count": 1240, "percentage": 99.2 },
    "icd10_code": { "count": 1250, "percentage": 100.0 },
    "tnm_staging": { "count": 1230, "percentage": 98.4 }
  },
  "surgery": {
    "total_surgical_episodes": 1100,
    "opcs4_code": { "count": 1095, "percentage": 99.5 },
    "asa_score": { "count": 1088, "percentage": 98.9 }
  }
}
```

**Target Completeness:**
- Mandatory fields: 100%
- Recommended fields: >95%
- Optional fields: Best effort

---

## XML Schema Reference

### COSD v9 Namespace

```xml
<COSDSubmission
  version="9.0"
  xmlns="http://www.datadictionary.nhs.uk/messages/COSD-v9-0">
  ...
</COSDSubmission>
```

### Submission Metadata

```xml
<SubmissionMetadata>
  <OrganisationCode>RHU</OrganisationCode>
  <ExtractDate>2026-01-07</ExtractDate>
  <RecordCount>1250</RecordCount>
</SubmissionMetadata>
```

### Cancer Record Structure

```xml
<CancerRecord>
  <Patient>...</Patient>
  <Episode>
    <LocalPatientIdentifier>...</LocalPatientIdentifier>
    <ProviderFirstSeen>...</ProviderFirstSeen>
    <Diagnosis>
      <PrimaryDiagnosisDate>...</PrimaryDiagnosisDate>
      <TNMStaging>...</TNMStaging>
      <Pathology>...</Pathology>
    </Diagnosis>
    <Treatments>
      <Treatment>
        <Surgery>...</Surgery>
      </Treatment>
    </Treatments>
  </Episode>
</CancerRecord>
```

### Example Complete Record

See [COSD Data Structure](#cosd-data-structure) section for a complete example.

---

## Export Process

### Step-by-Step Export Workflow

#### 1. Pre-Submission Preparation

**A. Run Data Completeness Check**
```
GET /api/admin/exports/data-completeness
```
- Review completeness percentages
- Identify fields with <100% mandatory field completion
- Target: 100% for mandatory, >95% for recommended

**B. Run NBOCA Validator**
```
GET /api/admin/exports/nboca-validator
```
- Review validation report
- Note episodes with errors (must fix before submission)
- Note episodes with warnings (recommended to fix)

**C. Fix Data Quality Issues**
1. Use search and filter to find incomplete records
2. Edit episodes to add missing mandatory fields
3. Review rectal cancer episodes for CRM status
4. Verify OPCS-4 codes for all surgical treatments
5. Re-run validator to confirm fixes

**Target:** `submission_ready: true` (zero errors)

#### 2. Generate COSD XML Export

**A. Access Export Page**
- Navigate to **Admin** → **Exports**
- Select **"NBOCA XML Export"**

**B. Set Date Range (Optional)**
- **Start Date**: Include episodes from this date
- **End Date**: Include episodes until this date
- **Leave blank**: Export all cancer episodes

**Example Date Ranges:**
- Audit year: `2025-04-01` to `2026-03-31`
- Calendar year: `2025-01-01` to `2025-12-31`
- All time: Leave both blank

**C. Generate Export**
- Click **"Generate XML"**
- Export processes (may take 10-60 seconds for large datasets)
- XML file downloads automatically

**D. Verify Export**
- Check file size (should be >100KB for 100+ episodes)
- Open in text editor or XML viewer
- Verify record count matches expected

#### 3. XML File Review

**A. Check Metadata**
```xml
<SubmissionMetadata>
  <OrganisationCode>RHU</OrganisationCode>
  <ExtractDate>2026-01-07</ExtractDate>
  <RecordCount>1250</RecordCount>  <!-- Should match your episode count -->
</SubmissionMetadata>
```

**B. Spot Check Records**
- Open 5-10 random records
- Verify NHS numbers present (10 digits)
- Verify ICD-10 codes (C18.x-C20)
- Verify OPCS-4 codes for surgical episodes
- Verify TNM staging present

**C. Validate Against Schema (Optional)**
- Use XML schema validator
- COSD v9 XSD available from NHS Digital
- No validation errors should be present

#### 4. NBOCA Submission

**A. Access NBOCA Portal**
- Navigate to: https://www.nboca.org.uk (example URL - check NBOCA website for actual submission portal)
- Log in with Trust credentials

**B. Upload XML**
- Select audit year
- Upload `nboca_export_YYYYMMDD_HHMMSS.xml`
- Await validation results

**C. Review Validation Report**
- NBOCA performs its own validation
- Review any errors flagged by NBOCA
- Common issues:
  - Invalid NHS numbers (not in PDS)
  - Invalid provider codes
  - Duplicate records
  - Date inconsistencies

**D. Correct Errors and Resubmit**
- If errors found, correct in IMPACT system
- Re-generate export
- Re-upload to NBOCA portal

**E. Submission Confirmation**
- Await NBOCA confirmation email
- Note submission reference number
- File confirmation for audit trail

#### 5. Post-Submission

**A. Document Submission**
- Record submission date
- Record number of episodes submitted
- Record any issues encountered
- File NBOCA confirmation

**B. Quality Improvement**
- Review validation warnings
- Identify data quality improvement opportunities
- Plan data quality initiatives
- Schedule follow-up data quality review

---

## Troubleshooting

### Common Export Issues

#### No Episodes Found

**Error Message:**
```
"No cancer episodes found in database. Please create cancer episodes before exporting."
```

**Causes:**
- No episodes with `condition_type: "cancer"` exist
- All episodes are non-cancer (IBD, benign)

**Solution:**
- Verify cancer episodes exist: Navigate to **Episodes** page, filter by "Cancer"
- Check episode records have `condition_type: "cancer"` and `cancer_type: "bowel"`

#### No Episodes Match Date Filter

**Error Message:**
```
"No cancer episodes match the specified criteria. Total cancer episodes: 1250.
Try clearing date filters or check that episodes have cancer_type='bowel'."
```

**Causes:**
- Date range too narrow
- Dates stored as strings, comparison issue
- Episodes outside date range

**Solution:**
- Widen date range or remove filters
- Check `referral_date`, `first_seen_date`, `diagnosis_date` fields
- Note: Some date fields are strings ("2025-06-15"), `created_at` is datetime

#### Missing NHS Number in Export

**Issue:** NHS numbers appear blank in XML

**Causes:**
- NHS number not entered in patient record
- NHS number not decrypted during export
- Encryption key file missing

**Solution:**
- Verify NHS number present in patient record (Edit patient, check field)
- Check encryption keys exist:
  ```bash
  ls -la /root/.field-encryption-key
  ls -la /root/.field-encryption-salt
  ```
- Verify `decrypt_document()` called in export logic

#### OPCS-4 Codes Not Exporting

**Issue:** Treatments missing from XML export

**Causes:**
- OPCS-4 code field empty in treatment
- Export filters treatments without OPCS-4 codes

**Solution:**
- Edit treatments to add OPCS-4 codes (mandatory for NBOCA)
- Use procedure search to find correct OPCS-4 code
- Common codes: H33 (right hemicolectomy), H08 (left hemicolectomy), H11 (rectal excision)

#### CRM Status Missing for Rectal Cancer

**Error (Validator):**
```
"CRM status mandatory for rectal cancer but missing"
```

**Causes:**
- Rectal cancer (C19, C20) without CRM status
- CRM field left blank

**Solution:**
- Edit tumour record
- Set CRM Status to: Clear / Involved / Close
- If clear, add CRM Distance (mm)

#### Invalid TNM Staging

**Error (Validator):**
```
"Clinical T stage missing"
```

**Causes:**
- TNM fields not completed
- TNM version not specified

**Solution:**
- Edit tumour record
- Select TNM Version (7 or 8)
- Enter Clinical T, N, M stages (all three required)
- Format: Store as "3", "1a", "0" (not "T3", "N1a", "M0")

### XML File Issues

#### XML Not Well-Formed

**Error:** XML parser errors

**Causes:**
- Special characters in free text fields
- Unescaped XML entities

**Solution:**
- IMPACT automatically escapes XML entities
- Check `description` and `notes` fields for unusual characters
- Use XML validator to identify specific line

#### File Size Too Large

**Issue:** File >100MB

**Causes:**
- Too many episodes in export
- Large free text fields

**Solution:**
- Use date filters to export in batches
- Example: Export by year (2023, 2024, 2025)
- NBOCA accepts multiple submissions

---

## NBOCA Submission Checklist

### Pre-Submission Checklist

- [ ] **Data Completeness Check:** >95% for recommended fields, 100% for mandatory
- [ ] **NBOCA Validator:** Zero errors, `submission_ready: true`
- [ ] **Rectal Cancer CRM:** All C19/C20 episodes have CRM status
- [ ] **OPCS-4 Codes:** All surgical treatments have valid OPCS-4 codes
- [ ] **ASA Scores:** All surgical treatments have ASA score (1-5)
- [ ] **TNM Staging:** All tumours have clinical T, N, M stages
- [ ] **NHS Numbers:** All patients have valid 10-digit NHS numbers
- [ ] **Date Logic:** Treatment dates after diagnosis dates

### Export Checklist

- [ ] **Export Generated:** XML file downloaded successfully
- [ ] **File Size Check:** File size >100KB (for 100+ episodes)
- [ ] **Record Count:** Metadata record count matches expected episodes
- [ ] **Random Sample:** Spot-checked 10 records, all fields present
- [ ] **XML Validation:** No XML parser errors (well-formed)

### Submission Checklist

- [ ] **NBOCA Portal Access:** Logged in successfully
- [ ] **Correct Audit Year:** Selected appropriate audit period
- [ ] **File Upload:** XML uploaded without errors
- [ ] **NBOCA Validation:** Passed NBOCA portal validation
- [ ] **Confirmation:** Received submission confirmation email
- [ ] **Reference Number:** Noted submission reference for records

### Post-Submission Checklist

- [ ] **Documentation:** Submission documented in audit file
- [ ] **Issues Logged:** Any errors/warnings documented
- [ ] **Quality Improvement:** Data quality improvement plan updated
- [ ] **Follow-Up:** Next audit submission date scheduled

---

## Appendix: COSD Field Quick Reference

### Mandatory Fields (59 Fields)

**Patient (5):**
- CR0010 NHS Number
- CR0100 Date of Birth
- CR3170 Gender
- CR0150 Ethnicity
- CR0080 Postcode

**Diagnosis (7):**
- CR2030 Diagnosis Date
- CR0370 ICD-10 Code
- CR2070 TNM Version
- CR0520 Clinical T
- CR0540 Clinical N
- CR0560 Clinical M
- pCR0930 Grade

**Surgery (3):**
- CR0710 Surgery Date
- CR0720 OPCS-4 Code
- CR6010 ASA Score

**Rectal Cancer (1):**
- pCR1150 CRM Status (C19/C20 only)

### Recommended Fields (15 Fields)

**Referral (5):**
- CR1600 Referral Source
- CR1410 Provider First Seen
- CR2050 CNS Involved
- CR3190 MDT Meeting Type
- CR0510 Performance Status

**Staging (3):**
- pCR6820 Pathological T
- pCR0910 Pathological N
- pCR0920 Pathological M

**Pathology (2):**
- pCR0890 Nodes Examined
- pCR0900 Nodes Positive

**Surgery (2):**
- CR6310 Surgical Approach
- CO6000 Urgency

**Provider (1):**
- CR1450 Provider Organisation

---

**End of COSD Export Documentation**

For additional documentation, see:
- [USER_GUIDE.md](USER_GUIDE.md)
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- [TECHNICAL_SPECIFICATIONS.md](TECHNICAL_SPECIFICATIONS.md)
- [SECURITY_AND_COMPLIANCE.md](SECURITY_AND_COMPLIANCE.md)
- [DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md)
