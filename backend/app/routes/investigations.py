"""Investigation routes for managing clinical investigations and imaging."""
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from typing import List, Optional
from datetime import datetime

from ..database import get_database, get_audit_logs_collection
from ..auth import get_current_user
from ..models.investigation import Investigation
from ..utils.audit import log_action

router = APIRouter(prefix="/api/investigations", tags=["investigations"])

@router.get("/", response_model=List[Investigation])
async def get_investigations(
    patient_id: Optional[str] = Query(None),
    episode_id: Optional[str] = Query(None),
    tumour_id: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    db = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """Get investigations filtered by patient, episode, tumour, or type."""
    query = {}
    
    if patient_id:
        query["patient_id"] = patient_id
    if episode_id:
        query["episode_id"] = episode_id
    if tumour_id:
        query["tumour_id"] = tumour_id
    if type:
        query["type"] = type
    
    investigations = list(db.investigations.find(query, {"_id": 0}).sort("date", -1))
    return investigations

@router.get("/{investigation_id}", response_model=Investigation)
async def get_investigation(
    investigation_id: str,
    db = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific investigation by ID."""
    investigation = db.investigations.find_one({"investigation_id": investigation_id}, {"_id": 0})
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return investigation

@router.post("/", response_model=Investigation)
async def create_investigation(
    investigation: Investigation,
    request: Request,
    db = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """Create a new investigation record."""
    audit_collection = await get_audit_logs_collection()
    
    investigation_dict = investigation.model_dump()
    investigation_dict["created_at"] = datetime.utcnow()
    investigation_dict["updated_at"] = datetime.utcnow()
    investigation_dict["created_by"] = current_user["username"]
    investigation_dict["updated_by"] = current_user["username"]
    
    # Check if investigation_id already exists
    existing = db.investigations.find_one({"investigation_id": investigation.investigation_id})
    if existing:
        raise HTTPException(status_code=400, detail="Investigation ID already exists")
    
    db.investigations.insert_one(investigation_dict)
    
    # Log audit entry
    await log_action(
        audit_collection,
        user_id=current_user["user_id"],
        username=current_user["username"],
        action="create",
        entity_type="investigation",
        entity_id=investigation.investigation_id,
        entity_name=f"Investigation {investigation.type}",
        details={
            "patient_id": investigation.patient_id,
            "episode_id": investigation.episode_id,
            "type": investigation.type
        },
        request=request
    )
    
    return investigation_dict

@router.put("/{investigation_id}", response_model=Investigation)
async def update_investigation(
    investigation_id: str,
    investigation: Investigation,
    request: Request,
    db = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """Update an existing investigation."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Attempting to update investigation: {investigation_id}")
    
    audit_collection = await get_audit_logs_collection()
    
    existing = db.investigations.find_one({"investigation_id": investigation_id})
    logger.info(f"Database lookup result: {'Found' if existing else 'Not Found'}")
    
    if not existing:
        # Log more details to help debug
        logger.error(f"Investigation {investigation_id} not found in database")
        count = db.investigations.count_documents({})
        logger.error(f"Total investigations in database: {count}")
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    investigation_dict = investigation.model_dump()
    investigation_dict["updated_at"] = datetime.utcnow()
    investigation_dict["updated_by"] = current_user["username"]
    
    db.investigations.update_one(
        {"investigation_id": investigation_id},
        {"$set": investigation_dict}
    )
    
    logger.info(f"Successfully updated investigation: {investigation_id}")
    
    # Log audit entry
    await log_action(
        audit_collection,
        user_id=current_user["user_id"],
        username=current_user["username"],
        action="update",
        entity_type="investigation",
        entity_id=investigation_id,
        entity_name=f"Investigation {investigation.type}",
        details={
            "patient_id": investigation.patient_id,
            "fields_updated": list(investigation_dict.keys())
        },
        request=request
    )
    
    return investigation_dict

@router.delete("/{investigation_id}")
async def delete_investigation(
    investigation_id: str,
    request: Request,
    db = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """Delete an investigation."""
    audit_collection = await get_audit_logs_collection()
    
    # Get investigation info before deletion
    existing = db.investigations.find_one({"investigation_id": investigation_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    # Delete investigation
    result = db.investigations.delete_one({"investigation_id": investigation_id})
    
    # Log audit entry
    await log_action(
        audit_collection,
        user_id=current_user["user_id"],
        username=current_user["username"],
        action="delete",
        entity_type="investigation",
        entity_id=investigation_id,
        entity_name=f"Investigation {existing.get('type', 'Unknown')}",
        details={
            "patient_id": existing.get("patient_id"),
            "episode_id": existing.get("episode_id"),
            "type": existing.get("type")
        },
        request=request
    )
    
    return {"message": "Investigation deleted successfully"}
