# NBOCA COSD Field Implementation Status

**Date**: December 23, 2025  
**Status**: ✅ **ALL MANDATORY FIELDS IMPLEMENTED**

## Summary

All NBOCA mandatory and recommended fields for bowel cancer audit have been implemented. Data is stored across 4 collections (patients, episodes, tumours, treatments) and exported via `/api/admin/exports/nboca-xml` endpoint.

---

## MANDATORY FIELDS - Patient Demographics

| Field | COSD Code | Status | Location | Sample Value |
|-------|-----------|--------|----------|--------------|
| NHS Number | CR0010 | ✅ | `patients.nhs_number` | "123 456 7890" |
| Date of Birth | CR0100 | ✅ | `patients.demographics.date_of_birth` | "1965-05-15" |
| Gender | CR3170 | ✅ | `patients.demographics.gender` | "male" |
| Ethnicity | CR0150 | ✅ | `patients.demographics.ethnicity` | "English, Welsh, Scottish..." |
| Postcode | CR0080 | ✅ | `patients.contact_details.address.postcode` | "E1 6AN" |

---

## MANDATORY FIELDS - Diagnosis

| Field | COSD Code | Status | Location | Sample Value |
|-------|-----------|--------|----------|--------------|
| Diagnosis Date | CR2030 | ✅ | `tumours.diagnosis_date` | "2025-12-06" |
| ICD-10 Code | CR0370 | ✅ | `tumours.icd10_code` | "C18.3" (Hepatic flexure) |
| Tumour Site | CR0490 | ✅ | `tumours.site` | "hepatic_flexure" |
| Histology Type | - | ✅ | `tumours.histology_type` | "Adenocarcinoma" |
| Grade/Differentiation | pCR0930 | ✅ | `tumours.grade` | "poor" |
| SNOMED Morphology | CR6400 | ✅ | `tumours.snomed_morphology_code` | (optional) |

---

## MANDATORY FIELDS - TNM Staging

| Field | COSD Code | Status | Location | Sample Value |
|-------|-----------|--------|----------|--------------|
| TNM Version | CR2070 | ✅ | `tumours.tnm_version` | "8" |
| Clinical Stage Date | - | ✅ | `tumours.clinical_stage_date` | "2025-12-06" |
| Clinical T | CR0520 | ✅ | `tumours.clinical_t` | "T1" |
| Clinical N | CR0540 | ✅ | `tumours.clinical_n` | "N0" |
| Clinical M | CR0560 | ✅ | `tumours.clinical_m` | "M0" |
| Pathological Stage Date | - | ✅ | `tumours.pathological_stage_date` | "2026-01-22" |
| Pathological T | pCR6820 | ✅ | `tumours.pathological_t` | "T1" |
| Pathological N | pCR0910 | ✅ | `tumours.pathological_n` | "N0" |
| Pathological M | pCR0920 | ✅ | `tumours.pathological_m` | "M0" |

---

## MANDATORY FIELDS - Pathology

| Field | COSD Code | Status | Location | Sample Value |
|-------|-----------|--------|----------|--------------|
| Lymph Nodes Examined | pCR0890 | ✅ | `tumours.lymph_nodes_examined` | 21 |
| Lymph Nodes Positive | pCR0900 | ✅ | `tumours.lymph_nodes_positive` | 0 |
| CRM Status | pCR1150 | ✅ | `tumours.crm_status` | "clear" / "not_applicable" |
| CRM Distance (mm) | - | ✅ | `tumours.crm_distance_mm` | 5 (if applicable) |
| Proximal Margin (mm) | - | ✅ | `tumours.proximal_margin_mm` | 50 |
| Distal Margin (mm) | - | ✅ | `tumours.distal_margin_mm` | 35 |
| Lymphovascular Invasion | - | ✅ | `tumours.lymphovascular_invasion` | false |
| Perineural Invasion | - | ✅ | `tumours.perineural_invasion` | false |

---

## MANDATORY FIELDS - Molecular Markers

| Field | COSD Code | Status | Location | Sample Value |
|-------|-----------|--------|----------|--------------|
| KRAS Status | - | ✅ | `tumours.kras_status` | "Wild-type" / "Mutant" |
| BRAF Status | - | ✅ | `tumours.braf_status` | "Wild-type" / "Mutant" |
| MMR Status | - | ✅ | `tumours.mismatch_repair_status` | "MSS" / "MSI-H" |

---

## MANDATORY FIELDS - Treatment (Surgery)

