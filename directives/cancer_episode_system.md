# Cancer Episode Management Directive

## Overview
This directive covers the new episode-based system for cancer care management. The system supports different condition types (cancer, IBD, benign) with cancer as the first full implementation.

## Architecture

### 3-Layer Structure
1. **Frontend** - React/TypeScript forms with condition-specific fields
2. **Backend** - FastAPI with Pydantic models for validation
3. **Database** - MongoDB with flexible schema for different cancer types

### Episode Structure
An episode represents a patient's contact with the hospital for a specific condition. Each episode contains:
- Base information (patient, dates, clinician, status)
- Condition-specific data (e.g., cancer type and clinical details)
- Treatments array (surgery, chemo, radio, etc.)

## Supported Cancer Types

1. **Bowel (Colorectal)**
   - Site location, presentation type
   - Histology, staging (TNM)
   - Molecular markers (MMR, KRAS, NRAS, BRAF)
   - Lymph node status

2. **Kidney (Renal)**
   - Histological subtypes
   - Fuhrman grade
   - IMDC risk stratification

3. **Breast (Primary & Metastatic)**
   - Receptor status (ER, PR, HER2, Ki67)
   - Genetic testing (BRCA1/2)
   - Metastatic sites if applicable

4. **Oesophageal**
   - Location (upper/middle/lower/GOJ)
   - Histology (adenocarcinoma/squamous)
   - Dysphagia scoring

5. **Ovarian**
   - FIGO staging
   - CA-125 levels
   - Genetic testing (BRCA, HRD)
   - Resectability assessment

6. **Prostate**
   - PSA tracking
   - Gleason score / ISUP grade group
   - PI-RADS scoring
   - Risk stratification

## API Endpoints

### New V2 Endpoints (Episode-based)
- `POST /api/v2/episodes` - Create new episode
- `GET /api/v2/episodes` - List episodes with filters
- `GET /api/v2/episodes/{id}` - Get specific episode
- `PUT /api/v2/episodes/{id}` - Update episode
- `DELETE /api/v2/episodes/{id}` - Delete episode
- `POST /api/v2/episodes/{id}/treatments` - Add treatment to episode
- `GET /api/v2/episodes/stats/overview` - Statistics
- `GET /api/v2/episodes/patient/{id}/timeline` - Patient timeline

### Legacy Endpoints
Previously there were legacy surgery-based endpoints. These have been fully migrated to the episode-based system.
All functionality is now handled through the v2 episode endpoints above.

## Database Schema

### Collections

#### episodes
- `episode_id` (string, unique): Episode identifier
- `patient_id` (string): Patient MRN
- `condition_type` (enum): cancer|ibd|benign
- `cancer_type` (enum): bowel|kidney|breast_primary|breast_metastatic|oesophageal|ovarian|prostate
- `cancer_data` (object): Cancer-specific clinical data
- `referral_date`, `first_seen_date`, `mdt_discussion_date`
- `lead_clinician`, `mdt_team`
- `episode_status`: active|completed|cancelled
- Audit fields: created_at, created_by, last_modified_at, last_modified_by

**Note**: As of 2024-12-23, treatments and tumours are stored in **separate collections** with `episode_id` references (see below).

#### treatments
- `treatment_id` (string, unique): Treatment identifier
- `episode_id` (string): Reference to parent episode (as string of ObjectId)
- `patient_id` (string): Patient MRN (denormalized for query performance)
- `treatment_type` (enum): surgery|chemotherapy|radiotherapy|immunotherapy|targeted_therapy
- `treatment_date` (datetime): When treatment occurred
- `treatment_intent` (string): curative|palliative|neo-adjuvant|adjuvant
- `provider_organisation` (string): Organization code
- Treatment-specific fields (varies by type)
- Audit fields: created_at, last_modified_at

**Benefits of separate collection:**
- Independent querying of treatments across episodes
- Better performance for treatment-level analytics
- Audit trails per treatment
- No document size limits from embedded arrays
- Aligns with NBOCA submission structure

#### tumours
- `tumour_id` (string, unique): Tumour identifier
- `episode_id` (string): Reference to parent episode (as string of ObjectId)
- `patient_id` (string): Patient MRN (denormalized)
- `tumour_type` (enum): primary|metastasis|recurrence
- `site` (string): Anatomical location
- `icd10_code` (string): ICD-10 diagnosis code
- `snomed_morphology_code` (string): SNOMED CT morphology
- `tnm_staging` (object): TNM classification
- `pathology` (object): Pathological findings
- `diagnosis_date` (datetime): Date of diagnosis
- Audit fields: created_at, last_modified_at

