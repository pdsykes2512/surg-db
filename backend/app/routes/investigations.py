"""Investigation routes for managing clinical investigations and imaging."""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime

from ..database import get_database
from ..auth import get_current_user
from ..models.investigation import Investigation

router = APIRouter()

@router.get("/investigations", response_model=List[Investigation])
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

@router.get("/investigations/{investigation_id}", response_model=Investigation)
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

@router.post("/investigations", response_model=Investigation)
async def create_investigation(
    investigation: Investigation,
    db = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """Create a new investigation record."""
    investigation_dict = investigation.model_dump()
    investigation_dict["created_at"] = datetime.utcnow()
    investigation_dict["updated_at"] = datetime.utcnow()
    
    # Check if investigation_id already exists
    existing = db.investigations.find_one({"investigation_id": investigation.investigation_id})
    if existing:
        raise HTTPException(status_code=400, detail="Investigation ID already exists")
    
    db.investigations.insert_one(investigation_dict)
    return investigation_dict

@router.put("/investigations/{investigation_id}", response_model=Investigation)
async def update_investigation(
    investigation_id: str,
    investigation: Investigation,
    db = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """Update an existing investigation."""
    existing = db.investigations.find_one({"investigation_id": investigation_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    investigation_dict = investigation.model_dump()
    investigation_dict["updated_at"] = datetime.utcnow()
    
    db.investigations.update_one(
        {"investigation_id": investigation_id},
        {"$set": investigation_dict}
    )
    
    return investigation_dict

@router.delete("/investigations/{investigation_id}")
async def delete_investigation(
    investigation_id: str,
    db = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """Delete an investigation."""
    result = db.investigations.delete_one({"investigation_id": investigation_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return {"message": "Investigation deleted successfully"}
