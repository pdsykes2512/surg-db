from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SurgeonBase(BaseModel):
    """Base surgeon model"""
    first_name: str = Field(..., description="Surgeon's first name")
    surname: str = Field(..., description="Surgeon's surname")
    gmc_number: Optional[str] = Field(None, description="GMC registration number")


class SurgeonCreate(SurgeonBase):
    """Model for creating a new surgeon"""
    pass


class SurgeonUpdate(BaseModel):
    """Model for updating a surgeon"""
    first_name: Optional[str] = None
    surname: Optional[str] = None
    gmc_number: Optional[str] = None


class Surgeon(SurgeonBase):
    """Complete surgeon model with database fields"""
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
