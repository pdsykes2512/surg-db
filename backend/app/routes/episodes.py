"""
New Episode API routes for condition-based care (cancer, IBD, benign)
Replaces surgery-centric episodes with flexible condition-specific episodes
"""
# Standard library
import logging
from datetime import datetime
from typing import List, Optional

# Third-party
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Query, Depends, Request

# Local application
from ..auth import get_current_user
from ..database import (
    get_episodes_collection,
    get_patients_collection,
    get_treatments_collection,
    get_tumours_collection,
    get_clinicians_collection,
    get_investigations_collection,
    get_audit_logs_collection
)
from ..models.episode import Episode, EpisodeCreate, EpisodeUpdate, ConditionType, CancerType
from ..utils.audit import log_action
from ..utils.clinician_helpers import build_clinician_maps
from ..utils.encryption import decrypt_field
from ..utils.mortality import enrich_treatment_with_mortality

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/episodes", tags=["episodes"])


def flatten_treatment_for_frontend(treatment: dict, clinician_map: dict = None, surname_map: dict = None) -> dict:
    """
    Flatten nested treatment structure for frontend compatibility.

    Frontend expects flat structure with direct access to fields like:
    - surgeon, procedure_name, approach, urgency, admission_date, etc.

    Database has nested structure:
    - team.primary_surgeon, procedure.primary_procedure, classification.approach, etc.

    This function flattens the nested structure while maintaining both versions
    for backward compatibility.
    """
    flattened = treatment.copy()

    # Flatten classification fields
    if 'classification' in treatment:
        flattened['approach'] = treatment['classification'].get('approach')
        flattened['urgency'] = treatment['classification'].get('urgency')

    # Flatten procedure fields
    if 'procedure' in treatment:
        flattened['procedure_name'] = treatment['procedure'].get('primary_procedure')
        flattened['procedure_type'] = treatment['procedure'].get('procedure_type')
        flattened['resection_performed'] = treatment['procedure'].get('resection_performed')
        flattened['robotic_surgery'] = treatment['procedure'].get('robotic_surgery')
        flattened['conversion_to_open'] = treatment['procedure'].get('conversion_to_open')

    # Flatten team fields with clinician resolution
    if 'team' in treatment:
        team = treatment['team']

        # Resolve primary surgeon with surname matching
        primary_surgeon_id = team.get('primary_surgeon')
        primary_surgeon_text = team.get('primary_surgeon_text')

        # Try to resolve surgeon name using multiple strategies
        surgeon_name = None
        if clinician_map and primary_surgeon_id:
            # Strategy 1: Resolve by clinician ID
            surgeon_name = clinician_map.get(primary_surgeon_id)

        if not surgeon_name and surname_map and primary_surgeon_text:
            # Strategy 2: Match by surname (case-insensitive)
            surgeon_name = surname_map.get(primary_surgeon_text.upper())

        if not surgeon_name:
            # Fallback: Use the text value as-is
            surgeon_name = primary_surgeon_text or primary_surgeon_id

        flattened['surgeon'] = surgeon_name

        # Resolve assistant surgeons with surname matching
        assistant_ids = team.get('assistant_surgeons', [])
        assistant_texts = team.get('assistant_surgeons_text', [])

        assistant_names = []
        if assistant_ids:
            for idx, surgeon_id in enumerate(assistant_ids):
                # Try to resolve by ID
                if clinician_map and surgeon_id:
                    name = clinician_map.get(surgeon_id)
                    if name:
                        assistant_names.append(name)
                        continue

                # Try to resolve by surname from text
                if surname_map and idx < len(assistant_texts):
                    text = assistant_texts[idx]
                    if text:
                        name = surname_map.get(text.upper())
                        if name:
                            assistant_names.append(name)
                            continue

                # Fallback to text or ID
                if idx < len(assistant_texts) and assistant_texts[idx]:
                    assistant_names.append(assistant_texts[idx])
                else:
                    assistant_names.append(surgeon_id)
        else:
            # No IDs, try to resolve text names
            for text in assistant_texts:
                if surname_map and text:
                    name = surname_map.get(text.upper())
                    assistant_names.append(name if name else text)
                else:
                    assistant_names.append(text)

        # Take first assistant for backward compatibility
        flattened['assistant_surgeon'] = assistant_names[0] if assistant_names else None
        flattened['assistant_surgeons'] = assistant_names

        flattened['surgeon_grade'] = team.get('surgeon_grade')
        flattened['anaesthetist_grade'] = team.get('anesthetist_grade')
        flattened['surgical_fellow'] = team.get('surgical_fellow')

    # Flatten perioperative_timeline fields
    if 'perioperative_timeline' in treatment:
        timeline = treatment['perioperative_timeline']
        flattened['admission_date'] = timeline.get('admission_date')
        flattened['discharge_date'] = timeline.get('discharge_date')
        flattened['surgery_date'] = timeline.get('surgery_date')
        flattened['operation_duration_minutes'] = timeline.get('operation_duration_minutes')
        flattened['length_of_stay'] = timeline.get('length_of_stay_days')

    # Flatten intraoperative fields
    if 'intraoperative' in treatment:
        intraop = treatment['intraoperative']
        flattened['blood_loss_ml'] = intraop.get('blood_loss_ml')
        flattened['stoma_created'] = intraop.get('stoma_created')
        flattened['stoma_type'] = intraop.get('stoma_type')
        flattened['anastomosis_performed'] = intraop.get('anastomosis_performed')
        flattened['bowel_prep'] = intraop.get('bowel_prep')
        flattened['defunctioning_stoma'] = intraop.get('defunctioning_stoma')

    # Flatten postoperative_events fields
    if 'postoperative_events' in treatment:
        postop = treatment['postoperative_events']
        if 'return_to_theatre' in postop:
            flattened['return_to_theatre'] = postop['return_to_theatre'].get('occurred')
            flattened['return_to_theatre_reason'] = postop['return_to_theatre'].get('reason')

    # Flatten outcomes fields
    if 'outcomes' in treatment:
        outcomes = treatment['outcomes']
        flattened['readmission_30d'] = outcomes.get('readmission_30day')
        flattened['readmission_reason'] = outcomes.get('readmission_reason')

    return flattened


