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

## 2025-12-27 - Fix Episode Modal Not Displaying Investigations, Tumours, and Treatments

**Changed by:** AI Session  
**Issue:** The cancer episode details modal showed empty tabs for investigations, tumours, and treatments despite data existing in the database. API calls were failing silently with 404 errors because the wrong URL path was being constructed.

**Root Cause:** The December 27 API URL fix was **incorrect**. The logic was:
```typescript
// WRONG: This produces the wrong URL!
const API_URL = import.meta.env.VITE_API_URL === '/api' ? '' : (...)
// Result: `${API_URL}/episodes/${id}` becomes `/episodes/${id}` instead of `/api/episodes/${id}`
```

When `VITE_API_URL=/api`, setting `API_URL` to empty string `''` caused URLs like `/episodes/E-123` instead of `/api/episodes/E-123`. The Vite proxy expects `/api/*` paths, not bare `/episodes/*` paths.

**Correct Solution:**
```typescript
// CORRECT: Always use /api as the base path
const API_URL = import.meta.env.VITE_API_URL || '/api'
// Result: `${API_URL}/episodes/${id}` becomes `/api/episodes/${id}` ✓
```

**Changes:**
1. Fixed all 10 instances of `API_URL` construction in `CancerEpisodeDetailModal.tsx`
2. Changed from `=== '/api' ? '' :` pattern to simple `|| '/api'` pattern
3. Added debug console.log statements to `loadTreatments()` function for troubleshooting
4. Verified backend API endpoint `/api/episodes/{episode_id}` returns correct data with treatments/tumours/investigations arrays

**Files affected:**
- `frontend/src/components/modals/CancerEpisodeDetailModal.tsx` (10 API_URL fixes)
- `frontend/src/pages/HomePage.tsx` (1 fix)
- `frontend/src/pages/ReportsPage.tsx` (1 fix for /reports endpoint)
- `frontend/src/pages/EpisodesPage.tsx` (2 fixes)
- `frontend/src/components/search/NHSProviderSelect.tsx` (2 fixes)
- `frontend/src/components/modals/TumourModal.tsx` (1 fix)
- `frontend/src/components/modals/AddTreatmentModal.tsx` (1 fix)
- **NOT CHANGED** (already correct): `AdminPage.tsx`, `SurgeonSearch.tsx`, `AuthContext.tsx`, `ReportsPage.tsx` (API_BASE for downloads)

**Testing:**
1. Open any cancer episode details modal
2. Switch to Tumours tab - should show tumour data
3. Switch to Treatments tab - should show treatment data
4. Switch to Investigations tab - should show investigation data
5. Check browser console for successful API calls: "Loading episode data from: /api/episodes/E-..."

**Notes:**
- This reveals that the previous "fix" for API URL construction was fundamentally flawed
- ALL other files that were "fixed" on Dec 27 may have the same bug and should be reviewed
- The correct pattern is: `const API_URL = import.meta.env.VITE_API_URL || '/api'`
- Never use empty string for API_URL when VITE_API_URL is '/api'
- The Vite proxy configuration (in vite.config.ts) expects `/api/*` paths

---

## 2025-12-27 - Fix Patients with Future Birth Dates Causing Pagination Errors

**Changed by:** AI Session  
**Issue:** Pages 7 and 8 of the patient list showed "Failed to load patient" errors. Backend logs showed Pydantic validation errors: `demographics.age: Input should be greater than or equal to 0 [input_value=-25]`. Investigation revealed 404 patients had future dates of birth (2026-2074) resulting in negative ages.

**Root Cause:** The data import script's 2-digit year parser had an edge case where years like "44" were interpreted as "2044" instead of "1944". The `parse_dob()` function checked `if dt.year > 2050` but years between 2026-2050 slipped through, along with datetime formatting issues during storage.

**Changes:**
1. Created `/root/surg-db/execution/fix_future_dobs.py` - Script to find and fix all patients with negative ages
2. Fixed 404 patients by subtracting 100 years from their DOB (e.g., 2044 → 1944, 2050 → 1950)
3. Recalculated ages for all affected patients
4. Updated `updated_at` timestamp for each modified patient record

**Files affected:**
- `execution/fix_future_dobs.py` (new)
- `execution/check_negative_ages.py` (new, diagnostic script)
- MongoDB `surgdb.patients` collection (404 records updated)

