# User Guide

Complete guide for using the Surgical Outcomes Database application.

## Table of Contents

- [Introduction](#introduction)
- [Getting Started](#getting-started)
- [Patient Management](#patient-management)
- [Cancer Episode Management](#cancer-episode-management)
- [Reports and Analytics](#reports-and-analytics)
- [Admin Functions](#admin-functions)
- [NBOCA Submission](#nboca-submission)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Introduction

The Surgical Outcomes Database is designed to help surgical teams record, track, and analyze patient outcomes, with special compliance support for the National Bowel Cancer Audit (NBOCA).

### User Roles

- **Admin**: Full system access, user management, NBOCA exports
- **Surgeon**: View and edit clinical data, access reports
- **Data Entry**: Create and edit patient and episode records
- **Viewer**: Read-only access to data and reports

---

## Getting Started

### Logging In

1. Open the application in your web browser
2. Enter your username and password
3. Click "Login"

**First Login:**
- Default admin username: `admin`
- Default admin password: `admin123`
- **⚠️ Change your password immediately after first login**

### Dashboard Overview

After logging in, you'll see the home page with:
- Quick statistics (Total Patients, Episodes, Recent Activity)
- Navigation menu (Patients, Episodes, Reports, Admin)
- Search bar for finding patients quickly

---

## Patient Management

### Creating a New Patient

1. Click **"Patients"** in the navigation menu
2. Click **"Add Patient"** button
3. Fill in the required fields:

#### Demographics (Required)
- **NHS Number**: 10 digits (format: XXX XXX XXXX)
- **Record Number**: Unique hospital identifier
- **Date of Birth**: Format DD/MM/YYYY
- **Gender**: Male, Female, or Other

#### Demographics (Optional)
- **Ethnicity**: Select from dropdown (NBOCA categories)
- **Postcode**: UK postcode format (e.g., SW1A 1AA)
- **Weight**: In kilograms
- **Height**: In centimeters
- **BMI**: Auto-calculated when weight and height provided

**💡 Tip**: When you enter both weight and height, BMI is automatically calculated and shows a WHO category (Underweight, Normal weight, Overweight, Obesity).

#### Medical History
- **Existing Conditions**: Diabetes, hypertension, COPD, etc.
- **Medications**: Current medications list
- **Allergies**: Any known allergies
- **Smoking Status**: Never, Current, Former
- **Alcohol Use**: None, Moderate, Heavy

### Editing a Patient

1. Find the patient in the patient list
2. Click the **"Edit"** button next to their record
3. Update fields as needed
4. Click **"Save Changes"**

### Searching for Patients

Use the search bar to find patients by:
- NHS Number
- Record Number
- Name (if stored)

---

## Cancer Episode Management

### Creating a Cancer Episode

1. Select a patient from the patient list
2. Click **"Add Episode"** or navigate to Episodes page
3. Select **"Bowel Cancer Episode"** template
4. Complete the required sections

### Episode Sections

#### 1. Diagnosis Information

**Required Fields:**
- **Episode ID**: Unique identifier (e.g., EP001)
- **Diagnosis Date**: When cancer was diagnosed
- **Primary Site**: ICD-10 code (use lookup)

**💡 Tip**: Click the magnifying glass icon next to ICD-10 code to search available codes. For example:
- C18.7 = Sigmoid colon
- C20 = Rectum
- C19 = Rectosigmoid junction

**Optional Fields:**
- **Symptoms**: Bleeding, pain, change in bowel habit, etc.
- **Referral Source**: GP, screening, emergency
- **Performance Status**: 0-4 (ECOG scale)

#### 2. MDT Discussion

- **MDT Date**: When discussed at multi-disciplinary meeting
- **MDT Outcome**: Treatment recommendation
- **Participants**: Surgeons, oncologists, radiologists present

#### 3. TNM Staging

Enter tumour staging details:
- **T Stage**: T1, T2, T3, T4a, T4b
- **N Stage**: N0, N1a, N1b, N2a, N2b
- **M Stage**: M0, M1a, M1b, M1c
- **TNM Version**: 8th edition (current standard)

**💡 Tip**: If unsure about staging, consult pathology report or MDT notes.

#### 4. Treatment Details

**Pre-operative Treatment:**
- Chemotherapy dates and cycles
- Radiotherapy dates and dose
- Response to neoadjuvant therapy

**Surgery:**
- **Operation Date**: Required for NBOCA
- **Procedure**: OPCS-4 code (use lookup)
- **Surgeon**: Select from dropdown
- **Urgency**: Elective, Urgent, Emergency
- **ASA Score**: 1-5 (validated automatically)
- **Approach**: Open, Laparoscopic, Robotic
- **Conversion**: If laparoscopic converted to open

**💡 Tip**: Use OPCS-4 code lookup:
- H04-H06 = Right hemicolectomy
- H07-H08 = Anterior resection
- H09 = Abdominoperineal resection
- H46-H48 = Laparoscopic procedures

**Operative Details:**
- **Duration**: In minutes
- **Blood Loss**: In millilitres
- **Stoma Created**: Yes/No and type
- **Anastomosis**: Yes/No
- **Specimen**: Describe resection

#### 5. Pathology Results

- **Tumour Size**: In millimetres
- **Differentiation**: Well, Moderate, Poor
- **Lymph Nodes**: Examined and positive counts
- **Margins**: Clear, Close, Involved (with distances)
- **Lymphovascular Invasion**: Yes/No
- **Perineural Invasion**: Yes/No

**🔍 NBOCA Requirement**: Minimum 12 lymph nodes should be examined for adequate staging.

#### 6. Post-operative Course

**Complications:**
- Select from dropdown (Clavien-Dindo classification)
- Common: Anastomotic leak, ileus, wound infection
- Grade: I-V based on severity

**💡 Tip**: Anastomotic leak detection:
- Enter "anastomotic leak" in complications
- System tracks for NBOCA reporting
- May require return to theatre

**Discharge:**
- **Date**: Discharge date
- **Length of Stay**: Auto-calculated
- **Destination**: Home, rehabilitation, nursing home

**Follow-up:**
- **Readmission**: Within 30 days
- **Mortality**: 30-day and 90-day status
- **Adjuvant Treatment**: Chemotherapy planned/received

---

## Reports and Analytics

### Accessing Reports

Navigate to **"Reports"** in the main menu.

### Available Reports

#### 1. Summary Report

Overview of all surgical activity:
- Total surgeries
- Average operation duration
- Complication rate
- Readmission rate
- Mortality rate
- Return to theatre rate
- Average length of stay
- Urgency breakdown (Elective/Urgent/Emergency)

**Download**: Click **"Export Summary (Excel)"** to download spreadsheet.

#### 2. Surgeon Performance

Per-surgeon metrics:
- Total surgeries
- Complication rate
- Readmission rate
- Average duration
- Average length of stay

**Download**: Click **"Export Surgeon Performance (Excel)"**.

**💡 Tip**: Use for appraisal, revalidation, or quality improvement.

#### 3. Trends Report

Daily surgery counts over time period:
- Default: Last 30 days
- Visualize workload patterns
- Identify capacity issues

**Download**: Click **"Export Trends (Excel)"**.

#### 4. NBOCA Mortality Report

National audit specific report:
- 30-day mortality rate
- 90-day mortality rate
- Breakdown by urgency (Elective vs Emergency)

**🔍 NBOCA Standard**: Elective mortality <2%, Emergency <15%

**Download**: Click **"Export NBOCA Mortality (Excel)"**.

#### 5. NBOCA Anastomotic Leak Report

Leak rates for procedures with anastomosis:
- Overall leak rate
- Per-procedure breakdown
- Identifies high-risk procedures

**🔍 NBOCA Standard**: Leak rate <8% for anterior resection

**Download**: Click **"Export NBOCA Leak Analysis (Excel)"**.

#### 6. NBOCA Conversion Rates

Laparoscopic to open conversion tracking:
- Overall conversion rate
- Per-procedure conversion rates

**🔍 NBOCA Standard**: Conversion rate <15% is acceptable

**View**: Click **"View Conversion Rates"** for JSON data.

---

## Admin Functions

**⚠️ Admin Role Required**

### User Management

#### Creating Users

1. Click **"Admin"** in navigation
2. Go to **"User Management"** tab
3. Click **"Add User"**
4. Fill in details:
   - Username (unique)
   - Password (minimum 8 characters)
   - Full Name
   - Role (Admin/Surgeon/Data Entry/Viewer)
5. Click **"Create User"**

#### Editing Users

1. Find user in list
2. Click **"Edit"**
3. Update fields (cannot change username)
4. Click **"Save Changes"**

#### Deleting Users

1. Find user in list
2. Click **"Delete"**
3. Confirm deletion

**⚠️ Warning**: Cannot delete the last admin user.

### Clinician Management

#### Adding Clinicians

1. Click **"Admin"** → **"Clinicians"** tab
2. Click **"Add Clinician"**
3. Enter details:
   - Full Name
   - GMC Number (7 digits)
   - Speciality (Colorectal Surgery, General Surgery, etc.)
   - Grade (Consultant, ST3-ST8, SAS)
4. Click **"Save"**

**💡 Tip**: Clinicians appear in surgery dropdown lists.

---

## NBOCA Submission

**⚠️ Admin Role Required**

### Checking Data Completeness

1. Navigate to **"Admin"** → **"NBOCA Exports"**
2. Click **"Check Data Completeness"**
3. Review completeness percentages:
   - Patient Demographics
   - Diagnosis Information
   - TNM Staging
   - Pathology
   - Surgery Details

**🔍 Target**: >95% completeness for all sections

### Validating Data

1. Click **"Validate NBOCA Data"**
2. Review validation report:
   - **Errors**: Must fix before submission (red)
   - **Warnings**: Should review (yellow)
   - **Valid**: Ready to submit (green)

Common Errors:
- Missing NHS number
- Missing diagnosis date
- Missing procedure code
- ASA score outside 1-5 range
- TNM staging incomplete

**💡 Tip**: Click on episode ID to jump directly to that record for editing.

### Exporting NBOCA XML

Once validation passes:

1. Click **"Download NBOCA XML"**
2. Save file (format: `nboca_submission_YYYYMMDD.xml`)
3. Upload to NBOCA submission portal

**File Format**: COSD v9/v10 compliant XML

### Submission Checklist

- [ ] Data completeness >95%
- [ ] Validation shows 0 errors
- [ ] Review all warnings
- [ ] Confirm date range covers submission period
- [ ] Download XML file
- [ ] Upload to NBOCA portal
- [ ] Confirm submission received

---

## Best Practices

### Data Entry

1. **Enter Data Promptly**: Record within 48 hours of surgery
2. **Use Code Lookups**: Always use ICD-10 and OPCS-4 lookups to ensure valid codes
3. **Complete All Fields**: Aim for 100% completeness on mandatory fields
4. **Check BMI**: Ensure weight and height are entered for auto-calculation
5. **Verify NHS Numbers**: Use NHS number validation tools

### Quality Assurance

1. **Weekly Reviews**: Check recent entries for completeness
2. **Monthly Reports**: Review surgeon performance and trends
3. **Quarterly NBOCA**: Run validation checks before submission
4. **Annual Audits**: Complete data quality audit

### Security

1. **Strong Passwords**: Minimum 8 characters, mix of types
2. **Log Out**: Always log out when leaving workstation
3. **Screen Privacy**: Use privacy screens in public areas
4. **Data Protection**: Never share patient data via email
5. **Regular Backups**: Ensure backups are running (check with IT)

---

## Troubleshooting

### Cannot Log In

**Problem**: "Invalid username or password"

**Solutions**:
1. Check CAPS LOCK is off
2. Verify username spelling
3. Try password reset (contact admin)
4. Check account is active (contact admin)

### BMI Not Auto-Calculating

**Problem**: BMI field stays empty after entering height and weight

**Solutions**:
1. Ensure both height (cm) and weight (kg) are entered
2. Check values are numeric
3. Refresh the page
4. Try entering values again

### Cannot Find ICD-10/OPCS-4 Code

**Problem**: Code lookup returns no results

**Solutions**:
1. Use broader search terms (e.g., "sigmoid" instead of "sigmoid colon")
2. Browse all codes using "Show All Codes" button
3. Check correct code system (ICD-10 for diagnosis, OPCS-4 for procedures)
4. Consult coding manual if still unsure

### Report Shows Incorrect Data

**Problem**: Statistics don't match expectations

**Solutions**:
1. Check date range filter
2. Verify data entry is complete
3. Run data validation check
4. Refresh the report
5. Contact admin if problem persists

### NBOCA Validation Fails

**Problem**: Multiple validation errors

**Solutions**:
1. Review error messages carefully
2. Click episode ID to jump to record
3. Fix mandatory fields first
4. Check TNM staging format
5. Verify dates are in correct order (diagnosis → surgery → discharge)
6. Re-run validation after fixes

### Slow Performance

**Problem**: Pages load slowly

**Solutions**:
1. Check internet connection
2. Clear browser cache
3. Close unused tabs
4. Try different browser
5. Contact IT if problem persists

---

## Getting Help

### Documentation
- [README.md](README.md) - Quick start guide
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - API reference
- [DEPLOYMENT.md](DEPLOYMENT.md) - System administration

### Support Contacts
- **Technical Issues**: it-support@yourhospital.nhs.uk
- **Data Entry Questions**: audit-team@yourhospital.nhs.uk
- **NBOCA Submissions**: nboca.coordinator@yourhospital.nhs.uk

### Useful External Resources
- [NBOCA Homepage](https://www.nboca.org.uk/)
- [NHS Data Dictionary](https://www.datadictionary.nhs.uk/)
- [ICD-10 Browser](https://icd.who.int/browse10/2019/en)
- [OPCS-4 Classification](https://classbrowser.nhs.uk/)

---

**Version**: 1.0.0  
**Last Updated**: December 23, 2025  
**For**: Clinicians, Data Entry Staff, Audit Coordinators
