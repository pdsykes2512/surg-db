"""
Episode data models for hospital contacts across different conditions
Redesigned to support: cancer, IBD, benign conditions
Each condition type has specific data collection requirements
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Union, Literal
from datetime import datetime, date
from bson import ObjectId
from enum import Enum

from .utils import parse_date_string


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        """Validate ObjectId string format.
        
        Args:
            v: ObjectId string to validate
        
        Returns:
            ObjectId: Valid MongoDB ObjectId instance
        
        Raises:
            ValueError: If string is not a valid ObjectId format
        """
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


# Enums for standardized values
class ConditionType(str, Enum):
    CANCER = "cancer"
    IBD = "ibd"
    BENIGN = "benign"


class CancerType(str, Enum):
    BOWEL = "bowel"
    KIDNEY = "kidney"
    BREAST_PRIMARY = "breast_primary"
    BREAST_METASTATIC = "breast_metastatic"
    OESOPHAGEAL = "oesophageal"
    OVARIAN = "ovarian"
    PROSTATE = "prostate"


class TreatmentType(str, Enum):
    SURGERY = "surgery"
    CHEMOTHERAPY = "chemotherapy"
    RADIOTHERAPY = "radiotherapy"
    IMMUNOTHERAPY = "immunotherapy"
    HORMONE_THERAPY = "hormone_therapy"
    TARGETED_THERAPY = "targeted_therapy"
    PALLIATIVE = "palliative"
    SURVEILLANCE = "surveillance"


# Base Episode Model
class EpisodeBase(BaseModel):
    """Base episode information - common across all condition types"""
    episode_id: str = Field(..., min_length=1, description="Unique episode identifier")
    patient_id: str = Field(..., min_length=1, description="Patient MRN/record number")
    condition_type: ConditionType = Field(..., description="Type of condition: cancer/ibd/benign")
    
    # Contact details
    referral_date: Union[datetime, date, str]
    first_seen_date: Optional[Union[datetime, date, str]] = None
    mdt_discussion_date: Optional[Union[datetime, date, str]] = None
    
    # NBOCA COSD Referral Pathway Fields
    referral_source: Optional[str] = Field(None, description="CR1600: gp/2ww/emergency/screening/consultant/private/other")
    provider_first_seen: Optional[str] = Field(None, description="CR1410: NHS Trust code where first seen")
    cns_involved: Optional[str] = Field(None, description="CR2050: yes/no/unknown - Clinical Nurse Specialist")
    mdt_meeting_type: Optional[str] = Field(None, description="CR3190: colorectal/upper_gi/lower_gi/combined/other")
    performance_status: Optional[str] = Field(None, description="CR0510: ECOG score 0-5 - Patient fitness")
    no_treatment_reason: Optional[str] = Field(None, description="CR0490: Reason if no treatment given")
    
    # Clinical team
    lead_clinician: str = Field(..., description="Name of lead consultant")
    mdt_team: List[str] = Field(default_factory=list)
    
    # Episode status
    episode_status: str = Field(default="active", description="active/completed/cancelled")
    
    # Audit trail
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    last_modified_at: datetime = Field(default_factory=datetime.utcnow)
    last_modified_by: str
    
    @field_validator('referral_date', 'first_seen_date', 'mdt_discussion_date', mode='before')
    @classmethod
    def parse_dates(cls, v):
        """Parse date strings to standardized format.
        
        Args:
            v: Date string or datetime object
        
        Returns:
            datetime or str: Parsed date in standardized format
        """
        return parse_date_string(v)


# TNM Staging (used across multiple cancer types)
class TNMStaging(BaseModel):
    """TNM cancer staging system"""
    clinical_t: Optional[str] = Field(None, description="Clinical T stage (e.g., T1, T2, T3, T4)")
    clinical_n: Optional[str] = Field(None, description="Clinical N stage (e.g., N0, N1, N2)")
    clinical_m: Optional[str] = Field(None, description="Clinical M stage (e.g., M0, M1)")
    pathological_t: Optional[str] = Field(None, description="Pathological T stage")
    pathological_n: Optional[str] = Field(None, description="Pathological N stage")
    pathological_m: Optional[str] = Field(None, description="Pathological M stage")
    stage_group: Optional[str] = Field(None, description="Overall stage group (I, II, III, IV)")
    staging_date: Optional[Union[datetime, date, str]] = None
    tnm_version: Optional[str] = Field("8", description="CR2070/pCR6820: TNM version (7 or 8)")


# Performance Status
class PerformanceStatus(BaseModel):
    """Patient performance status at time of assessment"""
    ecog_score: Optional[int] = Field(None, ge=0, le=5, description="ECOG performance status 0-5")
    karnofsky_score: Optional[int] = Field(None, ge=0, le=100, description="Karnofsky score 0-100")
    assessment_date: Union[datetime, date, str]


# ============== CANCER-SPECIFIC MODELS ==============

class BowelCancerData(BaseModel):
    """Colorectal/Bowel cancer specific data (NATCAN aligned)"""
    # Diagnosis details
    cancer_site: str = Field(..., description="colon/rectum/sigmoid/caecum/other")
    site_specific_location: Optional[str] = Field(None, description="Specific anatomical location")
    distance_from_anal_verge_cm: Optional[float] = Field(None, ge=0, description="For rectal cancers")
    diagnosis_date: Optional[Union[datetime, date, str]] = Field(None, description="CR2030: Date of primary diagnosis")
    icd10_code: Optional[str] = Field(None, description="CR0370: ICD-10 diagnosis code (e.g., C18.0-C20)")
    snomed_morphology_code: Optional[str] = Field(None, description="CR6400: SNOMED morphology code")
    
    # Presentation
    presentation_type: str = Field(..., description="symptomatic/screening/surveillance/emergency")
    symptoms: List[str] = Field(default_factory=list, description="bleeding/obstruction/perforation/pain/weight_loss/anemia")
    emergency_presentation: bool = False
    
    # Staging and grading
    tnm_staging: Optional[TNMStaging] = None
    histological_type: Optional[str] = Field(None, description="adenocarcinoma/mucinous/signet_ring/other")
    differentiation: Optional[str] = Field(None, description="well/moderate/poor/undifferentiated")
    
    # Tumor characteristics
    tumor_size_mm: Optional[float] = Field(None, ge=0)
    lymph_nodes_examined: Optional[int] = Field(None, ge=0)
    lymph_nodes_positive: Optional[int] = Field(None, ge=0)
    lymphovascular_invasion: Optional[bool] = None
    perineural_invasion: Optional[bool] = None
    extramural_vascular_invasion: Optional[bool] = None
    
    # Molecular markers
    mismatch_repair_status: Optional[str] = Field(None, description="proficient/deficient/unknown")
    kras_status: Optional[str] = Field(None, description="wild_type/mutant/unknown")
    nras_status: Optional[str] = Field(None, description="wild_type/mutant/unknown")
    braf_status: Optional[str] = Field(None, description="wild_type/mutant/unknown")
    
    # Metastases
    metastatic_sites: List[str] = Field(default_factory=list, description="liver/lung/peritoneum/bone/brain/other")
    resectable_metastases: Optional[bool] = None
    
    # Treatment plan
    neoadjuvant_therapy: Optional[str] = Field(None, description="chemotherapy/radiotherapy/chemoradiotherapy/none")
    mdt_treatment_plan: Optional[str] = None


class KidneyCancerData(BaseModel):
    """Renal cell carcinoma specific data"""
    # Diagnosis
    cancer_site: str = Field(..., description="right_kidney/left_kidney/bilateral")
    histological_type: str = Field(..., description="clear_cell/papillary/chromophobe/collecting_duct/other")
    histological_subtype: Optional[str] = None
    fuhrman_grade: Optional[int] = Field(None, ge=1, le=4, description="Fuhrman nuclear grade 1-4")
    
    # Presentation
    presentation_type: str = Field(..., description="incidental/symptomatic/screening")
    symptoms: List[str] = Field(default_factory=list, description="hematuria/pain/mass/weight_loss/paraneoplastic")
    
    # Tumor characteristics
    tnm_staging: Optional[TNMStaging] = None
    tumor_size_mm: Optional[float] = Field(None, ge=0)
    tumor_location: Optional[str] = Field(None, description="upper_pole/mid/lower_pole")
    
    # Risk stratification
    performance_status: Optional[PerformanceStatus] = None
    imdc_risk_score: Optional[str] = Field(None, description="favorable/intermediate/poor")
    
    # Metastatic disease
    metastatic_sites: List[str] = Field(default_factory=list, description="lung/bone/liver/brain/lymph_nodes/other")
    
    # Treatment plan
    mdt_treatment_plan: Optional[str] = None


class BreastCancerData(BaseModel):
    """Breast cancer specific data - covers both primary and metastatic"""
    is_metastatic: bool = Field(default=False, description="True if metastatic at presentation")
    
    # Primary tumor details
    cancer_site: str = Field(..., description="right_breast/left_breast/bilateral")
    quadrant: Optional[str] = Field(None, description="upper_outer/upper_inner/lower_outer/lower_inner/central/multifocal")
    laterality: str = Field(..., description="left/right/bilateral")
    
    # Detection method
    detection_method: str = Field(..., description="screening/symptomatic/self_detected/incidental")
    symptoms: List[str] = Field(default_factory=list)
    
    # Histopathology
    histological_type: str = Field(..., description="ductal/lobular/mixed/other")
    histological_grade: Optional[int] = Field(None, ge=1, le=3, description="Grade 1-3")
    
    # Receptor status (critical for treatment)
    er_status: Optional[str] = Field(None, description="positive/negative/unknown")
    er_percentage: Optional[float] = Field(None, ge=0, le=100)
    pr_status: Optional[str] = Field(None, description="positive/negative/unknown")
    pr_percentage: Optional[float] = Field(None, ge=0, le=100)
    her2_status: Optional[str] = Field(None, description="positive/negative/equivocal/unknown")
    her2_method: Optional[str] = Field(None, description="IHC/FISH/both")
    ki67_percentage: Optional[float] = Field(None, ge=0, le=100, description="Proliferation index")
    
    # Staging
    tnm_staging: Optional[TNMStaging] = None
    tumor_size_mm: Optional[float] = Field(None, ge=0)
    lymph_nodes_examined: Optional[int] = Field(None, ge=0)
    lymph_nodes_positive: Optional[int] = Field(None, ge=0)
    lymphovascular_invasion: Optional[bool] = None
    
    # Metastatic-specific fields
    metastatic_sites: List[str] = Field(default_factory=list, description="bone/liver/lung/brain/other")
    line_of_therapy: Optional[int] = Field(None, ge=1, description="1st line, 2nd line, etc.")
    
    # Genetic testing
    brca1_status: Optional[str] = Field(None, description="positive/negative/vus/not_tested")
    brca2_status: Optional[str] = Field(None, description="positive/negative/vus/not_tested")
    
    # Treatment plan
    neoadjuvant_therapy: Optional[str] = Field(None, description="chemotherapy/hormone/her2_targeted/none")
    surgery_plan: Optional[str] = Field(None, description="lumpectomy/mastectomy/bilateral_mastectomy/none")
    mdt_treatment_plan: Optional[str] = None


class OesophagealCancerData(BaseModel):
    """Oesophageal cancer specific data"""
    # Tumor location
    cancer_site: str = Field(..., description="upper_third/middle_third/lower_third/goj_type1/goj_type2/goj_type3")
    distance_from_incisors_cm: Optional[float] = Field(None, ge=0, description="Measured at endoscopy")
    
    # Histopathology
    histological_type: str = Field(..., description="adenocarcinoma/squamous_cell/other")
    differentiation: Optional[str] = Field(None, description="well/moderate/poor/undifferentiated")
    
    # Presentation
    symptoms: List[str] = Field(default_factory=list, description="dysphagia/weight_loss/pain/bleeding/aspiration")
    dysphagia_score: Optional[int] = Field(None, ge=0, le=4, description="0=none to 4=complete")
    weight_loss_kg: Optional[float] = Field(None, ge=0)
    
    # Staging
    tnm_staging: Optional[TNMStaging] = None
    tumor_length_mm: Optional[float] = Field(None, ge=0)
    
    # Invasion
    lymphovascular_invasion: Optional[bool] = None
    perineural_invasion: Optional[bool] = None
    
    # HER2 status (for adenocarcinoma)
    her2_status: Optional[str] = Field(None, description="positive/negative/unknown")
    
    # Performance status
    performance_status: Optional[PerformanceStatus] = None
    
    # Metastatic disease
    metastatic_sites: List[str] = Field(default_factory=list)
    
    # Treatment plan
    neoadjuvant_therapy: Optional[str] = Field(None, description="chemotherapy/chemoradiotherapy/none")
    mdt_treatment_plan: Optional[str] = None


class OvarianCancerData(BaseModel):
    """Ovarian cancer specific data"""
    # Tumor characteristics
    cancer_site: str = Field(..., description="right_ovary/left_ovary/bilateral/fallopian_tube/primary_peritoneal")
    
    # Histopathology
    histological_type: str = Field(..., description="serous/mucinous/endometrioid/clear_cell/carcinosarcoma/other")
    histological_grade: Optional[int] = Field(None, ge=1, le=3)
    
    # Staging (FIGO)
    figo_stage: Optional[str] = Field(None, description="IA/IB/IC1/IC2/IC3/IIA/IIB/IIIA1/IIIA2/IIIB/IIIC/IVA/IVB")
    tnm_staging: Optional[TNMStaging] = None
    
    # Presentation
    presentation_type: str = Field(..., description="symptomatic/incidental/screening")
    symptoms: List[str] = Field(default_factory=list, description="abdominal_pain/bloating/ascites/mass/bleeding")
    ascites_present: Optional[bool] = None
    
    # Tumor markers
    ca125_at_diagnosis: Optional[float] = Field(None, ge=0, description="U/mL")
    ca125_date: Optional[Union[datetime, date, str]] = None
    he4_level: Optional[float] = Field(None, ge=0)
    
    # Disease extent
    peritoneal_disease: Optional[bool] = None
    omental_involvement: Optional[bool] = None
    lymph_node_involvement: Optional[bool] = None
    distant_metastases: List[str] = Field(default_factory=list)
    
    # Genetic testing
    brca1_status: Optional[str] = Field(None, description="positive/negative/vus/not_tested")
    brca2_status: Optional[str] = Field(None, description="positive/negative/vus/not_tested")
    hrd_status: Optional[str] = Field(None, description="positive/negative/not_tested")
    
    # Resectability
    resectability_assessment: Optional[str] = Field(None, description="optimal/suboptimal/unresectable")
    
    # Treatment plan
    neoadjuvant_chemotherapy: Optional[bool] = None
    interval_debulking_planned: Optional[bool] = None
    mdt_treatment_plan: Optional[str] = None


class ProstateCancerData(BaseModel):
    """Prostate cancer specific data"""
    # Diagnosis
    detection_method: str = Field(..., description="psa_screening/symptomatic/incidental")
    
    # PSA history
    psa_at_diagnosis: Optional[float] = Field(None, ge=0, description="ng/mL")
    psa_date: Optional[Union[datetime, date, str]] = None
    psa_velocity: Optional[float] = Field(None, description="ng/mL/year")
    
    # Biopsy details
    gleason_primary: Optional[int] = Field(None, ge=1, le=5, description="Primary Gleason pattern")
    gleason_secondary: Optional[int] = Field(None, ge=1, le=5, description="Secondary Gleason pattern")
    gleason_score: Optional[int] = Field(None, ge=2, le=10, description="Sum of primary + secondary")
    isup_grade_group: Optional[int] = Field(None, ge=1, le=5, description="ISUP grade group 1-5")
    
    cores_taken: Optional[int] = Field(None, ge=0)
    cores_positive: Optional[int] = Field(None, ge=0)
    maximum_cancer_core_length_mm: Optional[float] = Field(None, ge=0)
    
    # MRI findings
    pirads_score: Optional[int] = Field(None, ge=1, le=5, description="PI-RADS score 1-5")
    mri_stage: Optional[str] = None
    
    # Clinical staging
    tnm_staging: Optional[TNMStaging] = None
    clinical_stage: Optional[str] = Field(None, description="T1/T2/T3/T4")
    
    # Risk stratification
    risk_group: Optional[str] = Field(None, description="low/intermediate/high/very_high")
    metastatic: bool = False
    metastatic_sites: List[str] = Field(default_factory=list, description="bone/lymph_nodes/liver/lung/other")
    
    # Metastatic workup
    bone_scan_result: Optional[str] = Field(None, description="negative/positive/not_done")
    psma_pet_result: Optional[str] = Field(None, description="negative/positive/not_done")
    
    # Treatment plan
    mdt_treatment_plan: Optional[str] = Field(None, description="active_surveillance/surgery/radiotherapy/adt/chemotherapy/other")


# Union type for cancer-specific data
CancerSpecificData = Union[
    BowelCancerData,
    KidneyCancerData,
    BreastCancerData,
    OesophagealCancerData,
    OvarianCancerData,
    ProstateCancerData
]


class CancerEpisode(EpisodeBase):
    """Cancer episode with cancer-specific data"""
    condition_type: Literal[ConditionType.CANCER] = ConditionType.CANCER
    cancer_type: CancerType = Field(..., description="Specific cancer type")
    cancer_data: CancerSpecificData = Field(..., description="Cancer type-specific clinical data")
    treatments: List[dict] = Field(default_factory=list, description="List of treatments (surgeries, chemo, etc)")


# ============== TREATMENT MODELS ==============
# Treatments are now separate components within an episode

class TreatmentBase(BaseModel):
    """Base treatment record"""
    treatment_id: str = Field(..., min_length=1)
    treatment_type: TreatmentType
    treatment_date: Union[datetime, date, str]
    treating_clinician: str
    treatment_intent: str = Field(..., description="curative/palliative/adjuvant/neoadjuvant")
    notes: Optional[str] = None


# Import surgery models for use as a treatment type
# (We'll keep the existing surgery.py models and reference them)


# ============== CREATE/UPDATE MODELS ==============

class EpisodeCreate(BaseModel):
    """Model for creating new episodes"""
    episode_id: str
    patient_id: str
    condition_type: ConditionType
    cancer_type: Optional[CancerType] = None
    cancer_data: Optional[CancerSpecificData] = None
    referral_date: Union[datetime, date, str]
    first_seen_date: Optional[Union[datetime, date, str]] = None
    mdt_discussion_date: Optional[Union[datetime, date, str]] = None
    
    # NBOCA COSD Referral Pathway Fields
    referral_source: Optional[str] = None
    provider_first_seen: Optional[str] = None
    cns_involved: Optional[str] = None
    mdt_meeting_type: Optional[str] = None
    performance_status: Optional[str] = None
    no_treatment_reason: Optional[str] = None
    
    lead_clinician: str
    mdt_team: List[str] = Field(default_factory=list)
    episode_status: str = "active"
    created_by: str
    last_modified_by: str
    treatments: List[dict] = Field(default_factory=list)
    tumours: List[dict] = Field(default_factory=list)


class EpisodeUpdate(BaseModel):
    """Model for updating episodes"""
    first_seen_date: Optional[Union[datetime, date, str]] = None
    mdt_discussion_date: Optional[Union[datetime, date, str]] = None
    
    # NBOCA COSD Referral Pathway Fields
    referral_source: Optional[str] = None
    provider_first_seen: Optional[str] = None
    cns_involved: Optional[str] = None
    mdt_meeting_type: Optional[str] = None
    performance_status: Optional[str] = None
    no_treatment_reason: Optional[str] = None
    
    lead_clinician: Optional[str] = None
    mdt_team: Optional[List[str]] = None
    episode_status: Optional[str] = None
    cancer_data: Optional[CancerSpecificData] = None
    treatments: Optional[List[dict]] = None
    tumours: Optional[List[dict]] = None
    last_modified_by: str
    last_modified_at: datetime = Field(default_factory=datetime.utcnow)


class Episode(EpisodeBase):
    """Episode model with MongoDB ID"""
    id: Optional[str] = Field(None, alias="_id")
    cancer_type: Optional[CancerType] = None
    cancer_data: Optional[CancerSpecificData] = None
    treatments: List[dict] = Field(default_factory=list)
    tumours: List[dict] = Field(default_factory=list, description="Individual tumour sites tracked in this episode")
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
