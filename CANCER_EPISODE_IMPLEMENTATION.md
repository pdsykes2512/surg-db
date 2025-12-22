# Cancer Episode System - Implementation Summary

## What's Been Built

I've successfully redesigned your episodes system from a surgery-focused approach to a flexible, condition-based system that supports cancer, IBD, and benign conditions. The cancer module is fully implemented with detailed data collection for 7 cancer types.

## Key Changes

### 1. **Architectural Redesign**
- **Before**: Each episode = one surgery
- **After**: Each episode = hospital contact for a condition, containing multiple treatments

### 2. **New Data Models**

#### Episode Model (`backend/app/models/episode.py`)
- Base episode structure for all conditions
- Cancer-specific models for:
  - **Bowel (Colorectal)**: Site, presentation, histology, molecular markers (MMR, KRAS, BRAF), lymph node status
  - **Kidney**: Histology subtypes, Fuhrman grade, IMDC risk score
  - **Breast** (Primary & Metastatic): Receptor status (ER/PR/HER2/Ki67), BRCA testing, metastatic sites
  - **Oesophageal**: Location (GOJ types), histology, dysphagia scoring
  - **Ovarian**: FIGO staging, CA-125 levels, BRCA/HRD testing, resectability
  - **Prostate**: PSA tracking, Gleason/ISUP grading, PI-RADS, risk stratification

#### Treatment Model (`backend/app/models/treatment.py`)
- Surgery (preserves all original surgery data)
- Chemotherapy (regimens, cycles, toxicity tracking)
- Radiotherapy (dose, fractions, technique)
- Immunotherapy (irAEs, response assessment)
- Hormone therapy
- Targeted therapy (biomarker-driven)
- Palliative care
- Surveillance protocols

### 3. **API Endpoints**

New V2 API (`/api/v2/episodes`):
```
POST   /api/v2/episodes                      - Create episode
GET    /api/v2/episodes                      - List with filters
GET    /api/v2/episodes/{id}                 - Get specific episode
PUT    /api/v2/episodes/{id}                 - Update episode
DELETE /api/v2/episodes/{id}                 - Delete episode
POST   /api/v2/episodes/{id}/treatments      - Add treatment
GET    /api/v2/episodes/stats/overview       - Statistics
GET    /api/v2/episodes/patient/{id}/timeline - Patient journey
```

Legacy API (`/api/episodes`) preserved for backward compatibility.

### 4. **Database Tools**

#### `execution/init_episodes_collection.py`
- Creates episodes collection with optimized indexes
- Indexes on: episode_id, patient_id, condition_type, cancer_type, dates, clinician, status
- Text search indexes for MDT plans and notes

#### `execution/migrate_surgeries_to_episodes.py`
- Migrates existing surgery records to episode format
- Preserves all original data
- Intelligent mapping of surgery indications to condition types
- Converts surgeries to treatments within episodes
- Safe to rerun (idempotent)

### 5. **Frontend Component**

#### `CancerEpisodeForm.tsx`
3-step wizard for cancer episode creation:

**Step 1: Patient & Episode Info**
- Patient search and selection
- Cancer type selection (dropdown with 7 types)
- Dates: referral, first seen, MDT discussion
- Lead clinician assignment

**Step 2: Cancer-Specific Clinical Data**
Dynamic fields based on cancer type:
- Bowel: Site location, presentation, histology, molecular markers
- Breast: Laterality, receptor status (ER/PR/HER2), genetic testing
- Prostate: PSA, Gleason scoring, PI-RADS, risk group
- Generic forms for kidney, oesophageal, ovarian (extensible)

**Step 3: Review & Submit**
- Summary of all entered data
- Validation before submission

## File Structure

```
backend/app/
├── models/
│   ├── episode.py          # NEW: Episode and cancer-specific models
│   ├── treatment.py        # NEW: Treatment types including surgery
│   └── surgery.py          # KEPT: Original surgery components reused
├── routes/
│   ├── episodes_v2.py      # NEW: V2 API for episode-based system
│   └── episodes.py         # KEPT: Legacy surgery-based API
├── database.py             # UPDATED: Added get_episodes_collection()
└── main.py                 # UPDATED: Added episodes_v2 router

frontend/src/components/
└── CancerEpisodeForm.tsx   # NEW: Multi-step cancer episode form

execution/
├── init_episodes_collection.py      # NEW: Database setup
└── migrate_surgeries_to_episodes.py # NEW: Data migration

directives/
└── cancer_episode_system.md         # NEW: Comprehensive guide
```

## Getting Started

### 1. Initialize the Database

```bash
# Set up episodes collection with indexes
python execution/init_episodes_collection.py

# Optional: Migrate existing surgery data
python execution/migrate_surgeries_to_episodes.py
```

### 2. Start the Application

```bash
# Backend
cd backend
source venv/bin/activate  # or your virtual environment
uvicorn app.main:app --reload

# Frontend
cd frontend
npm run dev
```

### 3. Test the API

