"""
Patient API routes
"""
from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from ..models.patient import Patient, PatientCreate, PatientUpdate
from ..database import get_patients_collection


router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.post("/", response_model=Patient, status_code=status.HTTP_201_CREATED)
async def create_patient(patient: PatientCreate):
    """Create a new patient"""
    collection = await get_patients_collection()
    
    # Check if patient_id already exists
    existing = await collection.find_one({"patient_id": patient.patient_id})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Patient with ID {patient.patient_id} already exists"
        )
    
    # Insert patient
    patient_dict = patient.model_dump()
    patient_dict["created_at"] = datetime.utcnow()
    patient_dict["created_by"] = "system"  # TODO: Replace with actual user from auth
    patient_dict["updated_at"] = datetime.utcnow()
    patient_dict["updated_by"] = None
    
    result = await collection.insert_one(patient_dict)
    
    # Retrieve and return created patient
    created_patient = await collection.find_one({"_id": result.inserted_id})
    return Patient(**created_patient)


@router.get("/", response_model=List[Patient])
async def list_patients(skip: int = 0, limit: int = 100):
    """List all patients with pagination"""
    collection = await get_patients_collection()
    
    cursor = collection.find().skip(skip).limit(limit)
    patients = await cursor.to_list(length=limit)
    
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