def enrich_episode_with_treatment_data(episode: dict, treatments: list, clinician_map: dict = None) -> dict:
    """
    Enrich episode with fields from primary surgical treatment for frontend display.

    Frontend expects these fields on episode object:
    - episode.classification (urgency, approach, etc.)
    - episode.procedure (primary_procedure, approach, etc.)
    - episode.team (primary_surgeon, assistant_surgeons, etc.)

    These fields actually live in treatment documents, so we populate from first surgical treatment.
    """
    # Find first surgical treatment
    surgical_treatments = [t for t in treatments if t.get('treatment_type') == 'surgery']

    if not surgical_treatments:
        # No surgery - return episode as-is
        return episode

    # Get primary surgical treatment (first one)
    primary_surgery = surgical_treatments[0]

    # Populate classification from treatment
    episode['classification'] = {
        'urgency': primary_surgery.get('classification', {}).get('urgency'),
        'approach': primary_surgery.get('classification', {}).get('approach'),
        'complexity': None,  # Not in current data model
        'primary_diagnosis': primary_surgery.get('procedure', {}).get('primary_procedure'),
        'indication': None  # Not in current data model
    }

    # Populate procedure from treatment
    episode['procedure'] = {
        'primary_procedure': primary_surgery.get('procedure', {}).get('primary_procedure'),
        'approach': primary_surgery.get('classification', {}).get('approach'),
        'additional_procedures': [],  # Could add from multiple treatments later
        'procedure_type': primary_surgery.get('procedure', {}).get('procedure_type'),
        'robotic_surgery': primary_surgery.get('procedure', {}).get('robotic_surgery'),
        'conversion_to_open': primary_surgery.get('procedure', {}).get('conversion_to_open')
    }

    # Populate team from treatment
    team_data = primary_surgery.get('team', {})

    # Resolve primary surgeon
    primary_surgeon_id = team_data.get('primary_surgeon')
    primary_surgeon_text = team_data.get('primary_surgeon_text')

    if clinician_map and primary_surgeon_id:
        primary_surgeon_name = clinician_map.get(primary_surgeon_id, primary_surgeon_text)
    else:
        primary_surgeon_name = primary_surgeon_text

    # Resolve assistant surgeons
    assistant_ids = team_data.get('assistant_surgeons', [])
    assistant_texts = team_data.get('assistant_surgeons_text', [])

    assistant_names = []
    if clinician_map:
        for surgeon_id in assistant_ids:
            assistant_names.append(clinician_map.get(surgeon_id, surgeon_id))
    else:
        assistant_names = assistant_texts

    episode['team'] = {
        'primary_surgeon': primary_surgeon_name,
        'assistant_surgeons': assistant_names,
        'surgeon_grade': team_data.get('surgeon_grade'),
        'anesthetist_grade': team_data.get('anesthetist_grade'),
        'surgical_fellow': team_data.get('surgical_fellow')
    }

    # Populate perioperative data
    timeline = primary_surgery.get('perioperative_timeline', {})
    episode['perioperative'] = {
        'admission_date': timeline.get('admission_date'),
        'surgery_date': timeline.get('surgery_date'),
        'discharge_date': timeline.get('discharge_date'),
        'length_of_stay_days': timeline.get('length_of_stay_days'),
        'operation_duration_minutes': timeline.get('operation_duration_minutes')
    }

    # Populate outcomes
    episode['outcomes'] = primary_surgery.get('outcomes', {})

    return episode


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
        patient = await patients_collection.find_one({"patient_id": episode.patient_id})
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
        logger.error(f"Error creating episode: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create episode: {str(e)}"
        )


