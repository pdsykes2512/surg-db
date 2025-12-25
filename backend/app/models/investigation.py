"""Investigation model for storing clinical investigations and imaging results."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class Investigation(BaseModel):
    """Clinical investigation or imaging study."""
    investigation_id: str = Field(..., description="Unique investigation identifier")
    patient_id: str = Field(..., description="Associated patient ID")
    episode_id: Optional[str] = Field(None, description="Associated episode ID")
    tumour_id: Optional[str] = Field(None, description="Associated tumour ID")
    
    type: str = Field(..., description="Investigation type: imaging, endoscopy, laboratory")
    subtype: str = Field(..., description="Specific investigation: ct_abdomen, mri_primary, colonoscopy, etc")
    
    date: Optional[str] = Field(None, description="Investigation date (YYYY-MM-DD)")
    result: Optional[str] = Field(None, description="Primary result/finding")
    findings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Detailed findings")
    
    report_url: Optional[str] = Field(None, description="Link to full report in EHR")
    
    notes: Optional[str] = Field(None, description="Additional notes")
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "investigation_id": "INV-ABC123-MRI-01",
                "patient_id": "ABC123",
                "episode_id": "E-ABC123-01",
                "tumour_id": "TUM-ABC123-01",
                "type": "imaging",
                "subtype": "mri_primary",
                "date": "2024-03-15",
                "result": "T3N1 disease",
                "findings": {
                    "t_stage": "3",
                    "n_stage": "1",
                    "crm_status": "negative",
                    "distance_from_anal_verge": 8.5,
                    "emvi": "negative"
                },
                "report_url": None
            }
        }
