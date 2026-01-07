# IMPACT User Guide

**Version:** 1.6.2
**Last Updated:** January 2026
**Document Status:** Production

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [User Roles and Permissions](#user-roles-and-permissions)
4. [Patient Management](#patient-management)
5. [Episode Management](#episode-management)
6. [Treatment Recording](#treatment-recording)
7. [Tumour Tracking](#tumour-tracking)
8. [Investigation Management](#investigation-management)
9. [Reports and Analytics](#reports-and-analytics)
10. [NBOCA COSD Export](#nboca-cosd-export)
11. [Data Quality Dashboard](#data-quality-dashboard)
12. [Keyboard Shortcuts](#keyboard-shortcuts)
13. [Troubleshooting](#troubleshooting)

---

## Introduction

IMPACT (Integrated Monitoring Platform for Audit Care & Treatment) is a comprehensive surgical outcomes tracking system designed specifically for colorectal cancer care and general surgery. The system is fully compliant with National Bowel Cancer Audit (NBOCA) requirements and supports COSD v9/v10 XML exports for national audit submissions.

### Key Features

- **Patient Management**: Complete patient demographics and medical history tracking
- **Episode-Based Care**: Track cancer, IBD, and benign condition episodes from referral to follow-up
- **Treatment Recording**: Record all treatment modalities including surgery, chemotherapy, radiotherapy
- **TNM Staging**: Full support for TNM v7 and v8 staging with pathology data
- **NBOCA Compliance**: All 59/59 mandatory COSD fields implemented with validation
- **Data Quality**: Real-time completeness tracking and pre-submission validation
- **Security**: AES-256 field-level encryption for sensitive patient data
- **Audit Trail**: Comprehensive logging of all data changes

---

## Getting Started

### Logging In

1. Navigate to the IMPACT application URL (e.g., `http://impact.vps:3000`)
2. Enter your email address and password
3. Click "Sign In"

**Default Administrator Credentials** (change immediately after first login):
- Email: `admin@example.com`
- Password: `admin123`

### Dashboard Overview

After logging in, you'll see the main dashboard with:
- **Total Patients**: Overall patient count
- **Active Episodes**: Currently active clinical episodes
- **Total Treatments**: All recorded treatments
- **Recent Activity**: Latest data entries and modifications

### Navigation

The main navigation menu provides access to:
- **Patients**: Patient list and management
- **Episodes**: Clinical episode tracking
- **Reports**: Analytics and outcome reports
- **Admin**: User and clinician management (admin only)

---

## User Roles and Permissions

IMPACT implements role-based access control with four user roles:

### Admin
- Full system access
- User management
- Clinician management
- System configuration
- Data export and backup
- NBOCA XML export

### Surgeon
- View all patient data
- Create and edit episodes and treatments
- View reports and analytics
- Cannot manage users or clinicians

### Data Entry
- Create and edit patient records
- Create and edit episodes and treatments
- Limited report access
- Cannot manage users or export data

### Viewer
- Read-only access to patient data
- View reports and analytics
- Cannot create or modify records

---

## Patient Management

### Creating a New Patient

1. Navigate to **Patients** page
2. Click **"Add Patient"** button (or press `N` keyboard shortcut)
3. Complete the patient form:

#### Demographics Tab
- **NHS Number**: 10-digit national identifier (automatically formatted)
- **Medical Record Number (MRN)**: Hospital identifier (8 digits or IW+6 digits)
- **Date of Birth**: Patient's date of birth
- **Age**: Auto-calculated from DOB
- **Gender**: Male/Female/Other
- **Ethnicity**: Ethnicity code (required for NBOCA)
- **Postcode**: UK postcode (required for NBOCA)

#### Medical History Tab
- **Conditions**: Pre-existing medical conditions
- **Previous Surgeries**: Surgical history
- **Medications**: Current medications
- **Allergies**: Known drug allergies
- **Smoking Status**: Never/Former/Current
- **Alcohol Use**: Consumption level

4. Click **"Save"** to create the patient record

### Searching for Patients

**Search Methods:**
- **Quick Search**: Type in the search box to filter by name, NHS number, or MRN
- **Advanced Filters**: Use filters for gender, age range, ethnicity
- **Keyboard Navigation**: Use arrow keys to navigate results, Enter to select

### Editing Patient Records

1. Find the patient in the patients list
2. Click the patient row or press Enter
3. Click **"Edit"** button
4. Make necessary changes
5. Click **"Save"** to update

**Note:** All changes are logged in the audit trail with user information and timestamp.

### Data Security

- NHS numbers and MRNs are encrypted at rest using AES-256 encryption
- Dates of birth and postcodes are also encrypted for GDPR compliance
- All access is logged for audit purposes

---

## Episode Management

Episodes represent distinct clinical contacts or treatment pathways for conditions such as cancer, IBD, or benign conditions.

### Creating a Cancer Episode

1. Navigate to **Episodes** page
2. Click **"Add Episode"** button
3. Select or search for the patient
4. Complete the episode form:

#### Basic Information
- **Condition Type**: Cancer/IBD/Benign
- **Cancer Type**: Bowel/Kidney/Breast/Oesophageal/Ovarian/Prostate
- **Referral Date**: Date patient was referred (COSD CR1600)
- **First Seen Date**: Date first seen by provider (COSD CR1410)
- **Referral Source**: GP/Consultant/Screening/Two Week Wait/Emergency/Other
- **Provider First Seen**: NHS Trust code (e.g., "RHU")

#### MDT Information
- **MDT Discussion Date**: Date of multidisciplinary team meeting
- **MDT Meeting Type**: Colorectal/Upper GI/Lower GI/Combined/Other (COSD CR3190)
- **Lead Clinician**: Responsible consultant
- **MDT Team**: Team members involved

#### Clinical Assessment
- **Performance Status**: ECOG score 0-5 (COSD CR0510)
- **CNS Involved**: Clinical Nurse Specialist involvement (COSD CR2050)
- **Treatment Intent**: Curative/Palliative
- **Treatment Plan**: Free text description

4. Click **"Save"** to create the episode

### Adding Tumours to Episodes

For cancer episodes, you must record at least one tumour:

1. Open the episode detail view
2. Click **"Add Tumour"** button
3. Complete the tumour form:

#### Diagnosis
- **Diagnosis Date**: Date of primary diagnosis (COSD CR2030)
- **ICD-10 Code**: Primary diagnosis code (e.g., C18.7 for sigmoid colon) (COSD CR0370)
- **SNOMED Morphology**: Morphology code (COSD CR6400)
- **Tumour Site**: Anatomical location
- **Tumour Type**: Primary/Metastasis/Recurrence

#### TNM Staging
- **TNM Version**: 7 or 8 (COSD CR2070)
- **Clinical T**: T category (pretreatment) (COSD CR0520)
- **Clinical N**: N category (pretreatment) (COSD CR0540)
- **Clinical M**: M category (pretreatment) (COSD CR0560)
- **Pathological T**: Post-surgery T stage (COSD pCR6820)
- **Pathological N**: Post-surgery N stage (COSD pCR0910)
- **Pathological M**: Post-surgery M stage (COSD pCR0920)

#### Pathology
- **Grade**: Well/Moderate/Poor/Undifferentiated (COSD pCR0930)
- **Histology Type**: Adenocarcinoma/Mucinous/Signet Ring/Other
- **Lymph Nodes Examined**: Total nodes counted (COSD pCR0890)
- **Lymph Nodes Positive**: Positive nodes (COSD pCR0900)
- **CRM Status**: Circumferential resection margin (COSD pCR1150) - **Mandatory for rectal cancer**
- **CRM Distance**: Distance to margin in mm
- **Lymphovascular Invasion**: Present/Absent/Uncertain
- **Perineural Invasion**: Present/Absent/Uncertain

#### Molecular Markers (Optional)
- **KRAS Status**: Wild type/Mutant/Unknown
- **BRAF Status**: Wild type/Mutant/Unknown
- **MMR Status**: Proficient/Deficient/Unknown

4. Click **"Save"** to add the tumour

---

## Treatment Recording

### Recording Surgical Treatment

1. Open the episode detail view
2. Click **"Add Treatment"** button
3. Select **"Surgery (Primary)"** as treatment type
4. Complete the surgical treatment form:

#### Classification
- **Urgency**: Elective/Urgent/Emergency (COSD CO6000)
- **Complexity**: Routine/Intermediate/Complex
- **Primary Diagnosis**: Main diagnosis
- **Indication**: Cancer/IBD/Diverticular/Benign/Other

#### Procedure Details
- **Primary Procedure**: Main procedure name
- **OPCS-4 Code**: Procedure code (e.g., H33 for right hemicolectomy) (COSD CR0720) - **Mandatory**
- **Additional Procedures**: Any additional procedures performed
- **Surgical Approach**: Open/Laparoscopic/Robotic/Converted (COSD CR6310)
- **Robotic Surgery**: Whether robotic assistance used
- **Conversion to Open**: If converted from laparoscopic

#### Timeline
- **Admission Date**: Date admitted to hospital
- **Surgery Date**: Date of operation (COSD CR0710)
- **Operation Duration**: Length of procedure in minutes
- **Discharge Date**: Date discharged from hospital
- **Length of Stay**: Auto-calculated

#### Surgical Team
- **Primary Surgeon**: Lead surgeon (COSD requirement)
- **Assistant Grade**: Consultant/Specialist Registrar/Core Trainee/Other
- **Anaesthetist**: Anaesthesiologist name

#### Intraoperative Details
- **ASA Score**: 1-5 (COSD CR6010) - **Mandatory for surgical patients**
- **Anaesthesia Type**: General/Regional/Local
- **Blood Loss**: Volume in millilitres
- **Transfusion Required**: Yes/No
- **Intraoperative Findings**: Free text description

#### Stoma Information
- **Stoma Created**: Yes/No
- **Stoma Type**: Loop Ileostomy/End Ileostomy/Loop Colostomy/End Colostomy
- **Defunctioning Stoma**: Auto-calculated (Yes if both stoma AND anastomosis created)

#### Anastomosis Information
- **Anastomosis Performed**: Yes/No
- **Anastomosis Type**: Hand sewn/Stapled/Hybrid
- **Configuration**: End-to-end/End-to-side/Side-to-side
- **Location**: Colorectal/Coloanal/Ileocolic/Ileorectal/Other
- **Height Above Anal Verge**: Distance in cm (for rectal)

#### Postoperative Events
- **Complications**: Record any complications with Clavien-Dindo grade (I-V)
- **Anastomotic Leak**: Full tracking with ISGPS severity (A-C)
- **Return to Theatre**: Auto-linked when RTT surgery created
- **Escalation of Care**: ICU/HDU admission

#### Outcomes
- **30-day Readmission**: Yes/No with reason
- **30-day Mortality**: Yes/No
- **90-day Mortality**: Yes/No
- **Date of Death**: If applicable

5. Click **"Save"** to record the treatment

### Recording Return to Theatre (RTT)

If a patient requires reoperation:

1. Open the episode detail view
2. Click **"Add Treatment"** button
3. Select **"Surgery (Return to Theatre)"** as treatment type
4. **Parent Surgery**: Select the original surgery from dropdown (required)
5. **RTT Reason**: Specify reason for return (required)
6. Complete other surgical details as above
7. Click **"Save"**

**Automatic Updates:**
- Parent surgery's "Return to Theatre" flag set to True
- Parent surgery's RTT date and reason auto-populated
- Link added to parent surgery's related surgeries list

### Recording Stoma Reversal

1. Open the episode detail view
2. Click **"Add Treatment"** button
3. Select **"Surgery (Stoma Reversal)"** as treatment type
4. **Parent Surgery**: Select the surgery where stoma was created (required)
5. **Reversal Notes**: Optional notes
6. Complete other surgical details as above
7. Click **"Save"**

**Automatic Updates:**
- Parent surgery's stoma closure date set to reversal date
- Parent surgery's reversal treatment ID recorded
- Link added to parent surgery's related surgeries list

### Recording Chemotherapy

1. Open the episode detail view
2. Click **"Add Treatment"** button
3. Select **"Chemotherapy"** as treatment type
4. Complete:
   - **Regimen**: Chemotherapy protocol (e.g., FOLFOX, CAPOX)
   - **Treatment Intent**: Adjuvant/Neoadjuvant/Palliative
   - **Start Date**: Treatment commencement date
   - **Cycles Planned**: Number of cycles planned
   - **Cycles Completed**: Number completed
   - **Response**: Response to treatment
5. Click **"Save"**

### Recording Radiotherapy

1. Open the episode detail view
2. Click **"Add Treatment"** button
3. Select **"Radiotherapy"** as treatment type
4. Complete:
   - **Technique**: IMRT/3DCRT/SBRT/Other
   - **Total Dose**: Dose in Gray (Gy)
   - **Fractions**: Number of treatment sessions
   - **Treatment Intent**: Neoadjuvant/Adjuvant/Palliative
   - **Target Site**: Treatment location
5. Click **"Save"**

---

## Tumour Tracking

### Viewing Tumours

- Navigate to **Episodes** page
- Click on an episode to view details
- Tumours are displayed in the episode detail view
- Each tumour shows:
  - Tumour ID
  - Site and type
  - TNM staging
  - ICD-10 code
  - Diagnosis date

### Editing Tumours

1. Open the episode detail view
2. Find the tumour in the list
3. Click **"Edit"** button
4. Make necessary changes
5. Click **"Save"**

**Important:**
- CRM status is **mandatory for rectal cancer** (ICD-10 codes C19, C20)
- Minimum 12 lymph nodes should be examined for adequate staging
- TNM version must be specified (7 or 8)

---

## Investigation Management

IMPACT tracks clinical investigations including imaging, endoscopy, and laboratory tests.

### Adding Investigations

1. Open the episode detail view
2. Click **"Add Investigation"** button
3. Select investigation type:
   - **Imaging**: CT Abdomen, CT Colonography, MRI Primary, MRI Liver
   - **Endoscopy**: Colonoscopy, Sigmoidoscopy
   - **Laboratory**: Blood tests, tumour markers
4. Complete investigation details:
   - **Date**: Investigation date
   - **Result**: Primary finding
   - **Findings**: Detailed structured findings
   - **Notes**: Free text notes
5. Click **"Save"**

### MRI Primary Investigation

For rectal cancer staging, MRI provides critical information:
- **T Stage**: MRI T category
- **N Stage**: MRI N category
- **CRM Status**: Margin involvement
- **Distance from Anal Verge**: Tumour height in cm
- **EMVI**: Extramural vascular invasion (Yes/No)

---

## Reports and Analytics

### Summary Report

View overall surgical outcomes:
- **Total Surgeries**: All recorded surgical procedures
- **Complication Rate**: Percentage with complications
- **Readmission Rate**: 30-day readmissions
- **30-day Mortality**: Early mortality rate
- **90-day Mortality**: Extended mortality rate
- **Return to Theatre Rate**: Percentage requiring reoperation
- **Escalation Rate**: ICU/HDU admission rate
- **Median Length of Stay**: Average hospital stay in days

### Surgeon Performance Report

View individual surgeon outcomes:
- Aggregated metrics per clinician
- Yearly breakdown (2023-2025)
- Color-coded performance indicators
- Case volume and complexity

### NBOCA Compliance Report

Track data completeness for NBOCA submission:
- **Field Completeness**: Percentage complete per field
- **Mandatory Fields**: 59/59 COSD field status
- **Missing Data**: Fields requiring completion
- **Validation Status**: Pre-submission checks

### Excel Export

All reports can be exported to Excel:
1. Open any report view
2. Click **"Export to Excel"** button
3. Excel file downloads with professional formatting
4. Includes charts, tables, and summary statistics

---

## NBOCA COSD Export

### Generating XML Export

1. Navigate to **Admin** → **Exports** (admin only)
2. Select **"NBOCA XML Export"**
3. Optional: Filter by date range
   - **Start Date**: Include episodes from this date
   - **End Date**: Include episodes until this date
4. Click **"Generate XML"**
5. XML file downloads in COSD v9/v10 format

### What's Included

The XML export includes:
- **Patient Demographics**: NHS number, DOB, gender, ethnicity, postcode
- **Episode Information**: Referral pathway, MDT details, performance status
- **Tumour Data**: TNM staging, pathology, ICD-10 codes
- **Treatment Details**: Surgery details, OPCS-4 codes, ASA scores
- **Outcomes**: Complications, mortality, readmissions

### Export Validation

Before generating XML:
1. Run **"Data Completeness Check"** to identify missing fields
2. Run **"NBOCA Validator"** to check submission readiness
3. Review validation report and fix any errors
4. Ensure all mandatory fields are complete:
   - NHS Number (CR0010)
   - Date of Birth (CR0100)
   - Gender (CR3170)
   - Postcode (CR0080)
   - Diagnosis Date (CR2030)
   - ICD-10 Code (CR0370)
   - TNM Staging (CR0520, CR0540, CR0560)
   - OPCS-4 Code (CR0720) - for surgical patients
   - ASA Score (CR6010) - for surgical patients
   - CRM Status (pCR1150) - for rectal cancer

---

## Data Quality Dashboard

### Accessing the Dashboard

1. Navigate to **Admin** → **Data Quality**
2. View real-time completeness metrics

### Metrics Displayed

- **Patient Demographics**: Completeness percentage
  - NHS Number
  - Date of Birth
  - Gender
  - Ethnicity
  - Postcode

- **Diagnosis Data**: Completeness percentage
  - Diagnosis Date
  - ICD-10 Code
  - TNM Staging

- **Surgery Data**: Completeness percentage (for surgical episodes)
  - OPCS-4 Code
  - ASA Score
  - Surgical Approach
  - Urgency

### Improving Data Quality

1. Review fields with low completeness (<90%)
2. Use search filters to find incomplete records
3. Edit records to add missing mandatory fields
4. Re-run data quality check to verify improvement

---

## Keyboard Shortcuts

IMPACT supports keyboard shortcuts for efficient navigation:

### Global Shortcuts
- `Ctrl + K` or `Cmd + K`: Open command palette
- `H`: Open help dialog
- `Esc`: Close modal/dialog

### Patients Page
- `N`: Create new patient
- `↑/↓`: Navigate patient list
- `Enter`: Open selected patient
- `/`: Focus search box

### Episodes Page
- `N`: Create new episode
- `↑/↓`: Navigate episode list
- `Enter`: Open selected episode
- `/`: Focus search box

### Modal Navigation
- `Tab`: Next field
- `Shift + Tab`: Previous field
- `Enter`: Submit form (when valid)
- `Esc`: Close modal

---

## Troubleshooting

### Common Issues

#### "Could not validate credentials" Error
**Solution**: Your session has expired. Click "Sign Out" and log in again.

#### Cannot See "Add Patient" Button
**Solution**: You need Data Entry, Surgeon, or Admin role. Contact your administrator.

#### NHS Number Not Accepted
**Solution**: NHS number must be exactly 10 digits. Check for spaces or incorrect formatting.

#### Cannot Export XML
**Solution**: XML export requires Admin role. Contact your administrator.

#### Tumour CRM Status Required
**Solution**: For rectal cancer (C19, C20), CRM status is mandatory. Select Clear/Involved/Close.

#### Missing OPCS-4 Code Validation Error
**Solution**: All surgical treatments require a valid OPCS-4 procedure code for NBOCA submission.

### Getting Help

**Technical Support:**
- Email: support@example.com
- Internal Help Desk: ext. 1234

**Training Resources:**
- User Guide: `/docs/USER_GUIDE.md`
- Video Tutorials: (link to training videos)
- NBOCA Documentation: https://www.nboca.org.uk

### Reporting Bugs

If you encounter a bug:
1. Note the exact steps to reproduce
2. Take a screenshot if applicable
3. Check the browser console for errors (F12)
4. Report to IT support with details

---

## Appendix A: NBOCA Field Codes Reference

| COSD Code | Field Name | Required | Notes |
|-----------|-----------|----------|-------|
| CR0010 | NHS Number | Mandatory | 10 digits |
| CR0100 | Date of Birth | Mandatory | YYYY-MM-DD |
| CR3170 | Gender | Mandatory | Male/Female/Other |
| CR0080 | Postcode | Mandatory | UK postcode |
| CR0150 | Ethnicity | Mandatory | Ethnicity code |
| CR1600 | Referral Source | Recommended | GP/Consultant/Screening/2WW |
| CR1410 | Provider First Seen | Recommended | NHS Trust code |
| CR2050 | CNS Involved | Recommended | Yes/No/Unknown |
| CR3190 | MDT Meeting Type | Recommended | Colorectal/Upper GI/etc |
| CR0510 | Performance Status | Recommended | ECOG 0-5 |
| CR2030 | Diagnosis Date | Mandatory | Date of diagnosis |
| CR0370 | ICD-10 Code | Mandatory | C18.x-C20 for bowel |
| CR6400 | SNOMED Morphology | Recommended | Morphology code |
| CR2070 | TNM Version | Mandatory | 7 or 8 |
| CR0520 | Clinical T Stage | Mandatory | Tx-T4b |
| CR0540 | Clinical N Stage | Mandatory | Nx-N2b |
| CR0560 | Clinical M Stage | Mandatory | Mx-M1c |
| pCR6820 | Pathological T | Recommended | pTx-pT4b |
| pCR0910 | Pathological N | Recommended | pNx-pN2b |
| pCR0920 | Pathological M | Recommended | pMx-pM1c |
| pCR0930 | Grade | Mandatory | Well/Moderate/Poor |
| pCR0890 | Lymph Nodes Examined | Recommended | Minimum 12 |
| pCR0900 | Lymph Nodes Positive | Recommended | Count |
| pCR1150 | CRM Status | Mandatory (rectal) | Clear/Involved/Close |
| CR0720 | OPCS-4 Code | Mandatory (surgery) | Procedure code |
| CR6010 | ASA Score | Mandatory (surgery) | 1-5 |
| CR6310 | Surgical Approach | Recommended | Open/Lap/Robotic |
| CO6000 | Urgency | Recommended | Elective/Urgent/Emergency |
| CR0710 | Surgery Date | Mandatory (surgery) | Date of operation |
| CR1450 | Provider Organisation | Recommended | NHS Trust code |

---

**End of User Guide**

For technical documentation, see:
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- [TECHNICAL_SPECIFICATIONS.md](TECHNICAL_SPECIFICATIONS.md)
- [SECURITY_AND_COMPLIANCE.md](SECURITY_AND_COMPLIANCE.md)
- [DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md)
