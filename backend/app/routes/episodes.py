"""
Episode API routes
"""
from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from ..models.surgery import Surgery, SurgeryCreate, SurgeryUpdate
from ..database import get_surgeries_collection, get_patients_collection


router = APIRouter(prefix="/api/episodes", tags=["episodes"])


@router.post("/", response_model=Surgery, status_code=status.HTTP_201_CREATED)
async def create_episode(surgery: SurgeryCreate):
    """Create a new episode record"""
    try:
        collection = await get_surgeries_collection()
        patients_collection = await get_patients_collection()
        
        # Verify patient exists (patient_id is the record_number/MRN)
        patient = await patients_collection.find_one({"record_number": surgery.patient_id})
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Patient with MRN {surgery.patient_id} not found"
            )
        
        # Check if surgery_id already exists
        existing = await collection.find_one({"surgery_id": surgery.surgery_id})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Surgery with ID {surgery.surgery_id} already exists"
            )
        
        # Insert surgery (audit_trail is already included in SurgeryCreate model)
        surgery_dict = surgery.model_dump()
        
        result = await collection.insert_one(surgery_dict)
        
        # Retrieve and return created surgery
        created_surgery = await collection.find_one({"_id": result.inserted_id})
        return Surgery(**created_surgery)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error creating episode: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create episode: {str(e)}"
        )


@router.get("/", response_model=List[Surgery])
async def list_episodes(
    skip: int = 0,
    limit: int = 100,
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    category: Optional[str] = Query(None, description="Filter by category (major_resection/proctology/hernia/cholecystectomy)"),
    urgency: Optional[str] = Query(None, description="Filter by urgency (elective/emergency/urgent)"),
    primary_surgeon: Optional[str] = Query(None, description="Filter by primary surgeon"),
    start_date: Optional[str] = Query(None, description="Filter surgeries after this date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter surgeries before this date (YYYY-MM-DD)")
):
    """List all surgeries with pagination and optional filters"""
    collection = await get_surgeries_collection()
    
    # Build query filters
    query = {}
    if patient_id:
        query["patient_id"] = patient_id
    if category:
        query["classification.category"] = category
    if urgency:
        query["classification.urgency"] = urgency
    if primary_surgeon:
        query["team.primary_surgeon"] = primary_surgeon
    
    # Date range filtering
    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = datetime.fromisoformat(start_date)
        if end_date:
            date_query["$lte"] = datetime.fromisoformat(end_date)
        query["perioperative_timeline.surgery_date"] = date_query
    
    cursor = collection.find(query).sort("perioperative_timeline.surgery_date", -1).skip(skip).limit(limit)
    surgeries = await cursor.to_list(length=limit)
    
    return [Surgery(**surgery) for surgery in surgeries]


@router.get("/{surgery_id}", response_model=Surgery)
async def get_episode(surgery_id: str):
    """Get a specific episode by surgery_id"""
    collection = await get_surgeries_collection()
    
    surgery = await collection.find_one({"surgery_id": surgery_id})
    if not surgery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Surgery {surgery_id} not found"
        )
    
    return Surgery(**surgery)


@router.put("/{surgery_id}", response_model=Surgery)
async def update_episode(surgery_id: str, surgery_update: SurgeryUpdate):
    """Update an episode record"""
    collection = await get_surgeries_collection()
    
    # Check if surgery exists
    existing = await collection.find_one({"surgery_id": surgery_id})
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Surgery {surgery_id} not found"
        )
    
    # Update only provided fields
    update_data = surgery_update.model_dump(exclude_unset=True)
    if update_data:
        # Update audit trail
        await collection.update_one(
            {"surgery_id": surgery_id},
            {
                "$set": {
                    **update_data,
                    "audit_trail.updated_at": datetime.utcnow(),
                    "audit_trail.updated_by": "system"  # TODO: Replace with actual user from auth
                }
            }
        )
    
    # Return updated surgery
    updated_surgery = await collection.find_one({"surgery_id": surgery_id})
    return Surgery(**updated_surgery)


@router.delete("/{surgery_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_episode(surgery_id: str):
    """Delete an episode record"""
    collection = await get_surgeries_collection()
    
    result = await collection.delete_one({"surgery_id": surgery_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Surgery {surgery_id} not found"
        )
    
    return None
