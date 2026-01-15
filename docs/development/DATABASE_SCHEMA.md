# Database Schema Reference

**Version:** 2025-12-30
**Database:** MongoDB (impact)
**Purpose:** Surgical outcomes database for colorectal cancer and general surgery

> ⚠️ **IMPORTANT:** This document is the definitive reference for the database structure. Do NOT modify the data structure without explicit user approval. Any changes must be documented here and in RECENT_CHANGES.md.

---

## Table of Contents
1. [Overview](#overview)
2. [Collections](#collections)
3. [Relationships](#relationships)
4. [Data Standards](#data-standards)
5. [NBOCA/COSD Compliance](#nbocacosd-compliance)

---

## Overview

The IMPACT database uses a **hierarchical patient-episode-treatment model** designed for surgical outcomes tracking and NBOCA/COSD cancer registry compliance.

### Core Architecture
```
Patient (1) ──► Episode (N) ──► Treatment (N)
                    │
                    ├──► Tumour (N)
                    └──► Investigation (N)
```

### Collections Summary
- **patients** - Patient demographics and medical history
- **episodes** - Clinical episodes/contacts (cancer, IBD, benign conditions)
- **treatments** - Individual treatments within episodes (surgery, chemo, radiotherapy, etc.)
- **tumours** - Individual tumour sites tracked within cancer episodes
- **investigations** - Clinical investigations and imaging studies
- **clinicians** - Clinician directory (superseded surgeons collection)
- **users** - System users and authentication
- **audit_logs** - System audit trail
- **nhs_providers** - NHS organization codes and names

---

## Collections

### 1. Patients Collection (`patients`)

**Purpose:** Patient demographics and medical history

#### Schema
```python
{
    "_id": ObjectId,
    "patient_id": str,           # Unique 6-character hash (e.g., "ABC123")
    "mrn": str | null,           # Medical Record Number: 8 digits or IW+6 digits
    "nhs_number": str | null,    # NHS number: 10 digits (stored as string, no decimals)
    "demographics": {
        "date_of_birth": str | null,     # YYYY-MM-DD format
        "age": int | null,               # 0-150
        "gender": str,                    # Required, min 1 char
        "ethnicity": str | null,
        "postcode": str | null           # UK postcode
    },
    "medical_history": {
        "conditions": [str],             # List of medical conditions
        "previous_surgeries": [dict],    # Previous surgical history
        "medications": [str],
        "allergies": [str],
        "smoking_status": str | null,    # never/former/current
        "alcohol_use": str | null
    },
    "created_at": datetime,
    "updated_at": datetime
}
```

#### Indexes
- `patient_id` (unique)
- `mrn`
- `nhs_number`

#### Data Quality Standards
- NHS number: String format, no decimal places
- Postcode: Populated for all patients
- Patient ID: 6-character hash generated from source data

---

### 2. Episodes Collection (`episodes`)

**Purpose:** Clinical episodes for cancer, IBD, or benign conditions

#### Schema
```python
{
    "_id": ObjectId,
    "episode_id": str,               # Unique identifier (e.g., "E-ABC123-01")
    "patient_id": str,               # Foreign key to patients.patient_id
    "condition_type": str,           # "cancer" | "ibd" | "benign"

    # Contact details
    "referral_date": datetime | str,
    "first_seen_date": datetime | str | null,
    "mdt_discussion_date": datetime | str | null,

    # NBOCA COSD Referral Pathway Fields
    "referral_source": str | null,        # gp/consultant/screening/two_week_wait/emergency/other
    "provider_first_seen": str | null,    # CR1410: NHS Trust code (e.g., "RHU")
    "cns_involved": str | null,           # CR2050: yes/no/unknown - Clinical Nurse Specialist
    "mdt_meeting_type": str | null,       # CR3190: colorectal/upper_gi/lower_gi/combined/other
    "performance_status": str | null,     # CR0510: ECOG score 0-5 - Patient fitness
    "no_treatment_reason": str | null,    # CR0490: Reason if no treatment given

    # Clinical team
    "lead_clinician": str,           # Clinician name (string, NOT ObjectId)
    "mdt_team": [str],               # List of team member names

    # Episode status
    "episode_status": str,           # active/completed/cancelled
    "treatment_intent": str | null,  # curative/palliative
    "treatment_plan": str | null,    # Free text treatment plan

    # Cancer-specific (if condition_type == "cancer")
    "cancer_type": str | null,       # bowel/kidney/breast_primary/breast_metastatic/oesophageal/ovarian/prostate
    "cancer_data": {                 # Cancer type-specific clinical data
        # Structure varies by cancer_type - see Episode Models section
    },

    # Related data
    "treatments": [dict],            # List of treatment records (denormalized for performance)
    "tumours": [dict],               # List of tumour sites (denormalized)

    # Audit trail
    "created_at": datetime,
    "created_by": str,
    "last_modified_at": datetime,
    "last_modified_by": str
}
```

#### Indexes
- `episode_id` (unique)
- `patient_id`
- `condition_type`
- `referral_date`

#### Data Quality Standards
- `lead_clinician`: Stored as string name (case-insensitive match to clinicians table), NOT ObjectId
- `referral_source`: Clean values (gp/consultant/screening/two_week_wait/emergency/other), no leading numbers
- `provider_first_seen`: Set to "RHU" (Royal Hospital for Neurodisability) for all records
- `mdt_meeting_type`: Set to "Colorectal MDT" for colorectal episodes

---

### 3. Treatments Collection (`treatments`)

**Purpose:** Individual treatments within episodes (surgery, chemotherapy, radiotherapy, etc.)

#### Common Treatment Fields
```python
{
    "_id": ObjectId,
    "treatment_id": str,             # Unique identifier (e.g., "T-ABC123-01")
    "episode_id": str,               # Foreign key to episodes.episode_id
    "patient_id": str,               # Foreign key to patients.patient_id
    "treatment_type": str,           # surgery_primary/surgery_rtt/surgery_reversal/chemotherapy/radiotherapy/immunotherapy/hormone_therapy/targeted_therapy/palliative/surveillance
    "treatment_date": datetime | str,
    "treating_clinician": str,
    "treatment_intent": str,         # curative/palliative/adjuvant/neoadjuvant/prophylactic
    "notes": str | null,

    # Surgery Relationship Fields (for surgery_rtt and surgery_reversal only)
    "parent_surgery_id": str | null,      # Treatment ID of parent surgery (required for surgery_rtt and surgery_reversal)
    "parent_episode_id": str | null,      # Episode ID of parent surgery (auto-populated)
    "rtt_reason": str | null,             # Reason for return to theatre (required for surgery_rtt)
    "reversal_notes": str | null,         # Notes for stoma reversal (optional for surgery_reversal)

    # Related Surgeries (for surgery_primary with RTT/reversals)
    "related_surgery_ids": [              # Array of related surgery IDs (RTT and reversals linked to this primary surgery)
        {
            "treatment_id": str,
            "treatment_type": str,        # "surgery_rtt" | "surgery_reversal"
            "date_created": datetime
        }
    ]
}
```

#### Treatment Type Values

**Surgery Types:**
- `surgery_primary` - Original/primary surgical procedures
- `surgery_rtt` - Return to theatre surgeries (complications requiring reoperation)
- `surgery_reversal` - Stoma reversal surgeries

**Oncology Types:**
- `chemotherapy` - Systemic chemotherapy regimens
- `radiotherapy` - Radiation therapy
- `immunotherapy` - Immune checkpoint inhibitors
- `hormone_therapy` - Hormonal treatment
- `targeted_therapy` - Targeted molecular therapy

**Other Types:**
- `palliative` - Palliative care interventions
- `surveillance` - Active surveillance/watchful waiting

#### Surgery Treatment Fields
```python
{
    # ... common fields above ...
    "treatment_type": str,  # "surgery_primary" | "surgery_rtt" | "surgery_reversal"

    # Provider
    "provider_organisation": str | null,  # CR1450: NHS Trust code

    # Patient Vitals at Time of Treatment
    "height_cm": float | null,           # Patient height in cm (0-300) - recorded per treatment as it can change
    "weight_kg": float | null,           # Patient weight in kg (0-500) - recorded per treatment as it can change
    "bmi": float | null,                 # Body Mass Index (0-100) - recorded per treatment as it can change

    # Classification
    "classification": {
        "urgency": str,              # elective/emergency/urgent
        "complexity": str | null,    # routine/intermediate/complex
        "primary_diagnosis": str,
        "indication": str | null     # cancer/ibd/diverticular/benign/other
    },

    # Procedure
    "procedure": {
        "primary_procedure": str,
        "additional_procedures": [str],
        "cpt_codes": [str],
        "icd10_codes": [str],
        "opcs_codes": [str],
        "approach": str,             # open/laparoscopic/robotic/converted
        "robotic_surgery": bool,     # Whether robotic assistance used
        "conversion_to_open": bool,  # Whether converted from lap to open
        "conversion_reason": str | null,  # oncological/adhesions/bleeding/fat/difficult_op/time/technical/other
        "description": str | null
    },

    # Timeline
    "perioperative_timeline": {
        "admission_date": datetime | str,
        "surgery_date": datetime | str,
        "induction_time": datetime | str | null,
        "knife_to_skin_time": datetime | str | null,
        "surgery_end_time": datetime | str | null,
        "anesthesia_duration_minutes": int | null,
        "operation_duration_minutes": int | null,
        "discharge_date": datetime | str | null,
        "length_of_stay_days": int | null
    },

    # Team
    "team": {
        "primary_surgeon": str,
        "primary_surgeon_text": str,     # Clean surgeon name (NOT ObjectId)
        "assistant_surgeons": [str],
        "assistant_grade": str | null,   # consultant/specialist_registrar/core_trainee/other
        "second_assistant": str | null,
        "anesthesiologist": str | null,
        "scrub_nurse": str | null,
        "circulating_nurse": str | null
    },

    # Intraoperative
    "intraoperative": {
        "anesthesia_type": str | null,   # general/regional/local
        "blood_loss_ml": int | null,
        "transfusion_required": bool,
        "units_transfused": int | null,
        "findings": str | null,
        "specimens_sent": [str],
        "drains_placed": bool,
        "drain_types": [str],

        # Colorectal-specific: Stoma
        "stoma_created": bool,
        "stoma_type": str | null,        # loop_ileostomy/end_ileostomy/loop_colostomy/end_colostomy/double_barrelled_ileostomy/double_barrelled_ileo_colostomy/double_barrelled_colostomy
        "stoma_closure_date": datetime | str | null,  # Auto-set when surgery_reversal created
        "reversal_treatment_id": str | null,          # Treatment ID of surgery_reversal that closed this stoma

        # Colorectal-specific: Anastomosis
        "anastomosis_performed": bool,
        "anastomosis_type": str | null,  # hand_sewn/stapled/hybrid
        "anastomosis_configuration": str | null,  # end_to_end/end_to_side/side_to_side/side_to_end
        "anastomosis_height_cm": float | null,
        "anastomosis_location": str | null,  # colorectal/coloanal/ileocolic/ileorectal/other
        "anterior_resection_type": str | null,  # high/low
        "defunctioning_stoma": str | null  # yes/no - ONLY yes if both anastomosis AND stoma performed
    },

    # Pathology
    "pathology": {
        "histology": str | null,
        "grade": str | null,
        "lymph_nodes_examined": int | null,
        "lymph_nodes_positive": int | null,
        "margins": str | null,           # clear/involved/close
        "margin_distance_mm": float | null,
        "tumor_size_mm": float | null,
        "lymphovascular_invasion": str | null,  # present/absent/uncertain
        "perineural_invasion": str | null       # present/absent/uncertain
    },

    # Postoperative events
    "postoperative_events": {
        "return_to_theatre": {
            "occurred": bool,                    # Auto-set to True when surgery_rtt created
            "date": datetime | null,             # Auto-set from first surgery_rtt date
            "reason": str | null,                # Auto-set from first surgery_rtt reason
            "procedure_performed": str | null,   # Auto-set from first surgery_rtt procedure
            "rtt_treatment_id": str | null       # Treatment ID of first surgery_rtt
        },
        "escalation_of_care": {
            "occurred": bool,
            "destination": str | null,   # hdu/icu
            "date": datetime | null,
            "reason": str | null,
            "duration_days": int | null
        },
        "complications": [{
            "type": str,
            "clavien_dindo_grade": str | null,  # I/II/IIIa/IIIb/IVa/IVb/V
            "description": str,
            "date_identified": datetime,
            "treatment": str | null,
            "resolved": bool
        }],
        "anastomotic_leak": {
            "occurred": bool,
            "severity": str | null,      # A/B/C
            "date_identified": datetime | null,
            "days_post_surgery": int | null,
            "presentation": str | null,  # clinical/radiological/endoscopic/at_reoperation
            # ... additional leak tracking fields
        }
    },

    # Outcomes
    "outcomes": {
        "readmission_30day": bool,
        "readmission_date": datetime | null,
        "readmission_reason": str | null,
        "mortality_30day": bool,
        "mortality_90day": bool,
        "date_of_death": datetime | null,
        "cause_of_death": str | null
    },

    # Follow-up
    "follow_up": {
        "appointments": [{
            "date": datetime,
            "type": str,             # post_op/surveillance/mdt
            "provider": str,
            "findings": str | null,
            "imaging_results": str | null,
            "plan": str | null
        }],
        "long_term_outcomes": {
            "recurrence": bool,
            "recurrence_date": datetime | null,
            "recurrence_type": str | null,
            "functional_status": str | null,
            "quality_of_life_score": int | null  # 0-100
        }
    },

    # Documents
    "documents": [{
        "type": str,                 # operation_note/pathology_report/imaging/discharge_summary
        "filename": str,
        "file_path": str,
        "uploaded_date": datetime,
        "uploaded_by": str | null
    }]
}
```

#### Data Quality Standards
- `approach`: Determined via priority logic: robotic > converted > standard lap/open
- `stoma_type`: Uses StomDone field (ileostomy/colostomy/urostomy/none), NOT StomType
- `defunctioning_stoma`: Returns "yes" ONLY if both anastomosis AND stoma performed
- `readmission_30day`: Uses Post_IP field (readmission for complications)
- `primary_surgeon_text`: Clean surgeon name (NOT ObjectId)

#### Surgery Relationship Validation Rules
- **surgery_rtt** MUST have `parent_surgery_id` and `rtt_reason`
- **surgery_reversal** MUST have `parent_surgery_id`
- **surgery_primary** MUST NOT have `parent_surgery_id`
- Parent surgery MUST be `surgery_primary`
- `episode_id` for RTT/reversal MUST match parent's `episode_id` (auto-populated)
- When `surgery_rtt` created: Parent surgery's `return_to_theatre.occurred` auto-set to True
- When `surgery_reversal` created: Parent surgery's `stoma_closure_date` auto-set to reversal date
- Multiple RTTs are supported via `related_surgery_ids` array
- Deleting RTT/reversal removes from parent's `related_surgery_ids` and resets flags if no other related surgeries exist

---

### 4. Tumours Collection (`tumours`)

**Purpose:** Individual tumour sites tracked within cancer episodes

#### Schema
```python
{
    "_id": ObjectId,
    "tumour_id": str,                # Unique identifier (e.g., "TUM-ABC123-01")
    "episode_id": str,               # Foreign key to episodes.episode_id
    "patient_id": str,               # Foreign key to patients.patient_id
    "tumour_type": str,              # primary/metastasis/recurrence
    "site": str,                     # Anatomical location (see TumourSite enum)

    # Diagnosis
    "diagnosis_date": date | null,   # CR2030: Date of primary diagnosis
    "icd10_code": str | null,        # CR0370: ICD-10 code (e.g., C18.0-C20)
    "snomed_morphology": str | null, # CR6400: SNOMED morphology code

    # TNM Staging - Clinical (Pretreatment)
    "tnm_version": str,              # "7" | "8" (CR2070/pCR6820)
    "clinical_t": str | null,        # CR0520: Tx/T0/Tis/T1/T2/T3/T4/T4a/T4b
    "clinical_n": str | null,        # CR0540: Nx/N0/N1/N1a/N1b/N1c/N2/N2a/N2b
    "clinical_m": str | null,        # CR0560: Mx/M0/M1/M1a/M1b/M1c
    "clinical_stage_date": date | null,

    # TNM Staging - Pathological (Post-surgery)
    "pathological_t": str | null,    # pCR0910: Pathological T stage
    "pathological_n": str | null,    # pCR0920: Pathological N stage
    "pathological_m": str | null,    # pCR0930: Pathological M stage
    "pathological_stage_date": date | null,

    # Tumour characteristics
    "grade": str | null,             # well/moderate/poor/undifferentiated
    "histology_type": str | null,    # adenocarcinoma/mucinous/signet_ring/other
    "size_mm": float | null,         # Maximum tumour dimension

    # Rectal cancer specific (C20)
    "distance_from_anal_verge_cm": float | null,  # CO5160: Height above anal verge
    "mesorectal_involvement": bool | null,

    # Pathology (post-resection)
    "background_morphology": str | null,    # Origin: Adenoma (Tubular/Tubulovillous/Villous)/IBD/Serrated lesion/De novo/Unknown
    "lymph_nodes_examined": int | null,     # pCR0890: Total nodes examined
    "lymph_nodes_positive": int | null,     # pCR0900: Positive nodes
    "apical_node": str | null,              # Involved/Not Involved/Unknown
    "lymphatic_invasion": str | null,       # yes/no/uncertain (L0/L1)
    "vascular_invasion": str | null,        # yes/no/uncertain (V0/V1)
    "perineural_invasion": str | null,      # yes/no/uncertain (Pn0/Pn1)

    # Resection margins
    "margin_status": str | null,     # pCR1150: R0/R1/R2/uncertain (resection margin status)
    "crm_distance_mm": float | null, # Distance to CRM
    "proximal_margin_mm": float | null,
    "distal_margin_mm": float | null,
    "donuts_involved": str | null,   # Involved/Not Involved/Not Sent/Unknown

    # Molecular markers
    "mismatch_repair_status": str | null,  # intact/deficient/unknown
    "kras_status": str | null,             # wild_type/mutant/unknown
    "braf_status": str | null,             # wild_type/mutant/unknown

    # Treatment associations
    "treated_by_treatment_ids": [str],     # List of treatment IDs

    "notes": str | null,
    "created_at": datetime,
    "last_modified_at": datetime
}
```

#### Tumor Site Values (TumourSite enum)
**Colorectal sites (ICD-10 C18.x, C19, C20):**
- `caecum` (C18.0)
- `appendix` (C18.1)
- `ascending_colon` (C18.2)
- `hepatic_flexure` (C18.3)
- `transverse_colon` (C18.4)
- `splenic_flexure` (C18.5)
- `descending_colon` (C18.6)
- `sigmoid_colon` (C18.7)
- `rectosigmoid_junction` (C19)
- `rectum` (C20)
- `colon_unspecified` (C18.9)

**Metastatic sites:**
- `liver`, `lung`, `peritoneum`, `lymph_node`, `bone`, `brain`, `other`

#### Data Quality Standards
- TNM staging: Stored as simple numbers/letters (e.g., "3", "1a", "0") - frontend adds prefixes
- CRM status: Uses yes/no/uncertain format (user requirement)
- All boolean invasion/marker fields: present/absent/uncertain format

---

### 5. Investigations Collection (`investigations`)

**Purpose:** Clinical investigations and imaging studies

#### Schema
```python
{
    "_id": ObjectId,
    "investigation_id": str,         # Unique identifier (e.g., "INV-ABC123-ct_abdomen-01")
    "patient_id": str,               # Foreign key to patients.patient_id
    "episode_id": str | null,        # Foreign key to episodes.episode_id
    "tumour_id": str | null,         # Foreign key to tumours.tumour_id

    "type": str,                     # imaging/endoscopy/laboratory
    "subtype": str,                  # ct_abdomen/mri_primary/colonoscopy/ct_colonography/etc

    "date": str | null,              # Investigation date (YYYY-MM-DD)
    "result": str | null,            # Primary result/finding (cleaned - no leading numbers)
    "findings": {                    # Investigation-specific detailed findings
        # For MRI Primary:
        "t_stage": str | null,
        "n_stage": str | null,
        "crm_status": str | null,
        "distance_from_anal_verge": float | null,
        "emvi": str | null,
        # For CT/Colonoscopy:
        # ... varies by investigation type
    },

    "report_url": str | null,        # Link to full report in EHR
    "notes": str | null,

    "created_at": datetime | null,
    "updated_at": datetime | null
}
```

#### Investigation Types
- **CT Abdomen** (`ct_abdomen`): From Dt_CT_Abdo field
- **CT Colonography** (`ct_colonography`): From Dt_CT_pneumo field
- **Colonoscopy** (`colonoscopy`): From Date_Col field
- **MRI Primary** (`mri_primary`): From Dt_MRI1 with TNM staging details

#### Data Quality Standards
- `result`: Leading numbers removed (e.g., "1 Normal" → "normal")
- Investigation ID format: `INV-{patient_id}-{type}-{seq}`
- All imaging data extracted from tumours.csv fields

---

### 6. Clinicians Collection (`clinicians`)

**Purpose:** Clinician directory for active clinical staff

#### Schema
```python
{
    "_id": ObjectId,
    "clinician_id": str,             # Unique identifier
    "name": str,                     # Full name
    "specialty": str | null,         # Colorectal/Upper GI/General Surgery/etc
    "grade": str | null,             # consultant/specialist_registrar/core_trainee
    "active": bool,                  # Active status
    "created_at": datetime,
    "updated_at": datetime
}
```

---

### 7. NHS Providers Collection (`nhs_providers`)

**Purpose:** NHS organization codes and names for COSD compliance

#### Schema
```python
{
    "_id": ObjectId,
    "code": str,                     # NHS organization code (e.g., "RHU", "RDZ")
    "name": str,                     # Full organization name
    "type": str,                     # NHS Trust/Hospital/GP Practice/etc
    "active": bool
}
```

---

## Relationships

### Patient → Episodes (1:N)
- One patient can have multiple episodes
- Join: `patients.patient_id` = `episodes.patient_id`

### Episode → Treatments (1:N)
- One episode can have multiple treatments
- Join: `episodes.episode_id` = `treatments.episode_id`
- Treatments are also denormalized within episodes for performance

### Episode → Tumours (1:N)
- One cancer episode can track multiple tumour sites
- Join: `episodes.episode_id` = `tumours.episode_id`
- Tumours are also denormalized within episodes for performance

### Episode → Investigations (1:N)
- One episode can have multiple investigations
- Join: `episodes.episode_id` = `investigations.episode_id`

### Tumour → Investigations (1:N)
- Investigations can be linked to specific tumour sites
- Join: `tumours.tumour_id` = `investigations.tumour_id`

---

## Data Standards

### String Format Standards

All categorical fields follow these conventions:

1. **No leading numbers**: "1 GP" → "gp"
2. **Lowercase snake_case**: "Two Week Wait" → "two_week_wait"
3. **No ObjectId strings**: Lead clinician stored as name string, not ObjectId
4. **Boolean fields use yes/no**: "1 Yes" → "yes", "2 No" → "no"

### Date Handling

- **Date fields**: Stored as ISO 8601 strings (YYYY-MM-DD) or datetime objects
- **Date parsing**: Flexible parser handles multiple formats during import
- **Display**: Frontend formats dates for display

### TNM Staging

- **Storage**: Simple numbers/letters (e.g., "3", "1a", "0")
- **Display**: Frontend adds prefixes (e.g., "T3", "N1a", "M0")
- **Versions**: TNM v7 or v8 specified via `tnm_version` field

### Surgical Approach Priority Logic

When determining surgical approach:
1. **First check**: Robotic field = true → "robotic"
2. **Then check**: "converted to open" in LapType → "converted"
3. **Otherwise**: Use LapProc mapping → "open/laparoscopic"

### Defunctioning Stoma Logic

Returns "yes" ONLY when:
- `anastomosis_performed` = true AND
- `stoma_created` = true

This identifies protective/defunctioning stomas specifically.

---

## NBOCA/COSD Compliance

### National Bowel Cancer Audit (NBOCA) Fields

The database tracks NBOCA-required fields with their official codes:

#### Referral Pathway
- **CR1600** `referral_source`: Referral route
- **CR1410** `provider_first_seen`: NHS Trust code where first seen
- **CR2050** `cns_involved`: Clinical Nurse Specialist involvement
- **CR3190** `mdt_meeting_type`: MDT meeting type
- **CR0510** `performance_status`: ECOG performance status
- **CR0490** `no_treatment_reason`: Reason for no treatment

#### Diagnosis
- **CR2030** `diagnosis_date`: Date of primary diagnosis
- **CR0370** `icd10_code`: ICD-10 diagnosis code
- **CR6400** `snomed_morphology`: SNOMED morphology code

#### Staging
- **CR2070/pCR6820** `tnm_version`: TNM classification version (7 or 8)
- **CR0520** `clinical_t`: Clinical T stage
- **CR0540** `clinical_n`: Clinical N stage
- **CR0560** `clinical_m`: Clinical M stage
- **pCR0910** `pathological_t`: Pathological T stage
- **pCR0920** `pathological_n`: Pathological N stage
- **pCR0930** `pathological_m`: Pathological M stage

#### Pathology
- **pCR0890** `lymph_nodes_examined`: Total lymph nodes examined
- **pCR0900** `lymph_nodes_positive`: Positive lymph nodes
- **pCR1150** `margin_status`: Resection margin status (R0/R1/R2)

#### Treatment
- **CR1450** `provider_organisation`: NHS Trust code of provider
- **CO5160** `distance_from_anal_verge_cm`: Height above anal verge (rectal cancers)

### Cancer Outcomes and Services Dataset (COSD)

The system supports COSD v9+ exports with all required fields mapped to the appropriate COSD codes as listed above.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-30 | Initial schema documentation based on comprehensive data quality cleanup |

---

## Maintenance Notes

**When making schema changes:**
1. Update this document first
2. Update Pydantic models in `/root/impact/backend/app/models/`
3. Update import scripts in `/root/impact/execution/migrations/`
4. Test changes in `impact_test` database before production
5. Document changes in `RECENT_CHANGES.md`
6. Update version history above