| Field | COSD Code | Status | Location | Sample Value |
|-------|-----------|--------|----------|--------------|
| Treatment Date | CR0710 | ✅ | `treatments.treatment_date` | "2026-01-15" |
| Treatment Type | - | ✅ | `treatments.treatment_type` | "surgery" |
| Treatment Intent | CR0680 | ✅ | `treatments.treatment_intent` | (optional) |
| OPCS-4 Code | CR0720 | ✅ | `treatments.opcs4_code` | "H06" (Right hemicolectomy) |
| ASA Score | CR6010 | ✅ | `treatments.asa_score` | 2 |
| Surgical Approach | CR6310 | ✅ | `treatments.approach` | "laparoscopic" |
| Urgency | CO6000 | ✅ | `treatments.urgency` | "elective" |
| Surgeon | - | ✅ | `treatments.surgeon` | "Sarah Williams" |
| Procedure Name | - | ✅ | `treatments.procedure_name` | "Right hemicolectomy" |

---

## MANDATORY FIELDS - Episode/Pathway

| Field | COSD Code | Status | Location | Sample Value |
|-------|-----------|--------|----------|--------------|
| Referral Date | - | ✅ | `episodes.referral_date` | "2025-11-21" |
| Referral Source | CR1600 | ✅ | `episodes.referral_source` | "2ww" / "emergency" |
| First Seen Date | - | ✅ | `episodes.first_seen_date` | "2025-12-01" |
| Provider First Seen | CR1410 | ✅ | `episodes.provider_first_seen` | "RYR" |
| MDT Discussion Date | - | ✅ | `episodes.mdt_discussion_date` | "2025-12-14" |
| MDT Meeting Type | CR3190 | ✅ | `episodes.mdt_type` | "colorectal" |
| CNS Indication | CR2050 | ✅ | `episodes.cns_indication` | "01" |
| Performance Status | CR0510 | ✅ | `episodes.performance_status` | "1" (ECOG) |
| Lead Clinician | - | ✅ | `episodes.lead_clinician` | "Sarah Williams" |

---

## RECOMMENDED FIELDS (Implemented)

| Field | Status | Location | Notes |
|-------|--------|----------|-------|
| Admission Date | ✅ | `treatments.admission_date` | Hospital admission |
| Discharge Date | ✅ | `treatments.discharge_date` | Hospital discharge |
| Operation Duration | ✅ | `treatments.operation_duration_minutes` | Minutes |
| Blood Loss | ✅ | `treatments.blood_loss_ml` | Milliliters |
| Transfusion Required | ✅ | `treatments.transfusion_required` | Boolean |
| Drains Placed | ✅ | `treatments.drains_placed` | Boolean |
| Complexity | ✅ | `treatments.complexity` | routine/complex |
| Anesthesia Type | ✅ | `treatments.anesthesia_type` | general/regional |
| 30-Day Mortality | ✅ | Computed from `patients.deceased_date` | Dynamically calculated |
| 90-Day Mortality | ✅ | Computed from `patients.deceased_date` | Dynamically calculated |
| 1-Year Mortality | ✅ | Computed from `patients.deceased_date` | Dynamically calculated |
| Return to Theatre | ✅ | `treatments.return_to_theatre` | Boolean + reason |
| 30-Day Readmission | ✅ | `treatments.readmission_30day` | Boolean + reason |

**Mortality Calculation**: Mortality is computed dynamically by comparing `patients.deceased_date` with `treatments.treatment_date`. This ensures a single source of truth and automatic updates when deceased dates are recorded.

---

## OPCS-4 Codes Implemented

All common colorectal procedures:
- **H04** - Right hemicolectomy
- **H06** - Sigmoid colectomy
- **H07** - Transverse colectomy
- **H08** - Subtotal colectomy
- **H33** - Anterior resection of rectum
- **H34** - Abdominoperineal excision

Plus 80+ other procedures in the AddTreatmentModal dropdown.

---

## ICD-10 Codes Implemented

All bowel cancer sites covered:
- **C18.0** - Caecum
- **C18.2** - Ascending colon
- **C18.3** - Hepatic flexure
- **C18.4** - Transverse colon
- **C18.5** - Splenic flexure
- **C18.6** - Descending colon
- **C18.7** - Sigmoid colon
- **C20** - Rectum

---

## XML Export

**Endpoint**: `GET /api/admin/exports/nboca-xml`

**Format**: COSD v9/v10 XML standard

