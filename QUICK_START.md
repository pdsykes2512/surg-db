# Quick Start Guide - New Features

## What's New (December 21, 2025)

### 1. Complete Episode Management 🎉

**Create New Episodes**
- Click "+ Record Surgery" button on Episodes page
- Multi-step form guides you through:
  1. Basic info (Surgery ID, Patient ID)
  2. Classification & Procedure details
  3. Timeline (dates, durations)
  4. Team & Intraoperative data
  5. Review & Submit
- Progress indicator shows your position in the form

**View Episode Details**
- Click "View" on any episode in the list
- See comprehensive read-only details
- Quick "Edit" button to modify

**Edit Episodes**
- Click "Edit" on any episode
- Form pre-filled with existing data
- Same multi-step interface as creation

**Filter & Search**
- Search bar: Find by Surgery ID, Patient ID, Procedure, or Surgeon
- Filters: Category, Urgency, Surgeon, Date Range
- "Clear Filters" button resets all filters

**Delete Episodes**
- Click "Delete" with confirmation prompt

### 2. Toast Notifications 🔔

Success and error messages now appear as elegant toast notifications in the top-right corner:
- ✅ Green for success
- ❌ Red for errors
- ⚠️ Yellow for warnings
- ℹ️ Blue for info

Auto-dismiss after 3 seconds or click X to close immediately.

### 3. Enhanced Reports & Analytics 📊

**New Dashboard Metrics:**
- Total Procedures
- Success Rate (with complication breakdown)
- Average Length of Stay
- 30-Day Readmission Rate
- Return to Theatre Rate
- ICU/HDU Escalation Rate
- 30-Day Mortality Rate

**Visual Analytics:**
- Surgery Urgency breakdown with color-coded bars
- Category distribution charts
- Surgeon Performance table with:
  - Total cases
  - Color-coded complication rates
  - Readmission rates
  - Average duration and length of stay

## How to Start the Application

### ⚠️ Production: Use Systemd Services

The application runs as systemd services in production:

```bash
# Restart backend
sudo systemctl restart surg-db-backend

# Restart frontend
sudo systemctl restart surg-db-frontend

# Check status
sudo systemctl status surg-db-backend
sudo systemctl status surg-db-frontend

# View logs
tail -f ~/.tmp/backend.log
tail -f ~/.tmp/frontend.log
```

### Development: Manual Startup

For development/debugging only:

1. **Start the backend:**
   ```bash
   ./execution/start_backend.sh
   ```
   
   Logs are stored in `~/.tmp/backend.log`

2. **Start the frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

## How to Test

3. **Test Episode Creation:**
   - Navigate to Episodes page
   - Click "+ Record Surgery"
   - Fill in the multi-step form
   - Submit and see success toast

4. **Test Filtering:**
   - Create a few episodes with different urgencies/categories
   - Use the filter dropdowns
   - Try the search bar

5. **Test Reports:**
   - Navigate to Reports page
   - View the analytics dashboard
   - Check surgeon performance table

## Technical Notes

### API Endpoints Used
- `GET /api/episodes?category=X&urgency=Y&surgeon=Z&start_date=...&end_date=...`
- `POST /api/episodes`
- `PUT /api/episodes/{surgery_id}`
- `DELETE /api/episodes/{surgery_id}`
- `GET /api/reports/summary`
- `GET /api/reports/surgeon-performance`

### Components Structure
```
frontend/src/
├── components/
│   ├── EpisodeForm.tsx (multi-step form)
│   ├── EpisodeDetailModal.tsx (read-only view)
│   └── Toast.tsx (notifications)
├── pages/
│   ├── EpisodesPage.tsx (list, filters, CRUD)
│   └── ReportsPage.tsx (analytics dashboard)
```

### Data Flow
1. User interactions → React component state
2. Form submission → API call via apiService
3. Success/Error → Toast notification
4. List refresh → Updated data displayed

## Known Limitations

- No pagination yet (all episodes loaded at once)
- No CSV/PDF export yet
- No file upload for surgical notes yet
- BMI auto-calculation not implemented yet

These are tracked in TODO.md for future development.

## Troubleshooting

**Episode form not submitting?**
- Check required fields (marked with *)
- Ensure Patient ID exists in the system
- Check browser console for errors

**Reports showing "No Data"?**
- Create at least one episode first
- Check API connectivity
- Verify backend is running

**Filters not working?**
- Clear all filters and try again
- Check date format (YYYY-MM-DD)
- Ensure backend supports filter parameters

## Support

For issues or questions:
1. Check IMPLEMENTATION_SUMMARY.md for technical details
2. Review TODO.md for planned features
3. Check backend logs for API errors
4. Review browser console for frontend errors
