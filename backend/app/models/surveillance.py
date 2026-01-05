"""
Surveillance schedule models for tracking cancer follow-up investigations

Supports automated scheduling of investigations based on clinical protocols
(e.g., NBOCA colorectal cancer surveillance guidelines)
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from datetime import datetime, date
from bson import ObjectId


class SurveillanceScheduleBase(BaseModel):
    """Base model for surveillance schedules"""
    patient_id: str = Field(..., description="Patient identifier")
    episode_id: str = Field(..., description="Episode identifier")
    surveillance_type: Literal[
        "colonoscopy",
        "ct_abdomen_pelvis",
        "ct_chest",
        "ct_thorax_abdomen_pelvis",  # CT CAP
        "mri_pelvis",
        "cea_blood_test",
        "clinic_visit",
        "other"
    ] = Field(..., description="Type of surveillance investigation")

    protocol: str = Field(
        default="nboca_colorectal",
        description="Surveillance protocol (nboca_colorectal/custom)"
    )

    due_date: datetime = Field(..., description="Target due date for investigation")
    due_window_start: Optional[datetime] = Field(
        None,
        description="Earliest acceptable date (if None, uses due_date - 2 weeks)"
    )
    due_window_end: Optional[datetime] = Field(
        None,
        description="Latest acceptable date (if None, uses due_date + 4 weeks)"
    )

    status: Literal["pending", "completed", "overdue", "cancelled", "rescheduled"] = Field(
        default="pending",
        description="Status of scheduled investigation"
    )

    frequency_months: Optional[int] = Field(
        None,
        description="Recurring frequency in months (e.g., 6 for every 6 months)"
    )

    end_surveillance_date: Optional[datetime] = Field(
        None,
        description="Date to stop auto-scheduling (typically 5 years post-treatment)"
    )

    assigned_clinician: Optional[str] = Field(
        None,
        description="Clinician responsible for this surveillance item"
    )

    notes: Optional[str] = Field(None, description="Additional notes")

    # Alert configuration
    send_email_reminder: bool = Field(
        default=True,
        description="Send email reminders for this investigation"
    )
    reminder_days_before: int = Field(
        default=14,
        description="Days before due date to send reminder"
    )
    escalation_days_overdue: int = Field(
        default=30,
        description="Days overdue before escalating to senior clinician"
    )


class SurveillanceScheduleCreate(SurveillanceScheduleBase):
    """Model for creating new surveillance schedule"""
    pass


class SurveillanceScheduleUpdate(BaseModel):
    """Model for updating surveillance schedule"""
    due_date: Optional[datetime] = None
    due_window_start: Optional[datetime] = None
    due_window_end: Optional[datetime] = None
    status: Optional[Literal["pending", "completed", "overdue", "cancelled", "rescheduled"]] = None
    notes: Optional[str] = None
    assigned_clinician: Optional[str] = None
    send_email_reminder: Optional[bool] = None


class SurveillanceSchedule(SurveillanceScheduleBase):
    """Full surveillance schedule model with tracking fields"""
    schedule_id: str = Field(..., description="Unique schedule identifier")

    # Completion tracking
    completed_date: Optional[datetime] = Field(None, description="Date investigation was completed")
    investigation_id: Optional[str] = Field(
        None,
        description="Link to investigations collection record"
    )

    # Auto-scheduling
    next_scheduled: Optional[datetime] = Field(
        None,
        description="Next auto-scheduled investigation date"
    )
    recurrence_count: int = Field(
        default=0,
        description="Number of times this has been auto-rescheduled"
    )

    # Alert tracking
    reminder_sent: bool = Field(default=False, description="Whether reminder email was sent")
    reminder_sent_date: Optional[datetime] = Field(None, description="When reminder was sent")
    escalation_sent: bool = Field(default=False, description="Whether escalation alert was sent")
    escalation_sent_date: Optional[datetime] = Field(None, description="When escalation was sent")

    # Audit trail
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    last_modified_at: datetime = Field(default_factory=datetime.utcnow)
    last_modified_by: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "schedule_id": "SURV-ABC123-colonoscopy-01",
                "patient_id": "ABC123",
                "episode_id": "E-ABC123-01",
                "surveillance_type": "colonoscopy",
                "protocol": "nboca_colorectal",
                "due_date": "2026-06-15T00:00:00",
                "status": "pending",
                "frequency_months": 12,
                "assigned_clinician": "Dr. Smith",
                "notes": "First post-operative surveillance colonoscopy"
            }
        }


class SurveillanceProtocolTemplate(BaseModel):
    """Template for defining surveillance protocols"""
    protocol_name: str = Field(..., description="Protocol identifier")
    display_name: str = Field(..., description="Human-readable protocol name")
    condition_type: Literal["cancer", "ibd", "benign"] = Field(..., description="Condition type")
    cancer_type: Optional[str] = Field(None, description="Specific cancer type if applicable")

    description: str = Field(..., description="Protocol description")

    # Criteria for protocol applicability
    applicable_stages: Optional[List[str]] = Field(
        None,
        description="Cancer stages this protocol applies to (e.g., ['I', 'II', 'III'])"
    )
    treatment_intent_required: Optional[Literal["curative", "palliative"]] = Field(
        None,
        description="Required treatment intent"
    )

    # Surveillance items
    investigations: List[dict] = Field(
        ...,
        description="List of investigations with timing (see example)"
    )

    duration_years: int = Field(
        default=5,
        description="Total duration of surveillance protocol"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "protocol_name": "nboca_colorectal_stage_2_3",
                "display_name": "NBOCA Colorectal Stage II-III Surveillance",
                "condition_type": "cancer",
                "cancer_type": "bowel",
                "description": "Standard follow-up for Stage II-III colorectal cancer per NBOCA guidelines",
                "applicable_stages": ["II", "III"],
                "treatment_intent_required": "curative",
                "duration_years": 5,
                "investigations": [
                    {
                        "type": "colonoscopy",
                        "schedule": [
                            {"months_post_treatment": 12, "description": "1-year post-op"},
                            {"months_post_treatment": 36, "description": "3-year surveillance"},
                            {"months_post_treatment": 60, "description": "5-year surveillance"}
                        ]
                    },
                    {
                        "type": "cea_blood_test",
                        "schedule": [
                            {"frequency_months": 3, "duration_months": 24, "description": "Every 3 months for 2 years"},
                            {"frequency_months": 6, "duration_months": 36, "start_after_months": 24, "description": "Every 6 months for years 3-5"}
                        ]
                    },
                    {
                        "type": "ct_thorax_abdomen_pelvis",
                        "schedule": [
                            {"frequency_months": 6, "duration_months": 24, "description": "Every 6 months for 2 years"},
                            {"frequency_months": 12, "duration_months": 36, "start_after_months": 24, "description": "Annually for years 3-5"}
                        ]
                    },
                    {
                        "type": "clinic_visit",
                        "schedule": [
                            {"frequency_months": 3, "duration_months": 24, "description": "Every 3 months for 2 years"},
                            {"frequency_months": 6, "duration_months": 36, "start_after_months": 24, "description": "Every 6 months for years 3-5"}
                        ]
                    }
                ]
            }
        }


class SurveillanceSummary(BaseModel):
    """Summary statistics for surveillance dashboard"""
    total_scheduled: int = Field(default=0, description="Total scheduled investigations")
    pending: int = Field(default=0, description="Pending investigations")
    overdue: int = Field(default=0, description="Overdue investigations")
    due_this_week: int = Field(default=0, description="Due within 7 days")
    due_this_month: int = Field(default=0, description="Due within 30 days")
    completed_this_month: int = Field(default=0, description="Completed in last 30 days")

    by_type: dict = Field(
        default_factory=dict,
        description="Breakdown by investigation type"
    )

    overdue_details: List[dict] = Field(
        default_factory=list,
        description="List of overdue items with patient info"
    )
