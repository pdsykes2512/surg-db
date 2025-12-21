"""
Surgery data models
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from .patient import PyObjectId


class Procedure(BaseModel):
    """Surgery procedure details"""
    type: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1, description="CPT or ICD code")
    description: str
    date: datetime
    duration_minutes: int = Field(..., ge=0)


class SurgicalTeam(BaseModel):
    """Surgical team members"""
    surgeon: str = Field(..., min_length=1)
    anesthesiologist: Optional[str] = None
    nurses: List[str] = Field(default_factory=list)


class Complication(BaseModel):
    """Surgery complication record"""
    type: str
    severity: str = Field(..., description="mild, moderate, severe")
    description: str
    occurred_at: datetime


class Outcomes(BaseModel):
    """Surgery outcomes"""
    success: bool = True
    complications: List[Complication] = Field(default_factory=list)
    length_of_stay_days: Optional[int] = Field(None, ge=0)
    readmission_30day: bool = False
    mortality: bool = False
    patient_satisfaction: Optional[int] = Field(None, ge=1, le=10)


class FollowUpAppointment(BaseModel):
    """Follow-up appointment record"""
    date: datetime
    provider: str
    notes: Optional[str] = None


class FollowUp(BaseModel):
    """Surgery follow-up information"""
    appointments: List[FollowUpAppointment] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class SurgeryBase(BaseModel):
    """Base surgery model"""
    surgery_id: str = Field(..., min_length=1)
    patient_id: str = Field(..., min_length=1)
    procedure: Procedure
    team: SurgicalTeam
    outcomes: Outcomes = Field(default_factory=Outcomes)
    follow_up: FollowUp = Field(default_factory=FollowUp)


class SurgeryCreate(SurgeryBase):
    """Surgery creation model"""
    pass


class SurgeryUpdate(BaseModel):
    """Surgery update model - all fields optional"""
    surgery_id: Optional[str] = None
    patient_id: Optional[str] = None
    procedure: Optional[Procedure] = None
    team: Optional[SurgicalTeam] = None
    outcomes: Optional[Outcomes] = None
    follow_up: Optional[FollowUp] = None


class SurgeryInDB(SurgeryBase):
    """Surgery model as stored in database"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Surgery(SurgeryInDB):
    """Surgery response model"""
    pass
