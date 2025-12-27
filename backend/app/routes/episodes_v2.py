"""
New Episode API routes for condition-based care (cancer, IBD, benign)
Replaces surgery-centric episodes with flexible condition-specific episodes
"""
from fastapi import APIRouter, HTTPException, status, Query, Depends, Request
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from ..models.episode import (
    Episode, EpisodeCreate, EpisodeUpdate,
    ConditionType, CancerType
)
from ..database import get_episodes_collection, get_patients_collection, get_treatments_collection, get_tumours_collection, get_clinicians_collection, get_investigations_collection, get_audit_logs_collection
from ..utils.audit import log_action
from ..utils.mortality import enrich_treatment_with_mortality
from ..utils.encryption import decrypt_field
from ..auth import get_current_user


router = APIRouter(prefix="/api/episodes", tags=["episodes"])


@router.post("/", response_model=Episode, status_code=status.HTTP_201_CREATED)
async def create_episode(
    episode: EpisodeCreate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Create a new episode record (cancer, IBD, or benign)"""
    try:
        episodes_collection = await get_episodes_collection()
        treatments_collection = await get_treatments_collection()
        tumours_collection = await get_tumours_collection()
        patients_collection = await get_patients_collection()
        audit_collection = await get_audit_logs_collection()
        
        # Verify patient exists
        patient = await patients_collection.find_one({"record_number": episode.patient_id})
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Patient with MRN {episode.patient_id} not found"
            )
        
        # Check if episode_id already exists
        existing = await episodes_collection.find_one({"episode_id": episode.episode_id})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Episode with ID {episode.episode_id} already exists"
            )
        
        # Validate condition-specific data
        if episode.condition_type == ConditionType.CANCER:
            if not episode.cancer_type:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="cancer_type is required when condition_type is 'cancer'"
                )
            # cancer_data is optional - detailed data captured in tumours array
        
        # Set timestamps
        now = datetime.utcnow()
        episode_dict = episode.model_dump()
        episode_dict['created_at'] = now
        episode_dict['last_modified_at'] = now
        episode_dict['created_by'] = current_user["username"]
        episode_dict['updated_by'] = current_user["username"]
        
        # Extract treatments and tumours before inserting episode
        treatments = episode_dict.pop('treatments', [])
        tumours = episode_dict.pop('tumours', [])
        
        # Insert episode
        result = await episodes_collection.insert_one(episode_dict)
        episode_oid = result.inserted_id
        
        # Insert treatments into separate collection if any
        if treatments:
            for treatment in treatments:
                treatment['episode_id'] = str(episode_oid)
                treatment['patient_id'] = episode.patient_id
                treatment['created_at'] = now
                treatment['last_modified_at'] = now
                if 'treatment_id' not in treatment:
                    treatment['treatment_id'] = str(ObjectId())
            await treatments_collection.insert_many(treatments)
        
        # Insert tumours into separate collection if any
        if tumours:
            for tumour in tumours:
                tumour['episode_id'] = str(episode_oid)
                tumour['patient_id'] = episode.patient_id
                tumour['created_at'] = now
                tumour['last_modified_at'] = now
                if 'tumour_id' not in tumour:
                    tumour['tumour_id'] = str(ObjectId())
            await tumours_collection.insert_many(tumours)
        
        # Retrieve and return created episode
        created_episode = await episodes_collection.find_one({"_id": episode_oid})
        if created_episode:
            created_episode["_id"] = str(created_episode["_id"])
        
        # Log audit entry
        await log_action(
            audit_collection,
            user_id=current_user["user_id"],
            username=current_user["username"],
            action="create",
            entity_type="episode",
            entity_id=episode.episode_id,
            entity_name=f"Episode {episode.episode_id}",
            details={
                "patient_id": episode.patient_id,
                "condition_type": episode.condition_type.value,
                "cancer_type": episode.cancer_type.value if episode.cancer_type else None
            },
            request=request
        )
        
        return Episode(**created_episode)
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


@router.get("/count")
async def count_episodes(
    search: Optional[str] = Query(None, description="Search by episode ID, MRN, cancer type, or clinician"),
    patient_id: Optional[str] = Query(None, description="Filter by patient MRN"),
    condition_type: Optional[ConditionType] = Query(None, description="Filter by condition type"),
    cancer_type: Optional[CancerType] = Query(None, description="Filter by cancer type"),
    lead_clinician: Optional[str] = Query(None, description="Filter by lead clinician"),
    episode_status: Optional[str] = Query(None, description="Filter by episode status"),
    start_date: Optional[str] = Query(None, description="Filter episodes after this date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter episodes before this date (YYYY-MM-DD)")
):
    """Get total count of episodes with optional filters"""
    collection = await get_episodes_collection()
    patients_collection = await get_patients_collection()

    # Build query filters (same logic as list_episodes)
    query = {}

    # Search filter
    if search:
        search_pattern = {"$regex": search.replace(" ", ""), "$options": "i"}

        # Find patients matching the MRN search
        matching_patients = await patients_collection.find(
            {"mrn": search_pattern},
            {"patient_id": 1}
        ).to_list(length=None)
        matching_patient_ids = [p["patient_id"] for p in matching_patients]

        # Build OR query
        or_conditions = [
            {"episode_id": search_pattern},
            {"cancer_type": search_pattern},
            {"lead_clinician": search_pattern}
        ]

        if matching_patient_ids:
            or_conditions.append({"patient_id": {"$in": matching_patient_ids}})

        query["$or"] = or_conditions

    # Other filters
    if patient_id:
        query["patient_id"] = patient_id
    if condition_type:
        query["condition_type"] = condition_type.value
    if cancer_type:
        query["cancer_type"] = cancer_type.value
    if lead_clinician:
        query["lead_clinician"] = lead_clinician
    if episode_status:
        query["episode_status"] = episode_status
    if start_date:
        query["referral_date"] = query.get("referral_date", {})
        query["referral_date"]["$gte"] = start_date
    if end_date:
        query["referral_date"] = query.get("referral_date", {})
        query["referral_date"]["$lte"] = end_date

    total = await collection.count_documents(query)
    return {"count": total}


@router.get("/treatment-breakdown")
async def get_treatment_breakdown():
    """Get count of treatments by type"""
    from ..database import get_treatments_collection
    treatments_collection = await get_treatments_collection()
    
    # Aggregate treatments by type
    pipeline = [
        {
            "$group": {
                "_id": "$treatment_type",
                "count": {"$sum": 1}
            }
        }
    ]
    
    result = []
    async for doc in treatments_collection.aggregate(pipeline):
        result.append({
            "treatment_type": doc["_id"] or "unspecified",
            "count": doc["count"]
        })
    
    # Return with total
    total = sum(item["count"] for item in result)
    return {
        "total": total,
        "breakdown": result
    }


@router.get("/treatments")
async def get_all_treatments():
    """Get all treatments with minimal data (for dashboard statistics)"""
    from ..database import get_treatments_collection
    treatments_collection = await get_treatments_collection()

    # Fetch only the fields we need for date calculations
    treatments = await treatments_collection.find(
        {},
        {"treatment_date": 1, "treatment_type": 1, "_id": 0}
    ).to_list(length=None)

    return treatments


@router.get("/treatments/{treatment_id}")
async def get_treatment_by_id(treatment_id: str):
    """Get a specific treatment by its treatment_id"""
    treatments_collection = await get_treatments_collection()

    # Find the treatment
    treatment = await treatments_collection.find_one({"treatment_id": treatment_id})

    if not treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Treatment {treatment_id} not found"
        )

    # Convert ObjectId to string
    treatment["_id"] = str(treatment["_id"])

    return treatment


@router.get("/tumours/{tumour_id}")
async def get_tumour_by_id(tumour_id: str):
    """Get a specific tumour by its tumour_id"""
    tumours_collection = await get_tumours_collection()

    # Find the tumour
    tumour = await tumours_collection.find_one({"tumour_id": tumour_id})

    if not tumour:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tumour {tumour_id} not found"
        )

    # Convert ObjectId to string
    tumour["_id"] = str(tumour["_id"])

    return tumour


@router.get("/investigations/{investigation_id}")
async def get_investigation_by_id(investigation_id: str):
    """Get a specific investigation by its investigation_id"""
    investigations_collection = await get_investigations_collection()

    # Find the investigation
    investigation = await investigations_collection.find_one({"investigation_id": investigation_id})

    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {investigation_id} not found"
        )

    # Convert ObjectId to string
    investigation["_id"] = str(investigation["_id"])

    return investigation


@router.get("/")
async def list_episodes(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = Query(None, description="Search by episode ID, MRN, cancer type, or clinician"),
    patient_id: Optional[str] = Query(None, description="Filter by patient MRN"),
    condition_type: Optional[ConditionType] = Query(None, description="Filter by condition type"),
    cancer_type: Optional[CancerType] = Query(None, description="Filter by cancer type"),
    lead_clinician: Optional[str] = Query(None, description="Filter by lead clinician"),
    episode_status: Optional[str] = Query(None, description="Filter by episode status"),
    start_date: Optional[str] = Query(None, description="Filter episodes after this date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter episodes before this date (YYYY-MM-DD)"),
    sort_by: Optional[str] = Query("referral_date", description="Field to sort by (referral_date or last_modified_at)")
):
    """List all episodes with pagination and filters"""
    collection = await get_episodes_collection()
    patients_collection = await get_patients_collection()
    
    # Build query filters
    query = {}
    
    # Search filter - search across multiple fields including MRN
    if search:
        search_pattern = {"$regex": search.replace(" ", ""), "$options": "i"}
        
        # First, find patients matching the MRN search
        matching_patients = await patients_collection.find(
            {"mrn": search_pattern},
            {"patient_id": 1}
        ).to_list(length=None)
        matching_patient_ids = [p["patient_id"] for p in matching_patients]
        
        # Build OR query including patient_id matches from MRN search
        or_conditions = [
            {"episode_id": search_pattern},
            {"cancer_type": search_pattern},
            {"lead_clinician": search_pattern}
        ]
        
        # Add patient_id matches from MRN search
        if matching_patient_ids:
            or_conditions.append({"patient_id": {"$in": matching_patient_ids}})
        
        query["$or"] = or_conditions
    
    # Other filters
    if patient_id:
        query["patient_id"] = patient_id
    if condition_type:
        query["condition_type"] = condition_type.value
    if cancer_type:
        query["cancer_type"] = cancer_type.value
    if lead_clinician:
        query["lead_clinician"] = lead_clinician
    if episode_status:
        query["episode_status"] = episode_status
    
    # Date range filtering
    # Note: referral_date may be stored as string in database, so we compare as strings
    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = start_date  # Compare as string: "2025-12-01"
        if end_date:
            date_query["$lte"] = end_date  # Compare as string: "2025-12-22"
        query["referral_date"] = date_query
    
    # Determine sort field (default to referral_date)
    sort_field = "last_modified_at" if sort_by == "last_modified_at" else "referral_date"
    cursor = collection.find(query).sort(sort_field, -1).skip(skip).limit(limit)
    episodes = await cursor.to_list(length=limit)
    
    # Get patient collection to fetch MRN
    patients_collection = await get_patients_collection()
    
    # Convert ObjectIds to strings and add patient MRN
    for episode in episodes:
        episode["_id"] = str(episode["_id"])

        # Fetch patient MRN and decrypt
        if "patient_id" in episode:
            patient = await patients_collection.find_one({"patient_id": episode["patient_id"]})
            if patient:
                mrn = patient.get("mrn", None)
                # Decrypt MRN if it's encrypted
                if mrn:
                    episode["patient_mrn"] = decrypt_field("mrn", mrn)
                else:
                    episode["patient_mrn"] = None
    
    # Return raw dicts without Pydantic validation to support flexible episode structure
    return episodes


@router.get("/{episode_id}")
async def get_episode(episode_id: str):
    """Get a specific episode by ID (includes treatments, tumours, and investigations from separate collections)"""
    episodes_collection = await get_episodes_collection()
    treatments_collection = await get_treatments_collection()
    tumours_collection = await get_tumours_collection()
    investigations_collection = await get_investigations_collection()
    clinicians_collection = await get_clinicians_collection()
    patients_collection = await get_patients_collection()
    
    episode = await episodes_collection.find_one({"episode_id": episode_id})
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Episode {episode_id} not found"
        )
    
    # Get patient to check deceased date for mortality calculations
    patient = await patients_collection.find_one({"patient_id": episode.get("patient_id")})
    deceased_date = patient.get("deceased_date") if patient else None
    
    # Fetch treatments using treatment_ids array
    treatment_ids = episode.get("treatment_ids", [])
    treatments_cursor = treatments_collection.find({"treatment_id": {"$in": treatment_ids}}) if treatment_ids else []
    treatments = await treatments_cursor.to_list(length=None) if treatment_ids else []
    
    # Fetch tumours using tumour_ids array
    tumour_ids = episode.get("tumour_ids", [])
    tumours_cursor = tumours_collection.find({"tumour_id": {"$in": tumour_ids}}) if tumour_ids else []
    tumours = await tumours_cursor.to_list(length=None) if tumour_ids else []
    
    # Fetch investigations by episode_id
    investigations_cursor = investigations_collection.find({"episode_id": episode_id})
    investigations = await investigations_cursor.to_list(length=None)
    
    # Build a map of all clinicians for efficient lookup
    all_clinicians = await clinicians_collection.find({}).to_list(length=None)
    clinician_map = {}
    for clinician in all_clinicians:
        # Map by _id string
        clinician_map[str(clinician["_id"])] = f"{clinician.get('first_name', '')} {clinician.get('surname', '')}".strip()
        # Also map by name (for cases where name is already stored)
        full_name = f"{clinician.get('first_name', '')} {clinician.get('surname', '')}".strip()
        if full_name:
            clinician_map[full_name] = full_name
    
    # Convert ObjectIds to strings
    episode["_id"] = str(episode["_id"])
    
    for treatment in treatments:
        treatment["_id"] = str(treatment["_id"])
        
        # Resolve clinician names for surgeon and anaesthetist fields
        if "surgeon" in treatment and treatment["surgeon"]:
            surgeon_id = treatment["surgeon"]
            treatment["surgeon_name"] = clinician_map.get(surgeon_id, surgeon_id)
        
        if "anaesthetist" in treatment and treatment["anaesthetist"]:
            anaesthetist_id = treatment["anaesthetist"]
            treatment["anaesthetist_name"] = clinician_map.get(anaesthetist_id, anaesthetist_id)
        
        # Enrich with computed mortality fields
        treatment = enrich_treatment_with_mortality(treatment, deceased_date)
    
    for tumour in tumours:
        tumour["_id"] = str(tumour["_id"])
    
    for investigation in investigations:
        investigation["_id"] = str(investigation["_id"])
    
    # Include treatments, tumours, and investigations in response
    episode["treatments"] = treatments
    episode["tumours"] = tumours
    episode["investigations"] = investigations
    
    # Return raw dict without Pydantic validation to support flexible episode structure
    return episode


@router.put("/{episode_id}")
async def update_episode(
    episode_id: str,
    update_data: dict,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Update an existing episode"""
    try:
        collection = await get_episodes_collection()
        audit_collection = await get_audit_logs_collection()
        
        # Check if episode exists
        existing = await collection.find_one({"episode_id": episode_id})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Episode {episode_id} not found"
            )
        
        # Remove fields that shouldn't be updated
        fields_to_remove = ['_id', 'episode_id', 'patient_id', 'created_at', 'created_by', 'treatments', 'tumours']
        update_dict = {k: v for k, v in update_data.items() if k not in fields_to_remove and v is not None}
        
        # Set last_modified_at timestamp and updated_by
        update_dict['last_modified_at'] = datetime.utcnow()
        update_dict['updated_by'] = current_user["username"]
        
        # Update episode
        await collection.update_one(
            {"episode_id": episode_id},
            {"$set": update_dict}
        )
        
        # Retrieve and return updated episode
        updated_episode = await collection.find_one({"episode_id": episode_id})
        updated_episode["_id"] = str(updated_episode["_id"])
        
        # Log audit entry
        await log_action(
            audit_collection,
            user_id=current_user["user_id"],
            username=current_user["username"],
            action="update",
            entity_type="episode",
            entity_id=episode_id,
            entity_name=f"Episode {episode_id}",
            details={"fields_updated": list(update_dict.keys())},
            request=request
        )
        
        # Return raw dict without Pydantic validation to support flexible episode structure
        return updated_episode
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error updating episode: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update episode: {str(e)}"
        )


