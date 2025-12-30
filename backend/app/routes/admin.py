from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from pydantic import BaseModel, Field

from ..database import get_database
from ..auth import get_current_user, get_password_hash, require_admin, get_system_database
from ..models.user import User, UserCreate, UserUpdate, UserRole

router = APIRouter(prefix="/api/admin/users", tags=["Admin - User Management"])


class PasswordChange(BaseModel):
    """Password change model"""
    password: str = Field(..., min_length=6, description="New password")


@router.get("", response_model=List[User])
async def list_users(
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_system_database),
    role: str = None,
    is_active: bool = None
):
    """
    List all users (Admin only)
    
    - **role**: Filter by role
    - **is_active**: Filter by active status
    """
    query = {}
    if role:
        query["role"] = role
    if is_active is not None:
        query["is_active"] = is_active
    
    cursor = db.users.find(query).sort("created_at", -1)
    users = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        users.append(User(**doc))
    
    return users


@router.post("", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_system_database)
):
    """Create a new user (Admin only)"""
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user document
    user_doc = {
        "email": user_data.email,
        "full_name": user_data.full_name,
        "hashed_password": get_password_hash(user_data.password),
        "role": user_data.role.value,
        "is_active": user_data.is_active,
        "department": user_data.department,
        "job_title": user_data.job_title,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "last_login": None
    }
    
    result = await db.users.insert_one(user_doc)
    user_doc["_id"] = str(result.inserted_id)
    
    return User(**user_doc)


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_system_database)
):
    """Get a user by ID (Admin only)"""
    try:
        user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
    except:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")
    
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    user_doc["_id"] = str(user_doc["_id"])
    return User(**user_doc)


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_system_database)
):
    """Update a user (Admin only)"""
    try:
        existing_user = await db.users.find_one({"_id": ObjectId(user_id)})
    except:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")
    
    if not existing_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Build update document
    update_data = {}
    if user_data.email is not None:
        # Check email not taken by another user
        email_check = await db.users.find_one({"email": user_data.email, "_id": {"$ne": ObjectId(user_id)}})
        if email_check:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        update_data["email"] = user_data.email
    
    if user_data.full_name is not None:
        update_data["full_name"] = user_data.full_name
    if user_data.role is not None:
        update_data["role"] = user_data.role.value
    if user_data.is_active is not None:
        update_data["is_active"] = user_data.is_active
    if user_data.department is not None:
        update_data["department"] = user_data.department
    if user_data.job_title is not None:
        update_data["job_title"] = user_data.job_title
    if user_data.password is not None:
        update_data["hashed_password"] = get_password_hash(user_data.password)
    
    update_data["updated_at"] = datetime.utcnow()
    
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )
    
    # Fetch updated user
    user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
    user_doc["_id"] = str(user_doc["_id"])
    return User(**user_doc)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_system_database)
):
    """Delete a user (Admin only)"""
    try:
        result = await db.users.delete_one({"_id": ObjectId(user_id)})
    except:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return None


@router.put("/{user_id}/password", response_model=User)
async def change_user_password(
    user_id: str,
    password_data: PasswordChange,
    current_user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_system_database)
):
    """Change a user's password (Admin only)"""
    try:
        existing_user = await db.users.find_one({"_id": ObjectId(user_id)})
    except:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")
    
    if not existing_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Update password
    update_data = {
        "hashed_password": get_password_hash(password_data.password),
        "updated_at": datetime.utcnow()
    }
    
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )
    
    # Fetch updated user
    user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
    user_doc["_id"] = str(user_doc["_id"])
    return User(**user_doc)
