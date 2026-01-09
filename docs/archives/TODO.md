# TODO - IMPACT (Integrated Monitoring Platform for Audit Care & Treatment)

> **IMPORTANT:** When completing tasks from this list, mark them as complete (✅) and update the "Last Updated" date at the bottom. This ensures continuity across AI sessions and prevents duplicate work.

## Current Status
- ✅ Backend API with FastAPI and MongoDB
- ✅ Frontend with React, TypeScript, and Tailwind CSS
- ✅ Authentication system with JWT and role-based access
- ✅ Patient CRUD operations with NHS number validation
- ✅ Episode (surgery) tracking with renamed nomenclature
- ✅ Dashboard with real-time statistics
- ✅ Admin user management with password changes
- ✅ Complete Episode CRUD interface with multi-step form
- ✅ Episode list with filtering and search
- ✅ Toast notifications for UX feedback
- ✅ Reports & Analytics page with real data visualization
- ✅ Patient-centric episode workflow (click patient to view their episodes)
- ✅ Comprehensive audit logging system across all CRUD operations
- ✅ Investigation tracking (imaging, endoscopy, laboratory)
- ✅ Follow-up visit management

## High Priority

### Surgery Recording Enhancements (CRITICAL)
- **Stoma Formation and Status** ✅ (Complete)
  - ✅ Add stoma creation field (yes/no) to surgery model
  - ✅ Add stoma type (ileostomy/colostomy with temporary/permanent designation)
  - ✅ Add stoma closure date tracking
  - ✅ Frontend form fields implemented in AddTreatmentModal
  - ✅ Add validation: temporary stoma should have closure date within 2 years
  - ✅ Add planned reversal date field (separate from actual closure date)
  - ✅ Link reversal surgery to original stoma creation
  - ✅ Display in TreatmentSummaryModal with planned and actual dates

- **Anastomosis Recording** ✅ (Complete - 2025-12-27)
  - ✅ Add anastomosis field (yes/no) to surgery model
  - ✅ Add anastomosis type field (hand-sewn/stapled/hybrid)
  - ✅ Add anastomosis configuration (end-to-end/end-to-side/side-to-side/side-to-end)
  - ✅ Add anastomosis location field (colorectal/coloanal/ileocolic/ileorectal/colocolic/ileoanal_pouch/other)
  - ✅ Add anastomosis height from anal verge (cm) field
  - ✅ Add defunctioning/protective stoma tracking
  - ✅ Frontend form fields implemented in AddTreatmentModal
  - ✅ Display in TreatmentSummaryModal
  - ✅ **Comprehensive Anastomotic Leak Tracking (NBOCA Compliant)**
    - ✅ ISGPS severity grading (A/B/C) with descriptions
    - ✅ Date identified and days post-surgery calculation
    - ✅ Presentation method (clinical/radiological/endoscopic/at_reoperation)
    - ✅ Clinical signs checklist (fever, tachycardia, peritonitis, sepsis, ileus, pain)
    - ✅ CT findings (free fluid, gas, contrast leak, collection)
    - ✅ Endoscopy findings (defect, dehiscence, ischemia)
    - ✅ Management strategy (conservative/drainage/endoscopic/reoperation)
    - ✅ Reoperation tracking (procedure type and date)
    - ✅ ICU admission and length of stay
    - ✅ Total hospital stay tracking
    - ✅ Protective stoma presence indicator
    - ✅ Mortality tracking
    - ✅ Resolution status and date
    - ✅ Additional notes field
    - ✅ Backend AnastomoticLeak model with all fields
    - ✅ Frontend comprehensive UI with conditional rendering
    - ✅ Integrated into post-operative complications section

### NBOCA COSD Compliance (NEW - Critical for Bowel Cancer)
- [x] **Phase 1: Critical Fields** (see NBOCA_FIELDS_STATUS.md)
  - ✅ NHS Number (already in patient model with validation)
  - ✅ Postcode (already in demographics)
  - ✅ Ethnicity (already in demographics)
  - ✅ Add ICD-10 diagnosis code to bowel cancer data
  - ✅ Add TNM version field (v7/v8) to staging
  - ✅ Add date of diagnosis to bowel cancer data
  - ✅ Add OPCS-4 procedure codes to surgery
  - ✅ Add ASA score to surgical classification
  - ✅ Add circumferential resection margin (CRM) to pathology