```bash
# Create a bowel cancer episode
curl -X POST http://localhost:8000/api/v2/episodes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "episode_id": "EPI-TEST-001",
    "patient_id": "MRN12345",
    "condition_type": "cancer",
    "cancer_type": "bowel",
    "referral_date": "2025-12-20",
    "lead_clinician": "Dr. Smith",
    "created_by": "admin",
    "last_modified_by": "admin",
    "cancer_data": {
      "cancer_site": "colon",
      "presentation_type": "symptomatic",
      "mdt_treatment_plan": "Surgical resection planned"
    }
  }'

# List cancer episodes
curl http://localhost:8000/api/v2/episodes?condition_type=cancer \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get statistics
curl http://localhost:8000/api/v2/episodes/stats/overview \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Data Fields by Cancer Type

### Bowel (Colorectal)
✅ **Required**: cancer_site, presentation_type  
📊 **Clinical**: histology, differentiation, tumor_size_mm, lymph nodes  
🧬 **Molecular**: MMR status, KRAS, NRAS, BRAF  
🎯 **Staging**: TNM (clinical and pathological)

### Breast
✅ **Required**: laterality, detection_method, histological_type  
🔬 **Receptors**: ER/PR/HER2 status with percentages, Ki67  
🧬 **Genetic**: BRCA1/2 testing  
📍 **Metastatic**: Sites, line of therapy (for metastatic type)

### Prostate
✅ **Required**: detection_method  
📈 **PSA**: Level at diagnosis, velocity tracking  
📊 **Grading**: Gleason (primary/secondary), ISUP grade group  
🎯 **Imaging**: PI-RADS score, MRI staging  
⚠️ **Risk**: Stratification (low/intermediate/high/very high)

### Kidney
✅ **Required**: cancer_site, histological_type  
📊 **Grading**: Fuhrman grade (1-4)  
🎯 **Risk**: IMDC score (favorable/intermediate/poor)

### Oesophageal
✅ **Required**: cancer_site, histological_type  
📍 **Location**: Distance from incisors, GOJ classification  
📊 **Symptoms**: Dysphagia score (0-4), weight loss

### Ovarian
✅ **Required**: cancer_site, histological_type  
🎯 **Staging**: FIGO stage (detailed substaging)  
🔬 **Markers**: CA-125 levels  
🧬 **Genetic**: BRCA1/2, HRD status

## Migration Path

### Phase 1: Parallel Running (Current)
- Both old (`/api/episodes`) and new (`/api/v2/episodes`) APIs active
- Legacy data remains in surgeries collection
- New data goes to episodes collection

### Phase 2: Frontend Migration
- Update Episodes page to use CancerEpisodeForm
- Switch API calls to V2 endpoints
- Add treatment forms for surgery/chemo/radio

### Phase 3: Complete Transition
- Migrate all historical surgery data
- Deprecate V1 endpoints
- Archive surgeries collection

## Next Steps

### Immediate
1. **Test the backend**: Run `init_episodes_collection.py`
2. **Integrate frontend**: Import CancerEpisodeForm in Episodes page
3. **Create first cancer episode**: Use the new form to test end-to-end

### Short-term
1. **Complete cancer forms**: Build out kidney, oesophageal, ovarian fields
2. **Treatment forms**: Build TreatmentForm component for adding treatments
3. **TNM staging component**: Reusable across multiple cancers
4. **Episode detail view**: Display episode with timeline of treatments

### Medium-term
1. **IBD episodes**: Implement IBD-specific data collection
2. **Benign episodes**: Add benign condition support
3. **Reporting**: Build cancer-specific outcome reports
4. **Analytics dashboard**: Visualize cancer care metrics

## Benefits of New System

1. **Flexibility**: Easily add new condition types without restructuring
2. **Comprehensive**: Captures full patient journey, not just surgery
3. **Standards-aligned**: Based on NATCAN and NHS cancer data collection
4. **Future-proof**: Treatment model supports adding oncological therapies
5. **Research-ready**: Structured data enables audit and research
6. **Backward compatible**: Legacy system continues to function

## Support

- **Documentation**: See `/root/directives/cancer_episode_system.md`
- **API Docs**: http://localhost:8000/docs (when backend is running)
- **Models**: Review `/root/backend/app/models/episode.py` for field definitions
- **Examples**: Check migration script for data structure examples

## Questions?

Common scenarios:

**Q: Can I still create surgery-only episodes?**  
A: Yes! Use the new system and add surgery as a treatment. Or continue using legacy API during transition.

**Q: What happens to my existing surgery data?**  
A: It's completely preserved. Migration script converts it to episode format without data loss.

**Q: How do I add chemotherapy to an episode?**  
A: Use `POST /api/v2/episodes/{id}/treatments` with treatment_type="chemotherapy" and appropriate data.

**Q: Can I customize cancer fields for my hospital?**  
A: Absolutely! Modify the Pydantic models in `episode.py` and update the frontend form.

---

**System is ready to use!** Start by initializing the database and creating your first cancer episode. 🚀
