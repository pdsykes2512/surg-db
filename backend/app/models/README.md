# Pydantic Models

This directory contains Pydantic v2 data models for the IMPACT application.

## Purpose

Pydantic models provide:
- **Type validation** - Automatic validation of all input/output data
- **Serialization** - Convert between Python objects and JSON/dict
- **Documentation** - Self-documenting schemas for API endpoints
- **IDE support** - Type hints for better development experience

## Model Files

### Core Domain Models
- **`patient.py`** - Patient demographics and medical history
- **`episode.py`** - Cancer care episode with staging and referral data
- **`tumour.py`** - Tumour characteristics and TNM staging
- **`treatment.py`** - Treatment records (surgery, chemo, radio, other)
- **`investigation.py`** - Diagnostic investigations and results
- **`surveillance.py`** - Follow-up appointments and surveillance

### Supporting Models
- **`clinician.py`** - Healthcare professional records
- **`user.py`** - System user accounts with role-based access
- **`audit_log.py`** - Audit trail for compliance

### Special-Purpose Models
- **`surgery.py`** - Detailed surgical procedure model (legacy)
- **`utils.py`** - Shared model utilities and base classes

## Model Structure

### Base Model Pattern
```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ResourceBase(BaseModel):
    """Base fields shared by create and response models"""
    field_name: str = Field(..., description="Field description")
    optional_field: Optional[str] = None

class ResourceCreate(ResourceBase):
    """Model for creating new resource (no _id, timestamps)"""
    pass

class ResourceUpdate(BaseModel):
    """Model for updates (all fields optional)"""
    field_name: Optional[str] = None

class Resource(ResourceBase):
    """Full model with _id and timestamps for responses"""
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(populate_by_name=True)
```

### Key Patterns

#### Field Validation
```python
from pydantic import field_validator, Field

class Patient(BaseModel):
    age: int = Field(..., ge=0, le=150)  # Range validation
    nhs_number: Optional[str] = None
    
    @field_validator('nhs_number')
    @classmethod
    def validate_nhs_number(cls, v):
        """Custom validation logic"""
        if v and len(v.replace(' ', '')) != 10:
            raise ValueError('NHS number must be 10 digits')
        return v
```

#### Nested Models
```python
class Demographics(BaseModel):
    """Nested demographics model"""
    date_of_birth: str
    gender: str
    postcode: Optional[str] = None

class Patient(BaseModel):
    """Patient with nested demographics"""
    patient_id: str
    demographics: Demographics  # Nested validation
```

#### ObjectId Handling
```python
from bson import ObjectId

class PyObjectId(str):
    """Custom type for MongoDB ObjectId"""
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        # Validation logic
        pass

class Resource(BaseModel):
    id: PyObjectId = Field(alias="_id")
```

## Field Documentation

All fields should include:
- **Type annotation** - Explicit type for validation
- **Description** - Clear explanation of field purpose
- **Constraints** - Range limits, patterns, etc.
- **Optional/Required** - Clear indication via Optional[] or default values

Example:
```python
mrn: Optional[str] = Field(
    None, 
    description="Medical Record Number: 8 digits or IW+6 digits",
    pattern=r"^(IW\d{6}|\d{8,})$"
)
```

## Validation Rules

### Required vs Optional
- **Required** - No default value: `field: str`
- **Optional** - Use Optional[] type: `field: Optional[str] = None`
- **Default value** - Provide default: `field: str = "default"`

### Common Validators
```python
# String length
name: str = Field(..., min_length=1, max_length=100)

# Numeric range
age: int = Field(..., ge=0, le=150)

# Pattern matching
postcode: str = Field(..., pattern=r"^[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}$")

# Email
email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
```

### Custom Validators
```python
@field_validator('field_name', mode='before')
@classmethod
def validate_field(cls, v):
    """
    Custom validation logic
    
    Args:
        v: Field value to validate
    
    Returns:
        Validated/transformed value
    
    Raises:
        ValueError: If validation fails
    """
    if not valid(v):
        raise ValueError('Validation error message')
    return transform(v)
```

## Model Usage

### In Route Handlers
```python
from fastapi import APIRouter
from ..models.patient import Patient, PatientCreate

@router.post("/", response_model=Patient)
async def create_patient(patient: PatientCreate):
    """
    FastAPI automatically:
    1. Validates request body against PatientCreate model
    2. Converts to Pydantic object
    3. Returns 422 if validation fails
    4. Validates response against Patient model
    5. Serializes to JSON
    """
    patient_dict = patient.model_dump()
    # ... database operations ...
    return Patient(**created_patient)
```

### Manual Validation
```python
# Parse and validate
patient = Patient(**data_dict)

# Convert to dict
patient_dict = patient.model_dump()

# Convert to JSON
patient_json = patient.model_dump_json()

# Exclude unset fields (for updates)
update_data = patient_update.model_dump(exclude_unset=True)
```

## Sensitive Data Handling

Models containing sensitive fields should document encryption requirements:

```python
class Patient(BaseModel):
    """
    Patient model with encrypted sensitive fields.
    
    Encrypted fields (AES-256):
        - nhs_number: NHS patient identifier
        - mrn: Medical record number
        - date_of_birth: Date of birth
        - postcode: UK postcode
    
    These fields are encrypted before storage and decrypted on retrieval
    using app/utils/encryption.py utilities.
    """
    nhs_number: Optional[str] = None  # Encrypted
    mrn: Optional[str] = None  # Encrypted
```

## NBOCA/COSD Compliance

Models used for COSD exports should document field mappings:

```python
class Treatment(BaseModel):
    """
    Treatment model for COSD export.
    
    COSD v9/v10 Mappings:
        - treatment_date: TREATMENT_DATE (mandatory)
        - opcs4_code: PRIMARY_PROCEDURE_OPCS (mandatory for surgery)
        - surgeon_code: CONSULTANT_CODE_AT_TREATMENT (mandatory)
    """
```

## Best Practices

1. **Always use type hints** - Enable proper validation
2. **Document all fields** - Use Field() with description parameter
3. **Use nested models** - Group related fields logically
4. **Validate constraints** - Use ge, le, min_length, max_length, pattern
5. **Handle Optional fields** - Explicitly use Optional[] for clarity
6. **Custom validators** - Add @field_validator for complex logic
7. **Model config** - Set populate_by_name=True for MongoDB _id
8. **Docstrings** - Document model purpose and special requirements

## Testing Models

```python
import pytest
from pydantic import ValidationError

def test_patient_validation():
    # Valid data
    patient = Patient(patient_id="ABC123", demographics={...})
    assert patient.patient_id == "ABC123"
    
    # Invalid data should raise
    with pytest.raises(ValidationError):
        Patient(patient_id="", demographics={...})
```

## Migration from Pydantic v1

This codebase uses Pydantic v2. Key differences:
- `model_dump()` instead of `dict()`
- `model_validate()` instead of `parse_obj()`
- `model_config` instead of `Config` class
- `@field_validator` instead of `@validator`