@router.delete("/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_episode(
    episode_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Delete an episode"""
    collection = await get_episodes_collection()
    audit_collection = await get_audit_logs_collection()
    
    # Check if episode exists and capture info before deletion
    existing = await collection.find_one({"episode_id": episode_id})
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Episode {episode_id} not found"
        )
    
    # Capture episode info before deletion
    episode_info = {
        "episode_id": episode_id,
        "patient_id": existing.get("patient_id"),
        "condition_type": existing.get("condition_type")
    }
    
    # Delete the episode
    result = await collection.delete_one({"episode_id": episode_id})
    
    # Log audit entry
    await log_action(
        audit_collection,
        user_id=current_user["user_id"],
        username=current_user["username"],
        action="delete",
        entity_type="episode",
        entity_id=episode_id,
        entity_name=f"Episode {episode_id}",
        details=episode_info,
        request=request
    )


@router.post("/{episode_id}/treatments", response_model=dict)
async def add_treatment_to_episode(
    episode_id: str,
    treatment: dict,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Add a treatment (surgery, chemo, etc.) to an episode"""
    try:
        episodes_collection = await get_episodes_collection()
        treatments_collection = await get_treatments_collection()
        audit_collection = await get_audit_logs_collection()
        
        # Check if episode exists
        episode = await episodes_collection.find_one({"episode_id": episode_id})
        if not episode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Episode {episode_id} not found"
            )
        
        # Add episode metadata to treatment
        treatment['episode_id'] = str(episode['_id'])
        treatment['patient_id'] = episode.get('patient_id')
        treatment['created_at'] = datetime.utcnow()
        treatment['last_modified_at'] = datetime.utcnow()
        treatment['created_by'] = current_user["username"]
        treatment['updated_by'] = current_user["username"]
        
        # Generate treatment_id if not provided
        if 'treatment_id' not in treatment:
            treatment['treatment_id'] = str(ObjectId())
        
        # Insert treatment into separate collection
        result = await treatments_collection.insert_one(treatment)
        
        # Update episode's last_modified_at
        await episodes_collection.update_one(
            {"episode_id": episode_id},
            {"$set": {"last_modified_at": datetime.utcnow()}}
        )
        
        # Return created treatment
        created_treatment = await treatments_collection.find_one({"_id": result.inserted_id})
        if created_treatment:
            created_treatment["_id"] = str(created_treatment["_id"])
        
        # Log audit entry
        await log_action(
            audit_collection,
            user_id=current_user["user_id"],
            username=current_user["username"],
            action="create",
            entity_type="treatment",
            entity_id=treatment['treatment_id'],
            entity_name=f"Treatment {treatment.get('treatment_type', 'Unknown')}",
            details={
                "episode_id": episode_id,
                "patient_id": episode.get('patient_id'),
                "treatment_type": treatment.get('treatment_type')
            },
            request=request
        )
        
        return created_treatment
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error adding treatment: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add treatment: {str(e)}"
        )