**Testing:**
```bash
# Verify no more negative ages exist
python3 execution/check_negative_ages.py

# Test pagination pages that were failing
curl "http://localhost:8000/api/patients/?skip=150&limit=25"  # Page 7
curl "http://localhost:8000/api/patients/?skip=175&limit=25"  # Page 8
```

**Notes:**
- The issue only appeared on pages 7-8 because those specific pagination ranges contained patients with the problematic DOBs
- The fix is retroactive; the import script logic in `execution/import_fresh_with_improvements.py` should also be reviewed to prevent this issue on future imports
- Consider updating `parse_dob()` to be more conservative: any year > current_year - 10 should subtract 100 years
- All DOBs should be stored as datetime objects (which they are), but age should be calculated dynamically rather than stored

---

## 2025-12-27 - Fix API URL Configuration for Remote Access

**Changed by:** AI Session
**Issue:** Admin section and other pages showed "Network Error" when accessed via `surg-db.vps` hostname. The application worked on localhost but failed on remote machines due to hardcoded `http://localhost:8000` fallback in API_URL configuration.

**Changes:**

### Root Cause
Multiple components used incorrect API_URL construction logic:
```typescript
// BROKEN: Empty string is falsy, falls back to localhost
const API_URL = import.meta.env.VITE_API_URL?.replace('/api', '') || 'http://localhost:8000'
```

When `VITE_API_URL=/api`, this becomes:
- `'/api'.replace('/api', '')` = `''` (empty string)
- Empty string is falsy → falls back to `'http://localhost:8000'`
- Hardcoded localhost fails for remote access

### Solution
Applied AuthContext pattern across all components:
```typescript
// FIXED: Explicitly check for '/api' and use empty string for relative URLs
const API_URL = import.meta.env.VITE_API_URL === '/api' ? '' : (import.meta.env.VITE_API_URL?.replace('/api', '') || 'http://localhost:8000')
```

This enables:
- Empty string when `VITE_API_URL=/api` → uses relative URLs through Vite proxy
- Works from any hostname (localhost, surg-db.vps, IP addresses)
- Proxy forwards requests to backend at `http://192.168.11.238:8000`

### Files Fixed

**Pages (4 files):**
- `frontend/src/pages/AdminPage.tsx` (line 9-11)
- `frontend/src/pages/HomePage.tsx` (line 89-90)
- `frontend/src/pages/EpisodesPage.tsx` (lines 154-155, 207-208)
- `frontend/src/pages/ReportsPage.tsx` (lines 104-105, 123-124)

**Search Components (2 files):**
- `frontend/src/components/search/SurgeonSearch.tsx` (line 44-45)
- `frontend/src/components/search/NHSProviderSelect.tsx` (lines 62-63, 97-98)

**Modal Components (3 files):**
- `frontend/src/components/modals/TumourModal.tsx` (line 126-127)
- `frontend/src/components/modals/AddTreatmentModal.tsx` (line 137-138)
- `frontend/src/components/modals/CancerEpisodeDetailModal.tsx` (10 instances)

**Context (already fixed):**
- `frontend/src/contexts/AuthContext.tsx` (line 4-6) - Reference pattern

**Total:** 11 files updated with consistent API_URL handling

**Files affected:**
- 11 TypeScript files (pages, components, contexts)
- Multiple API call locations fixed
- Vite proxy configuration verified: `frontend/vite.config.ts`

**Testing:**
```bash
# 1. Verify frontend service is running
sudo systemctl status surg-db-frontend

# 2. Test login from remote machine
# Access via http://surg-db.vps:3000/login
# Login should succeed

# 3. Test admin section
# Navigate to Admin page
# Should load users, clinicians, backups without error

# 4. Test other sections
# Verify patients, episodes, reports all load
# Verify modals open and fetch data correctly
```

**Notes:**
- All components now use consistent API_URL pattern from AuthContext
- Remote access works from any hostname via Vite proxy
- Proxy configuration: `/api` → `http://192.168.11.238:8000`
- Frontend uses relative URLs when `VITE_API_URL=/api`
- Backend listens on `0.0.0.0:8000` (all interfaces)
- Previous fix to AuthContext.tsx inspired this broader solution
- Modal components had 10+ instances of incorrect pattern (all fixed)

**Benefits:**
- Application now fully accessible from remote machines
- Consistent API URL handling across entire codebase
- No more hardcoded localhost URLs
- Works seamlessly with Vite proxy in development
- Easy to switch to production API URL in future

---

## 2025-12-27 - Frontend Component Directory Reorganization

