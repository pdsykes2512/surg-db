# API Documentation

Complete API reference for the Surgical Outcomes Database REST API.

## Base URL

- **Development**: `http://localhost:8000` (API) / `http://localhost:3000` (Frontend)
- **Production**: `https://api.yourdomain.com` (API) / `https://yourdomain.com` (Frontend)

## Authentication

All endpoints (except `/api/auth/login`) require JWT authentication.

### Headers
```http
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

### Login
```http
POST /api/auth/login
```

**Request Body:**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "username": "admin",
    "role": "admin",
    "full_name": "Admin User"
  }
}
```

---

## Patients API

### List Patients
```http
GET /api/patients?skip=0&limit=100
```

**Response:**
```json
[
  {
    "_id": "507f1f77bcf86cd799439011",
    "record_number": "REC001",
    "nhs_number": "123 456 7890",
    "demographics": {
      "date_of_birth": "1960-01-15",
      "age": 65,
      "gender": "male",
      "ethnicity": "white_british",
      "postcode": "SW1A 1AA",
      "bmi": 25.4,
      "weight_kg": 75.0,
      "height_cm": 172.0
    },
    "medical_history": {
      "conditions": ["hypertension", "type_2_diabetes"],
      "medications": ["metformin", "lisinopril"],
      "allergies": ["penicillin"],
      "smoking_status": "former",
      "alcohol_use": "moderate"
    },
    "created_at": "2025-01-01T10:00:00",
    "updated_at": "2025-01-01T10:00:00"
  }
]
```

### Create Patient
```http
POST /api/patients
```

**Request Body:**
```json
{
  "record_number": "REC001",
  "nhs_number": "123 456 7890",
  "demographics": {
    "date_of_birth": "1960-01-15",
    "gender": "male",
    "ethnicity": "white_british",
    "postcode": "SW1A 1AA",
    "weight_kg": 75.0,
    "height_cm": 172.0
  },
  "medical_history": {
    "conditions": ["hypertension"],
    "medications": ["lisinopril"],
    "allergies": ["penicillin"],
    "smoking_status": "former",
    "alcohol_use": "moderate"
  }
}
```

### Get Patient
```http
GET /api/patients/{record_number}
```

### Update Patient
```http
PUT /api/patients/{record_number}
```

### Delete Patient
```http
DELETE /api/patients/{record_number}
```

### Calculate BMI
```http
POST /api/patients/calculate-bmi?weight_kg=75&height_cm=172
```

**Response:**
```json
{
  "bmi": 25.4,
  "category": "Overweight",
  "weight_kg": 75.0,
  "height_cm": 172.0,
  "height_m": 1.72
}
```

---

## Episodes API

### List Episodes
```http
GET /api/episodes/v2?skip=0&limit=100
```

### Create Bowel Cancer Episode
```http
POST /api/episodes/v2/bowel-cancer
```

**Request Body:**
```json
{
  "patient_id": "REC001",
  "episode_id": "EP001",
  "diagnosis_date": "2025-01-15",
  "primary_site": "C20",
  "mdt_date": "2025-01-20",
  "mdt_outcome": "surgery_recommended",
  "performance_status": 1,
  "referral_source": "gp",
  "symptoms": ["bleeding", "pain"]
}
```

### Get Episode
```http
GET /api/episodes/v2/{episode_id}
```

### Update Episode
```http
PUT /api/episodes/v2/{episode_id}
```

### Delete Episode
```http
DELETE /api/episodes/v2/{episode_id}
```

---

## Code Validation API

### ICD-10 Code Validation

#### Validate Code
```http
GET /api/codes/icd10/validate/C20
```

**Response:**
```json
{
  "valid": true,
  "code": "C20",
  "description": "Malignant neoplasm of rectum",
  "is_rectal": true,
  "is_colon": false
}
```

#### Lookup Code
```http
GET /api/codes/icd10/lookup/C18.7
```

**Response:**
```json
{
  "code": "C18.7",
  "description": "Malignant neoplasm of sigmoid colon",
  "is_rectal": false,
  "is_colon": true
}
```

#### Search Codes
```http
GET /api/codes/icd10/search?q=sigmoid
```

**Response:**
```json
{
  "query": "sigmoid",
  "count": 6,
  "results": [
    {
      "code": "C18.7",
      "description": "Malignant neoplasm of sigmoid colon"
    },
    {
      "code": "C19",
      "description": "Malignant neoplasm of rectosigmoid junction"
    }
  ]
}
```

#### Get Codes by Site
```http
GET /api/codes/icd10/site/rectum
```

