"""
Surgery data models for general surgery outcomes tracking
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Union
from datetime import datetime, date
from bson import ObjectId
from .patient import PyObjectId
from .utils import parse_date_string


class Classification(BaseModel):
    """Surgery classification"""
    urgency: str = Field(..., description="elective/emergency/urgent")
    complexity: Optional[str] = Field(None, description="routine/intermediate/complex")
    primary_diagnosis: str
    indication: Optional[str] = Field(None, description="cancer/ibd/diverticular/benign/other")


class Procedure(BaseModel):
    """Surgery procedure details"""
    primary_procedure: str = Field(..., min_length=1)
    additional_procedures: List[str] = Field(default_factory=list)
    cpt_codes: List[str] = Field(default_factory=list)
    icd10_codes: List[str] = Field(default_factory=list)
    opcs4_codes: List[str] = Field(default_factory=list)
    approach: str = Field(..., description="open/laparoscopic/robotic/converted")
    robotic_surgery: bool = Field(False, description="Whether robotic assistance was used")
    conversion_to_open: bool = Field(False, description="Whether laparoscopic procedure was converted to open")
    conversion_reason: Optional[str] = Field(None, description="Reason for conversion: oncological/adhesions/bleeding/fat/difficult_op/time/technical/other")
    description: Optional[str] = None


class PerioperativeTimeline(BaseModel):
    """Perioperative timeline with admission, surgery, and discharge dates"""
    admission_date: Union[datetime, date, str]
    surgery_date: Union[datetime, date, str]
    induction_time: Optional[Union[datetime, str]] = None
    knife_to_skin_time: Optional[Union[datetime, str]] = None
    surgery_end_time: Optional[Union[datetime, str]] = None
    anesthesia_duration_minutes: Optional[int] = Field(None, ge=0)
    operation_duration_minutes: Optional[int] = Field(None, ge=0)
    discharge_date: Optional[Union[datetime, date, str]] = None
    length_of_stay_days: Optional[int] = Field(None, ge=0)
    
    @field_validator('admission_date', 'surgery_date', 'discharge_date', mode='before')
    @classmethod
    def parse_dates(cls, v):
        """Parse date strings to standardized format.
        
        Args:
            v: Date string or datetime object
        
        Returns:
            datetime or str: Parsed date in standardized format
        """
        return parse_date_string(v)
    
    @field_validator('induction_time', 'knife_to_skin_time', 'surgery_end_time', mode='before')
    @classmethod
    def parse_datetimes(cls, v):
        return parse_date_string(v)


class SurgicalTeam(BaseModel):
    """Surgical team members"""
    primary_surgeon: str = Field(..., min_length=1)
    assistant_surgeons: List[str] = Field(default_factory=list)
    assistant_grade: Optional[str] = Field(None, description="Grade of first assistant surgeon")
    second_assistant: Optional[str] = Field(None, description="Second assistant surgeon")
    anesthesiologist: Optional[str] = None
    scrub_nurse: Optional[str] = None
    circulating_nurse: Optional[str] = None


class Intraoperative(BaseModel):
    """Intraoperative details"""
    anesthesia_type: Optional[str] = Field(None, description="general/regional/local")
    blood_loss_ml: Optional[int] = Field(None, ge=0)
    transfusion_required: bool = False
    units_transfused: Optional[int] = Field(None, ge=0)
    findings: Optional[str] = None
    specimens_sent: List[str] = Field(default_factory=list)
    drains_placed: bool = False
    drain_types: List[str] = Field(default_factory=list)
    # Colorectal-specific: Stoma
    stoma_created: bool = Field(False, description="Whether a stoma was created")
    stoma_type: Optional[str] = Field(None, description="Type of stoma: ileostomy_temporary/ileostomy_permanent/colostomy_temporary/colostomy_permanent")
    stoma_closure_date: Optional[Union[datetime, date, str]] = Field(None, description="Date when stoma was closed - auto-set from surgery_reversal")
    reversal_treatment_id: Optional[str] = Field(None, description="Treatment ID of surgery_reversal that closed this stoma")
    # Colorectal-specific: Anastomosis
    anastomosis_performed: bool = Field(False, description="Whether an anastomosis was performed")
    anastomosis_type: Optional[str] = Field(None, description="Type: hand_sewn/stapled/hybrid")
    anastomosis_configuration: Optional[str] = Field(None, description="Configuration: end_to_end/end_to_side/side_to_side/side_to_end")
    anastomosis_height_cm: Optional[float] = Field(None, ge=0, description="Height of anastomosis from anal verge in cm")
    anastomosis_location: Optional[str] = Field(None, description="Anatomical location: colorectal/coloanal/ileocolic/ileorectal/other")
    anterior_resection_type: Optional[str] = Field(None, description="Type of anterior resection: high/low")
    defunctioning_stoma: bool = Field(False, description="Whether a defunctioning/protective stoma was created for this anastomosis")
    
    @field_validator('stoma_closure_date', mode='before')
    @classmethod
    def parse_closure_date(cls, v):
        return parse_date_string(v)


class TNMStaging(BaseModel):
    """TNM cancer staging"""
    clinical_t: Optional[str] = None
    clinical_n: Optional[str] = None
    clinical_m: Optional[str] = None
    pathological_t: Optional[str] = None
    pathological_n: Optional[str] = None
    pathological_m: Optional[str] = None


class Pathology(BaseModel):
    """Pathology results"""
    histology: Optional[str] = None
    grade: Optional[str] = None
    lymph_nodes_examined: Optional[int] = Field(None, ge=0)
    lymph_nodes_positive: Optional[int] = Field(None, ge=0)
    margins: Optional[str] = Field(None, description="clear/involved/close")
    margin_distance_mm: Optional[float] = Field(None, ge=0)
    tumor_size_mm: Optional[float] = Field(None, ge=0)
    lymphovascular_invasion: Optional[bool] = None
    perineural_invasion: Optional[bool] = None


class CancerSpecific(BaseModel):
    """Cancer-specific data"""
    applicable: bool = False
    cancer_type: Optional[str] = None
    tnm_staging: Optional[TNMStaging] = None
    pathology: Optional[Pathology] = None
    neoadjuvant_therapy: bool = False
    neoadjuvant_details: Optional[str] = None
    adjuvant_therapy_planned: bool = False
    # Surgical intent for cancer
    surgical_intent: Optional[str] = Field(None, description="curative/palliative/uncertain")
    palliative_reason: Optional[str] = Field(None, description="Reason if palliative: local_disease/distant_disease/other")


class IBDSpecific(BaseModel):
    """IBD-specific data"""
    applicable: bool = False
    disease_type: Optional[str] = Field(None, description="crohns/ulcerative_colitis")
    disease_extent: Optional[str] = None
    previous_biologics: List[str] = Field(default_factory=list)
    indication_for_surgery: Optional[str] = None
    stoma_created: bool = False
    stoma_type: Optional[str] = None


class HerniaSpecific(BaseModel):
    """Hernia-specific data"""
    applicable: bool = False
    hernia_type: Optional[str] = Field(None, description="inguinal/ventral/incisional/umbilical/femoral")
    hernia_size_cm: Optional[float] = Field(None, ge=0)
    recurrent: bool = False
    mesh_used: bool = False
    mesh_type: Optional[str] = None
    mesh_fixation: Optional[str] = None
    component_separation: bool = False


class ReturnToTheatre(BaseModel):
    """Return to theatre event - auto-populated from surgery_rtt relationships"""
    occurred: bool = False
    date: Optional[datetime] = None
    reason: Optional[str] = None
    procedure_performed: Optional[str] = None
    rtt_treatment_id: Optional[str] = Field(None, description="Treatment ID of first surgery_rtt")


class EscalationOfCare(BaseModel):
    """Escalation to HDU/ICU"""
    occurred: bool = False
    destination: Optional[str] = Field(None, description="hdu/icu")
    date: Optional[datetime] = None
    reason: Optional[str] = None
    duration_days: Optional[int] = Field(None, ge=0)


class Complication(BaseModel):
    """Surgery complication record"""
    type: str
    clavien_dindo_grade: Optional[str] = Field(None, description="I/II/IIIa/IIIb/IVa/IVb/V")
    description: str
    date_identified: datetime
    treatment: Optional[str] = None
    resolved: bool = False


class AnastomoticLeak(BaseModel):
    """Detailed anastomotic leak tracking for NBOCA compliance"""
    occurred: bool = False
    severity: Optional[str] = Field(None, description="Grade: A (asymptomatic)/B (requiring intervention but not reop)/C (requiring reoperation)")
    date_identified: Optional[datetime] = None
    days_post_surgery: Optional[int] = Field(None, ge=0, description="Number of days after surgery")
    presentation: Optional[str] = Field(None, description="How detected: clinical/radiological/endoscopic/at_reoperation")
    clinical_signs: List[str] = Field(default_factory=list, description="e.g., fever, tachycardia, peritonitis, sepsis")
    
    # Investigation findings
    ct_finding: Optional[str] = Field(None, description="CT findings: free_fluid/gas/contrast_leak/collection/none")
    endoscopy_finding: Optional[str] = Field(None, description="Endoscopy findings: defect_visible/dehiscence/ischemia/normal")
    
    # Management
    management: Optional[str] = Field(None, description="conservative/percutaneous_drainage/endoscopic_intervention/reoperation")
    reoperation_performed: bool = False
    reoperation_procedure: Optional[str] = Field(None, description="Procedure: washout/resection/stoma_formation/anastomotic_revision")
    reoperation_date: Optional[datetime] = None
    
    # Outcomes
    icu_admission: bool = False
    icu_length_of_stay_days: Optional[int] = Field(None, ge=0)
    total_hospital_stay_days: Optional[int] = Field(None, ge=0, description="Total days from original surgery to discharge after leak")
    mortality: bool = False
    resolved: bool = False
    resolution_date: Optional[datetime] = None
    
    # NBOCA specific
    defunctioning_stoma_present: Optional[bool] = Field(None, description="Was there a protective stoma at time of leak?")
    notes: Optional[str] = None


class PostoperativeEvents(BaseModel):
    """Postoperative events and complications"""
    return_to_theatre: Optional[ReturnToTheatre] = Field(default_factory=ReturnToTheatre)
    escalation_of_care: Optional[EscalationOfCare] = Field(default_factory=EscalationOfCare)
    complications: List[Complication] = Field(default_factory=list)
    
    # Specific tracking for anastomotic leak (NBOCA requirement)
    anastomotic_leak: Optional[AnastomoticLeak] = Field(default_factory=AnastomoticLeak, description="Detailed anastomotic leak tracking")


class Outcomes(BaseModel):
    """Surgery outcomes"""
    readmission_30day: bool = False
    readmission_date: Optional[datetime] = None
    readmission_reason: Optional[str] = None
    mortality_30day: bool = False
    mortality_90day: bool = False
    date_of_death: Optional[datetime] = None
    cause_of_death: Optional[str] = None


class FollowUpAppointment(BaseModel):
    """Follow-up appointment record"""
    date: datetime
    type: str = Field(..., description="post_op/surveillance/mdt")
    provider: str
    findings: Optional[str] = None
    imaging_results: Optional[str] = None
    plan: Optional[str] = None


class LongTermOutcomes(BaseModel):
    """Long-term follow-up outcomes"""
    recurrence: bool = False
    recurrence_date: Optional[datetime] = None
    recurrence_type: Optional[str] = None
    functional_status: Optional[str] = None
    quality_of_life_score: Optional[int] = Field(None, ge=0, le=100)


class FollowUp(BaseModel):
    """Surgery follow-up information"""
    appointments: List[FollowUpAppointment] = Field(default_factory=list)
    long_term_outcomes: Optional[LongTermOutcomes] = Field(default_factory=LongTermOutcomes)


class Document(BaseModel):
    """Attached document metadata"""
    type: str = Field(..., description="operation_note/pathology_report/imaging/discharge_summary")
    filename: str
    file_path: str
    uploaded_date: datetime = Field(default_factory=datetime.utcnow)
    uploaded_by: Optional[str] = None


class Modification(BaseModel):
    """Audit trail modification record"""
    timestamp: datetime
    user: str
    field_changed: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None


class AuditTrail(BaseModel):
    """Audit trail for data changes"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = None
    modifications: List[Modification] = Field(default_factory=list)


