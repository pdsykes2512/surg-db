"""
Patient data models
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
import re


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class Demographics(BaseModel):
    """Patient demographics"""
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    date_of_birth: str = Field(..., description="Date of birth in YYYY-MM-DD format")
    age: Optional[int] = Field(None, ge=0, le=150)
    gender: str = Field(..., min_length=1)
    ethnicity: Optional[str] = None
    postcode: Optional[str] = None
    bmi: Optional[float] = Field(None, ge=10, le=80)
    weight_kg: Optional[float] = Field(None, ge=20, le=300)
    height_cm: Optional[float] = Field(None, ge=100, le=250)


class Contact(BaseModel):
    """Patient contact information"""
    phone: Optional[str] = None
    email: Optional[str] = None


class MedicalHistory(BaseModel):
    """Patient medical history"""
    conditions: List[str] = Field(default_factory=list)
    previous_surgeries: List[dict] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    smoking_status: Optional[str] = Field(None, description="never/former/current")
    alcohol_use: Optional[str] = None


class PatientBase(BaseModel):
    """Base patient model"""
    record_number: str = Field(..., min_length=1, description="Unique patient record number: 8 digits or IW + 6 digits")
    nhs_number: str = Field(..., description="NHS number: 10 digits formatted as XXX XXX XXXX")
    demographics: Demographics
    contact: Optional[Contact] = None
    medical_history: Optional[MedicalHistory] = Field(default_factory=MedicalHistory)
    
    @field_validator('record_number')
    @classmethod
    def validate_record_number(cls, v: str) -> str:
        """Validate record number format: 8 digits or IW followed by 6 digits"""
        if not re.match(r'^(\d{8}|IW\d{6})$', v):
            raise ValueError('Record number must be either 8 digits or IW followed by 6 digits')
        return v
    
    @field_validator('nhs_number')
    @classmethod
    def validate_nhs_number(cls, v: str) -> str:
        """Validate NHS number format: XXX XXX XXXX"""
        if not re.match(r'^\d{3} \d{3} \d{4}$', v):
            raise ValueError('NHS number must be 10 digits formatted as XXX XXX XXXX')
        return v


class PatientCreate(PatientBase):
    """Patient creation model"""
    pass


class PatientUpdate(BaseModel):
    """Patient update model - all fields optional"""
    record_number: Optional[str] = None
    nhs_number: Optional[str] = None
    demographics: Optional[Demographics] = None
    contact: Optional[Contact] = None
    medical_history: Optional[MedicalHistory] = None


class PatientInDB(PatientBase):
    """Patient model as stored in database"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Patient(PatientInDB):
    """Patient response model"""
    pass