- [x] **Phase 2: Process Metrics**
  - ✅ Add referral source tracking to episodes
  - ✅ Add provider organisation identifiers
  - ✅ Add MDT meeting type classification
  - ✅ Add CNS involvement indicator
- [x] **Data Export & Quality**
  - ✅ Create COSD XML export endpoint
  - ✅ Add data completeness checker
  - ✅ Implement NBOCA submission validator
  - ✅ Build data quality dashboard for COSD fields (visual dashboard with color-coded completeness metrics)

### Episode Management
- ✅ Build complete Episode CRUD interface in frontend
- ✅ Add episode creation form with all fields from Surgery model
- ✅ Implement episode edit functionality
- ✅ Add episode detail view with full information
- ✅ Create episode list with filtering (date range, surgeon, category, urgency)
- ✅ Add episode search functionality

### Reports & Analytics
- ✅ Design reports page UI
- ✅ Implement outcome metrics dashboard
- ✅ Add complication rate analysis
- ✅ Create length of stay statistics
- ✅ Build readmission tracking reports
- ✅ Add surgeon performance analytics (aggregated)
- ✅ Export reports to PDF/Excel
- ✅ Add NBOCA-specific reports (30-day mortality, anastomotic leak rates, conversion rates)
- ✅ Add return to theatre (RTT) tracking to surgeon performance table
- ✅ Implement yearly breakdown of outcomes (2023-2025) across all metrics
- ✅ Add color-coding to yearly metrics for quick visual assessment
- ✅ Fix RTT data quality from CSV source (1.6% rate verified)

### Data Validation & Quality
- ✅ Add comprehensive form validation on frontend
- ✅ Implement date range validation (surgery dates, follow-up dates)
- ✅ Add BMI calculation from height/weight (auto-calculated)
- ✅ Validate ASA score ranges (1-5)
- ✅ Add ICD-10 code lookup/validation (63 codes with API endpoints)
- ✅ Add OPCS-4 code lookup/validation (126 codes with API endpoints)
- ✅ Validate COSD mandatory fields
- ✅ Fix RTT data from CSV source using NHS number matching (execution/fix_rtt_from_csv.py)
- ✅ Create data migration guide for reproducible fixes (DATABASE_MIGRATION_SUMMARY.md)
- ✅ Fix investigation date format inconsistencies (converted 17,564 datetime objects to strings)
- ✅ Update DATA_MIGRATION_GUIDE.md with fix_rtt_from_csv.py script details

### Audit Logging & Activity Tracking
- ✅ Create audit log data model and API endpoints
- ✅ Implement audit logging for patient CRUD operations
- ✅ Implement audit logging for episode CRUD operations
- ✅ Implement audit logging for treatment CRUD operations
- ✅ Implement audit logging for tumour CRUD operations
- ✅ Implement audit logging for investigation CRUD operations
- ✅ Display recent activity on HomePage from audit logs
- ✅ Add user context (user_id, username, IP address, user-agent) to audit entries
- ✅ Add audit API endpoints (recent activity, user history, entity history, statistics)

### Investigation Management
- ✅ Create investigation data model (imaging, endoscopy, laboratory)
- ✅ Import historical investigation data from Access database (17,564 records)
- ✅ Build investigation modal for create/edit operations
- ✅ Add investigations tab to episode detail modal
- ✅ Implement investigation delete functionality
- ✅ Add investigation API integration for updates
- ✅ Fix investigation form data population issues
- ✅ Add CT Colonography to imaging investigation types
- ✅ Make investigation result field optional

## Medium Priority