**Benefits of separate collection:**
- Supports multiple primaries per episode
- Track metastatic sites independently
- Longitudinal tumour tracking
- Better COSD data export alignment

### Database Indexes

**episodes collection:**
- episode_id (unique)
- patient_id
- condition_type
- cancer_type
- referral_date

**treatments collection:**
- episode_id (for joins)
- patient_id (for patient-level queries)
- treatment_type
- treatment_date
- compound index: (episode_id, treatment_date)

**tumours collection:**
- episode_id (for joins)
- patient_id
- tumour_type
- diagnosis_date
- compound index: (episode_id, tumour_id)

## Scripts

### Execution Scripts

1. **init_episodes_collection.py**
   - Purpose: Initialize episodes collection with indexes
   - When to use: First-time setup or after database reset
   - Command: `python execution/init_episodes_collection.py`

2. **migrate_to_separate_collections.py**
   - Purpose: Move treatments and tumours from embedded arrays to separate collections
   - When to use: Database restructuring (completed 2024-12-23)
   - Command: `python execution/migrate_to_separate_collections.py`
   - Features:
     * Before/after validation with comprehensive statistics
     * User confirmation required before migration
     * Generates detailed JSON report in `~/.tmp/migration_report_*.json`
     * Creates indexes for optimal query performance
     * Idempotent - safe to rerun
   - Status: **COMPLETED** - All episodes migrated to separate collections structure

3. **create_sample_data.py**
   - Purpose: Generate realistic test data for development
   - Creates: Patients, episodes, treatments, tumours with proper relationships
   - Command: `python execution/create_sample_data.py`

### Startup Scripts
- `start_backend.sh` - Start FastAPI backend
- `start_frontend.sh` - Start React frontend

## Frontend Components

### CancerEpisodeForm.tsx
Multi-step form for creating/editing cancer episodes:
- **Step 1**: Patient selection, cancer type, dates, clinician
- **Step 2**: Cancer-specific clinical data
- **Step 3**: Review and submit

Implements dynamic field rendering based on cancer type.

### Future Components Needed
- TreatmentForm.tsx - Add treatments to episodes
- EpisodeTimeline.tsx - Visual timeline of patient journey
- CancerDashboard.tsx - Analytics and reporting

## Data Collection Standards

Cancer data fields based on:
- NATCAN (National Cancer Audit) standards
- NHS England cancer data collection
- COSD (Cancer Outcomes and Services Dataset)
- UICC TNM staging classification

## Workflows

### Creating a Cancer Episode
1. User selects "New Cancer Episode"
2. Searches for patient by MRN or name
3. Selects cancer type
4. Enters referral date and assigns lead clinician
5. Completes cancer-specific clinical data
6. Reviews and submits
7. System generates unique episode ID (EPI-xxxxx)

### Adding a Treatment
1. Open existing episode
2. Click "Add Treatment"
3. Select treatment type (surgery/chemo/radio/etc)
4. Enter treatment-specific data
5. Treatment is appended to episode's treatments array

### Migrating Legacy Data
1. Run `init_episodes_collection.py` to set up collection
2. Run `migrate_surgeries_to_episodes.py` to convert surgeries
3. Verify migration success
4. Update frontend to use V2 API endpoints
5. Keep legacy endpoints active during transition

## Testing Checklist

### Backend
- [ ] Create episode for each cancer type
- [ ] Validate required fields are enforced
- [ ] Filter episodes by condition_type, cancer_type
- [ ] Add treatments to episode
- [ ] Get patient timeline
- [ ] Migration script preserves all data

### Frontend
- [ ] Patient search works
- [ ] Dynamic fields show based on cancer type
- [ ] Form validation prevents submission with missing required fields
- [ ] Multi-step navigation works
- [ ] Episode displays correctly after creation

## Future Enhancements

### Short-term
1. Complete all cancer type forms (kidney, oesophageal, ovarian)
2. Build treatment forms for chemo/radio/immunotherapy
3. Add TNM staging component (reusable across cancers)
4. Episode timeline visualization

### Medium-term
1. IBD-specific episode types
2. Benign condition episodes
3. Bulk data import from existing systems
4. Automated MDT documentation templates

### Long-term
1. Integration with pathology systems
2. RECIST imaging response tracking
3. Survivorship pathway tracking
4. Research data export capabilities

## Common Issues & Solutions