@router.put("/{episode_id}/treatments/{treatment_id}", response_model=dict)
async def update_treatment_in_episode(
    episode_id: str,
    treatment_id: str,
    treatment: dict,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Update a specific treatment in an episode"""
    try:
        episodes_collection = await get_episodes_collection()
        treatments_collection = await get_treatments_collection()
        audit_collection = await get_audit_logs_collection()
        
        # Check if episode exists
        episode = await episodes_collection.find_one({"episode_id": episode_id})
        if not episode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Episode {episode_id} not found"
            )
        
        # Find treatment in separate collection using episode_id field (EPI-NHSNUMBER-##)
        existing_treatment = await treatments_collection.find_one({
            "treatment_id": treatment_id,
            "episode_id": episode["episode_id"]
        })
        
        if not existing_treatment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Treatment {treatment_id} not found in episode {episode_id}"
            )
        
        # Update treatment (remove _id if present as it's immutable)
        if '_id' in treatment:
            del treatment['_id']
        treatment['last_modified_at'] = datetime.utcnow()
        treatment['updated_by'] = current_user["username"]
        await treatments_collection.update_one(
            {"treatment_id": treatment_id, "episode_id": episode["episode_id"]},
            {"$set": treatment}
        )
        
        # Update episode's last_modified_at
        await episodes_collection.update_one(
            {"episode_id": episode_id},
            {"$set": {"last_modified_at": datetime.utcnow()}}
        )
        
        # Return updated treatment
        updated_treatment = await treatments_collection.find_one({
            "treatment_id": treatment_id,
            "episode_id": episode["episode_id"]
        })
        if updated_treatment:
            updated_treatment["_id"] = str(updated_treatment["_id"])
        
        # Log audit entry
        await log_action(
            audit_collection,
            user_id=current_user["user_id"],
            username=current_user["username"],
            action="update",
            entity_type="treatment",
            entity_id=treatment_id,
            entity_name=f"Treatment {treatment.get('treatment_type', 'Unknown')}",
            details={
                "episode_id": episode_id,
                "fields_updated": list(treatment.keys())
            },
            request=request
        )
        
        return updated_treatment
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error updating treatment: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update treatment: {str(e)}"
        )


@router.get("/stats/overview")
async def get_episodes_overview():
    """Get overview statistics for episodes"""
    collection = await get_episodes_collection()
    
    # Count by condition type
    pipeline = [
        {
            "$group": {
                "_id": "$condition_type",
                "count": {"$sum": 1}
            }
        }
    ]
    condition_counts = await collection.aggregate(pipeline).to_list(length=None)
    
    # Count by cancer type
    pipeline = [
        {
            "$match": {"condition_type": "cancer"}
        },
        {
            "$group": {
                "_id": "$cancer_type",
                "count": {"$sum": 1}
            }
        }
    ]
    cancer_counts = await collection.aggregate(pipeline).to_list(length=None)
    
    # Count by status
    pipeline = [
        {
            "$group": {
                "_id": "$episode_status",
                "count": {"$sum": 1}
            }
        }
    ]
    status_counts = await collection.aggregate(pipeline).to_list(length=None)
    
    return {
        "total_episodes": await collection.count_documents({}),
        "by_condition": {item["_id"]: item["count"] for item in condition_counts},
        "by_cancer_type": {item["_id"]: item["count"] for item in cancer_counts},
        "by_status": {item["_id"]: item["count"] for item in status_counts}
    }


@router.get("/patient/{patient_id}/timeline")
async def get_patient_episode_timeline(patient_id: str):
    """Get chronological timeline of all episodes and treatments for a patient"""
    episodes_collection = await get_episodes_collection()
    treatments_collection = await get_treatments_collection()
    
    episodes = await episodes_collection.find({"patient_id": patient_id}).sort("referral_date", 1).to_list(length=None)
    
    if not episodes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No episodes found for patient {patient_id}"
        )
    
    # Build timeline
    timeline = []
    for episode in episodes:
        episode["_id"] = str(episode["_id"])
        timeline.append({
            "type": "episode_start",
            "date": episode.get("referral_date"),
            "episode_id": episode.get("episode_id"),
            "condition_type": episode.get("condition_type"),
            "cancer_type": episode.get("cancer_type")
        })
        
        # Fetch treatments from separate collection
        treatments_cursor = treatments_collection.find({"episode_id": episode["_id"]})
        treatments = await treatments_cursor.to_list(length=None)
        
        for treatment in treatments:
            timeline.append({
                "type": "treatment",
                "date": treatment.get("treatment_date"),
                "episode_id": episode.get("episode_id"),
                "treatment_id": treatment.get("treatment_id"),
                "treatment_type": treatment.get("treatment_type"),
                "treating_clinician": treatment.get("treating_clinician")
            })
    
    # Sort by date
    timeline.sort(key=lambda x: x.get("date") or datetime.min)
    
    return {
        "patient_id": patient_id,
        "timeline": timeline,
        "episode_count": len(episodes)
    }


# ============== TUMOUR MANAGEMENT ENDPOINTS ==============

@router.post("/{episode_id}/tumours", response_model=dict)
async def add_tumour_to_episode(
    episode_id: str,
    tumour: dict,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Add a tumour site to an episode (supports multiple primaries/metastases)"""
    try:
        episodes_collection = await get_episodes_collection()
        tumours_collection = await get_tumours_collection()
        audit_collection = await get_audit_logs_collection()
        
        # Check if episode exists
        episode = await episodes_collection.find_one({"episode_id": episode_id})
        if not episode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Episode {episode_id} not found"
            )
        
        # Add episode metadata to tumour
        tumour['episode_id'] = episode.get('episode_id')  # Use semantic ID, not ObjectId
        tumour['patient_id'] = episode.get('patient_id')
        tumour['created_at'] = datetime.utcnow()
        tumour['last_modified_at'] = datetime.utcnow()
        tumour['created_by'] = current_user["username"]
        tumour['updated_by'] = current_user["username"]
        
        # Generate tumour_id if not provided
        if 'tumour_id' not in tumour:
            tumour['tumour_id'] = str(ObjectId())
        
        # Insert tumour into separate collection
        result = await tumours_collection.insert_one(tumour)
        
        # Update episode's last_modified_at
        await episodes_collection.update_one(
            {"episode_id": episode_id},
            {"$set": {"last_modified_at": datetime.utcnow()}}
        )
        
        # Return created tumour
        created_tumour = await tumours_collection.find_one({"_id": result.inserted_id})
        if created_tumour:
            created_tumour["_id"] = str(created_tumour["_id"])
        
        # Log audit entry
        await log_action(
            audit_collection,
            user_id=current_user["user_id"],
            username=current_user["username"],
            action="create",
            entity_type="tumour",
            entity_id=tumour['tumour_id'],
            entity_name=f"Tumour {tumour.get('site', 'Unknown')}",
            details={
                "episode_id": episode_id,
                "patient_id": episode.get('patient_id'),
                "site": tumour.get('site')
            },
            request=request
        )
        
        return created_tumour
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error adding tumour: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add tumour: {str(e)}"
        )