class IntegrationData(BaseModel):
    """External system integration data"""
    ehr_encounter_id: Optional[str] = None
    lab_system_ids: List[str] = Field(default_factory=list)
    pacs_study_ids: List[str] = Field(default_factory=list)
    last_sync: Optional[datetime] = None


class SurgeryBase(BaseModel):
    """Base surgery model"""
    surgery_id: str = Field(..., min_length=1)
    patient_id: str = Field(..., min_length=1, description="Patient MRN")
    classification: Classification
    procedure: Procedure
    perioperative_timeline: PerioperativeTimeline
    team: SurgicalTeam
    intraoperative: Optional[Intraoperative] = Field(default_factory=Intraoperative)
    cancer_specific: Optional[CancerSpecific] = Field(default_factory=CancerSpecific)
    ibd_specific: Optional[IBDSpecific] = Field(default_factory=IBDSpecific)
    hernia_specific: Optional[HerniaSpecific] = Field(default_factory=HerniaSpecific)
    postoperative_events: Optional[PostoperativeEvents] = Field(default_factory=PostoperativeEvents)
    outcomes: Optional[Outcomes] = Field(default_factory=Outcomes)
    follow_up: Optional[FollowUp] = Field(default_factory=FollowUp)
    documents: List[Document] = Field(default_factory=list)
    integration_data: Optional[IntegrationData] = Field(default_factory=IntegrationData)


