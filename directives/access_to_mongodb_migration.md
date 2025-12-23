# Access Database to MongoDB Migration Directive

## Purpose
Migrate historical surgical data from legacy Access database to the new MongoDB structure with proper schema mapping and data validation.

## Context
- **Source**: Microsoft Access database (.mdb or .accdb) with historical surgical records
- **Target**: MongoDB collections (episodes, patients, tumours, treatments)
- **Current Schema**: Episode-based structure supporting cancer, IBD, and benign conditions

## Data Flow

```
Access Database
    ↓
Export to intermediates (CSV/JSON)
    ↓
.tmp/ storage
    ↓
Python migration script
    ↓
MongoDB (episodes, patients, tumours, treatments collections)
```

## Prerequisites

### 1. Extract Data from Access - SELECTIVE EXPORT RECOMMENDED

**Best Practice**: Export ONLY the fields you need rather than entire tables. This makes migration cleaner and faster.

#### Required Fields by Collection

**For Patients Collection** - Export these fields to `patients.csv`:
- Patient identifier (ID, PatientID, etc.) - for linking records
- NHS Number
- Date of Birth
- Gender/Sex
- Ethnicity (if available)
- Postcode (if available)

**For Surgeries/Treatments** - Export these fields to `surgeries.csv`:
- Surgery/Treatment identifier
- Patient identifier (foreign key)
- Surgery Date
- Procedure name/description
- Surgeon name
- Approach (open/laparoscopic/robotic)
- ICD-10 diagnosis code (if available)
- OPCS-4 procedure code (if available)

**For Tumour/Pathology Data** - Export these fields to `tumours.csv`:
- Tumour identifier
- Surgery identifier (foreign key to link to treatment)
- Tumour site/location
- TNM staging (T stage, N stage, M stage)
- Overall stage (if available)
- Histology type
- Grade
- Diagnosis date

**Optional Fields** (if available):
- ASA grade
- Complications
- Length of stay
- Follow-up dates
- Outcomes

#### Export Methods

**Option A: Access Query Export (RECOMMENDED)**
1. Open Access database
2. Create Select Query for each table
3. Choose only the fields listed above
4. Export Query results to CSV (External Data > Export > Text File)

**Option B: Use mdbtools on Linux**
```bash
sudo apt-get install mdbtools
mdb-tables -1 database.mdb  # List tables
mdb-export database.mdb TableName > table.csv
# Then manually filter columns as needed
```

**Option C: Use pyodbc with custom SQL**
```python
import pyodbc
import pandas as pd

conn = pyodbc.connect(r'Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=path\to\database.mdb;')
# Select only needed fields
query = "SELECT PatientID, NHSNumber, DOB, Gender FROM Patients"
df = pd.read_sql(query, conn)
df.to_csv('patients.csv', index=False)
```

### 2. Understand Source Schema
Document Access tables and their relationships:
- Patient demographics table
- Surgery/procedure records
- Pathology data
- Follow-up records
- Surgeon/clinician data

### 3. Map Fields
Create mapping between Access fields and MongoDB schema:
- Patient fields → `patients` collection (Demographics, MedicalHistory)
- Surgery records → `treatments` collection (type=SURGERY)
- Tumour data → `tumours` collection (staging, sites, histology)
- Episode data → `episodes` collection (cancer episodes with references)

## Migration Script: `/root/execution/migrate_access_to_mongodb.py`

### Inputs
- Access database file path or exported CSV files in `.tmp/access_export/`
- MongoDB connection string (from environment)
- Mapping configuration

### Process
1. **Extract**: Read Access data (via mdbtools, pandas, or pyodbc)
2. **Transform**: 
   - Map old field names to new schema
   - Generate new IDs (patients: P-YYYYMMDD-XXXX, episodes: E-YYYYMMDD-XXXX)
   - Validate data types and required fields
   - Handle missing/null values
   - Create relationships (episode → patient, treatment → episode)
3. **Load**:
   - Insert patients first (to get ObjectIds)
   - Create tumours with references
   - Create treatments with references
   - Create episodes linking everything together
4. **Validate**: 
   - Check record counts
   - Verify relationships
   - Report any errors/warnings

### Outputs
- MongoDB collections populated with migrated data
- Migration log: `~/.tmp/migration_log_YYYYMMDD_HHMMSS.txt`
- Error report: `~/.tmp/migration_errors_YYYYMMDD_HHMMSS.csv`
- Summary statistics

