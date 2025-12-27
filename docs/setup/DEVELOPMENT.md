# Development Guide

Complete guide for developers working on the Surgical Outcomes Database.

## Table of Contents

- [Development Environment](#development-environment)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Backend Development](#backend-development)
- [Frontend Development](#frontend-development)
- [Database Schema](#database-schema)
- [Testing](#testing)
- [Code Standards](#code-standards)
- [Git Workflow](#git-workflow)
- [Contributing](#contributing)

---

## Development Environment

### Prerequisites

- **Python**: 3.10 or higher
- **Node.js**: 18.x or higher
- **MongoDB**: 6.0 or higher
- **Git**: 2.x or higher
- **VS Code** (recommended) with extensions:
  - Python
  - Pylance
  - ESLint
  - Prettier
  - MongoDB for VS Code

### Initial Setup

```bash
# Clone repository
git clone https://github.com/yourusername/surgical-outcomes-db.git
cd surgical-outcomes-db

# Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your settings

# Initialize database
python execution/init_database.py

# Frontend setup
cd ../frontend
npm install

# Create .env file
cp .env.example .env
# Edit .env with your settings
```

### Running Development Servers

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 3 - MongoDB:**
```bash
mongod --dbpath ~/data/db
# Or if using system service: sudo systemctl start mongod
```

Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Architecture Overview

### Technology Stack

**Frontend:**
- **React 18**: UI library
- **TypeScript**: Type-safe JavaScript
- **Vite**: Build tool and dev server
- **Tailwind CSS**: Utility-first styling
- **React Router**: Client-side routing

**Backend:**
- **FastAPI**: Modern async Python web framework
- **Pydantic**: Data validation using Python type annotations
- **Motor**: Async MongoDB driver
- **Python-JOSE**: JWT token handling
- **Passlib**: Password hashing with bcrypt

**Database:**
- **MongoDB**: NoSQL document database

### Design Patterns

**Backend:**
- **Repository Pattern**: Database access abstracted in models
- **Dependency Injection**: FastAPI's dependency system for auth
- **Service Layer**: Business logic in separate services (validators)
- **Router Pattern**: Endpoints organized by resource

**Frontend:**
- **Component-Based**: Reusable React components
- **Context API**: Global state (auth)
- **Custom Hooks**: Shared logic extraction
- **Service Layer**: API calls centralized in `services/api.ts`

---

## Project Structure

```
surgical-outcomes-db/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Configuration management
│   │   ├── database.py          # MongoDB connection
│   │   ├── auth.py              # JWT authentication
│   │   ├── models/              # Pydantic models
│   │   │   ├── patient.py       # Patient model
│   │   │   ├── episode.py       # Episode model
│   │   │   ├── treatment.py     # Treatment model
│   │   │   ├── surgery.py       # Surgery model
│   │   │   ├── surgeon.py       # Surgeon model
│   │   │   └── user.py          # User model
│   │   ├── routes/              # API endpoints
│   │   │   ├── auth.py          # Authentication routes
│   │   │   ├── patients.py      # Patient CRUD
│   │   │   ├── episodes_v2.py   # Episode CRUD
│   │   │   ├── reports.py       # Reports & analytics
│   │   │   ├── admin.py         # Admin functions
│   │   │   └── codes.py         # ICD-10/OPCS-4 validation
│   │   └── services/            # Business logic
│   │       ├── icd10_validator.py
│   │       └── opcs4_validator.py
│   ├── requirements.txt         # Python dependencies
│   └── tests/                   # Backend tests
├── frontend/
│   ├── src/
│   │   ├── main.tsx             # App entry point
│   │   ├── App.tsx              # Root component
│   │   ├── components/          # Reusable components
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Layout.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   ├── Toast.tsx
│   │   │   ├── CancerEpisodeForm.tsx
│   │   │   └── ...
│   │   ├── contexts/            # React contexts
│   │   │   └── AuthContext.tsx
│   │   ├── pages/               # Page components
│   │   │   ├── HomePage.tsx
│   │   │   ├── LoginPage.tsx
│   │   │   ├── PatientsPage.tsx
│   │   │   ├── EpisodesPage.tsx
│   │   │   ├── ReportsPage.tsx
│   │   │   └── AdminPage.tsx
│   │   └── services/            # API clients
│   │       └── api.ts           # API service functions
│   ├── package.json             # Node dependencies
│   ├── tsconfig.json            # TypeScript config
│   ├── vite.config.ts           # Vite config
│   ├── tailwind.config.js       # Tailwind config
│   └── tests/                   # Frontend tests
├── execution/                   # Utility scripts
│   ├── init_database.py
│   ├── create_admin_user.py
│   └── start_backend.sh
├── directives/                  # Documentation
│   ├── cancer_episode_system.md
│   └── surg_db_app.md
└── docs/                        # Additional documentation
```

---

## Backend Development

### Creating a New Model

Models are Pydantic classes that define data structure and validation.

**Example: Create a `Complication` model**

```python
# backend/app/models/complication.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class Complication(BaseModel):
    """Surgical complication tracking."""
    
    episode_id: str = Field(..., description="Related episode ID")
    complication_type: str = Field(..., description="Type of complication")
    clavien_dindo_grade: int = Field(..., ge=1, le=5, description="Severity grade 1-5")
    detected_date: datetime = Field(..., description="When complication detected")
    intervention: Optional[str] = Field(None, description="Intervention performed")
    resolved: bool = Field(default=False, description="Is resolved")
    
    class Config:
        json_schema_extra = {
            "example": {
                "episode_id": "EP001",
                "complication_type": "anastomotic_leak",
                "clavien_dindo_grade": 3,
                "detected_date": "2025-01-20T10:00:00",
                "intervention": "Return to theatre for repair",
                "resolved": True
            }
        }
```

### Creating API Routes

Routes define HTTP endpoints for your API.

**Example: Create complications routes**

```python
# backend/app/routes/complications.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from ..models.complication import Complication
from ..database import get_database
from ..auth import get_current_user

router = APIRouter(prefix="/api/complications", tags=["complications"])

@router.post("/", response_model=Complication, status_code=status.HTTP_201_CREATED)
async def create_complication(
    complication: Complication,
    db = Depends(get_database),
    current_user = Depends(get_current_user)
):
    """Create a new complication record."""
    result = await db.complications.insert_one(complication.model_dump())
    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to create complication")
    return complication

@router.get("/episode/{episode_id}", response_model=List[Complication])
async def get_complications_by_episode(
    episode_id: str,
    db = Depends(get_database),
    current_user = Depends(get_current_user)
):
    """Get all complications for an episode."""
    complications = await db.complications.find({"episode_id": episode_id}).to_list(100)
    return complications
```

**Register router in main.py:**

```python
# backend/app/main.py
from app.routes import complications

app.include_router(complications.router)
```

### Database Operations

**Using Motor (async MongoDB driver):**

```python
# Insert
result = await db.collection.insert_one(document)
inserted_id = result.inserted_id

# Find one
document = await db.collection.find_one({"_id": id})

# Find many
cursor = db.collection.find({"field": "value"})
documents = await cursor.to_list(length=100)

# Update
result = await db.collection.update_one(
    {"_id": id},
    {"$set": {"field": "new_value"}}
)

# Delete
result = await db.collection.delete_one({"_id": id})

# Aggregation
pipeline = [
    {"$match": {"status": "active"}},
    {"$group": {"_id": "$category", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
]
results = await db.collection.aggregate(pipeline).to_list(None)
```

### Authentication & Authorization

**Protect endpoints with authentication:**

```python
from app.auth import get_current_user, require_role

# Requires authentication
@router.get("/protected")
async def protected_endpoint(current_user = Depends(get_current_user)):
    return {"message": f"Hello {current_user['username']}"}

# Requires specific role
@router.delete("/admin-only")
async def admin_endpoint(current_user = Depends(require_role("admin"))):
    return {"message": "Admin access granted"}
```

### Field Validation

**Using Pydantic validators:**

```python
from pydantic import BaseModel, field_validator, Field

class Patient(BaseModel):
    nhs_number: str = Field(..., pattern=r"^\d{3} \d{3} \d{4}$")
    age: int = Field(..., ge=0, le=150)
    
    @field_validator('nhs_number')
    @classmethod
    def validate_nhs_number(cls, v: str) -> str:
        """Validate NHS number format and checksum."""
        digits = v.replace(" ", "")
        if len(digits) != 10:
            raise ValueError("NHS number must be 10 digits")
        
        # Verify checksum (simplified)
        weights = [10, 9, 8, 7, 6, 5, 4, 3, 2]
        total = sum(int(digit) * weight for digit, weight in zip(digits[:9], weights))
        checksum = (11 - (total % 11)) % 11
        
        if int(digits[9]) != checksum:
            raise ValueError("Invalid NHS number checksum")
        
        return v
```

### Error Handling

```python
from fastapi import HTTPException, status

# 404 Not Found
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Patient REC001 not found"
)

# 400 Bad Request
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Invalid NHS number format"
)

# 403 Forbidden
raise HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Not enough permissions"
)
```

---

## Frontend Development

### Creating Components

**Functional component with TypeScript:**

```typescript
// src/components/ComplicationCard.tsx
import React from 'react';
import { Card } from './Card';

interface ComplicationCardProps {
  complicationType: string;
  grade: number;
  detectedDate: string;
  resolved: boolean;
}

export const ComplicationCard: React.FC<ComplicationCardProps> = ({
  complicationType,
  grade,
  detectedDate,
  resolved
}) => {
  return (
    <Card>
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-semibold text-lg capitalize">
            {complicationType.replace('_', ' ')}
          </h3>
          <p className="text-sm text-gray-600">
            Grade {grade} | {new Date(detectedDate).toLocaleDateString()}
          </p>
        </div>
        <span className={`px-2 py-1 rounded text-sm ${
          resolved ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
        }`}>
          {resolved ? 'Resolved' : 'Active'}
        </span>
      </div>
    </Card>
  );
};
```

### Making API Calls

**Add API functions to `services/api.ts`:**

```typescript
// src/services/api.ts

export const getComplications = async (episodeId: string) => {
  const response = await fetch(`${API_BASE_URL}/api/complications/episode/${episodeId}`, {
    headers: {
      'Authorization': `Bearer ${getToken()}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch complications');
  }
  
  return response.json();
};

export const createComplication = async (complication: any) => {
  const response = await fetch(`${API_BASE_URL}/api/complications`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getToken()}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(complication)
  });
  
  if (!response.ok) {
    throw new Error('Failed to create complication');
  }
  
  return response.json();
};
```

### State Management

**Using React hooks:**

```typescript
import { useState, useEffect } from 'react';
import { getComplications } from '../services/api';

export const ComplicationsPage = () => {
  const [complications, setComplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await getComplications('EP001');
        setComplications(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);
  
  if (loading) return <LoadingSpinner />;
  if (error) return <div>Error: {error}</div>;
  
  return (
    <div>
      {complications.map(comp => (
        <ComplicationCard key={comp.id} {...comp} />
      ))}
    </div>
  );
};
```

### Styling with Tailwind

**Common patterns:**

```tsx
// Container
<div className="container mx-auto px-4 py-8">

// Card
<div className="bg-white rounded-lg shadow p-6">

// Button (primary)
<button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded">

// Button (secondary)
<button className="bg-gray-200 hover:bg-gray-300 text-gray-800 px-4 py-2 rounded">

// Input
<input className="border border-gray-300 rounded px-3 py-2 w-full focus:ring-2 focus:ring-blue-500 focus:border-transparent">

// Badge
<span className="bg-green-100 text-green-800 px-2 py-1 rounded text-sm">

// Grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
```

---

## Database Schema

### Collections

**patients:**
```javascript
{
  _id: ObjectId,
  record_number: String (unique),
  nhs_number: String (unique),
  demographics: {
    date_of_birth: Date,
    age: Number,
    gender: String,
    ethnicity: String,
    postcode: String,
    bmi: Number,
    weight_kg: Number,
    height_cm: Number
  },
  medical_history: {
    conditions: [String],
    medications: [String],
    allergies: [String],
    smoking_status: String,
    alcohol_use: String
  },
  created_at: Date,
  updated_at: Date
}
```

**episodes:**
```javascript
{
  _id: ObjectId,
  episode_id: String (unique),
  patient_id: String (ref: patients.record_number),
  diagnosis_date: Date,
  primary_site: String,  // ICD-10 code
  tnm_staging: {
    t_stage: String,
    n_stage: String,
    m_stage: String,
    tnm_version: String
  },
  mdt_date: Date,
  mdt_outcome: String,
  performance_status: Number,
  created_at: Date,
  updated_at: Date
}
```

**treatments:**
```javascript
{
  _id: ObjectId,
  episode_id: String (ref: episodes.episode_id),
  treatment_type: String,  // surgery, chemotherapy, radiotherapy
  date: Date,
  procedure_code: String,  // OPCS-4 for surgery
  surgeon_name: String,
  urgency: String,
  approach: String,
  duration_minutes: Number,
  complications: [String],
  outcome: String,
  created_at: Date,
  updated_at: Date
}
```

### Indexes

**Essential indexes for performance:**

```javascript
// Patients
db.patients.createIndex({ "record_number": 1 }, { unique: true })
db.patients.createIndex({ "nhs_number": 1 }, { unique: true })
db.patients.createIndex({ "demographics.postcode": 1 })

// Episodes
db.episodes.createIndex({ "episode_id": 1 }, { unique: true })
db.episodes.createIndex({ "patient_id": 1 })
db.episodes.createIndex({ "diagnosis_date": -1 })
db.episodes.createIndex({ "primary_site": 1 })

// Treatments
db.treatments.createIndex({ "episode_id": 1 })
db.treatments.createIndex({ "date": -1 })
db.treatments.createIndex({ "surgeon_name": 1 })
db.treatments.createIndex({ "procedure_code": 1 })
```

**Create indexes script:**
```bash
python execution/create_indexes.py
```

---

## Testing

### Backend Testing

**Install pytest:**
```bash
pip install pytest pytest-asyncio httpx
```

**Example test:**

```python
# backend/tests/test_patients.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_patient():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/patients", json={
            "record_number": "TEST001",
            "nhs_number": "123 456 7890",
            "demographics": {
                "date_of_birth": "1960-01-15",
                "gender": "male"
            }
        }, headers={"Authorization": "Bearer test_token"})
        
        assert response.status_code == 201
        data = response.json()
        assert data["record_number"] == "TEST001"

@pytest.mark.asyncio
async def test_get_patient():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/patients/TEST001",
            headers={"Authorization": "Bearer test_token"})
        
        assert response.status_code == 200
        data = response.json()
        assert "record_number" in data
```

**Run tests:**
```bash
cd backend
pytest
pytest -v  # Verbose
pytest tests/test_patients.py  # Specific file
```

### Frontend Testing

**Install testing libraries:**
```bash
npm install --save-dev @testing-library/react @testing-library/jest-dom vitest
```

**Example test:**

```typescript
// frontend/src/components/__tests__/Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '../Button';
import { describe, it, expect, vi } from 'vitest';

describe('Button', () => {
  it('renders with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });
  
  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    
    fireEvent.click(screen.getByText('Click me'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
  
  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Click me</Button>);
    expect(screen.getByText('Click me')).toBeDisabled();
  });
});
```

**Run tests:**
```bash
cd frontend
npm test
npm run test:ui  # Interactive UI
npm run coverage  # Coverage report
```

---

## Code Standards

### Python (Backend)

**Follow PEP 8:**
- 4 spaces for indentation
- Max line length: 100 characters
- Snake_case for functions and variables
- PascalCase for classes

**Type hints:**
```python
def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 1)
```

**Docstrings:**
```python
def get_patient(record_number: str) -> dict:
    """
    Retrieve patient by record number.
    
    Args:
        record_number: Unique hospital record identifier
        
    Returns:
        Patient document with demographics and medical history
        
    Raises:
        HTTPException: If patient not found (404)
    """
    pass
