from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from ..database import get_database
from ..models.clinician import Clinician, ClinicianCreate, ClinicianUpdate
from ..models.user import User
from ..auth import get_current_user, require_admin

router = APIRouter(prefix="/api/admin/clinicians", tags=["Admin - Clinician Management"])


@router.get("")
async def list_clinicians(
    skip: int = 0,
    limit: int = 1000,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List all clinicians, sorted by surname (paginated)
    """
    query = {}
    cursor = db.clinicians.find(query).sort("surname", 1).skip(skip).limit(limit)
    clinicians = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        clinicians.append(doc)
    
    return clinicians


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_clinician(
    clinician_data: ClinicianCreate,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new clinician (Admin only)
    """
    # Check if clinician with same name already exists
    existing = await db.clinicians.find_one({
        "first_name": clinician_data.first_name,
        "surname": clinician_data.surname
    })
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clinician with this name already exists"
        )
    
    clinician_dict = clinician_data.model_dump()
    clinician_dict["created_at"] = datetime.utcnow()
    clinician_dict["updated_at"] = datetime.utcnow()
    
    result = await db.clinicians.insert_one(clinician_dict)
    clinician_dict["_id"] = str(result.inserted_id)
    
    return clinician_dict


@router.put("/{clinician_id}")
async def update_clinician(
    clinician_id: str,
    clinician_data: ClinicianUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update a clinician (Admin only)
    """
    if not ObjectId.is_valid(clinician_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid clinician ID"
        )
    
    update_data = {k: v for k, v in clinician_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.clinicians.find_one_and_update(
        {"_id": ObjectId(clinician_id)},
        {"$set": update_data},
        return_document=True
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinician not found"
        )
    
    result["_id"] = str(result["_id"])
    return result


@router.delete("/{clinician_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clinician(
    clinician_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete a clinician (Admin only)
    """
    if not ObjectId.is_valid(clinician_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid clinician ID"
        )
    
    result = await db.clinicians.delete_one({"_id": ObjectId(clinician_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinician not found"
        )
