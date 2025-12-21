# Surgical Outcomes Database Application

## Goal
Build a full-stack application to store, manage, and report on patient surgery outcome data with a NoSQL database backend and web-based frontend for data entry and reporting.

## Architecture

### Technology Stack
- **Backend**: FastAPI (Python) - High-performance REST API
- **Database**: MongoDB - NoSQL database for flexible patient outcome schemas
- **Frontend**: React with TypeScript - Modern UI for data entry and reports
- **Styling**: Tailwind CSS - Responsive design
- **Data Visualization**: Chart.js / Recharts - For outcome reports

### Application Structure
```
/root/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── models/              # Pydantic models
│   │   │   ├── patient.py
│   │   │   └── surgery.py
│   │   ├── routes/              # API endpoints
│   │   │   ├── patients.py
│   │   │   ├── surgeries.py
│   │   │   └── reports.py
│   │   ├── database.py          # MongoDB connection
│   │   └── config.py            # Configuration
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   │   ├── PatientForm.tsx
│   │   │   ├── SurgeryForm.tsx
│   │   │   └── ReportViewer.tsx
│   │   ├── pages/               # Page components
│   │   ├── services/            # API calls
│   │   └── App.tsx
│   ├── package.json
│   └── Dockerfile
├── execution/                   # Execution layer scripts
│   ├── init_database.py         # Initialize MongoDB with schemas
│   ├── seed_data.py             # Seed sample data
│   └── generate_report.py       # Report generation utility
└── directives/
    └── surg_db_app.md          # This file
```

## Data Model

### Patient Document
```json
{
  "_id": "ObjectId",
  "patient_id": "string (unique, hospital MRN)",
  "demographics": {
    "age": "number",
    "gender": "string",
    "ethnicity": "string",
    "bmi": "number",
    "weight_kg": "number",
    "height_cm": "number"
  },
  "contact": {
    "phone": "string",
    "email": "string"
  },
  "medical_history": {
    "conditions": ["array of strings"],
    "previous_surgeries": ["array of objects"],
    "medications": ["array of strings"],
    "allergies": ["array of strings"],
    "smoking_status": "string (never/former/current)",
    "alcohol_use": "string"
  },
  "created_at": "datetime",
  "created_by": "string (user ID)",
  "updated_at": "datetime",
  "updated_by": "string (user ID)"
}
```

