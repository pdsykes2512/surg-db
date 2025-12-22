# Quick Start: Cancer Episode System

## Step-by-Step Setup

### 1. Initialize Database (2 minutes)

```bash
cd /root

# Initialize the new episodes collection with indexes
python3 execution/init_episodes_collection.py
```

Expected output:
```
Initializing episodes collection...
✓ Created collection 'episodes'
✓ Created index: episode_id_unique
✓ Created index: patient_id_index
... (more indexes)
✓ Episodes collection initialized successfully!
```

### 2. (Optional) Migrate Existing Data

If you have existing surgery records:

```bash
# Migrate surgeries to episode format
python3 execution/migrate_surgeries_to_episodes.py
```

This will:
- Convert each surgery into an episode
- Preserve all original data
- Surgery becomes a treatment within the episode
- Original surgeries collection remains unchanged

### 3. Start the Backend

```bash
cd /root
bash execution/start_backend.sh
```

Backend will be available at: http://localhost:8000

### 4. Verify API

Visit http://localhost:8000/docs to see the interactive API documentation.

You should see new endpoints under **episodes-v2** tag:
- POST /api/v2/episodes
- GET /api/v2/episodes
- GET /api/v2/episodes/{episode_id}
- PUT /api/v2/episodes/{episode_id}
- DELETE /api/v2/episodes/{episode_id}
- POST /api/v2/episodes/{episode_id}/treatments
- GET /api/v2/episodes/stats/overview
- GET /api/v2/episodes/patient/{patient_id}/timeline

### 5. Create Your First Cancer Episode

Using the API directly (replace YOUR_TOKEN with actual token):

```bash
curl -X POST http://localhost:8000/api/v2/episodes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "episode_id": "EPI-2025-BOWEL-001",
    "patient_id": "MRN00001",
    "condition_type": "cancer",
    "cancer_type": "bowel",
    "referral_date": "2025-12-20",
    "first_seen_date": "2025-12-22",
    "lead_clinician": "Dr. Smith",
    "created_by": "admin",
    "last_modified_by": "admin",
    "cancer_data": {
      "cancer_site": "colon",
      "presentation_type": "symptomatic",
      "histological_type": "adenocarcinoma",
      "tumor_size_mm": 35,
      "lymph_nodes_examined": 15,
      "lymph_nodes_positive": 2,
      "mdt_treatment_plan": "Right hemicolectomy planned. Adjuvant chemotherapy to be considered based on final pathology."
    }
  }'
```

### 6. List Episodes

```bash
# All episodes
curl http://localhost:8000/api/v2/episodes \
  -H "Authorization: Bearer YOUR_TOKEN"

# Filter by cancer type
curl "http://localhost:8000/api/v2/episodes?condition_type=cancer&cancer_type=bowel" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get statistics
curl http://localhost:8000/api/v2/episodes/stats/overview \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Frontend Integration

### Update Episodes Page

1. Import the new component:

```typescript
import { CancerEpisodeForm } from '../components/CancerEpisodeForm'
```

2. Add a button to create cancer episodes:

```typescript
<Button onClick={() => setShowCancerForm(true)}>
  New Cancer Episode
</Button>

