# Surveillance & Follow-up Timetabling Feature Plan

**Status:** Planning Phase
**Priority:** High
**Created:** 2026-01-05
**Target Users:** Clinicians tracking cancer surveillance schedules

---

## Overview

This feature adds automated surveillance scheduling for cancer patients based on clinical protocols (e.g., NBOCA colorectal cancer guidelines). The system will:
- Auto-generate follow-up investigation schedules when treatments are completed
- Track due/overdue investigations with visual alerts
- Send email notifications for overdue items
- Provide a dedicated surveillance calendar view
- Support custom surveillance protocols

---

## User Requirements (Confirmed 2026-01-05)

### Scheduling Approach
**Selected:** Auto-generate from treatment (Recommended)
- Automatically create surveillance schedule when curative treatment is completed
- Based on NBOCA guidelines for colorectal cancer
- Clinicians can adjust afterward

### Overdue Investigation Handling
**Selected:** All alerting features
- ✅ Show red warning badges (visual indicators)
- ✅ Email notifications (automated reminders to assigned clinicians)
- ✅ Extend due window (2-week grace period if slightly overdue)
- ✅ Escalation alerts (notify senior clinician if >30 days overdue)

### Initial Protocols
**Selected:**
- ✅ Colorectal cancer (NBOCA standard) - Most urgent
- ✅ Custom protocol builder - Flexible for other conditions

---

## Architecture

### Database Schema

**New Collection:** `surveillance_schedules`

```python
{
    "schedule_id": str,               # e.g., "SURV-ABC123-colonoscopy-01"
    "patient_id": str,                # Links to patients.patient_id
    "episode_id": str,                # Links to episodes.episode_id
    "surveillance_type": str,         # colonoscopy/ct_abdomen_pelvis/cea_blood_test/clinic_visit
    "protocol": str,                  # nboca_colorectal/custom

    # Scheduling
    "due_date": datetime,             # Target due date
    "due_window_start": datetime,     # Earliest acceptable (due_date - 2 weeks)
    "due_window_end": datetime,       # Latest acceptable (due_date + 4 weeks)
    "status": str,                    # pending/completed/overdue/cancelled

    # Recurrence
    "frequency_months": int,          # e.g., 6 for every 6 months
    "end_surveillance_date": datetime, # Stop scheduling after this date (typically 5 years)
    "recurrence_count": int,          # Number of times auto-rescheduled

    # Completion tracking
    "completed_date": datetime,
    "investigation_id": str,          # Links to investigations collection
    "next_scheduled": datetime,       # Auto-calculated next appointment

    # Assignment
    "assigned_clinician": str,        # Responsible clinician

    # Alerts
    "send_email_reminder": bool,
    "reminder_days_before": int,      # Default: 14 days
    "escalation_days_overdue": int,   # Default: 30 days
    "reminder_sent": bool,
    "reminder_sent_date": datetime,
    "escalation_sent": bool,
    "escalation_sent_date": datetime,

    "notes": str,
    "created_at": datetime,
    "created_by": str,
    "last_modified_at": datetime,
    "last_modified_by": str
}
```

---

## NBOCA Colorectal Cancer Surveillance Protocols

### Stage I (Curative Treatment)

**Years 1-2:**
- Clinic visit + CEA blood test: Every 6 months
- CT abdomen/chest: Annually

**Years 3-5:**
- Clinic visit + CEA blood test: Annually

**Colonoscopy:**
- 1 year post-surgery
- 3 years post-surgery
- 5 years post-surgery

### Stage II-III (Curative Treatment)

**Years 1-2:**
- Clinic visit + CEA blood test: Every 3-6 months
- CT thorax/abdomen/pelvis (CT CAP): Every 6-12 months

**Years 3-5:**
- Clinic visit + CEA blood test: Every 6 months
- CT CAP: Annually

**Colonoscopy:**
- Same as Stage I (1 year, 3 years, 5 years)

### Stage IV (Palliative)
- Individualized based on symptoms and treatment response
- No standard protocol - use custom protocol builder

---

## Backend Implementation

### 1. Protocol Engine

**File:** `backend/app/utils/surveillance_protocols.py`

```python
class SurveillanceProtocolEngine:
    """Generates surveillance schedules based on clinical protocols"""

    def generate_schedule(self, episode, treatment) -> List[SurveillanceSchedule]:
        """
        Auto-generate surveillance schedule from completed treatment

        Args:
            episode: Episode document with cancer type, stage
            treatment: Treatment document with completion date

        Returns:
            List of surveillance schedule items
        """

    def apply_nboca_colorectal_protocol(self, stage, treatment_date):
        """Apply NBOCA colorectal cancer surveillance guidelines"""

    def calculate_schedule_dates(self, base_date, frequency_months, duration_years):
        """Calculate all scheduled dates for recurring investigations"""
```

### 2. API Endpoints

**File:** `backend/app/routes/surveillance.py`

