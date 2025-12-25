"""
Audit logging utility for tracking user actions
"""
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import Request
import secrets


async def log_action(
    db_collection,
    user_id: str,
    username: str,
    action: str,
    entity_type: str,
    entity_id: str,
    entity_name: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
):
    """
    Log a user action to the audit log
    
    Args:
        db_collection: MongoDB audit_logs collection
        user_id: User performing the action
        username: Username for display
        action: Action type (create, update, delete, view)
        entity_type: Type of entity (patient, episode, treatment, etc.)
        entity_id: ID of the affected entity
        entity_name: Human-readable description of the entity
        details: Additional details about the action
        request: FastAPI request object for IP/user-agent extraction
    """
    log_entry = {
        "log_id": f"LOG-{secrets.token_hex(8).upper()}",
        "timestamp": datetime.utcnow(),
        "user_id": user_id,
        "username": username,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "entity_name": entity_name,
        "details": details or {},
        "ip_address": request.client.host if request else None,
        "user_agent": request.headers.get("user-agent") if request else None
    }
    
    await db_collection.insert_one(log_entry)
    return log_entry


def format_activity_message(log_entry: dict) -> str:
    """
    Format an audit log entry into a human-readable activity message
    
    Args:
        log_entry: Audit log entry dictionary
        
    Returns:
        Human-readable activity string
    """
    action = log_entry["action"]
    entity_type = log_entry["entity_type"]
    entity_name = log_entry.get("entity_name", log_entry["entity_id"])
    
    action_map = {
        "create": "created",
        "update": "updated",
        "delete": "deleted",
        "view": "viewed"
    }
    
    action_text = action_map.get(action, action)
    
    # Format entity type for display
    entity_display = entity_type.replace("_", " ").title()
    
    return f"{action_text.capitalize()} {entity_display}: {entity_name}"