class SurgeryCreate(SurgeryBase):
    """Surgery creation model"""
    audit_trail: AuditTrail


class SurgeryUpdate(BaseModel):
    """Surgery update model - all fields optional"""
    surgery_id: Optional[str] = None
    patient_id: Optional[str] = None
    classification: Optional[Classification] = None
    procedure: Optional[Procedure] = None
    perioperative_timeline: Optional[PerioperativeTimeline] = None
    team: Optional[SurgicalTeam] = None
    intraoperative: Optional[Intraoperative] = None
    cancer_specific: Optional[CancerSpecific] = None
    ibd_specific: Optional[IBDSpecific] = None
    hernia_specific: Optional[HerniaSpecific] = None
    postoperative_events: Optional[PostoperativeEvents] = None
    outcomes: Optional[Outcomes] = None
    follow_up: Optional[FollowUp] = None
    documents: Optional[List[Document]] = None
    integration_data: Optional[IntegrationData] = None


class SurgeryInDB(SurgeryBase):
    """Surgery model as stored in database"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    audit_trail: AuditTrail
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Surgery(SurgeryInDB):
    """Surgery/Episode response model with related entities"""
    treatments: List[dict] = Field(default_factory=list, description="Treatments associated with this episode")
    tumours: List[dict] = Field(default_factory=list, description="Tumours associated with this episode")
