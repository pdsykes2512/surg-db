from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from ..database import get_database
from ..models.surgeon import Surgeon, SurgeonCreate, SurgeonUpdate
from ..models.user import User
from ..auth import get_current_user, require_admin

router = APIRouter(prefix="/api/admin/surgeons", tags=["Admin - Surgeon Management"])


@router.get("", response_model=List[Surgeon])
async def list_surgeons(
    skip: int = 0,
    limit: int = 1000,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List all surgeons, sorted by surname (paginated)
    """
    cursor = db.surgeons.find({}).sort("surname", 1).skip(skip).limit(limit)
    surgeons = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        surgeons.append(Surgeon(**doc))
    
    return surgeons


@router.post("", response_model=Surgeon, status_code=status.HTTP_201_CREATED)
async def create_surgeon(
    surgeon_data: SurgeonCreate,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new surgeon (Admin only)
    """
    # Check if surgeon with same name already exists
    existing = await db.surgeons.find_one({
        "first_name": surgeon_data.first_name,
        "surname": surgeon_data.surname
    })
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Surgeon with this name already exists"
        )
    
    surgeon_dict = surgeon_data.model_dump()
    surgeon_dict["created_at"] = datetime.utcnow()
    surgeon_dict["updated_at"] = datetime.utcnow()
    
    result = await db.surgeons.insert_one(surgeon_dict)
    surgeon_dict["_id"] = str(result.inserted_id)
    
    return Surgeon(**surgeon_dict)


@router.put("/{surgeon_id}", response_model=Surgeon)
async def update_surgeon(
    surgeon_id: str,
    surgeon_data: SurgeonUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update a surgeon (Admin only)
    """
    if not ObjectId.is_valid(surgeon_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid surgeon ID"
        )
    
    update_data = {k: v for k, v in surgeon_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.surgeons.find_one_and_update(
        {"_id": ObjectId(surgeon_id)},
        {"$set": update_data},
        return_document=True
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Surgeon not found"
        )
    
    result["_id"] = str(result["_id"])
    return Surgeon(**result)


@router.delete("/{surgeon_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_surgeon(
    surgeon_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete a surgeon (Admin only)
    """
    if not ObjectId.is_valid(surgeon_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid surgeon ID"
        )
    
    result = await db.surgeons.delete_one({"_id": ObjectId(surgeon_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Surgeon not found"
        )