### User Experience
- ✅ Add loading spinners for async operations
- ✅ Implement toast notifications for success/error messages
- ✅ Add pagination to patient and episode lists
- [ ] Implement data export functionality (CSV/Excel)
- [ ] Add print-friendly views for reports
- ✅ **Create keyboard shortcuts for common actions** (Complete - 2025-12-31)
  - ✅ Global help dialog (Shift+/ or ?)
  - ✅ Page navigation (Cmd/Ctrl+1-4)
  - ✅ Table navigation (↑/↓ arrows, E to edit, Shift+D to delete)
  - ✅ Pagination shortcuts ([ previous, ] next page)
  - ✅ Quick actions (Cmd/Ctrl+Shift+P add patient, Cmd/Ctrl+Shift+E add episode)
  - ✅ Search focus (Cmd/Ctrl+K)
  - ✅ Modal shortcuts (Esc to close, Cmd/Ctrl+Enter to submit)
  - ✅ All shortcuts work with form elements focused (enableOnFormTags)

### Episode Features
- ✅ Investigation tracking integrated into episodes
- [ ] Add file upload for surgical notes/images
- ✅ Add complication tracking with severity levels (Complete - Clavien-Dindo grading I-V, anastomotic leak severity A-C)
- ✅ Build episode audit log (via comprehensive audit system)

### Security & Performance
- ✅ Implement audit logging for security tracking
- ✅ Add rate limiting to API endpoints
- ✅ Implement API request logging
- ✅ Add database query optimization
- ✅ **Create data backup strategy** (Complete - 2025-12-27)
  - ✅ Automated daily backups at 2 AM with cron job
  - ✅ Retention policy: 30d daily, 3m weekly, 1y monthly
  - ✅ Manual backup script with notes support
  - ✅ Restoration script with safety checks
  - ✅ Cleanup script for applying retention policy
  - ✅ Web UI in Admin page for backup management
  - ✅ Backend API with 7 endpoints for backup operations
  - ✅ Comprehensive documentation in directives/database_backup_system.md
- [ ] Implement session timeout handling
- [ ] Add HTTPS/SSL configuration guide
- ✅ **Implement database encryption at rest (MongoDB encryption)**

## Low Priority

### Integration & Automation
- [ ] Design EHR integration architecture
- [ ] Create lab results import functionality
- [ ] Add email notifications for follow-ups
- [ ] Build automated report generation
- [ ] Create data anonymization for research exports

### Documentation
- [ ] Write API documentation (OpenAPI/Swagger)
- [ ] Create user manual
- [ ] Document deployment procedures
- [ ] Add inline code documentation
- [ ] Create development setup guide

### Testing
- [ ] Write backend unit tests
- [ ] Create frontend component tests
- [ ] Add end-to-end testing
- [ ] Implement CI/CD pipeline
- [ ] Set up staging environment

## Technical Debt

- ✅ **Refactor API error handling for consistency** (Complete - 2025-12-31)
  - ✅ Standardized error classes (APIError, ResourceNotFoundError, ValidationError, etc.)
  - ✅ Global error handler middleware
  - ✅ Consistent JSON error response format across all endpoints
  - ✅ Comprehensive documentation in docs/ENVIRONMENT_SETUP.md
- ✅ Standardize date/time formats across application (investigation dates fixed)
- ✅ **Review and optimize database indexes** (Complete - 2025-12-31)
  - ✅ Created 27 indexes across 7 collections (patients, episodes, treatments, etc.)
  - ✅ Added hash indexes for encrypted field searches (nhs_number_hash, mrn_hash)
  - ✅ Implemented O(log n) hash-based lookups for encrypted searches
  - ✅ Performance improvement: ~100x speedup (seconds → milliseconds)
  - ✅ Migrated 15,074 hash fields for 7,971 existing patients