**Response:**
```json
{
  "site": "rectum",
  "codes": [
    {
      "code": "C20",
      "description": "Malignant neoplasm of rectum"
    },
    {
      "code": "C20.9",
      "description": "Malignant neoplasm of rectum"
    }
  ]
}
```

#### Get All ICD-10 Codes
```http
GET /api/codes/icd10/all
```

#### Get Primary Cancer Codes Only
```http
GET /api/codes/icd10/primary
```

### OPCS-4 Code Validation

#### Validate Code
```http
GET /api/codes/opcs4/validate/H08.1
```

**Response:**
```json
{
  "valid": true,
  "code": "H08.1",
  "description": "Anterior resection of rectum",
  "is_major_resection": true,
  "is_laparoscopic": false,
  "is_robotic": false
}
```

#### Lookup Code
```http
GET /api/codes/opcs4/lookup/H46.5
```

**Response:**
```json
{
  "code": "H46.5",
  "description": "Laparoscopic anterior resection of rectum",
  "is_major_resection": true,
  "is_laparoscopic": true,
  "is_robotic": false
}
```

#### Search Codes
```http
GET /api/codes/opcs4/search?q=laparoscopic
```

**Response:**
```json
{
  "query": "laparoscopic",
  "count": 17,
  "results": [
    {
      "code": "H46.1",
      "description": "Laparoscopic excision of right hemicolon"
    },
    {
      "code": "H46.5",
      "description": "Laparoscopic anterior resection of rectum"
    }
  ]
}
```

#### Get Codes by Procedure Type
```http
GET /api/codes/opcs4/procedure/anterior_resection
```

**Valid procedure types:**
- `right_hemicolectomy`
- `left_hemicolectomy`
- `sigmoid_colectomy`
- `anterior_resection`
- `apr` (abdominoperineal resection)
- `hartmann`
- `total_colectomy`
- `ileostomy`
- `colostomy`
- `stoma_closure`
- `laparoscopic`
- `robotic`

#### Get All OPCS-4 Codes
```http
GET /api/codes/opcs4/all
```

#### Get Major Resection Codes Only
```http
GET /api/codes/opcs4/resections
```

---

## Reports API

### Summary Report
```http
GET /api/reports/summary
```

**Response:**
```json
{
  "total_surgeries": 150,
  "avg_operation_duration_minutes": 225.5,
  "complication_rate": 0.08,
  "readmission_rate": 0.05,
  "mortality_rate": 0.02,
  "return_to_theatre_rate": 0.03,
  "escalation_rate": 0.04,
  "avg_length_of_stay_days": 6.5,
  "urgency_breakdown": {
    "elective": 120,
    "urgent": 20,
    "emergency": 10
  },
  "generated_at": "2025-12-23T10:00:00"
}
```

### Surgeon Performance
```http
GET /api/reports/surgeon-performance
```

**Response:**
```json
{
  "surgeons": [
    {
      "_id": "Jim Khan",
      "total_surgeries": 45,
      "complication_rate": 0.07,
      "readmission_rate": 0.04,
      "avg_duration": 215.5,
      "avg_los": 6.2
    }
  ],
  "generated_at": "2025-12-23T10:00:00"
}
```

### Trends Report
```http
GET /api/reports/trends?days=30
```

**Response:**
```json
{
  "period_days": 30,
  "start_date": "2025-11-23T00:00:00",
  "end_date": "2025-12-23T10:00:00",
  "daily_trends": [
    {
      "_id": "2025-11-23",
      "count": 5
    },
    {
      "_id": "2025-11-24",
      "count": 3
    }
  ],
  "generated_at": "2025-12-23T10:00:00"
}
```

### NBOCA Mortality Report
```http
GET /api/reports/nboca/mortality
```

**Response:**
```json
{
  "total_surgeries": 150,
  "mortality_30day_count": 3,
  "mortality_30day_rate": 2.0,
  "mortality_90day_count": 5,
  "mortality_90day_rate": 3.33,
  "by_urgency": [
    {
      "urgency": "elective",
      "total_surgeries": 120,
      "mortality_30day_count": 1,
      "mortality_30day_rate": 0.83,
      "mortality_90day_count": 2,
      "mortality_90day_rate": 1.67
    },
    {
      "urgency": "emergency",
      "total_surgeries": 10,
      "mortality_30day_count": 2,
      "mortality_30day_rate": 20.0,
      "mortality_90day_count": 3,
      "mortality_90day_rate": 30.0
    }
  ],
  "generated_at": "2025-12-23T10:00:00"
}
```

### NBOCA Anastomotic Leak Report
```http
GET /api/reports/nboca/anastomotic-leak
```

