# Recent Changes Log

This file tracks significant changes made to the surg-db application. **Update this file at the end of each work session** to maintain continuity between AI chat sessions.

## Format
```
## YYYY-MM-DD - Brief Summary
**Changed by:** [User/AI Session]
**Issue:** What problem was being solved
**Changes:** What was modified
**Files affected:** List of files
**Testing:** How to verify it works
**Notes:** Any important context for future sessions
```

---

## 2025-12-25 - Complication Rate Fix & Investigation API Integration

### Complication Rate Correction (Re-applied)
**Issue:** High complication rate due to incorrect data import (readmissions counted as complications)

**Solution:** Re-ran `execution/fix_complications_from_csv.py`
- Uses CSV export to identify TRUE complications only:
  - MJ_Leak (Major anastomotic leak)
  - MI_Leak (Minor anastomotic leak)
  - Cardio (Cardiovascular complications)
  - MJ_Bleed (Major bleeding)
  - MI_Bleed (Minor bleeding)
- Readmissions are tracked separately, NOT counted as complications

**Result:** 
- Updated 976 treatments (set to FALSE)
- Final complication rate: 3.51% (206 out of 5,866 treatments)
- Correct rate confirmed in data quality API

**Files:**
- `execution/fix_complications_from_csv.py` (existing script, re-executed)
- CSV files: `surgeries_export_new.csv`, `patients_export_new.csv` (symlinked from `~/.tmp/`)

**Testing:** 
```bash
curl -s http://localhost:8000/api/reports/data-quality | python3 -m json.tool | grep -A 2 "complications"
# Should show ~3.5% with 206 complications
```

---

### Surgery Urgency Formatting
**Issue:** Urgency breakdown labels not capitalized (showing "elective" instead of "Elective")

**Changes:**
- Added `capitalize` CSS class to urgency labels in Surgery Urgency Breakdown section

**Files:**
- `frontend/src/pages/ReportsPage.tsx` (line ~508)

**Testing:** Reports page → Surgery Urgency Breakdown should show "Elective", "Emergency", "Urgent" (capitalized)

---

### Investigation Modal Fixes (Critical)
**Issue:** 
1. Duplicate "Investigations" tab in episode detail modal
2. Investigations not appearing in modal
3. "API integration pending" error when updating investigations
4. Investigation API routes not working (404 errors)
5. **422 Unprocessable Content errors when updating investigations**
6. **"Failed to update investigation: [object Object]" errors**

**Root Causes:**
1. Two identical Investigation tabs in navigation (lines 433-441 and 464-472)
2. Frontend not extracting `investigations` from API response
3. Investigation handlers had TODO placeholders instead of actual API calls
4. Backend investigations router missing `/api/investigations` prefix
5. Routes incorrectly using full paths like `/investigations/{id}` instead of `/{id}`
6. **CRITICAL: Backend using synchronous `get_database()` instead of async `get_investigations_collection()`**
7. Frontend error handling not displaying validation errors properly

**Changes:**

**Frontend (`frontend/src/components/CancerEpisodeDetailModal.tsx`):**
- Removed duplicate Investigation tab navigation button
- Updated `loadTreatments()` to extract `investigations` and `follow_ups` from API response
- Implemented proper `handleAddInvestigation()` with POST to `/api/investigations`
- Implemented proper `handleEditInvestigation()` with PUT to `/api/investigations/{id}`
- Both handlers now reload data and show proper error messages
- Improved error handling to display Pydantic validation errors (array of error objects)

**Backend (`backend/app/routes/investigations.py`):**
- **CRITICAL FIX:** Changed from `get_database()` to `get_investigations_collection()` for async operations
- Made all database operations properly async with `await`:
  - `await investigations_collection.find_one()`
  - `await investigations_collection.insert_one()`
  - `await investigations_collection.update_one()`
  - `await investigations_collection.delete_one()`
  - `await cursor.to_list(length=None)` for queries
- Added router prefix: `router = APIRouter(prefix="/api/investigations", tags=["investigations"])`
- Updated all route decorators:
  - `@router.get("/investigations")` → `@router.get("/")`
  - `@router.get("/investigations/{investigation_id}")` → `@router.get("/{investigation_id}")`
  - `@router.post("/investigations")` → `@router.post("/")`
  - `@router.put("/investigations/{investigation_id}")` → `@router.put("/{investigation_id}")`
  - `@router.delete("/investigations/{investigation_id}")` → `@router.delete("/{investigation_id}")`