### Surgery Document
```json
{
  "_id": "ObjectId",
  "surgery_id": "string (unique, internal tracking)",
  "patient_id": "string (ref to Patient MRN)",
  
  "classification": {
    "urgency": "string (elective/emergency/urgent)",
    "category": "string (major_resection/proctology/hernia/cholecystectomy/other)",
    "complexity": "string (routine/intermediate/complex)",
    "primary_diagnosis": "string",
    "indication": "string (cancer/ibd/diverticular/benign/other)"
  },
  
  "procedure": {
    "primary_procedure": "string",
    "additional_procedures": ["array of strings"],
    "cpt_codes": ["array of strings"],
    "icd10_codes": ["array of strings"],
    "approach": "string (open/laparoscopic/robotic/converted)",
    "description": "string"
  },
  
  "perioperative_timeline": {
    "admission_date": "datetime",
    "surgery_date": "datetime",
    "surgery_start_time": "datetime",
    "surgery_end_time": "datetime",
    "anesthesia_duration_minutes": "number",
    "operation_duration_minutes": "number",
    "discharge_date": "datetime",
    "length_of_stay_days": "number"
  },
  
  "team": {
    "primary_surgeon": "string",
    "assistant_surgeons": ["array of strings"],
    "anesthesiologist": "string",
    "scrub_nurse": "string",
    "circulating_nurse": "string"
  },
  
  "intraoperative": {
    "anesthesia_type": "string (general/regional/local)",
    "blood_loss_ml": "number",
    "transfusion_required": "boolean",
    "units_transfused": "number",
    "findings": "string",
    "specimens_sent": ["array of strings"],
    "drains_placed": "boolean",
    "drain_types": ["array of strings"]
  },
  
  "cancer_specific": {
    "applicable": "boolean",
    "cancer_type": "string",
    "tnm_staging": {
      "clinical_t": "string",
      "clinical_n": "string",
      "clinical_m": "string",
      "pathological_t": "string",
      "pathological_n": "string",
      "pathological_m": "string"
    },
    "pathology": {
      "histology": "string",
      "grade": "string",
      "lymph_nodes_examined": "number",
      "lymph_nodes_positive": "number",
      "margins": "string (clear/involved/close)",
      "margin_distance_mm": "number",
      "tumor_size_mm": "number",
      "lymphovascular_invasion": "boolean",
      "perineural_invasion": "boolean"
    },
    "neoadjuvant_therapy": "boolean",
    "neoadjuvant_details": "string",
    "adjuvant_therapy_planned": "boolean"
  },
  
  "ibd_specific": {
    "applicable": "boolean",
    "disease_type": "string (crohns/ulcerative_colitis)",
    "disease_extent": "string",
    "previous_biologics": ["array of strings"],
    "indication_for_surgery": "string",
    "stoma_created": "boolean",
    "stoma_type": "string"
  },
  
  "hernia_specific": {
    "applicable": "boolean",
    "hernia_type": "string (inguinal/ventral/incisional/umbilical/femoral)",
    "hernia_size_cm": "number",
    "recurrent": "boolean",
    "mesh_used": "boolean",
    "mesh_type": "string",
    "mesh_fixation": "string",
    "component_separation": "boolean"
  },
  
  "postoperative_events": {
    "return_to_theatre": {
      "occurred": "boolean",
      "date": "datetime",
      "reason": "string",
      "procedure_performed": "string"
    },
    "escalation_of_care": {
      "occurred": "boolean",
      "destination": "string (hdu/icu)",
      "date": "datetime",
      "reason": "string",
      "duration_days": "number"
    },
    "complications": [{
      "type": "string",
      "clavien_dindo_grade": "string (I/II/IIIa/IIIb/IVa/IVb/V)",
      "description": "string",
      "date_identified": "datetime",
      "treatment": "string",
      "resolved": "boolean"
    }]
  },
  
  "outcomes": {
    "readmission_30day": "boolean",
    "readmission_date": "datetime",
    "readmission_reason": "string",
    "mortality_30day": "boolean",
    "mortality_90day": "boolean",
    "date_of_death": "datetime",
    "cause_of_death": "string"
  },
  
  "follow_up": {
    "appointments": [{
      "date": "datetime",
      "type": "string (post_op/surveillance/mdt)",
      "provider": "string",
      "findings": "string",
      "imaging_results": "string",
      "plan": "string"
    }],
    "long_term_outcomes": {
      "recurrence": "boolean",
      "recurrence_date": "datetime",
      "recurrence_type": "string",
      "functional_status": "string",
      "quality_of_life_score": "number"
    }
  },
  
  "documents": [{
    "type": "string (operation_note/pathology_report/imaging/discharge_summary)",
    "filename": "string",
    "file_path": "string",
    "uploaded_date": "datetime",
    "uploaded_by": "string"
  }],
  
  "audit_trail": {
    "created_at": "datetime",
    "created_by": "string (user ID/name)",
    "updated_at": "datetime",
    "updated_by": "string (user ID/name)",
    "modifications": [{
      "timestamp": "datetime",
      "user": "string",
      "field_changed": "string",
      "old_value": "string",
      "new_value": "string"
    }]
  },
  
  "integration_data": {
    "ehr_encounter_id": "string",
    "lab_system_ids": ["array of strings"],
    "pacs_study_ids": ["array of strings"],
    "last_sync": "datetime"
  }
}
```

## Inputs

### Environment Variables (in .env)
- `MONGODB_URI` - MongoDB connection string
- `MONGODB_DB_NAME` - Database name (default: "surg_outcomes")
- `API_HOST` - Backend API host (default: "localhost")
- `API_PORT` - Backend API port (default: "8000")
- `FRONTEND_PORT` - Frontend port (default: "3000")

### User Inputs (via Frontend)
- Patient demographics and medical history
- Surgery details (procedure, team, date)
- Outcome data (complications, length of stay, satisfaction)
- Follow-up information

## Tools/Scripts to Use

### Execution Layer Scripts

1. **execution/init_database.py**
   - Initialize MongoDB connection
   - Create collections with validation schemas
   - Set up indexes for performance
   - Usage: `python execution/init_database.py`

2. **execution/seed_data.py**
   - Populate database with sample patient and surgery data
   - Useful for testing and development
   - Usage: `python execution/seed_data.py [--count NUMBER]`

