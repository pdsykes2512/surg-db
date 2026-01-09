# Code Style Guide

Comprehensive coding standards and best practices for the IMPACT application.

## Table of Contents
1. [General Principles](#general-principles)
2. [Python Backend](#python-backend)
3. [TypeScript Frontend](#typescript-frontend)
4. [Database Patterns](#database-patterns)
5. [API Design](#api-design)
6. [Security Standards](#security-standards)
7. [Documentation Standards](#documentation-standards)
8. [Testing Standards](#testing-standards)

---

## General Principles

### Code Philosophy
- **Readability First** - Code is read more than written
- **Explicit over Implicit** - Clear is better than clever
- **DRY** - Don't Repeat Yourself (extract common patterns)
- **YAGNI** - You Aren't Gonna Need It (don't over-engineer)
- **Fail Fast** - Validate early, catch errors immediately
- **Security by Design** - Consider security at every level

### File Organization
```
backend/
├── app/
│   ├── routes/      # API endpoints
│   ├── models/      # Pydantic models
│   ├── utils/       # Utility functions
│   ├── auth.py      # Authentication
│   ├── database.py  # DB connection
│   └── main.py      # FastAPI app

frontend/
├── src/
│   ├── components/  # React components
│   │   ├── common/
│   │   ├── modals/
│   │   ├── forms/
│   │   └── layout/
│   ├── services/    # API client
│   ├── hooks/       # Custom hooks
│   ├── utils/       # Utilities
│   └── types/       # TypeScript types
```

---

## Python Backend

### Naming Conventions

#### Variables and Functions
```python
# snake_case for variables and functions
patient_id = "ABC123"
episode_count = 42

def get_patient_by_id(patient_id: str) -> dict:
    """Fetch patient from database"""
    pass

async def create_episode(episode_data: dict) -> Episode:
    """Create new episode asynchronously"""
    pass
```

#### Classes
```python
# PascalCase for classes
class PatientService:
    """Service for patient operations"""
    pass

class EpisodeRepository:
    """Database operations for episodes"""
    pass
```

#### Constants
```python
# UPPERCASE for constants
MAX_SEARCH_RESULTS = 100
DEFAULT_PAGINATION_LIMIT = 50
ENCRYPTION_PREFIX = 'ENC:'
```

#### Private Members
```python
# Leading underscore for private/internal
class Service:
    def __init__(self):
        self._internal_state = {}
    
    def _internal_method(self):
        """Not part of public API"""
        pass
```

### Import Organization
Organize imports in three groups with blank lines:

```python
"""Module docstring"""

# Standard library
import logging
import re
from datetime import datetime
from typing import List, Optional, Dict, Any

# Third-party
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

# Local application
from ..auth import get_current_user, require_admin
from ..database import get_collection
from ..models.patient import Patient, PatientCreate
from ..utils.encryption import encrypt_document

# Module-level setup
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/patients")
```

### Type Hints
Always use type hints for function signatures:

```python
from typing import List, Optional, Dict, Any

def get_patient(patient_id: str) -> Optional[dict]:
    """Return None if not found"""
    pass

async def list_patients(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None
) -> List[Patient]:
    """Explicit return type"""
    pass

def process_data(
    data: Dict[str, Any],
    options: Optional[Dict[str, bool]] = None
) -> tuple[bool, str]:
    """Return tuple of success flag and message"""
    return True, "Success"
```

### Docstrings
Use Google-style docstrings for all public functions:

```python
def calculate_mortality_flags(
    treatment_date: datetime,
    deceased_date: Optional[datetime],
    deceased_location: Optional[str]
) -> dict:
    """Calculate mortality outcome flags from treatment and death dates.
    
    Determines if patient died within 30 or 90 days of treatment, and
    whether death occurred in hospital or community. Used for NBOCA outcome
    reporting and surgeon performance metrics.
    
    Args:
        treatment_date: Date of primary treatment/surgery
        deceased_date: Date of death, None if patient alive
        deceased_location: Where death occurred ('hospital' or 'community')
    
    Returns:
        dict: Mortality flags with keys:
            - mortality_30d: bool, died within 30 days
            - mortality_30d_hospital: bool, died in hospital within 30 days
            - mortality_30d_community: bool, died in community within 30 days
            - mortality_90d: bool, died within 90 days
            - mortality_90d_hospital: bool, died in hospital within 90 days
            - mortality_90d_community: bool, died in community within 90 days
    
    Raises:
        ValueError: If deceased_date is before treatment_date
        TypeError: If dates are not datetime objects
    
    Example:
        >>> treatment = datetime(2024, 1, 1)
        >>> death = datetime(2024, 1, 20)
        >>> flags = calculate_mortality_flags(treatment, death, 'hospital')
        >>> flags['mortality_30d']
        True
        >>> flags['mortality_30d_hospital']
        True
    
    Note:
        Days are calculated as calendar days, not 24-hour periods.
        If deceased_date is None, all flags return False.
    """
    if deceased_date is None:
        return {
            "mortality_30d": False,
            "mortality_30d_hospital": False,
            # ...
        }
    
    days_to_death = (deceased_date - treatment_date).days
    # Implementation...
```

### Error Handling
Consistent error handling pattern:

```python
import logging
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

@router.post("/")
async def create_resource(data: ResourceCreate):
    """Create new resource with comprehensive error handling"""
    try:
        # Validate business rules
        if not data.required_field:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Required field is missing"
            )
        
        # Database operations
        result = await collection.insert_one(data.model_dump())
        
        # Return success
        return {"id": str(result.inserted_id)}
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as e:
        # Log unexpected errors with full stack trace
        logger.error(f"Error creating resource: {str(e)}", exc_info=True)
        # Return generic 500 error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create resource: {str(e)}"
        )
```

### Async/Await
FastAPI routes should always be async:

```python
# Good: Async route with await
@router.get("/")
async def list_patients() -> List[Patient]:
    collection = await get_patients_collection()
    patients = await collection.find().to_list(length=100)
    return patients

# Bad: Sync route blocks event loop
@router.get("/")
def list_patients() -> List[Patient]:
    collection = get_patients_collection()  # Blocks!
    patients = collection.find().to_list(length=100)
    return patients
```

### Logging
Use structured logging with appropriate levels:

```python
import logging

logger = logging.getLogger(__name__)

# DEBUG: Detailed diagnostic information
logger.debug(f"Searching patients with query: {query}")

# INFO: General informational messages
logger.info(f"Created patient {patient_id}")

# WARNING: Something unexpected but handled
logger.warning(f"Patient {patient_id} has no episodes")

# ERROR: Error occurred but application continues
logger.error(f"Failed to load patient {patient_id}: {str(e)}", exc_info=True)

# CRITICAL: Severe error, application may not continue
logger.critical(f"Database connection lost")
```

---

## TypeScript Frontend

### Naming Conventions

```typescript
// PascalCase for components and types
export function PatientModal() {}
interface PatientFormData {}

// camelCase for variables and functions
const patientId = "ABC123"
const fetchPatients = async () => {}

// UPPERCASE for constants
const MAX_RESULTS = 100
const API_BASE_URL = "/api"

// Boolean prefixes: is, has, should, can
const isLoading = true
const hasError = false
const shouldShowModal = true
const canEdit = true
```

### TypeScript Interfaces
Define explicit interfaces for all component props and data structures:

```typescript
/**
 * Props for the PatientModal component
 */
interface PatientModalProps {
  /** Existing patient data for edit mode, null for create */
  patient?: Patient | null;
  /** Callback when modal is closed */
  onClose: () => void;
  /** Callback when form is submitted with patient data */
  onSubmit: (data: PatientFormData) => void;
  /** Optional callback for delete action */
  onDelete?: (patient: Patient) => void;
  /** Whether form is currently submitting */
  loading?: boolean;
}

/**
 * Patient data structure from API
 */
interface Patient {
  _id: string;
  patient_id: string;
  mrn?: string;
  nhs_number?: string;
  demographics: Demographics;
  medical_history?: MedicalHistory;
  created_at: string;
  updated_at: string;
}

/**
 * Form data for creating/updating patient
 * Subset of Patient without _id and timestamps
 */
interface PatientFormData {
  patient_id: string;
  mrn?: string;
  nhs_number?: string;
  demographics: Demographics;
  medical_history: MedicalHistory;
}
```

### React Components
Component structure and patterns:

```typescript
import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'

/**
 * PatientModal - Create or edit patient records
 * 
 * Modal dialog for entering patient demographics and medical history.
 * Supports both create mode (no patient prop) and edit mode (patient provided).
 * 
 * @example
 * ```tsx
 * // Create new patient
 * <PatientModal
 *   onClose={() => setShowModal(false)}
 *   onSubmit={handleCreatePatient}
 * />
 * 
 * // Edit existing patient
 * <PatientModal
 *   patient={selectedPatient}
 *   onClose={() => setShowModal(false)}
 *   onSubmit={handleUpdatePatient}
 *   onDelete={handleDeletePatient}
 * />
 * ```
 */
export function PatientModal({
  patient,
  onClose,
  onSubmit,
  onDelete,
  loading = false
}: PatientModalProps) {
  // State declarations at top
  const [formData, setFormData] = useState<PatientFormData>(initialData)
  const [error, setError] = useState<string>('')
  const [isLoading, setIsLoading] = useState(false)
  
  // Effects after state
  useEffect(() => {
    if (patient) {
      // Populate form with patient data in edit mode
      setFormData(mapPatientToFormData(patient))
    }
  }, [patient])
  
  // Event handlers
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validate
    if (!validateFormData(formData)) {
      setError('Please fill required fields')
      return
    }
    
    // Clear error and submit
    setError('')
    onSubmit(formData)
  }
  
  // Render
  return createPortal(
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Modal content */}
      </div>
    </div>,
    document.body
  )
}
```

### Custom Hooks
Extract reusable logic into custom hooks:

```typescript
/**
 * usePatients - Fetch and manage patient list
 * 
 * Custom hook for loading patient data with search, pagination, and refresh.
 * 
 * @param {string} search - Optional search term
 * @param {number} limit - Number of results per page
 * @returns {Object} Patient data and methods
 * 
 * @example
 * ```tsx
 * const { patients, isLoading, error, refetch } = usePatients('John', 50)
 * 
 * if (isLoading) return <LoadingSpinner />
 * if (error) return <ErrorMessage message={error} />
 * return <PatientList patients={patients} onRefresh={refetch} />
 * ```
 */
export function usePatients(search?: string, limit: number = 50) {
  const [patients, setPatients] = useState<Patient[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  const fetchPatients = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const { data } = await apiService.patients.list({ search, limit })
      setPatients(data)
    } catch (err) {
      console.error('Error fetching patients:', err)
      setError('Failed to load patients')
    } finally {
      setIsLoading(false)
    }
  }
  
  useEffect(() => {
    fetchPatients()
  }, [search, limit])
  
  return { patients, isLoading, error, refetch: fetchPatients }
}
```

### JSDoc Comments
Add JSDoc for all exported functions:

```typescript
/**
 * Format NHS number with spaces for display
 * 
 * Converts 10-digit NHS number to readable format: XXX XXX XXXX
 * Handles various input formats and validates length.
 * 
 * @param {string} nhs - NHS number (10 digits, with or without spaces)
 * @returns {string} Formatted NHS number or empty string if invalid
 * 
 * @example
 * ```typescript
 * formatNHSNumber('1234567890')  // '123 456 7890'
 * formatNHSNumber('123 456 7890')  // '123 456 7890'
 * formatNHSNumber('123')  // '' (invalid length)
 * ```
 */
export function formatNHSNumber(nhs: string): string {
  if (!nhs) return ''
  
  // Remove existing spaces
  const digits = nhs.replace(/\s/g, '')
  
  // Validate length
  if (digits.length !== 10) return ''
  
  // Format as XXX XXX XXXX
  return `${digits.slice(0, 3)} ${digits.slice(3, 6)} ${digits.slice(6)}`
}
```

### Error Handling
Consistent error handling in async operations:

```typescript
const fetchData = async () => {
  try {
    setIsLoading(true)
    setError(null)
    
    const { data } = await apiService.resource.list()
    setData(data)
    
  } catch (err) {
    console.error('Error fetching data:', err)
    
    // Extract meaningful error message
    const message = err.response?.data?.detail || 'Failed to load data'
    setError(message)
    
  } finally {
    setIsLoading(false)
  }
}
```

---

## Database Patterns

### Collection Naming
- **Singular, lowercase** - `patients`, `episodes`, `treatments`
- **Descriptive** - Clear what data is stored
- **Consistent** - Follow same pattern across all collections

### Document Structure
```javascript
// Good: Flat structure with clear field names
{
  "patient_id": "ABC123",
  "mrn": "12345678",
  "demographics": {
    "date_of_birth": "1975-03-15",
    "gender": "male"
  },
  "created_at": ISODate("2024-01-01T00:00:00Z"),
  "updated_at": ISODate("2024-01-01T00:00:00Z")
}

// Bad: Deeply nested, unclear names
{
  "id": "ABC123",
  "data": {
    "personal": {
      "info": {
        "birth": "1975-03-15"
      }
    }
  }
}
```

### Indexes
Document all indexes in code comments:

```python
"""
Patient Collection Indexes:

Performance indexes:
- patient_id: Unique index for fast lookups
- mrn_hash: Index for encrypted MRN searches
- nhs_number_hash: Index for encrypted NHS number searches
- created_at: Index for time-range queries

Compound indexes:
- (patient_id, created_at): Composite for filtered sorting
"""

# Create indexes
await collection.create_index("patient_id", unique=True)
await collection.create_index("mrn_hash")
await collection.create_index([("patient_id", 1), ("created_at", -1)])
```

### Query Patterns
```python
# Good: Use indexes, specific fields
patients = await collection.find(
    {"patient_id": {"$in": patient_ids}},
    {"patient_id": 1, "demographics": 1, "_id": 0}
).to_list(length=None)

# Bad: Full table scan, return all fields
patients = await collection.find({}).to_list(length=None)
```

---

## API Design

### REST Conventions
Follow REST principles for all endpoints:

```
GET    /api/patients/           List patients (with pagination)
POST   /api/patients/           Create patient
GET    /api/patients/{id}       Get single patient
PUT    /api/patients/{id}       Update patient
DELETE /api/patients/{id}       Delete patient

GET    /api/patients/count      Count patients (special endpoint)
GET    /api/patients/{id}/episodes  Nested resource access
```

### Status Codes
Use appropriate HTTP status codes:

- **200 OK** - Successful GET/PUT request
- **201 Created** - Successful POST request
- **204 No Content** - Successful DELETE request
- **400 Bad Request** - Invalid input data
- **401 Unauthorized** - Missing/invalid auth token
- **403 Forbidden** - Insufficient permissions
- **404 Not Found** - Resource doesn't exist
- **409 Conflict** - Resource conflict (duplicate)
- **500 Internal Server Error** - Server-side error

### Request/Response Format
```javascript
// POST /api/patients/ - Create patient
Request:
{
  "patient_id": "ABC123",
  "mrn": "12345678",
  "demographics": {
    "date_of_birth": "1975-03-15",
    "gender": "male"
  }
}

Response (201 Created):
{
  "_id": "507f1f77bcf86cd799439011",
  "patient_id": "ABC123",
  "mrn": "12345678",
  "demographics": {
    "date_of_birth": "1975-03-15",
    "gender": "male"
  },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}

// Error Response (400 Bad Request)
{
  "detail": "Patient with MRN 12345678 already exists"
}
```

---

## Security Standards

### Authentication
- All routes require JWT authentication
- Token stored in localStorage on client
- Token sent in Authorization header
- Token expiry enforced (24 hours)

### Authorization
Role-based access control (RBAC):

```python
from ..auth import require_admin, require_data_entry_or_higher

@router.post("/")
async def create_resource(
    data: ResourceCreate,
    current_user: dict = Depends(require_data_entry_or_higher)
):
    """Requires data_entry, clinician, or admin role"""
    pass

@router.delete("/{id}")
async def delete_resource(
    id: str,
    current_user: dict = Depends(require_admin)
):
    """Requires admin role"""
    pass
```

### Data Encryption
Encrypt all sensitive patient identifiers:

```python
from ..utils.encryption import encrypt_document, decrypt_document

# Before storing
encrypted_data = encrypt_document(patient_data)
await collection.insert_one(encrypted_data)

# After retrieving
patient = await collection.find_one({"patient_id": id})
decrypted = decrypt_document(patient)
return Patient(**decrypted)
```

Encrypted fields:
- NHS number
- MRN
- Date of birth
- Postcode
- First/last names
- Deceased date

### Input Validation
- Use Pydantic models for all API inputs
- Sanitize search inputs to prevent NoSQL injection
- Validate formats (NHS number, postcodes, dates)
- Check business rules (MRN uniqueness)

---

## Documentation Standards

### Code Comments
Use comments sparingly, only for complex logic:

```python
# Good: Explains WHY, not WHAT
# Use hash-based lookup instead of full table scan
# for O(log n) performance on encrypted fields
query = create_searchable_query('mrn', search_term)

# Bad: States the obvious
# Increment counter by 1
counter += 1
```

### Module Docstrings
Every Python file should start with a module docstring:

```python
"""
Patient API Routes

Provides RESTful endpoints for managing patient records with field-level
encryption for sensitive data (NHS number, MRN, DOB).

Endpoints:
    POST   /api/patients/ - Create patient
    GET    /api/patients/ - List patients
    GET    /api/patients/{id} - Get patient
    PUT    /api/patients/{id} - Update patient
    DELETE /api/patients/{id} - Delete patient (admin)

Security:
    - All endpoints require authentication
    - Create/update/delete require data_entry role or higher
    - Delete requires admin role
    - Sensitive fields encrypted with AES-256

See Also:
    - models/patient.py: Patient data models
    - utils/encryption.py: Field encryption utilities
"""
```

### README Files
Every major directory should have a README.md:
- Purpose of directory
- File descriptions
- Common patterns
- Usage examples
- Best practices

---

## Testing Standards

### Unit Tests
Test individual functions in isolation:

```python
import pytest
from app.utils.encryption import encrypt_field, decrypt_field

def test_encrypt_decrypt_roundtrip():
    """Test encryption/decryption preserves data"""
    original = "1234567890"
    encrypted = encrypt_field('nhs_number', original)
    decrypted = decrypt_field('nhs_number', encrypted)
    assert decrypted == original

def test_encrypt_different_values():
    """Test same value encrypted differently each time"""
    value = "1234567890"
    encrypted1 = encrypt_field('nhs_number', value)
    encrypted2 = encrypt_field('nhs_number', value)
    assert encrypted1 != encrypted2  # Different due to random IV
```

### Integration Tests
Test API endpoints with test database:

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_patient():
    """Test patient creation via API"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/patients/",
            json={
                "patient_id": "TEST01",
                "mrn": "12345678",
                "demographics": {
                    "date_of_birth": "1975-03-15",
                    "gender": "male"
                }
            },
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["patient_id"] == "TEST01"
```

### Test Organization
```
tests/
├── unit/
│   ├── test_encryption.py
│   ├── test_serializers.py
│   └── test_formatters.py
├── integration/
│   ├── test_patients_api.py
│   ├── test_episodes_api.py
│   └── test_auth.py
└── conftest.py  # Shared fixtures
```

---

## Code Review Checklist

Before submitting code for review:

- [ ] All functions have type hints
- [ ] All public functions have docstrings
- [ ] Complex logic has inline comments explaining WHY
- [ ] Error handling follows standard pattern
- [ ] Security: Sensitive data encrypted
- [ ] Security: User inputs validated/sanitized
- [ ] Security: Authentication/authorization enforced
- [ ] Tests: Unit tests for new functions
- [ ] Tests: Integration tests for new endpoints
- [ ] Documentation: README updated if needed
- [ ] Formatting: Code follows style guide
- [ ] Linting: No linter warnings
- [ ] Performance: No obvious inefficiencies
- [ ] Accessibility: Frontend meets WCAG 2.1 AA
- [ ] Responsive: Mobile layouts tested

---

## Tools and Configuration

### Python
- **Black** - Code formatter (line length: 100)
- **Pylint** - Linter
- **mypy** - Type checker
- **pytest** - Testing framework

### TypeScript
- **Prettier** - Code formatter
- **ESLint** - Linter
- **TypeScript** - Type checking

### Git
- **Conventional Commits** - Commit message format
  - `feat:` - New feature
  - `fix:` - Bug fix
  - `docs:` - Documentation only
  - `style:` - Formatting, semicolons, etc
  - `refactor:` - Code restructuring
  - `test:` - Adding tests
  - `chore:` - Build process, dependencies

Example: `feat: add patient search by NHS number`

---

## Questions?

For questions about this style guide or code standards:
1. Check existing code for examples
2. Ask in team discussions
3. Refer to official documentation:
   - Python: [PEP 8](https://www.python.org/dev/peps/pep-0008/)
   - TypeScript: [TypeScript Handbook](https://www.typescriptlang.org/docs/)
   - React: [React Docs](https://react.dev/)