- Added proper HTTP status codes (201 for creation, proper 404s with status enum)

**Testing:**
1. Open any episode detail modal → should see ONE "Investigations" tab
2. Investigations should load and display if present
3. Add investigation → should save without "API integration pending" error
4. **Edit investigation → should save without 422 errors**
5. Backend check: `curl -s http://localhost:8000/api/investigations` should return 200

**Backend restart required:** `systemctl restart surg-db-backend`

**IMPORTANT:** The async/await pattern is critical - DO NOT revert to synchronous database calls. All collection operations must use `await`.

---

### Medical Acronym Formatting
**Issue:** Investigation subtypes showing "Ct" and "Mri" instead of "CT" and "MRI"

**Changes:**
- Created new `formatInvestigationType()` function in `frontend/src/utils/formatters.ts`
- Handles medical acronyms: CT, MRI, PET, US, XR, MRCP, ERCP, EUS, OGD, CT-CAP
- Capitalizes regular words normally
- Imported and used in `CancerEpisodeDetailModal.tsx` for investigation subtype display

**Files:**
- `frontend/src/utils/formatters.ts` (added function at end)
- `frontend/src/components/CancerEpisodeDetailModal.tsx` (imported and used on line ~1167)

**Testing:** 
- Create investigation with subtype "ct_chest" → should display as "CT Chest"
- Create investigation with subtype "mri" → should display as "MRI"

---

## Important Notes for Future Sessions

### Investigation System
- **Backend router:** `/api/investigations` is fully implemented and working
- **Frontend integration:** Now properly integrated, no more TODO placeholders
- **DO NOT revert** the investigation API calls to placeholder code
- If seeing 404 errors, check that router has `prefix="/api/investigations"` and routes use relative paths

### Complication Rate
- **Script location:** `execution/fix_complications_from_csv.py`
- **CSV requirements:** Needs `surgeries_export_new.csv` and `patients_export_new.csv`
- **Symlinks:** Create symlinks to `~/.tmp/` CSV exports if files not in root
- **Expected result:** ~3.5% complication rate (206 cases)
- **When to re-run:** After any bulk outcome data imports that might corrupt complications field

### Services Management
- Backend: `systemctl restart surg-db-backend`
- Frontend: `systemctl restart surg-db-frontend`
- **Never use:** `pkill -f uvicorn` or direct terminal runs (services are systemd-managed)
- **Logs:** `~/.tmp/backend.log` and `~/.tmp/frontend.log`

### Formatting Functions
- Medical acronyms: Use `formatInvestigationType()` from `utils/formatters.ts`
- General capitalization: Use `capitalize()` for simple cases
- Check for existing formatters before creating new ones to avoid duplicates

---

## Template for Next Session

```markdown
## YYYY-MM-DD - [Brief Summary of Changes]

### [Feature/Fix Name]
**Issue:** [What problem was being solved]

**Changes:**
- [Bullet point list of what was modified]

**Files:**
- [List files modified]

**Testing:** 
[How to verify the changes work]

**Notes:** [Any important context]

---
```

## Quick Reference Commands

### Backend
```bash
# Restart backend
systemctl restart surg-db-backend

# Check status
systemctl status surg-db-backend --no-pager

# View logs
tail -50 ~/.tmp/backend.log

# Check API
curl -s http://localhost:8000/api/investigations
```

### Database
```bash
# MongoDB shell
mongosh -u admin -p admin123

# Switch to surgdb
use surgdb

# Count investigations
db.investigations.countDocuments()

# Check complication rate
db.treatments.countDocuments({complications: true})
```

### Frontend
```bash
# Restart frontend
systemctl restart surg-db-frontend

# Check logs
tail -50 ~/.tmp/frontend.log
```

### Migration Scripts
```bash
# Re-run complication fix
cd /root/surg-db
python3 execution/fix_complications_from_csv.py

# Check data quality
curl -s http://localhost:8000/api/reports/data-quality | python3 -m json.tool
```