**Response:**
```json
{
  "total_anastomoses": 100,
  "leak_count": 8,
  "leak_rate": 8.0,
  "by_procedure": [
    {
      "procedure": "Anterior resection of rectum",
      "total_anastomoses": 45,
      "leak_count": 5,
      "leak_rate": 11.1
    },
    {
      "procedure": "Right hemicolectomy",
      "total_anastomoses": 55,
      "leak_count": 3,
      "leak_rate": 5.45
    }
  ],
  "generated_at": "2025-12-23T10:00:00"
}
```

### NBOCA Conversion Rates
```http
GET /api/reports/nboca/conversion-rates
```

**Response:**
```json
{
  "total_laparoscopic": 80,
  "conversion_count": 6,
  "conversion_rate": 7.5,
  "by_procedure": [
    {
      "procedure": "Laparoscopic anterior resection",
      "total_laparoscopic": 35,
      "conversion_count": 4,
      "conversion_rate": 11.43
    }
  ],
  "generated_at": "2025-12-23T10:00:00"
}
```

---

## Excel Export API

### Export Summary Report
```http
GET /api/reports/export/summary-excel
```

**Response**: Excel file download

### Export Surgeon Performance
```http
GET /api/reports/export/surgeon-performance-excel
```

**Response**: Excel file download

### Export Trends Report
```http
GET /api/reports/export/trends-excel?days=30
```

**Response**: Excel file download

### Export NBOCA Mortality Report
```http
GET /api/reports/export/nboca-mortality-excel
```

**Response**: Excel file download

### Export NBOCA Anastomotic Leak Report
```http
GET /api/reports/export/nboca-anastomotic-leak-excel
```

**Response**: Excel file download

---

## NBOCA Exports API

### Validate NBOCA Submission
```http
GET /api/admin/exports/nboca-validator
```

**Response:**
```json
{
  "summary": {
    "total_episodes": 150,
    "valid_episodes": 148,
    "episodes_with_errors": 2,
    "episodes_with_warnings": 5,
    "valid_percentage": 98.67,
    "submission_ready": false
  },
  "episodes": [
    {
      "episode_id": "EP123",
      "patient_nhs": "123 456 7890",
      "errors": [
        "Treatment 1: ASA score missing",
        "TNM staging incomplete"
      ],
      "warnings": [
        "Lymph node yield below 12 (only 10)"
      ]
    }
  ]
}
```

### Download NBOCA XML
```http
GET /api/admin/exports/nboca-xml
```

**Response**: XML file download (COSD v9/v10 format)

### Check Data Completeness
```http
GET /api/admin/exports/data-completeness
```

**Response:**
```json
{
  "total_episodes": 150,
  "patient": {
    "nhs_number": 150,
    "dob": 150,
    "gender": 150,
    "ethnicity": 145,
    "postcode": 148
  },
  "diagnosis": {
    "diagnosis_date": 150,
    "icd10_code": 148,
    "primary_site": 150
  },
  "tnm_staging": {
    "t_stage": 145,
    "n_stage": 145,
    "m_stage": 145,
    "tnm_version": 148
  },
  "percentages": {
    "patient": 98.0,
    "diagnosis": 98.2,
    "tnm_staging": 97.1,
    "pathology": 96.5,
    "surgery": 99.0
  },
  "generated_at": "2025-12-23T10:00:00"
}
```

---

## Admin API

### List Users
```http
GET /api/admin/users
```

**Requires**: Admin role

### Create User
```http
POST /api/admin/users
```

**Request Body:**
```json
{
  "username": "newuser",
  "password": "SecurePassword123!",
  "full_name": "New User",
  "role": "data_entry"
}
```

**Roles**: `admin`, `surgeon`, `data_entry`, `viewer`

### Update User
```http
PUT /api/admin/users/{username}
```

### Delete User
```http
DELETE /api/admin/users/{username}
```

### List Clinicians
```http
GET /api/admin/clinicians
```

### Create Clinician
```http
POST /api/admin/clinicians
```

**Request Body:**
```json
{
  "name": "Dr. Jane Smith",
  "gmc_number": "1234567",
  "speciality": "colorectal_surgery",
  "grade": "consultant"
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid NHS number format"
}
```

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden
```json
{
  "detail": "Not enough permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Patient REC001 not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "nhs_number"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limiting

- **Development**: No limits
- **Production**: 100 requests per minute per IP

## Pagination

Most list endpoints support pagination:
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 100, max: 1000)

---

**API Version**: 1.0.0  
**Last Updated**: December 23, 2025  
**Interactive Docs**: `/docs` (Swagger UI) or `/redoc` (ReDoc)