**Changed by:** AI Session
**Issue:** The frontend/src/components directory had grown to 25+ files in a flat structure, making navigation difficult and reducing code maintainability.

**Changes:**

### Directory Restructure
Reorganized components into logical subdirectories:

**1. components/modals/** (9 files)
- AddTreatmentModal.tsx
- CancerEpisodeDetailModal.tsx
- EpisodeDetailModal.tsx
- FollowUpModal.tsx
- InvestigationModal.tsx
- PatientModal.tsx
- TreatmentSummaryModal.tsx
- TumourModal.tsx
- TumourSummaryModal.tsx

**2. components/forms/** (2 files)
- CancerEpisodeForm.tsx
- EpisodeForm.tsx

**3. components/search/** (3 files)
- PatientSearch.tsx
- SurgeonSearch.tsx
- NHSProviderSelect.tsx

**4. components/common/** (9 files)
- Button.tsx
- Card.tsx
- DateInput.tsx
- LoadingSpinner.tsx
- PageHeader.tsx
- Pagination.tsx
- SearchableSelect.tsx
- Table.tsx
- Toast.tsx

**5. components/layout/** (2 files)
- Layout.tsx
- ProtectedRoute.tsx

### Import Statement Updates
Updated all import paths across 33 files:
- **App.tsx**: Updated Layout and ProtectedRoute imports
- **Pages (7 files)**: AdminPage, EpisodesPage, PatientsPage, CancerEpisodesPage, ReportsPage, HomePage
- **Components (24 files)**: All moved components updated to reference new paths

**Files affected:**
- All 25 component files moved to subdirectories
- 33 files total with import statement updates
- Used `git mv` to preserve file history

**Testing:**
```bash
# Verify build
cd /root/surg-db/frontend
npm run build

# Should complete with no TypeScript errors
# Build output: ✓ built in ~2s
```

**Notes:**
- All file moves used `git mv` to maintain git history
- Import paths updated using relative paths (../modals/, ../common/, etc.)
- Build completed successfully with no errors
- New structure follows React best practices
- Easier to add new components in appropriate subdirectories
- Clear separation: modals, forms, search, common UI, layout/routing

**Benefits:**
- Improved code navigation and discoverability
- Logical grouping by component type/purpose
- Better scalability for future development
- Follows industry-standard React project structure
- Reduces cognitive load when working with codebase

---

## 2025-12-27 - Patient Search Enhancement, Pagination & Modal Backdrop Fix

**Changed by:** AI Session
**Issue:** Multiple UI/UX improvements needed:
1. Patient search in cancer episode form needed to filter by MRN and NHS number
2. Patient ID field should be read-only in edit mode
3. MRN and NHS number should be visible for reference during episode creation
4. Pagination needed for large patient and episode lists
5. Modal backdrop not extending to top of viewport
6. Step titles in cancer episode form too long (wrapping to 3 lines)

**Changes:**

### 1. Patient Search Component Overhaul
- **PatientSearch.tsx**: Complete refactor from raw fetch() to api.get()
  - Fixed Patient interface to use correct field names (patient_id, mrn, nhs_number)
  - Changed to SearchableSelect component pattern for consistency
  - Added multi-field filter function (searches patient_id, MRN, NHS number)
  - Changed limit from 1000 to 100 (respecting backend limit)
  - Display label changed to show patient_id instead of mrn
  - Dropdown shows "MRN: xxx" and "NHS: xxx" for easy identification

### 2. Cancer Episode Form Enhancements
- **CancerEpisodeForm.tsx**:
  - Made Patient ID field read-only in edit mode with helper text
  - Added selectedPatientDetails state to store MRN and NHS number
  - Created 3-column grid layout: Patient Search | MRN | NHS Number
  - MRN and NHS number fields appear when patient is selected (read-only)
  - Updated step titles for better readability:
    - Step 1: "Patient Details" (was "Patient & Basics")
    - Step 2: "Referral Details" (was "Referral & Process")
  - Shorter titles prevent text wrapping in progress indicator

### 3. Pagination Implementation
- **Created Pagination.tsx**: Reusable pagination component
  - Shows page numbers with Previous/Next buttons
  - Displays "Showing X-Y of Z results"
  - Handles edge cases (first/last page, no results)
  - Consistent styling with application theme

- **PatientsPage.tsx**: Added pagination for patient list
  - 50 patients per page
  - Shows total count and current range
  - Pagination controls at bottom of table

- **EpisodesPage.tsx**: Added pagination for episode list
  - 50 episodes per page
  - Shows total count and current range
  - Pagination controls at bottom of table

### 4. API Layer Updates
- **api.ts**: Added count endpoints
  - apiService.patients.count() for patient totals
  - apiService.episodes.count() for episode totals

- **Backend routes updated**:
  - patients.py: Enhanced aggregation pipeline with better null handling
  - episodes_v2.py: Added count endpoint for pagination

### 5. Modal Backdrop Fix
- **All modal components**: Added `style={{ margin: 0 }}` to backdrop div
  - AddTreatmentModal.tsx
  - CancerEpisodeForm.tsx
  - EpisodeDetailModal.tsx
  - FollowUpModal.tsx
  - InvestigationModal.tsx
  - TreatmentSummaryModal.tsx
  - TumourModal.tsx
  - TumourSummaryModal.tsx
  - Fixes issue where dark background didn't extend to top of viewport
  - Overrides default body/html margins

### 6. SearchableSelect Enhancement
- **SearchableSelect.tsx**:
  - Shows first 100 options when search is empty (was showing nothing)
  - Increased z-index to z-[100] for better visibility

**Files affected:**
- `frontend/src/components/PatientSearch.tsx` - Complete refactor
- `frontend/src/components/CancerEpisodeForm.tsx` - Patient selection UI, step titles
- `frontend/src/components/Pagination.tsx` - New component
- `frontend/src/components/SearchableSelect.tsx` - Empty search behavior
- `frontend/src/pages/PatientsPage.tsx` - Added pagination
- `frontend/src/pages/EpisodesPage.tsx` - Added pagination
- `frontend/src/services/api.ts` - Added count endpoints
- `backend/app/routes/patients.py` - Aggregation improvements
- `backend/app/routes/episodes_v2.py` - Added count endpoint
- `frontend/src/components/AddTreatmentModal.tsx` - Modal backdrop fix
- `frontend/src/components/EpisodeDetailModal.tsx` - Modal backdrop fix
- `frontend/src/components/FollowUpModal.tsx` - Modal backdrop fix
- `frontend/src/components/InvestigationModal.tsx` - Modal backdrop fix
- `frontend/src/components/TreatmentSummaryModal.tsx` - Modal backdrop fix
- `frontend/src/components/TumourModal.tsx` - Modal backdrop fix
- `frontend/src/components/TumourSummaryModal.tsx` - Modal backdrop fix
- `STYLE_GUIDE.md` - Updated with modal backdrop requirement

**Testing:**
1. **Patient Search**:
   - Navigate to Cancer Episodes page
   - Click "New Cancer Episode"
   - Test patient search by typing MRN, NHS number, or Patient ID
   - Verify dropdown shows MRN and NHS number for each patient
   - Select a patient and verify Patient ID appears in search box
   - Verify MRN and NHS Number fields populate in same row

2. **Edit Mode**:
   - Open existing cancer episode
   - Click Edit
   - Verify Patient ID field is read-only with gray background
   - Verify helper text "Patient cannot be changed in edit mode"

3. **Pagination**:
   - Navigate to Patients page with >50 patients
   - Verify pagination controls appear
   - Test Previous/Next buttons
   - Verify "Showing 1-50 of X results" text
   - Navigate to Episodes page and repeat

4. **Modal Backdrop**:
   - Open any modal (patient, episode, treatment, etc.)
   - Verify dark backdrop extends fully to top of viewport
   - No white gap at top of screen

5. **Step Titles**:
   - Create new cancer episode
   - Verify step titles fit on 1-2 lines (not 3)
   - Check all 6 step titles display cleanly

**Notes:**
- Patient search now uses centralized API service (api.get) instead of raw fetch()
- Backend enforces 100 result limit for /patients/ endpoint
- Patient ID is always saved (not MRN) ensuring proper linking
- Pagination state managed at page level (currentPage state)
- Modal backdrop fix uses inline style to override browser defaults
- SearchableSelect now shows options on click (was requiring search input)
- Step title changes improve mobile/small screen readability

---

## 2025-12-27 - Backup System Frontend Integration

**Changed by:** AI Session
**Issue:** Backup system only accessible via CLI - users needed web UI for managing backups without SSH access.

**Changes:**
1. **Created Backend API** (`backend/app/routes/backups.py`):
   - 7 RESTful endpoints for backup management:
     - `GET /api/admin/backups/` - List all backups
     - `GET /api/admin/backups/status` - System status (counts, sizes, free space)
     - `POST /api/admin/backups/create` - Create manual backup with note
     - `GET /api/admin/backups/{backup_name}` - Get backup details
     - `DELETE /api/admin/backups/{backup_name}` - Delete backup
     - `POST /api/admin/backups/restore` - Get restore instructions (can't execute via web)
     - `POST /api/admin/backups/cleanup` - Run retention policy
     - `GET /api/admin/backups/logs/latest` - Last 50 log lines
   - All endpoints protected with `require_admin` auth
   - Background tasks for long operations (create, cleanup)
   - Calls Python scripts via subprocess

2. **Updated Backend Main** (`backend/app/main.py`):
   - Added backups router import and inclusion
   - Router available at `/api/admin/backups/`

3. **Added Backups Tab to Admin Page** (`frontend/src/pages/AdminPage.tsx`):
   - New "Backups" tab (4th tab alongside Users, Clinicians, Exports)
   - Added 6 state variables:
     - `backups: any[]` - List of backups
     - `backupStatus: any` - System status metrics
     - `backupLoading: boolean` - Loading state
     - `backupNote: string` - User input for manual backup notes
     - `showRestoreConfirm: boolean` - Restore modal visibility
     - `selectedBackup: string | null` - Selected backup for restore
   - Added `fetchBackups()` function with dual API calls (list + status)
   - Added helper functions:
     - `createBackup()` - POST to /create, auto-refresh after 5s
     - `deleteBackup()` - DELETE with confirmation
     - `formatBytes()` - Convert bytes to MB
     - `formatTimestamp()` - Format ISO date to locale string

4. **Backup Tab UI** (~200 lines of React components):
   - **Status Dashboard** - 4 metric cards with colored backgrounds:
     - Total Backups (blue bg)
     - Total Size (green bg)
     - Free Space (purple bg)
     - Total Documents (orange bg)
   - **Latest Backup Card** - Gradient styled card showing:
     - Timestamp
     - Type (Manual/Automatic)
     - Size
     - Collections count
     - Optional note
   - **Manual Backup Form** - Yellow warning-styled section:
     - Optional note input
     - "Create Backup Now" button
     - Warning text about duration
   - **Automatic Backups Info** - Info-styled section explaining:
     - Cron schedule (2 AM daily)
     - Retention policy (30d/3m/1y)
     - Manual backup protection
   - **Backup List Table** - Using standardized Table component:
     - 6 columns: Timestamp, Type, Size, Collections, Note, Actions
     - Delete button for each backup
     - "View Details" button to show restore modal
   - **Restore Confirmation Modal** - Warning-styled modal with:
     - Backup details display
     - SSH command with exact restore instructions
     - Red warning text about service restart
     - Safety guidelines
     - Close button (no web-based restore)

**Files affected:**
- `backend/app/routes/backups.py` - New API router (340 lines)
- `backend/app/main.py` - Added backups router import/inclusion
- `frontend/src/pages/AdminPage.tsx` - Added backups tab (~250 lines added)

**Testing:**
```bash
# Verify backend API (requires admin token)
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/admin/backups/
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/admin/backups/status

# Web UI testing:
# 1. Log in as admin user
# 2. Navigate to Admin page
# 3. Click "Backups" tab
# 4. Verify status cards show correct counts
# 5. Create manual backup with note
# 6. Wait 5-10 seconds, verify new backup appears
# 7. Click "View Details" on a backup
# 8. Verify restore modal shows SSH command
# 9. Test delete backup (with confirmation)
# 10. Verify backup disappears from list

# Check services
sudo systemctl status surg-db-backend
sudo systemctl status surg-db-frontend
```

**Bug Fixes:**
- Fixed backend import error: Changed `get_current_admin_user` to `require_admin` in backups.py (function didn't exist)
- Fixed frontend TypeScript error: Added `fetchBackups()` function that was referenced but not defined
- Added missing state updates: `setBackups()` and `setBackupStatus()` calls in fetchBackups

**Security:**
- All endpoints require admin role via `require_admin` dependency
- Restore operations cannot be executed via web UI (requires SSH for service restart)
- Delete confirmations prevent accidental deletion
- Modal shows exact SSH command for manual restoration

**Notes:**
- Backup creation takes 5-10 seconds depending on database size - UI shows loading spinner
- Manual backups never auto-deleted by retention policy
- Restore instructions provided via modal, but actual restore requires SSH (service restart needed)
- Backend uses subprocess to call Python scripts (backup_database.py, cleanup_old_backups.py)
- Background tasks prevent API timeout during long operations

---