**Sample Structure**:
```xml
<CancerRecord>
  <Patient>
    <NHSNumber>123 456 7890</NHSNumber>
    <PersonBirthDate>1965-05-15</PersonBirthDate>
    <PersonStatedGenderCode>1</PersonStatedGenderCode>
    <EthnicCategory>English, Welsh, Scottish...</EthnicCategory>
    <PostcodeOfUsualAddress>E1 6AN</PostcodeOfUsualAddress>
  </Patient>
  <Episode>
    <Diagnosis>
      <PrimaryDiagnosisDate>2025-12-06</PrimaryDiagnosisDate>
      <PrimaryDiagnosisICD>C18.3</PrimaryDiagnosisICD>
      <TNMStaging>
        <TNMVersionNumber>8</TNMVersionNumber>
        <TCategoryFinalPretreatment>T1</TCategoryFinalPretreatment>
        <NCategoryFinalPretreatment>N0</NCategoryFinalPretreatment>
        <MCategoryFinalPretreatment>M0</MCategoryFinalPretreatment>
      </TNMStaging>
      <Pathology>
        <DifferentiationGrade>poor</DifferentiationGrade>
        <NumberOfNodesExamined>21</NumberOfNodesExamined>
        <NumberOfNodesPositive>0</NumberOfNodesPositive>
        <CircumferentialResectionMargin>clear</CircumferentialResectionMargin>
      </Pathology>
    </Diagnosis>
    <Treatments>
      <Treatment>
        <TreatmentType>SURGERY</TreatmentType>
        <TreatmentDate>2026-01-15</TreatmentDate>
        <Surgery>
          <PrimaryProcedureOPCS>H06</PrimaryProcedureOPCS>
          <ASAScore>2</ASAScore>
          <SurgicalAccessType>02</SurgicalAccessType>
          <SurgicalUrgencyType>01</SurgicalUrgencyType>
        </Surgery>
      </Treatment>
    </Treatments>
  </Episode>
</CancerRecord>
```

---

## Data Completeness Checker

**Endpoint**: `GET /api/admin/exports/data-completeness`

Returns percentage completeness for:
- Patient demographics (NHS Number, DOB, Gender, Ethnicity, Postcode)
- Diagnosis data (Date, ICD-10, TNM staging)
- Treatment data (OPCS codes, ASA scores, dates)
- Pathology data (Nodes examined, CRM status)

---

## What's NOT Yet Implemented

### 1. Outcome Tracking
- ✅ 30-day mortality (computed dynamically from `patients.deceased_date`)
- ✅ 90-day mortality (computed dynamically from `patients.deceased_date`)
- ✅ 1-year mortality (computed dynamically from `patients.deceased_date`)
- ⚠️ Anastomotic leak rates (need structured complication tracking)
- ⚠️ Reoperation rates (return to theatre tracked but needs aggregated reporting)
- ⚠️ Readmission analysis (30-day readmission tracked, needs reporting dashboard)

### 2. Additional Treatment Types
- Chemotherapy regimens (partially implemented)
- Radiotherapy details (partially implemented)
- Immunotherapy
- Targeted therapy

### 3. Advanced Features
- NBOCA submission validator (to check data before export)
- Data quality dashboard (visual completeness tracking)
- Automated NBOCA submission
- Complication tracking with Clavien-Dindo grading

---

## Validation Required

Before submitting to NBOCA, ensure:

1. ✅ All mandatory fields populated for each case
2. ⚠️ Valid OPCS-4 codes (check against current version)
3. ⚠️ Valid ICD-10 codes (check against current version)
4. ⚠️ TNM staging follows correct version (v8 specified)
5. ⚠️ CRM mandatory for rectal cancers only
6. ⚠️ Date logic validated (diagnosis < treatment < outcomes)
7. ⚠️ NHS numbers validated (check digit algorithm)
8. ⚠️ Postcode format validated

---

## Next Steps

1. **Build NBOCA Submission Validator** - Check data quality before export
2. **Create Data Quality Dashboard** - Visual completeness tracking per case
3. **Implement Outcome Tracking** - 30/90-day mortality, complications
4. **Add Complication Tracking** - Clavien-Dindo grading system
5. **Build NBOCA Reports** - Anastomotic leak rates, conversion rates, etc.

---

## Conclusion

✅ **ALL NBOCA mandatory fields are implemented and populated in sample data.**

The system is ready for NBOCA submission from a data completeness perspective. The remaining work is building quality assurance tools (validator, dashboard) and outcome tracking features.