## Schema Mapping Examples

### Patient Demographics
```
Access Field          → MongoDB Field
-------------------------------------
PatientID             → (generate P-YYYYMMDD-XXXX)
NHS_Number            → patient_id
DOB                   → demographics.date_of_birth
Gender                → demographics.gender
Postcode              → demographics.postcode
```

### Surgery Records
```
Access Field          → MongoDB Field
-------------------------------------
SurgeryID             → treatment_id (T-YYYYMMDD-XXXX)
SurgeryDate           → treatment_date
Procedure             → surgery.classification.primary_procedure
Approach              → surgery.classification.approach
Surgeon               → treating_clinician
```

### Tumour/Pathology
```
Access Field          → MongoDB Field (tumours collection)
-------------------------------------
TumourSite            → site
TNM_T                 → staging.t_stage
TNM_N                 → staging.n_stage
TNM_M                 → staging.m_stage
Histology             → histology_type
```

## Validation Rules

### Required Fields
- Patient: patient_id, demographics.date_of_birth, demographics.gender
- Episode: episode_id, patient_id, condition_type, episode_date
- Treatment: treatment_id, treatment_type, treatment_date
- Tumour: site, tumour_type

### Data Quality Checks
- Date formats: Convert to ISO 8601 (YYYY-MM-DD)
- ID uniqueness: Ensure no duplicate IDs
- References: Verify patient_id exists before creating episodes
- Enums: Map to allowed values (gender, tumour sites, TNM stages)

## Error Handling

### During Migration
- Log all errors with line numbers and reason
- Continue processing other records (don't fail entire migration)
- Create summary of skipped records

### Post-Migration
- Compare record counts (Access vs MongoDB)
- Identify missing relationships
- Flag incomplete records for manual review

## Testing Strategy

1. **Dry Run**: Test with sample data first (10-20 records)
2. **Validation**: Run schema validation on test data
3. **Full Migration**: Process all historical data
4. **Verification**: 
   - Query MongoDB to confirm data integrity
   - Spot-check random patients in web UI
   - Compare totals with Access database

## Rollback Plan

If migration fails or data issues found:
```bash
# Drop collections and restart
mongosh
use surgdb
db.episodes.deleteMany({})
db.patients.deleteMany({})
db.tumours.deleteMany({})
db.treatments.deleteMany({})
```

## Post-Migration Tasks

1. **Index Creation**: Run `execution/create_indexes.py`
2. **Data Validation**: Run quality checks
3. **Backup**: Create MongoDB backup
4. **Documentation**: Update counts and migration notes

## Edge Cases

- **Duplicate patients**: Match by NHS number, merge records
- **Missing dates**: Use admission date or estimate
- **Invalid enum values**: Map to closest match or flag for review
- **Incomplete surgeries**: Create partial records, flag in notes
- **Multiple tumours per episode**: Create separate tumour documents

## Success Criteria

- [x] All Access records accounted for (or documented if skipped)
- [x] No orphaned references (all foreign keys valid)
- [x] All required fields populated
- [x] Dates in correct format
- [x] IDs follow new format conventions
- [ ] Web UI can display migrated data correctly
- [x] No MongoDB validation errors

## Migration Execution Summary (Completed Dec 23, 2025)

**Migration Results:**
- ✅ **7,973 patients** migrated from tblPatient
- ✅ **6,096 episodes** created from tblSurgery (1,861 surgeries had missing dates)
- ✅ **6,096 treatments** (surgery records) migrated
- ✅ **8,088 tumours** migrated from tblTumour
- ✅ **7,614 pathology** records linked from tblPathology

**Migration Steps Executed:**
1. Exported Access database using selective field extraction
2. Ran dry-run to validate data mapping
3. Executed live migration with MongoDB authentication
4. Verified data integrity in MongoDB

**Tools Used:**
- `execution/export_access_selective.py` - Export specific fields from Access
- `execution/migrate_acpdb_to_mongodb.py` - Main migration script
- MongoDB URI: `mongodb://admin:admin123@localhost:27017/?authSource=admin`

**Warnings:** 1,861 surgery records missing surgery dates were skipped but patients still migrated

**Next Steps:**
- Test web UI with migrated data
- Create indexes for performance
- Backup MongoDB database