### Issue: Migration script fails midway
**Solution**: Script is idempotent - safe to rerun. Skips already-migrated episodes.

### Issue: Episode ID conflicts
**Solution**: Episode IDs are timestamp + random string. Conflicts are extremely rare but checked on creation.

### Issue: Cancer data validation errors
**Solution**: Check that required fields for specific cancer type are provided. See models in `backend/app/models/episode.py`.

### Issue: Frontend shows old surgery form
**Solution**: Update Episodes page to use CancerEpisodeForm component and V2 API endpoints.

## Maintenance

### Adding a New Cancer Type
1. Add enum value to `CancerType` in `episode.py`
2. Create new Pydantic model (e.g., `LungCancerData`)
3. Add to `CancerSpecificData` union type
4. Create frontend form fields in `CancerEpisodeForm.tsx`
5. Update this directive

### Modifying Existing Cancer Type Fields
1. Update Pydantic model in `episode.py`
2. Update frontend form component
3. Consider migration script if changing required fields
4. Test thoroughly with existing data

## References

- Models: `backend/app/models/episode.py`, `treatment.py`
- Routes: `backend/app/routes/episodes_v2.py`
- Frontend: `frontend/src/components/CancerEpisodeForm.tsx`
- Migration: `execution/migrate_surgeries_to_episodes.py`
- Database setup: `execution/init_episodes_collection.py`

## Contact & Support

For questions about cancer data collection standards:
- Refer to NATCAN website: https://www.natcan.org.uk
- NHS England COSD documentation
- Local MDT coordinators

For technical issues:
- Check application logs: `~/.tmp/backend.log`, `~/.tmp/frontend.log`
- Review error messages in browser console
- Verify database connection and collection indexes

## Self-Annealing Notes

### 2024-12-23: Database Restructuring - Separate Collections
**Problem**: Treatments and tumours were stored as embedded arrays in episode documents. This limited:
- Independent querying of treatments across episodes
- Treatment-level analytics and reporting
- Audit trails per treatment
- NBOCA export flexibility

**Solution**: Migrated to separate collections architecture:
1. Created `treatments` and `tumours` collections with `episode_id` foreign key references
2. Built comprehensive migration script (`migrate_to_separate_collections.py`) with before/after validation
3. Updated all API endpoints in `routes/episodes_v2.py` to use separate collections:
   - POST/PUT/DELETE treatment endpoints now insert/update/delete in treatments collection
   - GET patient timeline now fetches treatments via episode_id lookup
   - Similar updates for tumour endpoints
4. Updated NBOCA XML export (`routes/exports.py`) to fetch treatments/tumours from separate collections
5. Added helper functions in `database.py`: `get_treatments_collection()`, `get_tumours_collection()`
6. Created indexes on episode_id, patient_id, treatment_type, treatment_date for optimal performance

**Migration Results** (from `/root/.tmp/migration_report_20251223_013813.json`):
- Episodes: 6 documents
- Treatments: 0 → 2 documents (migrated from embedded arrays)
- Tumours: 0 → 2 documents (migrated from embedded arrays)
- Embedded arrays: All cleared from episode documents
- Duration: 12.92 seconds
- Status: ✅ COMPLETED SUCCESSFULLY

**Validation**:
- Tested NBOCA XML export - generates correct COSD v9/v10 XML with treatments from separate collection
- All episode CRUD operations working
- Treatment and tumour add/update/delete endpoints functional
- Patient timeline correctly aggregates data from separate collections

**Benefits Realized**:
- Improved query performance (can query treatments without loading entire episode)
- Better alignment with NBOCA submission format (treatments as independent records)
- Scalability (no document size limits from embedded arrays)
- Foundation for treatment-level audit trails and versioning
- Enables future analytics dashboards querying treatments directly

**Files Modified**:
- `/root/backend/app/database.py` - Added collection helpers
- `/root/backend/app/routes/episodes_v2.py` - Updated all treatment/tumour endpoints
- `/root/backend/app/routes/exports.py` - Updated NBOCA export to fetch from separate collections
- `/root/directives/cancer_episode_system.md` - Documented new architecture

**Known Limitations**:
- Episode model still includes empty `treatments` and `tumours` arrays in schema (legacy fields, can be removed in future cleanup)
- Frontend may need updates if it expects treatments embedded in episode GET response (should fetch separately via new endpoints)

**Next Steps**:
- Monitor query performance with real data
- Consider adding treatment-level audit logging
- Build treatment analytics dashboard
- Update frontend to optimize fetching patterns (avoid N+1 queries)