@router.get("/count")
async def count_episodes(
    search: Optional[str] = Query(None, description="Search by episode ID, MRN, NHS number, cancer type, or clinician"),
    patient_id: Optional[str] = Query(None, description="Filter by patient MRN"),
    condition_type: Optional[ConditionType] = Query(None, description="Filter by condition type"),
    cancer_type: Optional[CancerType] = Query(None, description="Filter by cancer type"),
    lead_clinician: Optional[str] = Query(None, description="Filter by lead clinician"),
    episode_status: Optional[str] = Query(None, description="Filter by episode status"),
    start_date: Optional[str] = Query(None, description="Filter episodes after this date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter episodes before this date (YYYY-MM-DD)")
):
    """
    Get total count of episodes with optional filters.

    Search supports MRN, NHS number, episode ID, cancer type, and clinician name.
    """
    from ..utils.encryption import create_searchable_query
    from ..utils.search_helpers import sanitize_search_input

    collection = await get_episodes_collection()
    patients_collection = await get_patients_collection()

    # Build query filters (same logic as list_episodes)
    query = {}

    # Search filter - supports MRN and NHS number
    if search:
        # Check if search looks like MRN or NHS number (encrypted fields)
        search_encrypted_fields = False
        clean_search = search.replace(" ", "").upper()

        # MRN patterns: 8+ digits, IW+6digits, or C+6digits+2alphanumeric
        # NHS number: 10 digits
        is_mrn_or_nhs_pattern = (
            (clean_search.isdigit() and len(clean_search) >= 8) or
            (clean_search.startswith('IW') and len(clean_search) == 8 and clean_search[2:].isdigit()) or
            (clean_search.startswith('C') and len(clean_search) == 9 and clean_search[1:7].isdigit() and clean_search[7:9].isalnum())
        )

        if is_mrn_or_nhs_pattern:
            search_encrypted_fields = True

        matching_patient_ids = []

        if search_encrypted_fields:
            # Use hash-based lookup for encrypted fields
            clean_search_lower = search.replace(" ", "").lower()
            nhs_query = create_searchable_query('nhs_number', clean_search_lower)
            mrn_query = create_searchable_query('mrn', clean_search_lower)

            matching_patients = await patients_collection.find(
                {"$or": [nhs_query, mrn_query]},
                {"patient_id": 1}
            ).to_list(length=None)
            matching_patient_ids = [p["patient_id"] for p in matching_patients]
        else:
            # For non-encrypted searches, use regex pattern
            safe_search = sanitize_search_input(search)
            search_pattern = {"$regex": safe_search, "$options": "i"}

            matching_patients = await patients_collection.find(
                {"mrn": search_pattern},
                {"patient_id": 1}
            ).to_list(length=100)
            matching_patient_ids = [p["patient_id"] for p in matching_patients]

        # Build OR query
        safe_search = sanitize_search_input(search)
        search_pattern = {"$regex": safe_search, "$options": "i"}

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


@router.get("/dashboard-stats")
async def get_dashboard_stats():
    """
    Get optimized dashboard statistics using database aggregation.

    Returns:
        - totalPatients: Total count of patients
        - totalEpisodes: Total count of episodes
        - treatmentBreakdown: Count by treatment type
        - monthlyEpisodes: Surgery counts for last 4 months
        - yearToDateEpisodes: Surgery count for current year

    Performance: Uses MongoDB aggregation pipeline for efficient computation
    """
    from ..database import get_treatments_collection
    patients_collection = await get_patients_collection()
    episodes_collection = await get_episodes_collection()
    treatments_collection = await get_treatments_collection()

    # Get counts in parallel
    total_patients = await patients_collection.count_documents({})
    total_episodes = await episodes_collection.count_documents({})

    # Get treatment breakdown using aggregation
    treatment_breakdown_pipeline = [
        {
            "$group": {
                "_id": "$treatment_type",
                "count": {"$sum": 1}
            }
        }
    ]

    treatment_breakdown = []
    async for doc in treatments_collection.aggregate(treatment_breakdown_pipeline):
        treatment_breakdown.append({
            "treatment_type": doc["_id"] or "unspecified",
            "count": doc["count"]
        })

    # Calculate monthly surgery counts for last 4 months using aggregation
    now = datetime.utcnow()
    surgery_types = ['surgery', 'surgery_primary', 'surgery_rtt', 'surgery_reversal']

    # Build monthly buckets
    monthly_episodes = []
    for i in range(4):
        # Calculate month boundaries
        if i == 0:
            # Current month
            month_start = datetime(now.year, now.month, 1)
            month_end = now
        else:
            # Previous months
            target_month = now.month - i
            target_year = now.year
            if target_month <= 0:
                target_month += 12
                target_year -= 1

            month_start = datetime(target_year, target_month, 1)
            # Get last day of month
            if target_month == 12:
                month_end = datetime(target_year + 1, 1, 1)
            else:
                month_end = datetime(target_year, target_month + 1, 1)

        # Count surgeries in this month using aggregation
        count_pipeline = [
            {
                "$match": {
                    "treatment_type": {"$in": surgery_types},
                    "treatment_date": {
                        "$gte": month_start.isoformat(),
                        "$lt": month_end.isoformat()
                    }
                }
            },
            {
                "$count": "total"
            }
        ]

        count_result = await treatments_collection.aggregate(count_pipeline).to_list(length=1)
        count = count_result[0]["total"] if count_result else 0

        # Format month name
        month_name = month_start.strftime("%b")
        monthly_episodes.append({"month": month_name, "count": count})

    # Calculate year-to-date surgeries using aggregation
    year_start = datetime(now.year, 1, 1)
    ytd_pipeline = [
        {
            "$match": {
                "treatment_type": {"$in": surgery_types},
                "treatment_date": {
                    "$gte": year_start.isoformat(),
                    "$lte": now.isoformat()
                }
            }
        },
        {
            "$count": "total"
        }
    ]

    ytd_result = await treatments_collection.aggregate(ytd_pipeline).to_list(length=1)
    year_to_date_episodes = ytd_result[0]["total"] if ytd_result else 0

    return {
        "totalPatients": total_patients,
        "totalEpisodes": total_episodes,
        "treatmentBreakdown": treatment_breakdown,
        "monthlyEpisodes": monthly_episodes,
        "yearToDateEpisodes": year_to_date_episodes,
        "loading": False
    }


@router.get("/treatments")
async def get_all_treatments(
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    episode_id: Optional[str] = Query(None, description="Filter by episode ID"),
    search: Optional[str] = Query(None, description="Search by treatment ID, procedure name, or surgeon"),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
):
    """
    Get treatments with pagination, filtering, and search.

    Search queries the entire database first, then applies pagination to results.
    This ensures search works across all records, not just the current page.
    """
    from ..database import get_treatments_collection
    treatments_collection = await get_treatments_collection()

    # Build query based on filters
    query = {}

    # Filter by patient_id or episode_id
    if patient_id:
        query["patient_id"] = patient_id
    if episode_id:
        query["episode_id"] = episode_id

    # Search across multiple fields (searches entire database)
    if search:
        search_pattern = {"$regex": search, "$options": "i"}
        search_conditions = [
            {"treatment_id": search_pattern},
            {"procedure.primary_procedure": search_pattern},
            {"team.primary_surgeon_text": search_pattern},
            {"treatment_type": search_pattern}
        ]

        # Combine with existing filters using $and
        if query:
            query = {"$and": [query, {"$or": search_conditions}]}
        else:
            query = {"$or": search_conditions}

    # Fetch treatments with pagination (applied AFTER filtering/search)
    treatments = await treatments_collection.find(query).skip(skip).limit(limit).to_list(length=limit)

    # Convert ObjectId to string
    for treatment in treatments:
        treatment["_id"] = str(treatment["_id"])

    return treatments


