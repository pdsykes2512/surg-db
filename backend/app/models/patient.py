"""
Patient data models
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Any
from datetime import datetime
from bson import ObjectId
import re


class PyObjectId(str):
    """Custom ObjectId type for Pydantic v2"""
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        from pydantic_core import core_schema
        
        def validate(value):
            """Validate and convert MongoDB ObjectId to string.
            
            Accepts ObjectId instances or valid ObjectId strings and ensures
            the output is always a string representation of the ObjectId.
            
            Args:
                value: ObjectId instance, valid ObjectId string, or invalid value
            
            Returns:
                str: String representation of the ObjectId
            
            Raises:
                ValueError: If value is not a valid ObjectId or correct type
            """
            if isinstance(value, ObjectId):
                return str(value)
            if isinstance(value, str):
                if not ObjectId.is_valid(value):
                    raise ValueError("Invalid ObjectId")
                return value
            raise ValueError("Invalid ObjectId type")
        
        return core_schema.no_info_plain_validator_function(validate)
    
    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema, _handler):
        field_schema.update(type="string")


class Demographics(BaseModel):
    """Patient demographics"""
    date_of_birth: Optional[str] = Field(None, description="Date of birth in YYYY-MM-DD format")
    age: Optional[int] = Field(None, ge=0, le=150)
    gender: str = Field(..., min_length=1)
    ethnicity: Optional[str] = None
    postcode: Optional[str] = None
    bmi: Optional[float] = Field(None, ge=0, le=100)
    weight_kg: Optional[float] = Field(None, ge=0, le=500)
    height_cm: Optional[float] = Field(None, ge=0, le=300)


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
    patient_id: str = Field(..., min_length=1, description="Unique patient ID: 6-digit hash")
    mrn: Optional[str] = Field(None, description="Medical Record Number: 8 digits or IW+6 digits")
    nhs_number: Optional[str] = Field(None, description="NHS number: 10 digits")
    demographics: Demographics
    medical_history: Optional[MedicalHistory] = Field(default_factory=MedicalHistory)
    
    @field_validator('mrn', 'nhs_number', mode='before')
    @classmethod
    def convert_to_string(cls, v):
        """Convert numeric values to strings"""
        if v is None:
            return v
        return str(v) if v else None


class PatientCreate(PatientBase):
    """Patient creation model"""
    pass


class PatientUpdate(BaseModel):
    """Patient update model - all fields optional"""
    patient_id: Optional[str] = None
    mrn: Optional[str] = None
    nhs_number: Optional[str] = None
    demographics: Optional[Demographics] = None
    medical_history: Optional[MedicalHistory] = None
    
    @field_validator('mrn', 'nhs_number', mode='before')
    @classmethod
    def convert_to_string(cls, v):
        """Convert numeric values to strings"""
        if v is None:
            return v
        return str(v) if v else None


class PatientInDB(PatientBase):
    """Patient model as stored in database"""
    id: str = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class Patient(PatientInDB):
    """Patient response model"""
    episode_count: Optional[int] = Field(default=0, description="Count of episodes associated with this patient")