```python
# Core CRUD
POST   /api/surveillance/                    # Create schedule manually
GET    /api/surveillance/{schedule_id}       # Get single schedule
PUT    /api/surveillance/{schedule_id}       # Update schedule
DELETE /api/surveillance/{schedule_id}       # Delete/cancel schedule

# Listing & Filtering
GET    /api/surveillance/                    # List all schedules (paginated)
GET    /api/surveillance/patient/{patient_id} # Get patient's schedule
GET    /api/surveillance/episode/{episode_id} # Get episode's schedule
GET    /api/surveillance/due                 # Get due/overdue items (filterable)

# Auto-generation
POST   /api/surveillance/generate-schedule   # Auto-generate from treatment

# Completion
PUT    /api/surveillance/{schedule_id}/complete # Mark complete & schedule next

# Dashboard
GET    /api/surveillance/summary             # Summary statistics for dashboard
GET    /api/surveillance/overdue             # All overdue investigations
```

### 3. Email Notifications

**File:** `backend/app/utils/surveillance_notifications.py`

```python
def send_reminder_email(schedule: SurveillanceSchedule):
    """Send reminder 14 days before due date"""

def send_overdue_alert(schedule: SurveillanceSchedule):
    """Send overdue notification when investigation passes due window"""

def send_escalation_alert(schedule: SurveillanceSchedule):
    """Send escalation to senior clinician if >30 days overdue"""
```

### 4. Scheduled Job (Cron)

**File:** `backend/app/cron/surveillance_checker.py`

```python
# Run daily at 6 AM
def check_due_investigations():
    """
    Daily job to:
    1. Update status to 'overdue' for items past due_window_end
    2. Send reminder emails (14 days before due)
    3. Send escalation alerts (30+ days overdue)
    4. Extend grace period (auto-extend due_window_end by 2 weeks if needed)
    """
```

**Cron setup:**
```bash
# Add to crontab
0 6 * * * cd /root/impact && python3 -m backend.app.cron.surveillance_checker
```

---

## Frontend Implementation

### 1. SurveillancePage Component

**File:** `frontend/src/pages/SurveillancePage.tsx`

**Features:**
- Calendar/table view of all scheduled investigations
- Filters:
  - Date range (overdue, this week, this month, next 3 months)
  - Investigation type (colonoscopy, CT, CEA, clinic)
  - Patient name/ID search
  - Status (pending/overdue/completed)
  - Assigned clinician
- Color-coded urgency:
  - 🔴 Red: Overdue (past due_window_end)
  - 🟡 Yellow: Due soon (within 14 days)
  - 🟢 Green: Upcoming (>14 days away)
- Quick actions:
  - Mark complete
  - Reschedule
  - Cancel
  - View patient/episode details

**Layout:**
```tsx
<div className="surveillance-page">
  <header>
    <h1>Surveillance Calendar</h1>
    <button>Generate Schedule</button>
  </header>

  <filters>
    <DateRangeFilter />
    <TypeFilter />
    <StatusFilter />
    <PatientSearch />
  </filters>

  <table>
    {/* Investigation rows with status badges */}
  </table>

  <pagination />
</div>
```

### 2. SurveillanceScheduleModal Component

**File:** `frontend/src/components/modals/SurveillanceScheduleModal.tsx`

**Features:**
- Create/edit surveillance schedule
- Select protocol (NBOCA standard or custom)
- Select investigation type
- Set due date and frequency
- Assign clinician
- Preview upcoming dates (if recurring)
- Configure alerts

### 3. UpcomingInvestigationsWidget Component

**File:** `frontend/src/components/dashboard/UpcomingInvestigationsWidget.tsx`

**Features:**
- Display on HomePage dashboard
- Show next 5-10 due investigations
- Color-coded status indicators
- Quick link to full surveillance page
- Count badges (e.g., "3 overdue")

### 4. Episode Detail Integration

**Modifications:**
- `frontend/src/components/modals/EpisodeDetailModal.tsx`
- `frontend/src/components/modals/CancerEpisodeDetailModal.tsx`

**Add:**
- "Surveillance" tab showing scheduled investigations
- "Generate Schedule" button (appears when treatment is curative)
- Status summary (e.g., "5 scheduled, 2 overdue")

### 5. Navigation Integration

**File:** `frontend/src/components/layout/Layout.tsx`

**Add menu item:**
```tsx
<NavLink to="/surveillance">
  📅 Surveillance
  {overdueCount > 0 && <Badge>{overdueCount}</Badge>}
</NavLink>
```

---

## Implementation Checklist

### Backend (10 tasks)

