# TODO - Surgical Outcomes Database

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

## High Priority

### Surgery Recording Enhancements (CRITICAL)
- [ ] **Record of anastomosis in surgery section**
  - Add anastomosis field (yes/no) to surgery/treatment model
  - Add anastomosis type (e.g., hand-sewn, stapled, end-to-end, side-to-side)
  - Include location of anastomosis in form
  - NBOCA requirement for anastomotic leak tracking
- [ ] **Record of stoma formation and status**
  - Add stoma creation field (yes/no) to surgery model
  - Add stoma type (ileostomy/colostomy/other)
  - Add stoma intent field: temporary vs permanent
  - For temporary stomas: add planned reversal date field
  - Add validation: temporary stoma must have reversal date within 2 years
  - Track actual reversal date when it occurs
  - Link reversal surgery to original stoma creation

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
- [ ] Update DATA_MIGRATION_GUIDE.md with fix_rtt_from_csv.py script details

## Medium Priority

### User Experience
- ✅ Add loading spinners for async operations
- ✅ Implement toast notifications for success/error messages
- [ ] Add pagination to patient and episode lists
- [ ] Implement data export functionality (CSV/Excel)
- [ ] Add print-friendly views for reports
- [ ] Create keyboard shortcuts for common actions

### Episode Features
- [ ] Add file upload for surgical notes/images
- [ ] Implement episode timeline view
- [ ] Add complication tracking with severity levels
- [ ] Create follow-up appointment scheduler
- [ ] Build episode audit log

### Security & Performance
- [ ] Add rate limiting to API endpoints
- [ ] Implement API request logging
- [ ] Add database query optimization
- [ ] Create data backup strategy
- [ ] Implement session timeout handling
- [ ] Add HTTPS/SSL configuration guide
- [ ] **Implement database encryption at rest (MongoDB encryption)**

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

- [ ] Refactor API error handling for consistency
- [ ] Standardize date/time formats across application
- [ ] Review and optimize database indexes
- [ ] Clean up unused dependencies
- [ ] Improve TypeScript type coverage
- [ ] Add proper environment configuration management

## Future Enhancements

- [ ] Mobile-responsive design improvements
- [ ] Multi-language support
- [ ] Advanced search with filters
- [ ] Data visualization with charts (Chart.js/D3)
- [ ] Real-time collaboration features
- [ ] Audit trail for all data changes
- [ ] Version control for episode records

## Notes

- Episodes (previously "Surgeries") terminology updated throughout
- Current branch: `feat/app-scaffold`
- Database: MongoDB with optimized indexes
- Authentication: JWT with 4 roles (admin, surgeon, data_entry, viewer)

---
Last Updated: December 24, 2025
