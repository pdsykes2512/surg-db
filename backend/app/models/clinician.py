from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re


class ClinicianBase(BaseModel):
    """Base clinician model"""
    first_name: str = Field(..., description="Clinician's first name")
    surname: str = Field(..., description="Clinician's surname")
    gmc_number: Optional[str] = Field(None, description="GMC registration number (7 digits)")
    subspecialty_leads: List[str] = Field(default_factory=list, description="List of subspecialties: colorectal/urology/breast/upper_gi/gynae_onc/other")
    clinical_role: str = Field(default="surgeon", description="surgeon/anaesthetist/oncologist/radiologist/other")
    
    @field_validator('gmc_number')
    @classmethod
    def validate_gmc_number(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            # Remove any spaces or hyphens
            cleaned = re.sub(r'[\s-]', '', v)
            if not re.match(r'^\d{7}$', cleaned):
                raise ValueError('GMC number must be exactly 7 digits')
            return cleaned
        return None


class ClinicianCreate(ClinicianBase):
    """Model for creating a new clinician"""
    pass


class ClinicianUpdate(BaseModel):
    """Model for updating a clinician"""
    first_name: Optional[str] = None
    surname: Optional[str] = None
    gmc_number: Optional[str] = None
    subspecialty_leads: Optional[List[str]] = None
    clinical_role: Optional[str] = None


class Clinician(ClinicianBase):
    """Complete clinician model with database fields"""
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "first_name": "John",
                "surname": "Smith",
                "gmc_number": "1234567",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }
