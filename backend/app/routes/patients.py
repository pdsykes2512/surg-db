"""
Patient API routes
"""
from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from ..models.patient import Patient, PatientCreate, PatientUpdate
from ..database import get_patients_collection, get_episodes_collection


router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.post("/", response_model=Patient, status_code=status.HTTP_201_CREATED)
async def create_patient(patient: PatientCreate):
    """Create a new patient"""
    collection = await get_patients_collection()
    
    # Check if record_number already exists
    existing = await collection.find_one({"record_number": patient.record_number})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Patient with record number {patient.record_number} already exists"
        )
    
    # Insert patient
    patient_dict = patient.model_dump()
    patient_dict["created_at"] = datetime.utcnow()
    patient_dict["updated_at"] = datetime.utcnow()
    
    result = await collection.insert_one(patient_dict)
    
    # Retrieve and return created patient
    created_patient = await collection.find_one({"_id": result.inserted_id})
    created_patient["_id"] = str(created_patient["_id"])
    return Patient(**created_patient)


@router.get("/count")
async def count_patients():
    """Get total count of patients"""
    collection = await get_patients_collection()
    total = await collection.count_documents({})
    return {"count": total}


@router.get("/", response_model=List[Patient])
async def list_patients(skip: int = 0, limit: int = 100, search: Optional[str] = None):
    """List all patients with pagination and optional search, sorted by most recent episode referral date"""
    collection = await get_patients_collection()
    episodes_collection = await get_episodes_collection()
    
    # Build query with search filter if provided
    query = {}
    if search:
        # Search across patient_id, mrn, and nhs_number (case-insensitive, remove spaces)
        search_pattern = {"$regex": search.replace(" ", ""), "$options": "i"}
        query = {
            "$or": [
                {"patient_id": search_pattern},
                {"mrn": search_pattern},
                {"nhs_number": search_pattern}
            ]
        }
    
    # Use aggregation to join with episodes and get most recent referral date
    pipeline = [
        {"$match": query},
        # Lookup episodes for each patient
        {
            "$lookup": {
                "from": "episodes",
                "localField": "patient_id",
                "foreignField": "patient_id",
                "as": "episodes"
            }
        },
        # Add fields for episode count and most recent referral date
        {
            "$addFields": {
                "episode_count": {"$size": "$episodes"},
                "most_recent_referral": {
                    "$max": {
                        "$map": {
                            "input": "$episodes",
                            "as": "ep",
                            "in": {"$toDate": "$$ep.referral_date"}
                        }
                    }
                }
            }
        },
        # Sort by most recent referral date (nulls last), then by patient_id
        {"$sort": {"most_recent_referral": -1, "patient_id": 1}},
        # Remove the episodes array from output
        {"$project": {"episodes": 0}},
        # Pagination
        {"$skip": skip},
        {"$limit": limit}
    ]
    
    patients = await collection.aggregate(pipeline).to_list(length=None)
    
    # Convert ObjectId to string
    for patient in patients:
        patient["_id"] = str(patient["_id"])
        # Remove most_recent_referral from output (only used for sorting)
        patient.pop("most_recent_referral", None)
    
    return [Patient(**patient) for patient in patients]


@router.get("/{patient_id}", response_model=Patient)
async def get_patient(patient_id: str):
    """Get a specific patient by patient_id"""
    collection = await get_patients_collection()
    
    patient = await collection.find_one({"patient_id": patient_id})
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )
    
    patient["_id"] = str(patient["_id"])
    return Patient(**patient)


@router.put("/{patient_id}", response_model=Patient)
async def update_patient(patient_id: str, patient_update: PatientUpdate):
    """Update a patient"""
    collection = await get_patients_collection()
    
    # Check if patient exists
    existing = await collection.find_one({"patient_id": patient_id})
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )
    
    # Update only provided fields
    update_data = patient_update.model_dump(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        update_data["updated_by"] = "system"  # TODO: Replace with actual user from auth
        await collection.update_one(
            {"patient_id": patient_id},
            {"$set": update_data}
        )
    
    # Return updated patient
    updated_patient = await collection.find_one({"patient_id": patient_id})
    updated_patient["_id"] = str(updated_patient["_id"])
    return Patient(**updated_patient)


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(patient_id: str):
    """Delete a patient"""
    collection = await get_patients_collection()
    
    result = await collection.delete_one({"patient_id": patient_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )
    
    return None
