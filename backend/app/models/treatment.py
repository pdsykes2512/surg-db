"""
Treatment models for episode-based care
Treatments can be: surgery, chemotherapy, radiotherapy, etc.
Surgery data is preserved from the original surgery model
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Union
from datetime import datetime, date
from enum import Enum

from .utils import parse_date_string

# Import surgery components
from .surgery import (
    Classification, Procedure, PerioperativeTimeline, SurgicalTeam,
    Intraoperative, Pathology, TNMStaging, PostoperativeEvents,
    Outcomes, FollowUp, Document
)


class TreatmentType(str, Enum):
    SURGERY = "surgery"
    CHEMOTHERAPY = "chemotherapy"
    RADIOTHERAPY = "radiotherapy"
    IMMUNOTHERAPY = "immunotherapy"
    HORMONE_THERAPY = "hormone_therapy"
    TARGETED_THERAPY = "targeted_therapy"
    PALLIATIVE = "palliative"
    SURVEILLANCE = "surveillance"


class TreatmentIntent(str, Enum):
    CURATIVE = "curative"
    PALLIATIVE = "palliative"
    ADJUVANT = "adjuvant"
    NEOADJUVANT = "neoadjuvant"
    PROPHYLACTIC = "prophylactic"


class TreatmentBase(BaseModel):
    """Base treatment information"""
    treatment_id: str = Field(..., min_length=1, description="Unique treatment identifier")
    treatment_type: TreatmentType
    treatment_date: Union[datetime, date, str]
    treating_clinician: str = Field(..., min_length=1)
    treatment_intent: TreatmentIntent
    notes: Optional[str] = None
    
    @field_validator('treatment_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        return parse_date_string(v)


# ============== SURGERY TREATMENT ==============

class SurgeryTreatment(TreatmentBase):
    """Surgery as a treatment within an episode"""
    treatment_type: TreatmentType = TreatmentType.SURGERY
    
    # NBOCA COSD field
    provider_organisation: Optional[str] = Field(None, description="CR1450: NHS Trust code of provider")
    
    # Core surgery data (from original surgery model)
    classification: Classification
    procedure: Procedure
    perioperative_timeline: PerioperativeTimeline
    team: SurgicalTeam
    intraoperative: Optional[Intraoperative] = Field(default_factory=Intraoperative)
    
    # Pathology results
    pathology: Optional[Pathology] = None
    
    # Postoperative course
    postoperative_events: Optional[PostoperativeEvents] = Field(default_factory=PostoperativeEvents)
    outcomes: Optional[Outcomes] = Field(default_factory=Outcomes)
    follow_up: Optional[FollowUp] = Field(default_factory=FollowUp)
    
    # Documents
    documents: List[Document] = Field(default_factory=list)


# ============== CHEMOTHERAPY TREATMENT ==============

class ChemotherapyRegimen(BaseModel):
    """Chemotherapy regimen details"""
    regimen_name: str = Field(..., description="e.g., FOLFOX, FOLFIRI, AC-T")
    drugs: List[str] = Field(..., min_items=1)
    protocol_reference: Optional[str] = None


class ChemotherapyCycle(BaseModel):
    """Individual chemotherapy cycle"""
    cycle_number: int = Field(..., ge=1)
    date: Union[datetime, date, str]
    dose_modifications: Optional[str] = None
    toxicities: List[str] = Field(default_factory=list)
    performance_status: Optional[int] = Field(None, ge=0, le=5)
    completed: bool = True
    reason_incomplete: Optional[str] = None


class ChemotherapyTreatment(TreatmentBase):
    """Chemotherapy treatment"""
    treatment_type: TreatmentType = TreatmentType.CHEMOTHERAPY
    
    regimen: ChemotherapyRegimen
    planned_cycles: int = Field(..., ge=1)
    cycles: List[ChemotherapyCycle] = Field(default_factory=list)
    
    # Overall treatment status
    treatment_status: str = Field(default="ongoing", description="ongoing/completed/discontinued")
    discontinuation_reason: Optional[str] = None
    
    # Response assessment
    response_assessment: Optional[str] = Field(None, description="complete_response/partial_response/stable_disease/progressive_disease")
    assessment_date: Optional[Union[datetime, date, str]] = None
    assessment_method: Optional[str] = Field(None, description="CT/MRI/PET/clinical")


# ============== RADIOTHERAPY TREATMENT ==============

class RadiotherapyTreatment(TreatmentBase):
    """Radiotherapy treatment"""
    treatment_type: TreatmentType = TreatmentType.RADIOTHERAPY
    
    technique: str = Field(..., description="3D-CRT/IMRT/VMAT/SBRT/brachytherapy")
    target_site: str
    total_dose_gy: float = Field(..., gt=0)
    fractions: int = Field(..., ge=1)
    dose_per_fraction_gy: float = Field(..., gt=0)
    
    start_date: Union[datetime, date, str]
    end_date: Optional[Union[datetime, date, str]] = None
    
    # Treatment status
    treatment_status: str = Field(default="planned", description="planned/ongoing/completed/discontinued")
    fractions_delivered: Optional[int] = Field(None, ge=0)
    
    # Toxicity
    acute_toxicity: List[str] = Field(default_factory=list)
    late_toxicity: List[str] = Field(default_factory=list)
    
    # Response
    response_assessment: Optional[str] = None
    assessment_date: Optional[Union[datetime, date, str]] = None


# ============== IMMUNOTHERAPY TREATMENT ==============

class ImmunotherapyTreatment(TreatmentBase):
    """Immunotherapy treatment"""
    treatment_type: TreatmentType = TreatmentType.IMMUNOTHERAPY
    
    drug_name: str = Field(..., description="e.g., pembrolizumab, nivolumab, ipilimumab")
    drug_class: str = Field(..., description="PD-1/PD-L1/CTLA-4/other")
    
    # Dosing schedule
    dose_amount: Optional[str] = None
    dose_unit: Optional[str] = Field(None, description="mg/mg_per_kg")
    frequency: str = Field(..., description="e.g., every 3 weeks, every 4 weeks")
    
    # Treatment cycles
    cycles_received: int = Field(default=0, ge=0)
    planned_duration: Optional[str] = None
    
    # Status
    treatment_status: str = Field(default="ongoing", description="ongoing/completed/discontinued")
    discontinuation_reason: Optional[str] = None
    
    # Immune-related adverse events (irAEs)
    immune_related_aes: List[str] = Field(default_factory=list)
    steroid_required: Optional[bool] = None
    
    # Response
    response_assessment: Optional[str] = None
    assessment_date: Optional[Union[datetime, date, str]] = None


# ============== HORMONE THERAPY TREATMENT ==============

class HormoneTherapyTreatment(TreatmentBase):
    """Hormone therapy treatment"""
    treatment_type: TreatmentType = TreatmentType.HORMONE_THERAPY
    
    drug_name: str = Field(..., description="e.g., tamoxifen, letrozole, bicalutamide")
    drug_class: str = Field(..., description="SERM/AI/GnRH_agonist/antiandrogen/other")
    
    planned_duration_months: Optional[int] = Field(None, ge=0)
    start_date: Union[datetime, date, str]
    end_date: Optional[Union[datetime, date, str]] = None
    
    # Treatment status
    treatment_status: str = Field(default="ongoing", description="ongoing/completed/discontinued")
    discontinuation_reason: Optional[str] = None
    
    # Side effects
    side_effects: List[str] = Field(default_factory=list)
    
    # Monitoring
    compliance: Optional[str] = Field(None, description="good/fair/poor")


# ============== TARGETED THERAPY TREATMENT ==============

class TargetedTherapyTreatment(TreatmentBase):
    """Targeted therapy treatment"""
    treatment_type: TreatmentType = TreatmentType.TARGETED_THERAPY
    
    drug_name: str = Field(..., description="e.g., trastuzumab, cetuximab, bevacizumab")
    target: str = Field(..., description="HER2/EGFR/VEGF/other")
    
    # Biomarker status
    biomarker_status: Optional[str] = Field(None, description="Confirmatory biomarker test result")
    
    # Dosing
    dose_amount: Optional[str] = None
    frequency: str
    
    # Treatment course
    cycles_received: int = Field(default=0, ge=0)
    treatment_status: str = Field(default="ongoing", description="ongoing/completed/discontinued")
    
    # Response and toxicity
    response_assessment: Optional[str] = None
    specific_toxicities: List[str] = Field(default_factory=list, description="Drug-specific side effects")


# ============== PALLIATIVE CARE ==============

class PalliativeTreatment(TreatmentBase):
    """Palliative care intervention"""
    treatment_type: TreatmentType = TreatmentType.PALLIATIVE
    
    intervention_type: str = Field(..., description="symptom_control/pain_management/psychosocial_support/end_of_life_care")
    presenting_symptoms: List[str] = Field(default_factory=list)
    interventions_provided: List[str] = Field(default_factory=list)
    symptom_improvement: Optional[bool] = None
    
    palliative_performance_scale: Optional[int] = Field(None, ge=0, le=100)
    care_setting: Optional[str] = Field(None, description="home/hospice/hospital/outpatient")


# ============== SURVEILLANCE ==============

class SurveillanceTreatment(TreatmentBase):
    """Active surveillance"""
    treatment_type: TreatmentType = TreatmentType.SURVEILLANCE
    
    surveillance_protocol: str = Field(..., description="Name or reference for surveillance protocol")
    monitoring_frequency: str = Field(..., description="e.g., every 3 months, every 6 months")
    
    monitoring_tests: List[str] = Field(default_factory=list, description="Imaging, tumor markers, clinical exams")
    
    # Status
    surveillance_status: str = Field(default="ongoing", description="ongoing/discontinued/converted_to_active_treatment")
    progression_detected: Optional[bool] = None
    progression_date: Optional[Union[datetime, date, str]] = None


# ============== TREATMENT RESPONSE ==============

class TreatmentResponse(BaseModel):
    """Overall treatment response assessment"""
    assessment_date: Union[datetime, date, str]
    assessment_method: str = Field(..., description="RECIST/clinical/biomarker/pathological")
    response: str = Field(..., description="complete_response/partial_response/stable_disease/progressive_disease")
    details: Optional[str] = None
    next_treatment_plan: Optional[str] = None


# Union type for all treatments
Treatment = Union[
    SurgeryTreatment,
    ChemotherapyTreatment,
    RadiotherapyTreatment,
    ImmunotherapyTreatment,
    HormoneTherapyTreatment,
    TargetedTherapyTreatment,
    PalliativeTreatment,
    SurveillanceTreatment
]