3. **execution/generate_report.py**
   - Generate aggregate reports (success rates, complications, etc.)
   - Export to JSON, CSV, or PDF
   - Usage: `python execution/generate_report.py --type [summary|complications|trends] --output report.json`

### Backend API Endpoints

- `POST /api/patients` - Create new patient
- `GET /api/patients` - List all patients (with pagination)
- `GET /api/patients/{id}` - Get patient details
- `PUT /api/patients/{id}` - Update patient
- `DELETE /api/patients/{id}` - Delete patient

- `POST /api/surgeries` - Create new surgery record
- `GET /api/surgeries` - List all surgeries (with filters)
- `GET /api/surgeries/{id}` - Get surgery details
- `PUT /api/surgeries/{id}` - Update surgery outcomes
- `DELETE /api/surgeries/{id}` - Delete surgery record

- `GET /api/reports/summary` - Overall outcome statistics
- `GET /api/reports/complications` - Complication analysis
- `GET /api/reports/trends` - Trends over time
- `GET /api/reports/surgeon-performance` - Surgeon-specific metrics

## Outputs

### Deliverables
- Functional web application accessible via browser
- REST API documentation (auto-generated by FastAPI)
- MongoDB database with patient and surgery data
- Generated reports (JSON, CSV, PDF formats)

### Intermediates (in .tmp/)
- Temporary report files before export
- Data validation logs
- API response caches

## Implementation Steps

### Phase 1: Database Setup
1. Install MongoDB locally or use MongoDB Atlas
2. Run `execution/init_database.py` to set up database
3. Run `execution/seed_data.py` to create sample data
4. Verify collections and indexes

### Phase 2: Backend Development
1. Set up FastAPI project structure
2. Implement MongoDB connection and models
3. Create CRUD endpoints for patients and surgeries
4. Implement report generation endpoints
5. Add data validation and error handling
6. Test API with Postman or curl

### Phase 3: Frontend Development
1. Set up React project with TypeScript
2. Create patient entry form
3. Create surgery entry form with outcome fields
4. Build report visualization components
5. Implement API integration
6. Add responsive design and UX improvements

### Phase 4: Integration & Testing
1. Connect frontend to backend API
2. Test data flow end-to-end
3. Validate report generation
4. Performance optimization
5. Security review (authentication, data privacy)

### Phase 5: Deployment
1. Containerize with Docker
2. Set up docker-compose for local deployment
3. Document deployment process
4. Optional: Deploy to cloud (AWS, Azure, GCP)

## Edge Cases & Considerations

### Data Validation
- Patient ID uniqueness enforcement
- Date validation (surgery date cannot be in future beyond scheduling)
- Required fields vs optional fields
- Data type validation (numeric ranges, valid enums)

### Error Handling
- MongoDB connection failures
- Duplicate patient/surgery IDs
- Invalid data submissions
- Report generation failures (insufficient data)

### Performance
- Index on frequently queried fields (patient_id, surgery_id, procedure.date)
- Pagination for large result sets
- Caching for frequently accessed reports
- Query optimization for aggregate reports

### Security & Privacy
- HIPAA compliance considerations
- Data encryption at rest and in transit
- Access control (future: role-based authentication)
- Audit logging for data changes
- PHI (Protected Health Information) handling

### Scalability
- MongoDB sharding for large datasets
- API rate limiting
- Frontend code splitting
- CDN for static assets

## Testing Strategy
- Unit tests for API endpoints (pytest)
- Integration tests for database operations
- Frontend component tests (Jest, React Testing Library)
- End-to-end tests (Playwright or Cypress)
- Load testing for performance validation

## Monitoring & Maintenance
- API response time monitoring
- Database query performance
- Error rate tracking
- User activity logs
- Regular data backups

## Future Enhancements
- User authentication and authorization
- Real-time notifications for critical outcomes
- Machine learning for outcome predictions
- Integration with EHR systems
- Mobile app for data entry
- Advanced analytics and dashboards
- Multi-facility support
- Data export for research purposes

## Version Control
Follow the branching strategy:
- `feat/backend-api` - Backend API development
- `feat/frontend-ui` - Frontend UI development
- `feat/reports` - Report generation features
- `fix/...` - Bug fixes
- Merge to `main` only when features are complete and tested