- ✅ **Clean up unused dependencies** (Complete - 2025-12-31)
  - ✅ Removed fastapi-cors (FastAPI has built-in CORS)
  - ✅ Removed python-dateutil (replaced with Python's built-in datetime)
  - ✅ Removed httpx (testing dependency not actively used)
  - ✅ Reduced attack surface and maintenance burden
- ✅ **Improve TypeScript type coverage** (Foundation Complete - 2025-12-31)
  - ✅ Created comprehensive type definitions (models.ts, api.ts, index.ts)
  - ✅ 15+ domain models with nested types
  - ✅ 30+ API request/response types
  - ✅ Types ready for incremental adoption across 23 files
  - ⏭️  Component updates (can be done incrementally as features are worked on)
- ✅ **Add proper environment configuration management** (Complete - 2025-12-31)
  - ✅ Secret key validation with strength requirements
  - ✅ MongoDB URI format validation
  - ✅ .env.example template with all required variables
  - ✅ Comprehensive setup guide in docs/ENVIRONMENT_SETUP.md

## Future Enhancements

- ✅ **Mobile-responsive design improvements** (Complete - 2025-12-28)
  - ✅ Mobile navigation with hamburger menu (< 768px)
  - ✅ Responsive table padding (px-2 sm:px-4 md:px-6)
  - ✅ WCAG 2.1 compliant touch targets (44×44px minimum)
  - ✅ Progressive modal max-widths with breakpoint chains
  - ✅ Grid layouts with sm: breakpoints for tablets
  - ✅ Intelligent pagination with mobile page limiting
  - ✅ Visual step progress indicators scroll horizontally
  - ✅ Comprehensive responsive design documentation in STYLE_GUIDE.md
- [ ] **Surveillance & Follow-up Timetabling** (NEW - High Priority)
  - [ ] Create Pydantic models for surveillance schedules (✅ DONE - backend/app/models/surveillance.py)
  - [ ] Create surveillance protocol engine with NBOCA colorectal guidelines
  - [ ] Add surveillance_schedules collection to database.py
  - [ ] Build backend API routes for surveillance CRUD operations
  - [ ] Create GET /api/surveillance/due endpoint for filtering due investigations
  - [ ] Create POST /api/surveillance/generate-schedule endpoint for auto-generation
  - [ ] Create PUT /api/surveillance/{id}/complete endpoint to mark complete
  - [ ] Create GET /api/surveillance/summary endpoint for dashboard statistics
  - [ ] Create email notification utility for overdue investigations
  - [ ] Create scheduled job/cron for checking overdue investigations
  - [ ] Create SurveillanceScheduleModal.tsx component for creating/editing schedules
  - [ ] Create SurveillancePage.tsx with calendar/table view and filters
  - [ ] Add status badges (red/yellow/green) for overdue/due-soon/upcoming items
  - [ ] Create UpcomingInvestigationsWidget.tsx for home page dashboard
  - [ ] Add Surveillance link to navigation menu (Layout.tsx)
  - [ ] Add 'Generate Surveillance Schedule' button to episode detail modals
  - [ ] Create auto-schedule trigger when treatment marked as completed
  - [ ] Add surveillance schedule display section to episode detail modals
  - [ ] Create custom protocol builder modal for flexible surveillance schedules
  - [ ] Test surveillance feature end-to-end with sample data
  - [ ] Update DATABASE_SCHEMA.md with surveillance_schedules collection
  - [ ] Update RECENT_CHANGES.md with surveillance feature documentation
- [ ] Multi-language support
- [ ] Advanced search with filters
- ✅ **Data visualization with charts (Recharts)** (Complete - 2026-01-09)
  - ✅ Yearly outcomes trends line charts (complications, mortality, ICU escalation)
  - ✅ Surgery urgency breakdown pie chart (elective/urgent/emergency)
  - ✅ ASA grade stratification bar chart (color-coded by risk level)
  - ✅ Surgeon performance comparison bar chart (multi-metric)
  - ✅ COSD completeness bar chart by category (color-coded)
  - ✅ All charts responsive with interactive tooltips and legends
- [ ] Real-time collaboration features
- ✅ Audit trail for all data changes (comprehensive audit logging implemented)
- [ ] Version control for episode records

## Notes

- Episodes (previously "Surgeries") terminology updated throughout
- Current branch: `main`
- Database: MongoDB with optimized indexes
- Authentication: JWT with 4 roles (admin, surgeon, data_entry, viewer)
- **Backup System:** Daily automated backups with web UI management in Admin → Backups tab

---
Last Updated: December 31, 2025