- [ ] Create surveillance protocol engine (`backend/app/utils/surveillance_protocols.py`)
- [ ] Add surveillance_schedules collection to `backend/app/database.py`
- [ ] Create surveillance API routes (`backend/app/routes/surveillance.py`)
- [ ] Implement GET /api/surveillance/due endpoint with filters
- [ ] Implement POST /api/surveillance/generate-schedule with NBOCA protocols
- [ ] Implement PUT /api/surveillance/{id}/complete with auto-next scheduling
- [ ] Implement GET /api/surveillance/summary for dashboard stats
- [ ] Create email notification utility (`backend/app/utils/surveillance_notifications.py`)
- [ ] Create surveillance checker cron job (`backend/app/cron/surveillance_checker.py`)
- [ ] Add cron job to system crontab

### Frontend (9 tasks)

- [ ] Create SurveillanceScheduleModal.tsx
- [ ] Create SurveillancePage.tsx with filters and table view
- [ ] Add status badge component with color coding (red/yellow/green)
- [ ] Create UpcomingInvestigationsWidget.tsx
- [ ] Add Surveillance link to Layout.tsx navigation
- [ ] Add "Generate Schedule" button to episode detail modals
- [ ] Add "Surveillance" tab to episode detail modals
- [ ] Create custom protocol builder modal
- [ ] Add surveillance route to App.tsx

### Testing & Documentation (3 tasks)

- [ ] Test end-to-end with sample colorectal cancer patients
- [ ] Update DATABASE_SCHEMA.md with surveillance_schedules collection
- [ ] Update RECENT_CHANGES.md with feature documentation

---

## Data Model Reference

**File created:** `backend/app/models/surveillance.py` ✅

Models included:
- `SurveillanceScheduleBase` - Base fields
- `SurveillanceScheduleCreate` - Creation payload
- `SurveillanceScheduleUpdate` - Update payload
- `SurveillanceSchedule` - Full model with audit fields
- `SurveillanceProtocolTemplate` - Protocol definition template
- `SurveillanceSummary` - Dashboard statistics

---

## User Stories

### Story 1: Auto-generate surveillance schedule
**As a** colorectal surgeon
**I want** surveillance schedules to auto-generate when I complete a curative resection
**So that** I don't have to manually schedule every follow-up investigation

**Acceptance criteria:**
- When treatment is marked "completed" with curative intent
- System generates schedule based on cancer stage
- Clinician can review and adjust schedule
- All investigations are pre-scheduled for 5 years

### Story 2: View due investigations
**As a** surgical registrar
**I want** to see which patients need surveillance investigations this week
**So that** I can contact them and schedule appointments

**Acceptance criteria:**
- Can filter by date range (this week, this month, next 3 months)
- Can filter by investigation type
- Overdue items show in red with days overdue
- Can mark investigations as complete

### Story 3: Receive overdue alerts
**As a** colorectal nurse specialist
**I want** to receive email alerts when investigations are overdue
**So that** I can follow up with patients who haven't attended

**Acceptance criteria:**
- Email sent when investigation becomes overdue
- Escalation email sent to consultant if >30 days overdue
- Can configure alert preferences per investigation

### Story 4: Custom surveillance protocol
**As a** upper GI surgeon
**I want** to create custom surveillance schedules for non-colorectal patients
**So that** I can track follow-up for breast, kidney, or other cancers

**Acceptance criteria:**
- Can manually create surveillance schedule
- Can set custom frequency and duration
- Can specify investigation types
- Can save as template for future use

---

## Technical Considerations

### Performance
- Index surveillance_schedules on:
  - `patient_id`
  - `episode_id`
  - `due_date`
  - `status`
  - `assigned_clinician`
- Cache dashboard statistics (refresh every 5 minutes)

### Email Configuration
- Requires SMTP settings in .env:
  ```
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=noreply@hospital.nhs.uk
  SMTP_PASSWORD=***
  SMTP_FROM=IMPACT System <noreply@hospital.nhs.uk>
  ```

### Grace Period Logic
- Due window: [due_date - 2 weeks, due_date + 4 weeks]
- If investigation not completed by due_window_end, status becomes "overdue"
- Grace period: Auto-extend due_window_end by 2 weeks once (configurable)

### Auto-scheduling Next Investigation
When investigation marked complete:
1. Update status to "completed"
2. Set completed_date
3. If frequency_months is set AND current_date < end_surveillance_date:
   - Calculate next_due_date = completed_date + frequency_months
   - Create new surveillance_schedule record
   - Increment recurrence_count

---

## Future Enhancements (Not in Initial Release)

- SMS notifications for patients
- Patient portal access to view their surveillance schedule
- Integration with hospital booking system
- Automated result tracking (link investigation results to surveillance items)
- Mobile app for clinicians
- Calendar sync (iCal export)
- ML-based risk stratification (adjust surveillance frequency based on risk)

---

## References

- NBOCA Guidelines: https://www.nboca.org.uk/
- COSD Surveillance Fields: https://www.datadictionary.nhs.uk/
- Existing FollowUpModal: `frontend/src/components/modals/FollowUpModal.tsx`
- Existing Investigation tracking: DATABASE_SCHEMA.md lines 449-496
