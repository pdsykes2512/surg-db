"""
Tumour data models for tracking individual tumour sites
A cancer episode can have multiple tumours (primaries or metastases)
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime, date, timezone
from enum import Enum

from .utils import parse_date_string

class TumourType(str, Enum):
    PRIMARY = "primary"
    METASTASIS = "metastasis"
    RECURRENCE = "recurrence"


class TumourSite(str, Enum):
    # Colorectal sites (ICD-10 C18.x, C19, C20)
    CAECUM = "caecum"  # C18.0
    APPENDIX = "appendix"  # C18.1
    ASCENDING_COLON = "ascending_colon"  # C18.2
    HEPATIC_FLEXURE = "hepatic_flexure"  # C18.3
    TRANSVERSE_COLON = "transverse_colon"  # C18.4
    SPLENIC_FLEXURE = "splenic_flexure"  # C18.5
    DESCENDING_COLON = "descending_colon"  # C18.6
    SIGMOID_COLON = "sigmoid_colon"  # C18.7
    RECTOSIGMOID_JUNCTION = "rectosigmoid_junction"  # C19
    RECTUM = "rectum"  # C20
    COLON_UNSPECIFIED = "colon_unspecified"  # C18.9
    
    # Metastatic sites
    LIVER = "liver"
    LUNG = "lung"
    PERITONEUM = "peritoneum"
    LYMPH_NODE = "lymph_node"
    BONE = "bone"
    BRAIN = "brain"
    OTHER = "other"


class TNMVersion(str, Enum):
    V7 = "7"
    V8 = "8"


class TStage(str, Enum):
    TX = "Tx"
    T0 = "T0"
    TIS = "Tis"
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"
    T4A = "T4a"
    T4B = "T4b"


class NStage(str, Enum):
    NX = "Nx"
    N0 = "N0"
    N1 = "N1"
    N1A = "N1a"
    N1B = "N1b"
    N1C = "N1c"
    N2 = "N2"
    N2A = "N2a"
    N2B = "N2b"


class MStage(str, Enum):
    MX = "Mx"
    M0 = "M0"
    M1 = "M1"
    M1A = "M1a"
    M1B = "M1b"
    M1C = "M1c"


class MarginStatus(str, Enum):
    """Resection margin status (R classification)"""
    R0 = "R0"  # Complete resection, margins clear
    R1 = "R1"  # Microscopic residual disease
    R2 = "R2"  # Macroscopic residual disease
    UNCERTAIN = "uncertain"
    NOT_APPLICABLE = "not_applicable"


class TumourBase(BaseModel):
    """Base tumour information"""
    tumour_id: str = Field(..., description="Unique tumour identifier")
    tumour_type: TumourType = Field(..., description="Primary, metastasis, or recurrence")
    site: TumourSite = Field(..., description="Anatomical location")
    
    # Diagnosis
    diagnosis_date: Optional[date] = None  # CR2030
    icd10_code: Optional[str] = Field(None, description="ICD-10 diagnosis code (CR0370)")
    snomed_morphology: Optional[str] = Field(None, description="SNOMED morphology code (CR6400)")
    
    # TNM Staging - Clinical (Pretreatment)
    tnm_version: TNMVersion = Field(TNMVersion.V8, description="TNM version (CR2070)")
    clinical_t: Optional[TStage] = Field(None, description="Clinical T stage (CR0520)")
    clinical_n: Optional[NStage] = Field(None, description="Clinical N stage (CR0540)")
    clinical_m: Optional[MStage] = Field(None, description="Clinical M stage (CR0560)")
    clinical_stage_date: Optional[date] = None
    
    # TNM Staging - Pathological (Post-surgery)
    pathological_t: Optional[TStage] = Field(None, description="Pathological T stage (pCR0910)")
    pathological_n: Optional[NStage] = Field(None, description="Pathological N stage (pCR0920)")
    pathological_m: Optional[MStage] = Field(None, description="Pathological M stage (pCR0930)")
    pathological_stage_date: Optional[date] = None
    
    # Tumour characteristics
    grade: Optional[str] = Field(None, description="Histological grade (well/moderate/poor)")
    histology_type: Optional[str] = Field(None, description="Adenocarcinoma, mucinous, etc")
    size_mm: Optional[float] = Field(None, description="Maximum tumour dimension in mm")
    
    # Rectal cancer specific (C20)
    distance_from_anal_verge_cm: Optional[float] = Field(None, description="Height above anal verge (CO5160)")
    mesorectal_involvement: Optional[bool] = None
    
    # Pathology (post-resection)
    background_morphology: Optional[str] = Field(None, description="Cancer origin: Adenoma/IBD/Serrated/De novo/Unknown")
    lymph_nodes_examined: Optional[int] = Field(None, description="Total nodes examined (pCR0890)")
    lymph_nodes_positive: Optional[int] = Field(None, description="Positive nodes (pCR0900)")
    apical_node: Optional[str] = Field(None, description="Apical node status: Involved/Not Involved/Unknown")
    lymphatic_invasion: Optional[str] = Field(None, description="Lymphatic invasion (L0/L1): yes/no/uncertain")
    vascular_invasion: Optional[str] = Field(None, description="Vascular invasion (V0/V1): yes/no/uncertain")
    perineural_invasion: Optional[str] = Field(None, description="Perineural invasion (Pn0/Pn1): yes/no/uncertain")

    # Resection margins
    margin_status: Optional[MarginStatus] = Field(None, description="Resection margin status R0/R1/R2 (pCR1150)")
    crm_distance_mm: Optional[float] = Field(None, description="Distance to CRM in mm")
    proximal_margin_mm: Optional[float] = Field(None, description="Proximal margin in mm")
    distal_margin_mm: Optional[float] = Field(None, description="Distal margin in mm")
    donuts_involved: Optional[str] = Field(None, description="Donut status: Involved/Not Involved/Not Sent/Unknown")
    
    # Molecular markers
    mismatch_repair_status: Optional[str] = Field(None, description="Intact/Deficient/Unknown")
    kras_status: Optional[str] = Field(None, description="Wild-type/Mutant/Unknown")
    braf_status: Optional[str] = Field(None, description="Wild-type/Mutant/Unknown")
    
    # Treatment associations
    treated_by_treatment_ids: List[str] = Field(default_factory=list, description="Treatment IDs that addressed this tumour")
    
    # Notes
    notes: Optional[str] = None
    
    @field_validator('diagnosis_date', 'clinical_stage_date', 'pathological_stage_date', mode='before')
    @classmethod
    def parse_dates(cls, v: Any) -> date | str:
        result = parse_date_string(v)
        # Convert to date if we got a datetime
        if isinstance(result, datetime):
            return result.date()
        return result


class TumourCreate(TumourBase):
    """Model for creating a new tumour"""
    pass


class TumourUpdate(BaseModel):
    """Model for updating tumour - all fields optional"""
    tumour_type: Optional[TumourType] = None
    site: Optional[TumourSite] = None
    diagnosis_date: Optional[date] = None
    icd10_code: Optional[str] = None
    snomed_morphology: Optional[str] = None
    tnm_version: Optional[TNMVersion] = None
    clinical_t: Optional[TStage] = None
    clinical_n: Optional[NStage] = None
    clinical_m: Optional[MStage] = None
    clinical_stage_date: Optional[date] = None
    pathological_t: Optional[TStage] = None
    pathological_n: Optional[NStage] = None
    pathological_m: Optional[MStage] = None
    pathological_stage_date: Optional[date] = None
    grade: Optional[str] = None
    histology_type: Optional[str] = None
    size_mm: Optional[float] = None
    distance_from_anal_verge_cm: Optional[float] = None
    mesorectal_involvement: Optional[bool] = None
    background_morphology: Optional[str] = None
    lymph_nodes_examined: Optional[int] = None
    lymph_nodes_positive: Optional[int] = None
    apical_node: Optional[str] = None
    lymphatic_invasion: Optional[str] = None
    vascular_invasion: Optional[str] = None
    perineural_invasion: Optional[str] = None
    margin_status: Optional[MarginStatus] = None
    crm_distance_mm: Optional[float] = None
    proximal_margin_mm: Optional[float] = None
    distal_margin_mm: Optional[float] = None
    donuts_involved: Optional[str] = None
    mismatch_repair_status: Optional[str] = None
    kras_status: Optional[str] = None
    braf_status: Optional[str] = None
    treated_by_treatment_ids: Optional[List[str]] = None
    notes: Optional[str] = None


class Tumour(TumourBase):
    """Full tumour model with metadata"""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }
