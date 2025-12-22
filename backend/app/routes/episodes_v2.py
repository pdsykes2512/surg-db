"""
New Episode API routes for condition-based care (cancer, IBD, benign)
Replaces surgery-centric episodes with flexible condition-specific episodes
"""
from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from ..models.episode import (
    Episode, EpisodeCreate, EpisodeUpdate,
    ConditionType, CancerType
)
from ..database import get_episodes_collection, get_patients_collection


router = APIRouter(prefix="/api/v2/episodes", tags=["episodes-v2"])


@router.post("/", response_model=Episode, status_code=status.HTTP_201_CREATED)
async def create_episode(episode: EpisodeCreate):
    """Create a new episode record (cancer, IBD, or benign)"""
    try:
        collection = await get_episodes_collection()
        patients_collection = await get_patients_collection()
        
        # Verify patient exists
        patient = await patients_collection.find_one({"record_number": episode.patient_id})
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Patient with MRN {episode.patient_id} not found"
            )
        
        # Check if episode_id already exists
        existing = await collection.find_one({"episode_id": episode.episode_id})
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
        
        # Insert episode
        result = await collection.insert_one(episode_dict)
        
        # Retrieve and return created episode
        created_episode = await collection.find_one({"_id": result.inserted_id})
        if created_episode:
            created_episode["_id"] = str(created_episode["_id"])
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


@router.get("/", response_model=List[Episode])
async def list_episodes(
    skip: int = 0,
    limit: int = 100,
    patient_id: Optional[str] = Query(None, description="Filter by patient MRN"),
    condition_type: Optional[ConditionType] = Query(None, description="Filter by condition type"),
    cancer_type: Optional[CancerType] = Query(None, description="Filter by cancer type"),
    lead_clinician: Optional[str] = Query(None, description="Filter by lead clinician"),
    episode_status: Optional[str] = Query(None, description="Filter by episode status"),
    start_date: Optional[str] = Query(None, description="Filter episodes after this date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter episodes before this date (YYYY-MM-DD)")
):
    """List all episodes with pagination and filters"""
    collection = await get_episodes_collection()
    
    # Build query filters
    query = {}
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
    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = datetime.fromisoformat(start_date)
        if end_date:
            date_query["$lte"] = datetime.fromisoformat(end_date)
        query["referral_date"] = date_query
    
    cursor = collection.find(query).sort("referral_date", -1).skip(skip).limit(limit)
    episodes = await cursor.to_list(length=limit)
    
    # Convert ObjectIds to strings
    for episode in episodes:
        episode["_id"] = str(episode["_id"])
    
    return [Episode(**episode) for episode in episodes]


@router.get("/{episode_id}", response_model=Episode)
async def get_episode(episode_id: str):
    """Get a specific episode by ID"""
    collection = await get_episodes_collection()
    
    episode = await collection.find_one({"episode_id": episode_id})
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Episode {episode_id} not found"
        )
    
    episode["_id"] = str(episode["_id"])
    return Episode(**episode)


@router.put("/{episode_id}", response_model=Episode)
async def update_episode(episode_id: str, update_data: EpisodeUpdate):
    """Update an existing episode"""
    try:
        collection = await get_episodes_collection()
        
        # Check if episode exists
        existing = await collection.find_one({"episode_id": episode_id})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Episode {episode_id} not found"
            )
        
        # Build update document (only include non-None fields)
        update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
        update_dict['last_modified_at'] = datetime.utcnow()
        
        # Update episode
        await collection.update_one(
            {"episode_id": episode_id},
            {"$set": update_dict}
        )
        
        # Retrieve and return updated episode
        updated_episode = await collection.find_one({"episode_id": episode_id})
        updated_episode["_id"] = str(updated_episode["_id"])
        return Episode(**updated_episode)
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
async def delete_episode(episode_id: str):
    """Delete an episode"""
    collection = await get_episodes_collection()
    
    result = await collection.delete_one({"episode_id": episode_id})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Episode {episode_id} not found"
        )


@router.post("/{episode_id}/treatments", response_model=Episode)
async def add_treatment_to_episode(episode_id: str, treatment: dict):
    """Add a treatment (surgery, chemo, etc.) to an episode"""
    try:
        collection = await get_episodes_collection()
        
        # Check if episode exists
        episode = await collection.find_one({"episode_id": episode_id})
        if not episode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Episode {episode_id} not found"
            )
        
        # Add treatment to episode
        await collection.update_one(
            {"episode_id": episode_id},
            {
                "$push": {"treatments": treatment},
                "$set": {"last_modified_at": datetime.utcnow()}
            }
        )
        
        # Return updated episode
        updated_episode = await collection.find_one({"episode_id": episode_id})
        updated_episode["_id"] = str(updated_episode["_id"])
        return Episode(**updated_episode)
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


