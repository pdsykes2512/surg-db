"""Investigation routes for managing clinical investigations and imaging."""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
from datetime import datetime

from ..database import get_investigations_collection
from ..auth import get_current_user
from ..models.investigation import Investigation

router = APIRouter(prefix="/api/investigations", tags=["investigations"])

@router.get("/", response_model=List[Investigation])
async def get_investigations(
    patient_id: Optional[str] = Query(None),
    episode_id: Optional[str] = Query(None),
    tumour_id: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get investigations filtered by patient, episode, tumour, or type."""
    investigations_collection = await get_investigations_collection()
    
    query = {}
    if patient_id:
        query["patient_id"] = patient_id
    if episode_id:
        query["episode_id"] = episode_id
    if tumour_id:
        query["tumour_id"] = tumour_id
    if type:
        query["type"] = type
    
    cursor = investigations_collection.find(query, {"_id": 0}).sort("date", -1)
    investigations = await cursor.to_list(length=None)
    return investigations

@router.get("/{investigation_id}", response_model=Investigation)
async def get_investigation(
    investigation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific investigation by ID."""
    investigations_collection = await get_investigations_collection()
    
    investigation = await investigations_collection.find_one({"investigation_id": investigation_id}, {"_id": 0})
    if not investigation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")
    return investigation

@router.post("/", response_model=Investigation, status_code=status.HTTP_201_CREATED)
async def create_investigation(
    investigation: Investigation,
    current_user: dict = Depends(get_current_user)
):
    """Create a new investigation record."""
    investigations_collection = await get_investigations_collection()
    
    investigation_dict = investigation.model_dump()
    investigation_dict["created_at"] = datetime.utcnow()
    investigation_dict["updated_at"] = datetime.utcnow()
    
    # Check if investigation_id already exists
    existing = await investigations_collection.find_one({"investigation_id": investigation.investigation_id})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Investigation ID already exists")
    
    await investigations_collection.insert_one(investigation_dict)
    return investigation_dict

@router.put("/{investigation_id}", response_model=Investigation)
async def update_investigation(
    investigation_id: str,
    investigation: Investigation,
    current_user: dict = Depends(get_current_user)
):
    """Update an existing investigation."""
    investigations_collection = await get_investigations_collection()
    
    existing = await investigations_collection.find_one({"investigation_id": investigation_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")
    
    investigation_dict = investigation.model_dump()
    investigation_dict["updated_at"] = datetime.utcnow()
    
    await investigations_collection.update_one(
        {"investigation_id": investigation_id},
        {"$set": investigation_dict}
    )
    
    return investigation_dict

@router.delete("/{investigation_id}")
async def delete_investigation(
    investigation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an investigation."""
    investigations_collection = await get_investigations_collection()
    
    result = await investigations_collection.delete_one({"investigation_id": investigation_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")
    return {"message": "Investigation deleted successfully"}