@router.put("/{episode_id}/tumours/{tumour_id}", response_model=dict)
async def update_tumour_in_episode(
    episode_id: str,
    tumour_id: str,
    tumour: dict,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Update a specific tumour in an episode"""
    try:
        episodes_collection = await get_episodes_collection()
        tumours_collection = await get_tumours_collection()
        audit_collection = await get_audit_logs_collection()
        
        # Check if episode exists
        episode = await episodes_collection.find_one({"episode_id": episode_id})
        if not episode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Episode {episode_id} not found"
            )
        
        # Find tumour in separate collection using episode_id field (EPI-NHSNUMBER-##)
        existing_tumour = await tumours_collection.find_one({
            "tumour_id": tumour_id,
            "episode_id": episode["episode_id"]
        })
        
        if not existing_tumour:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tumour {tumour_id} not found in episode {episode_id}"
            )
        
        # Update tumour (remove _id if present as it's immutable)
        if '_id' in tumour:
            del tumour['_id']
        tumour['last_modified_at'] = datetime.utcnow()
        tumour['updated_by'] = current_user["username"]
        await tumours_collection.update_one(
            {"tumour_id": tumour_id, "episode_id": episode["episode_id"]},
            {"$set": tumour}
        )
        
        # Update episode's last_modified_at
        await episodes_collection.update_one(
            {"episode_id": episode_id},
            {"$set": {"last_modified_at": datetime.utcnow()}}
        )
        
        # Return updated tumour
        updated_tumour = await tumours_collection.find_one({
            "tumour_id": tumour_id,
            "episode_id": episode["episode_id"]
        })
        if updated_tumour:
            updated_tumour["_id"] = str(updated_tumour["_id"])
        
        # Log audit entry
        await log_action(
            audit_collection,
            user_id=current_user["user_id"],
            username=current_user["username"],
            action="update",
            entity_type="tumour",
            entity_id=tumour_id,
            entity_name=f"Tumour {tumour.get('site', 'Unknown')}",
            details={
                "episode_id": episode_id,
                "fields_updated": list(tumour.keys())
            },
            request=request
        )
        
        return updated_tumour
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error updating tumour: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tumour: {str(e)}"
        )


@router.delete("/{episode_id}/tumours/{tumour_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tumour_from_episode(
    episode_id: str,
    tumour_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Delete a tumour from an episode"""
    try:
        episodes_collection = await get_episodes_collection()
        tumours_collection = await get_tumours_collection()
        audit_collection = await get_audit_logs_collection()
        
        # Check if episode exists
        episode = await episodes_collection.find_one({"episode_id": episode_id})
        if not episode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Episode {episode_id} not found"
            )
        
        # Get tumour info before deletion
        existing_tumour = await tumours_collection.find_one({
            "tumour_id": tumour_id,
            "episode_id": str(episode["_id"])
        })
        
        # Delete tumour from separate collection
        result = await tumours_collection.delete_one({
            "tumour_id": tumour_id,
            "episode_id": str(episode["_id"])
        })
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tumour {tumour_id} not found in episode {episode_id}"
            )
        
        # Update episode's last_modified_at
        await episodes_collection.update_one(
            {"episode_id": episode_id},
            {"$set": {"last_modified_at": datetime.utcnow()}}
        )
        
        # Log audit entry
        if existing_tumour:
            await log_action(
                audit_collection,
                user_id=current_user["user_id"],
                username=current_user["username"],
                action="delete",
                entity_type="tumour",
                entity_id=tumour_id,
                entity_name=f"Tumour {existing_tumour.get('site', 'Unknown')}",
                details={
                    "episode_id": episode_id,
                    "site": existing_tumour.get("site")
                },
                request=request
            )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error deleting tumour: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tumour: {str(e)}"
        )

