"""
Audit log model for tracking user actions across the system
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class AuditLogEntry(BaseModel):
    """Audit log entry model"""
    log_id: str = Field(..., description="Unique log entry ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the action occurred")
    user_id: str = Field(..., description="User who performed the action")
    username: str = Field(..., description="Username for display")
    action: str = Field(..., description="Action type: create, update, delete, view")
    entity_type: str = Field(..., description="Type of entity: patient, episode, treatment, tumour, investigation, user")
    entity_id: str = Field(..., description="ID of the affected entity")
    entity_name: Optional[str] = Field(None, description="Human-readable name/description of entity")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional action details")
    ip_address: Optional[str] = Field(None, description="IP address of the user")
    user_agent: Optional[str] = Field(None, description="Browser/client user agent")


class AuditLogCreate(BaseModel):
    """Audit log creation model"""
    user_id: str
    username: str
    action: str
    entity_type: str
    entity_id: str
    entity_name: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