```

**Use Black for formatting:**
```bash
pip install black
black backend/app/
```

### TypeScript (Frontend)

**Follow ESLint rules:**
- 2 spaces for indentation
- Use semicolons
- Single quotes for strings
- PascalCase for components
- camelCase for functions

**Type everything:**
```typescript
interface Patient {
  recordNumber: string;
  nhsNumber: string;
  demographics: Demographics;
}

const getPatient = async (recordNumber: string): Promise<Patient> => {
  // ...
};
```

**Use Prettier for formatting:**
```bash
npm install --save-dev prettier
npm run format
```

---

## Git Workflow

### Branch Naming

- **feature/**: New features (`feature/add-complications-tracking`)
- **fix/**: Bug fixes (`fix/bmi-calculation`)
- **docs/**: Documentation (`docs/api-reference`)
- **refactor/**: Code refactoring (`refactor/patient-model`)
- **test/**: Adding tests (`test/patient-crud`)

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add complication tracking to episodes
fix: correct BMI calculation for edge cases
docs: update API documentation for new endpoints
refactor: extract validation logic to service layer
test: add unit tests for ICD-10 validator
```

### Development Workflow

1. **Create feature branch:**
   ```bash
   git checkout -b feature/add-complications
   ```

2. **Make changes and commit:**
   ```bash
   git add .
   git commit -m "feat: add complication model and routes"
   ```