@router.delete("/{episode_id}/treatments/{treatment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_treatment_from_episode(
    episode_id: str,
    treatment_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Delete a treatment from an episode"""
    try:
        episodes_collection = await get_episodes_collection()
        treatments_collection = await get_treatments_collection()
        audit_collection = await get_audit_logs_collection()
        
        # Check if episode exists
        episode = await episodes_collection.find_one({"episode_id": episode_id})
        if not episode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Episode {episode_id} not found"
            )
        
        # Get treatment info before deletion
        existing_treatment = await treatments_collection.find_one({
            "treatment_id": treatment_id,
            "episode_id": str(episode["_id"])
        })
        
        # Delete treatment from separate collection
        result = await treatments_collection.delete_one({
            "treatment_id": treatment_id,
            "episode_id": str(episode["_id"])
        })
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Treatment {treatment_id} not found in episode {episode_id}"
            )
        
        # Update episode's last_modified_at
        await episodes_collection.update_one(
            {"episode_id": episode_id},
            {"$set": {"last_modified_at": datetime.utcnow()}}
        )
        
        # Log audit entry
        if existing_treatment:
            await log_action(
                audit_collection,
                user_id=current_user["user_id"],
                username=current_user["username"],
                action="delete",
                entity_type="treatment",
                entity_id=treatment_id,
                entity_name=f"Treatment {existing_treatment.get('treatment_type', 'Unknown')}",
                details={
                    "episode_id": episode_id,
                    "treatment_type": existing_treatment.get("treatment_type")
                },
                request=request
            )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error deleting treatment: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete treatment: {str(e)}"
        )