{showCancerForm && (
  <CancerEpisodeForm
    onSubmit={async (data) => {
      const response = await fetch('http://localhost:8000/api/v2/episodes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(data)
      })
      if (response.ok) {
        // Success!
        setShowCancerForm(false)
        refreshEpisodes()
      }
    }}
    onCancel={() => setShowCancerForm(false)}
  />
)}
```

## Example: Complete Patient Journey

### 1. Create Bowel Cancer Episode

```json
{
  "episode_id": "EPI-001",
  "patient_id": "MRN12345",
  "condition_type": "cancer",
  "cancer_type": "bowel",
  "referral_date": "2025-11-01",
  "first_seen_date": "2025-11-05",
  "mdt_discussion_date": "2025-11-10",
  "lead_clinician": "Dr. Sarah Johnson",
  "cancer_data": {
    "cancer_site": "rectum",
    "presentation_type": "symptomatic",
    "symptoms": ["bleeding", "change_in_bowel_habit"],
    "histological_type": "adenocarcinoma",
    "differentiation": "moderate",
    "tnm_staging": {
      "clinical_t": "T3",
      "clinical_n": "N1",
      "clinical_m": "M0",
      "stage_group": "III"
    }
  }
}
```

### 2. Add Surgery Treatment

```json
POST /api/v2/episodes/EPI-001/treatments
{
  "treatment_id": "TRT-001",
  "treatment_type": "surgery",
  "treatment_date": "2025-12-01",
  "treating_clinician": "Dr. Sarah Johnson",
  "treatment_intent": "curative",
  "classification": {
    "urgency": "elective",
    "complexity": "complex",
    "primary_diagnosis": "Rectal cancer",
    "indication": "cancer"
  },
  "procedure": {
    "primary_procedure": "Anterior resection of rectum",
    "approach": "laparoscopic",
    "description": "Laparoscopic anterior resection with total mesorectal excision"
  },
  "perioperative_timeline": {
    "admission_date": "2025-11-30",
    "surgery_date": "2025-12-01",
    "discharge_date": "2025-12-07",
    "operation_duration_minutes": 240
  },
  "team": {
    "primary_surgeon": "Dr. Sarah Johnson",
    "assistant_surgeons": ["Dr. Michael Chen"]
  }
}
```

### 3. Add Chemotherapy Treatment (Future)

```json
POST /api/v2/episodes/EPI-001/treatments
{
  "treatment_id": "TRT-002",
  "treatment_type": "chemotherapy",
  "treatment_date": "2026-01-15",
  "treating_clinician": "Dr. Emily Roberts",
  "treatment_intent": "adjuvant",
  "regimen": {
    "regimen_name": "FOLFOX",
    "drugs": ["Oxaliplatin", "5-FU", "Leucovorin"]
  },
  "planned_cycles": 12
}
```

## Cancer Type Examples

### Breast Cancer (Primary)

```json
{
  "cancer_type": "breast_primary",
  "cancer_data": {
    "laterality": "left",
    "quadrant": "upper_outer",
    "detection_method": "screening",
    "histological_type": "ductal",
    "histological_grade": 2,
    "er_status": "positive",
    "er_percentage": 95,
    "pr_status": "positive",
    "pr_percentage": 80,
    "her2_status": "negative",
    "ki67_percentage": 20,
    "tumor_size_mm": 18,
    "surgery_plan": "lumpectomy"
  }
}
```

### Prostate Cancer

```json
{
  "cancer_type": "prostate",
  "cancer_data": {
    "detection_method": "psa_screening",
    "psa_at_diagnosis": 8.5,
    "gleason_primary": 3,
    "gleason_secondary": 4,
    "gleason_score": 7,
    "isup_grade_group": 2,
    "pirads_score": 4,
    "risk_group": "intermediate",
    "mdt_treatment_plan": "Radical prostatectomy recommended"
  }
}
```

## Troubleshooting

### Issue: ModuleNotFoundError

```bash
# Make sure you're in the backend directory and using the right Python
cd /root/backend
python3 -c "import app.models.episode"
```

### Issue: Database Connection Error

Check MongoDB is running and connection string is correct in `backend/app/config.py`.

### Issue: Import Error in Frontend

Make sure you've created the `CancerEpisodeForm.tsx` file in:
```
/root/frontend/src/components/CancerEpisodeForm.tsx
```

### Issue: API Returns 422 Validation Error

Check that all required fields are provided for the specific cancer type.
See `/root/backend/app/models/episode.py` for field definitions.

## What's Next?

1. ✅ Database initialized
2. ✅ API endpoints ready
3. ⏳ Integrate frontend form
4. ⏳ Create first cancer episode
5. ⏳ Add treatments to episode
6. ⏳ Build reporting dashboard

## Resources

- **Full Documentation**: `/root/directives/cancer_episode_system.md`
- **Implementation Summary**: `/root/CANCER_EPISODE_IMPLEMENTATION.md`
- **API Docs**: http://localhost:8000/docs (when running)
- **Models Reference**: `/root/backend/app/models/episode.py`

---

**Ready to go!** 🚀 Start with step 1 and work your way through. Each step takes just a few minutes.