@router.put("/{episode_id}/treatments/{treatment_id}", response_model=Episode)
async def update_treatment_in_episode(episode_id: str, treatment_id: str, treatment: dict):
    """Update a specific treatment in an episode"""
    try:
        collection = await get_episodes_collection()
        
        # Check if episode exists
        episode = await collection.find_one({"episode_id": episode_id})
        if not episode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Episode {episode_id} not found"
            )
        
        # Find the treatment in the treatments array
        treatment_found = False
        if "treatments" in episode:
            for i, t in enumerate(episode["treatments"]):
                if t.get("treatment_id") == treatment_id:
                    treatment_found = True
                    break
        
        if not treatment_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Treatment {treatment_id} not found in episode {episode_id}"
            )
        
        # Update the treatment
        await collection.update_one(
            {"episode_id": episode_id, "treatments.treatment_id": treatment_id},
            {
                "$set": {
                    "treatments.$": treatment,
                    "last_modified_at": datetime.utcnow()
                }
            }
        )
        
        # Return updated episode
        updated_episode = await collection.find_one({"episode_id": episode_id})
        updated_episode["_id"] = str(updated_episode["_id"])
        return Episode(**updated_episode)
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
    collection = await get_episodes_collection()
    
    episodes = await collection.find({"patient_id": patient_id}).sort("referral_date", 1).to_list(length=None)
    
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
        
        # Add treatments
        for treatment in episode.get("treatments", []):
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

@router.post("/{episode_id}/tumours", response_model=Episode)
async def add_tumour_to_episode(episode_id: str, tumour: dict):
    """Add a tumour site to an episode (supports multiple primaries/metastases)"""
    try:
        collection = await get_episodes_collection()
        
        # Check if episode exists
        episode = await collection.find_one({"episode_id": episode_id})
        if not episode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Episode {episode_id} not found"
            )
        
        # Add timestamps to tumour
        tumour['created_at'] = datetime.utcnow()
        tumour['last_modified_at'] = datetime.utcnow()
        
        # Add tumour to episode
        await collection.update_one(
            {"episode_id": episode_id},
            {
                "$push": {"tumours": tumour},
                "$set": {"last_modified_at": datetime.utcnow()}
            }
        )
        
        # Return updated episode
        updated_episode = await collection.find_one({"episode_id": episode_id})
        updated_episode["_id"] = str(updated_episode["_id"])
        return Episode(**updated_episode)
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


@router.put("/{episode_id}/tumours/{tumour_id}", response_model=Episode)
async def update_tumour_in_episode(episode_id: str, tumour_id: str, tumour: dict):
    """Update a specific tumour in an episode"""
    try:
        collection = await get_episodes_collection()
        
        # Check if episode exists
        episode = await collection.find_one({"episode_id": episode_id})
        if not episode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Episode {episode_id} not found"
            )
        
        # Find the tumour in the tumours array
        tumour_found = False
        if "tumours" in episode:
            for t in episode["tumours"]:
                if t.get("tumour_id") == tumour_id:
                    tumour_found = True
                    break
        
        if not tumour_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tumour {tumour_id} not found in episode {episode_id}"
            )
        
        # Update last_modified timestamp
        tumour['last_modified_at'] = datetime.utcnow()
        
        # Update the tumour
        await collection.update_one(
            {"episode_id": episode_id, "tumours.tumour_id": tumour_id},
            {
                "$set": {
                    "tumours.$": tumour,
                    "last_modified_at": datetime.utcnow()
                }
            }
        )
        
        # Return updated episode
        updated_episode = await collection.find_one({"episode_id": episode_id})
        updated_episode["_id"] = str(updated_episode["_id"])
        return Episode(**updated_episode)
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


@router.delete("/{episode_id}/tumours/{tumour_id}", response_model=Episode)
async def delete_tumour_from_episode(episode_id: str, tumour_id: str):
    """Delete a tumour from an episode"""
    try:
        collection = await get_episodes_collection()
        
        # Check if episode exists
        episode = await collection.find_one({"episode_id": episode_id})
        if not episode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Episode {episode_id} not found"
            )
        
        # Remove the tumour
        await collection.update_one(
            {"episode_id": episode_id},
            {
                "$pull": {"tumours": {"tumour_id": tumour_id}},
                "$set": {"last_modified_at": datetime.utcnow()}
            }
        )
        
        # Return updated episode
        updated_episode = await collection.find_one({"episode_id": episode_id})
        updated_episode["_id"] = str(updated_episode["_id"])
        return Episode(**updated_episode)
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

@router.delete("/{episode_id}/treatments/{treatment_id}", response_model=Episode)
async def delete_treatment_from_episode(episode_id: str, treatment_id: str):
    """Delete a treatment from an episode"""
    try:
        collection = await get_episodes_collection()
        
        # Check if episode exists
        episode = await collection.find_one({"episode_id": episode_id})
        if not episode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Episode {episode_id} not found"
            )
        
        # Remove the treatment
        await collection.update_one(
            {"episode_id": episode_id},
            {
                "$pull": {"treatments": {"treatment_id": treatment_id}},
                "$set": {"last_modified_at": datetime.utcnow()}
            }
        )
        
        # Return updated episode
        updated_episode = await collection.find_one({"episode_id": episode_id})
        updated_episode["_id"] = str(updated_episode["_id"])
        return Episode(**updated_episode)
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