@router.get("/treatments/{treatment_id}")
async def get_treatment_by_id(treatment_id: str):
    """Get a specific treatment by its treatment_id (flattened for frontend compatibility)"""
    treatments_collection = await get_treatments_collection()
    clinicians_collection = await get_clinicians_collection()

    # Find the treatment
    treatment = await treatments_collection.find_one({"treatment_id": treatment_id})

    if not treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Treatment {treatment_id} not found"
        )

    # Convert ObjectId to string
    treatment["_id"] = str(treatment["_id"])

    # Build clinician map and surname map for name resolution
    clinician_map, surname_map = await build_clinician_maps(clinicians_collection)

    # Flatten nested structure for frontend compatibility
    flattened_treatment = flatten_treatment_for_frontend(treatment, clinician_map, surname_map)

    return flattened_treatment


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
    search: Optional[str] = Query(None, description="Search by episode ID, MRN, NHS number, cancer type, or clinician"),
    patient_id: Optional[str] = Query(None, description="Filter by patient MRN"),
    condition_type: Optional[ConditionType] = Query(None, description="Filter by condition type"),
    cancer_type: Optional[CancerType] = Query(None, description="Filter by cancer type"),
    lead_clinician: Optional[str] = Query(None, description="Filter by lead clinician"),
    episode_status: Optional[str] = Query(None, description="Filter by episode status"),
    start_date: Optional[str] = Query(None, description="Filter episodes after this date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter episodes before this date (YYYY-MM-DD)"),
    sort_by: Optional[str] = Query("referral_date", description="Field to sort by (referral_date or last_modified_at)")
):
    """
    List all episodes with pagination and filters.

    Search supports:
    - Episode ID
    - MRN (Medical Record Number) - encrypted field with hash-based search
    - NHS Number (10 digits) - encrypted field with hash-based search
    - Cancer type
    - Lead clinician name
    """
    from ..utils.encryption import create_searchable_query
    from ..utils.search_helpers import sanitize_search_input

    collection = await get_episodes_collection()
    patients_collection = await get_patients_collection()

    # Build query filters
    query = {}

    # Search filter - search across multiple fields including MRN and NHS number
    if search:
        # Check if search looks like MRN or NHS number (encrypted fields)
        search_encrypted_fields = False
        clean_search = search.replace(" ", "").upper()

        # MRN patterns: 8+ digits, IW+6digits, or C+6digits+2alphanumeric
        # NHS number: 10 digits
        is_mrn_or_nhs_pattern = (
            (clean_search.isdigit() and len(clean_search) >= 8) or  # 8+ digits (MRN or NHS)
            (clean_search.startswith('IW') and len(clean_search) == 8 and clean_search[2:].isdigit()) or  # IW+6digits
            (clean_search.startswith('C') and len(clean_search) == 9 and clean_search[1:7].isdigit() and clean_search[7:9].isalnum())  # C+6digits+2alphanumeric
        )

        if is_mrn_or_nhs_pattern:
            search_encrypted_fields = True
            logger.debug(f"Episode search: Searching encrypted fields (MRN/NHS): {clean_search}")

        matching_patient_ids = []

        if search_encrypted_fields:
            # Use hash-based lookup for encrypted fields (O(log n) indexed search)
            clean_search_lower = search.replace(" ", "").lower()
            nhs_query = create_searchable_query('nhs_number', clean_search_lower)
            mrn_query = create_searchable_query('mrn', clean_search_lower)

            # Search for patients by MRN or NHS number using hash indexes
            matching_patients = await patients_collection.find(
                {"$or": [nhs_query, mrn_query]},
                {"patient_id": 1}
            ).to_list(length=None)
            matching_patient_ids = [p["patient_id"] for p in matching_patients]

            logger.debug(f"Episode search: Found {len(matching_patient_ids)} patients matching MRN/NHS")
        else:
            # For non-encrypted searches, use regex pattern on MRN (backward compatibility)
            # This is less efficient but works for partial matches
            safe_search = sanitize_search_input(search)
            search_pattern = {"$regex": safe_search, "$options": "i"}

            matching_patients = await patients_collection.find(
                {"mrn": search_pattern},
                {"patient_id": 1}
            ).to_list(length=100)  # Limit to 100 to prevent performance issues
            matching_patient_ids = [p["patient_id"] for p in matching_patients]

        # Build OR query including patient_id matches from MRN/NHS search
        safe_search = sanitize_search_input(search)
        search_pattern = {"$regex": safe_search, "$options": "i"}

        or_conditions = [
            {"episode_id": search_pattern},
            {"cancer_type": search_pattern},
            {"lead_clinician": search_pattern}
        ]

        # Add patient_id matches from MRN/NHS search
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
        # Database now stores names directly (e.g., "Jim Khan", "Parvaiz")
        # Just filter by the name as-is
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

    # Bulk fetch patient MRNs (fix N+1 query problem)
    # OLD: Made N separate queries (one per episode)
    # NEW: Make 1 query to fetch all patients at once
    patient_ids = [ep["patient_id"] for ep in episodes if ep.get("patient_id")]
    if patient_ids:
        # Fetch all patients in a single query
        patients_cursor = patients_collection.find(
            {"patient_id": {"$in": patient_ids}},
            {"patient_id": 1, "mrn": 1}  # Only fetch needed fields
        )
        patients = await patients_cursor.to_list(length=len(patient_ids))

        # Build lookup map for O(1) access
        patient_map = {p["patient_id"]: p for p in patients}
    else:
        patient_map = {}

    # Convert ObjectIds to strings and add patient MRN
    for episode in episodes:
        episode["_id"] = str(episode["_id"])

        # Get patient MRN from pre-fetched map
        if "patient_id" in episode:
            patient = patient_map.get(episode["patient_id"])
            if patient:
                mrn = patient.get("mrn", None)
                # Decrypt MRN if it's encrypted
                if mrn:
                    episode["patient_mrn"] = decrypt_field("mrn", mrn)
                else:
                    episode["patient_mrn"] = None
            else:
                episode["patient_mrn"] = None

        # lead_clinician is already stored as a name in the database - no conversion needed

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

    # Populate related_surgery_ids for primary surgeries
    # Find all RTT and reversal surgeries that have a parent in this episode
    primary_surgery_ids = [t["treatment_id"] for t in treatments if t.get("treatment_type") == "surgery_primary"]
    if primary_surgery_ids:
        # Find all RTT and reversal surgeries linked to these primaries
        related_surgeries_cursor = treatments_collection.find({
            "parent_surgery_id": {"$in": primary_surgery_ids},
            "treatment_type": {"$in": ["surgery_rtt", "surgery_reversal"]}
        })
        related_surgeries = await related_surgeries_cursor.to_list(length=None)

        # Build a map of parent_id -> list of related surgeries
        related_map = {}
        for related in related_surgeries:
            parent_id = related.get("parent_surgery_id")
            if parent_id not in related_map:
                related_map[parent_id] = []
            related_map[parent_id].append({
                "treatment_id": related["treatment_id"],
                "treatment_type": related["treatment_type"],
                "date_created": related.get("created_at", related.get("treatment_date"))
            })

        # Add related_surgery_ids to each primary surgery
        for treatment in treatments:
            if treatment.get("treatment_type") == "surgery_primary":
                treatment_id = treatment["treatment_id"]
                treatment["related_surgery_ids"] = related_map.get(treatment_id, [])

    # Fetch tumours using tumour_ids array
    tumour_ids = episode.get("tumour_ids", [])
    tumours_cursor = tumours_collection.find({"tumour_id": {"$in": tumour_ids}}) if tumour_ids else []
    tumours = await tumours_cursor.to_list(length=None) if tumour_ids else []
    
    # Fetch investigations by episode_id
    investigations_cursor = investigations_collection.find({"episode_id": episode_id})
    investigations = await investigations_cursor.to_list(length=None)
    
    # Build a map of all clinicians for efficient lookup
    clinician_map, surname_map = await build_clinician_maps(clinicians_collection)

    # Also map by full name (for cases where name is already stored)
    for full_name in list(clinician_map.values()):
        if full_name:
            clinician_map[full_name] = full_name

    # Convert ObjectIds to strings
    episode["_id"] = str(episode["_id"])

    # Flatten and enrich each treatment for frontend compatibility
    flattened_treatments = []
    for treatment in treatments:
        treatment["_id"] = str(treatment["_id"])

        # Enrich with computed mortality fields
        treatment = enrich_treatment_with_mortality(treatment, deceased_date)

        # Flatten nested structure for frontend compatibility
        flattened_treatment = flatten_treatment_for_frontend(treatment, clinician_map, surname_map)
        flattened_treatments.append(flattened_treatment)

    for tumour in tumours:
        tumour["_id"] = str(tumour["_id"])

    for investigation in investigations:
        investigation["_id"] = str(investigation["_id"])

    # Include flattened treatments, tumours, and investigations in response
    episode["treatments"] = flattened_treatments
    episode["tumours"] = tumours
    episode["investigations"] = investigations

    # Enrich episode with treatment data for frontend display
    episode = enrich_episode_with_treatment_data(episode, flattened_treatments, clinician_map)

    # Resolve lead_clinician ID or text to full name
    if "lead_clinician" in episode and episode["lead_clinician"]:
        clinician_value = episode["lead_clinician"]
        # Try to resolve as clinician ID first
        if clinician_value in clinician_map:
            episode["lead_clinician"] = clinician_map[clinician_value]
        # Try to match by surname (case-insensitive)
        elif clinician_value.upper() in surname_map:
            episode["lead_clinician"] = surname_map[clinician_value.upper()]
        # Otherwise keep the text value as-is

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
        logger.error(f"Error updating episode: {str(e)}", exc_info=True)
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
        treatment['episode_id'] = episode.get('episode_id')  # Use semantic ID, not ObjectId
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

        # Add treatment_id to episode's treatment_ids array and update last_modified_at
        await episodes_collection.update_one(
            {"episode_id": episode_id},
            {
                "$addToSet": {"treatment_ids": treatment['treatment_id']},
                "$set": {"last_modified_at": datetime.utcnow()}
            }
        )
        
        # Return created treatment (flattened for frontend)
        created_treatment = await treatments_collection.find_one({"_id": result.inserted_id})
        if created_treatment:
            created_treatment["_id"] = str(created_treatment["_id"])

            # Build clinician map and surname map for name resolution
            clinicians_collection = await get_clinicians_collection()
            clinician_map, surname_map = await build_clinician_maps(clinicians_collection)

            # Flatten for frontend compatibility
            created_treatment = flatten_treatment_for_frontend(created_treatment, clinician_map, surname_map)

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
        logger.error(f"Error adding treatment: {str(e)}", exc_info=True)
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
        
        # Return updated treatment (flattened for frontend)
        updated_treatment = await treatments_collection.find_one({
            "treatment_id": treatment_id,
            "episode_id": episode["episode_id"]
        })
        if updated_treatment:
            updated_treatment["_id"] = str(updated_treatment["_id"])

            # Build clinician map and surname map for name resolution
            clinicians_collection = await get_clinicians_collection()
            clinician_map, surname_map = await build_clinician_maps(clinicians_collection)

            # Flatten for frontend compatibility
            updated_treatment = flatten_treatment_for_frontend(updated_treatment, clinician_map, surname_map)

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
        logger.error(f"Error updating treatment: {str(e)}", exc_info=True)
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

        # Add tumour_id to episode's tumour_ids array and update last_modified_at
        await episodes_collection.update_one(
            {"episode_id": episode_id},
            {
                "$addToSet": {"tumour_ids": tumour['tumour_id']},
                "$set": {"last_modified_at": datetime.utcnow()}
            }
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
        logger.error(f"Error adding tumour: {str(e)}", exc_info=True)
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
        logger.error(f"Error updating tumour: {str(e)}", exc_info=True)
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
            "episode_id": episode_id
        })

        # Delete tumour from separate collection
        result = await tumours_collection.delete_one({
            "tumour_id": tumour_id,
            "episode_id": episode_id
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
        logger.error(f"Error deleting tumour: {str(e)}", exc_info=True)
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
            "episode_id": episode_id  # Use semantic episode_id, not ObjectId
        })

        # Delete treatment from separate collection
        result = await treatments_collection.delete_one({
            "treatment_id": treatment_id,
            "episode_id": episode_id  # Use semantic episode_id, not ObjectId
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
        logger.error(f"Error deleting treatment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete treatment: {str(e)}"
        )