3. **Keep branch updated:**
   ```bash
   git checkout main
   git pull origin main
   git checkout feature/add-complications
   git rebase main
   ```

4. **Push and create PR:**
   ```bash
   git push origin feature/add-complications
   # Create pull request on GitHub
   ```

5. **After PR approval:**
   ```bash
   git checkout main
   git pull origin main
   git branch -d feature/add-complications
   ```

---

## Contributing

### Getting Started

1. Fork the repository
2. Clone your fork
3. Create a feature branch
4. Make your changes
5. Write/update tests
6. Update documentation
7. Submit pull request

### Pull Request Checklist

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Commit messages follow conventions
- [ ] No merge conflicts with main

### Code Review Process

1. Automated checks (linting, tests)
2. Peer review (1-2 reviewers)
3. Address feedback
4. Approval and merge

---

## Useful Commands

### Backend
```bash
# Run dev server
uvicorn app.main:app --reload

# Run tests
pytest

# Format code
black app/

# Type checking
mypy app/

# Create migration
python execution/create_migration.py

# Reset database
python execution/init_database.py --reset
```

### Frontend
```bash
# Run dev server
npm run dev

# Build for production
npm run build

# Run tests
npm test

# Format code
npm run format

# Lint code
npm run lint

# Type check
npm run type-check
```

### Database
```bash
# Connect to MongoDB
mongosh

# Export data
mongodump --db surgical_outcomes --out backup/

# Import data
mongorestore --db surgical_outcomes backup/surgical_outcomes/

# Create indexes
python execution/create_indexes.py
```

---

**Version**: 1.0.0  
**Last Updated**: December 23, 2025  
**For**: Software Developers, DevOps Engineers
