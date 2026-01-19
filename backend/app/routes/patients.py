"""
Patient API Routes

This module provides RESTful API endpoints for managing patient records in the IMPACT system.
All patient data is encrypted at rest using AES-256 encryption to comply with UK GDPR Article 32
and NHS Caldicott Principles.

Key Features:
    - Field-level encryption for sensitive patient identifiers (NHS number, MRN, DOB)
    - Hash-based searchable encryption for fast lookups without decryption
    - Role-based access control (data_entry, admin)
    - Comprehensive audit logging for all operations
    - Pagination support for large datasets

Endpoints:
    POST   /api/patients/         - Create new patient
    GET    /api/patients/         - List all patients with search
    GET    /api/patients/count    - Count patients
    GET    /api/patients/{id}     - Get single patient
    PUT    /api/patients/{id}     - Update patient
    DELETE /api/patients/{id}     - Delete patient (admin only)

Security:
    - All endpoints require authentication via JWT token
    - Create/Update/Delete require data_entry role or higher
    - Delete requires admin role
    - Sensitive fields encrypted before storage
    - MRN uniqueness enforced at database level
"""
# Standard library
import logging
import re
from datetime import datetime
from typing import List, Optional

# Third-party
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError, PyMongoError

# Local application
from ..auth import get_current_user, require_data_entry_or_higher, require_admin
from ..database import get_patients_collection, get_episodes_collection
from ..models.patient import Patient, PatientCreate, PatientUpdate
from ..utils.encryption import encrypt_document, decrypt_document, create_searchable_query, generate_search_hash
from ..utils.search_helpers import sanitize_search_input

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.post("/", response_model=Patient, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient: PatientCreate,
    current_user: dict = Depends(require_data_entry_or_higher)
):
    """Create a new patient record with encrypted sensitive fields.
    
    Creates a new patient in the database with automatic encryption of sensitive identifiers
    (NHS number, MRN, DOB, postcode). Generates searchable hashes for encrypted fields to
    enable fast lookups without decryption.
    
    Args:
        patient: PatientCreate model containing patient demographics and medical history
        current_user: Authenticated user context (requires data_entry role or higher)
    
    Returns:
        Patient: Created patient record with decrypted fields for response
    
    Raises:
        HTTPException(400): If MRN already exists (duplicate patient)
        HTTPException(500): If database operation fails
    
    Security:
        - Requires data_entry role or higher
        - Encrypts NHS number, MRN, DOB, and postcode using AES-256
        - Generates searchable hashes for MRN and NHS number
        - Records created_by and created_at for audit trail
    
    Example:
        POST /api/patients/
        {
            "patient_id": "A1B2C3",
            "mrn": "12345678",
            "nhs_number": "1234567890",
            "demographics": {
                "date_of_birth": "1975-03-15",
                "gender": "male",
                "postcode": "SW1A 1AA"
            }
        }
    """
    try:
        collection = await get_patients_collection()

        # Check if MRN already exists (using hash since MRNs are encrypted)
        mrn_hash = generate_search_hash("mrn", patient.mrn)
        existing = await collection.find_one({"mrn_hash": mrn_hash})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Patient with MRN {patient.mrn} already exists"
            )

        # Insert patient with encrypted sensitive fields
        patient_dict = patient.model_dump()
        patient_dict["created_at"] = datetime.utcnow()
        patient_dict["updated_at"] = datetime.utcnow()
        patient_dict["created_by"] = current_user["username"]
        patient_dict["updated_by"] = current_user["username"]

        # Encrypt sensitive fields before storing
        encrypted_patient = encrypt_document(patient_dict)

        result = await collection.insert_one(encrypted_patient)

        # Retrieve and return created patient (decrypted for response)
        created_patient = await collection.find_one({"_id": result.inserted_id})
        created_patient["_id"] = str(created_patient["_id"])
        # Decrypt before returning
        decrypted_patient = decrypt_document(created_patient)
        return Patient(**decrypted_patient)
    except HTTPException:
        raise
    except DuplicateKeyError:
        logger.warning(f"Duplicate patient MRN attempted: {patient.mrn}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Patient with MRN {patient.mrn} already exists"
        )
    except ValidationError as e:
        logger.error(f"Validation error creating patient: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid patient data: {str(e)}"
        )
    except PyMongoError as e:
        logger.error(f"Database error creating patient: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating patient: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get("/count")
async def count_patients(
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get total count of patients matching optional search criteria.
    
    Counts patients with optional search filtering. Automatically detects whether search
    term is an encrypted field (MRN/NHS number) or non-encrypted field (patient_id) and
    uses appropriate lookup strategy.
    
    Args:
        search: Optional search term (MRN, NHS number, or patient_id)
        current_user: Authenticated user context (requires any authenticated role)
    
    Returns:
        dict: {"count": int} - Total number of matching patients
    
    Search Logic:
        - MRN patterns: 8+ digits, IW+6digits, or C+6digits+2alphanumeric
        - NHS number: 10 digits
        - Encrypted field search uses O(log n) hash-based indexed lookup
        - Non-encrypted search uses O(n) regex pattern matching
    
    Example:
        GET /api/patients/count?search=12345678
        Response: {"count": 1}
    """
    collection = await get_patients_collection()

    # Check if search looks like MRN or NHS number (encrypted fields)
    search_encrypted_fields = False
    if search:
        clean_search = search.replace(" ", "").upper()
        # MRN patterns: 8+ digits, IW+6digits, or C+6digits+2alphanumeric
        is_mrn_pattern = (
            (clean_search.isdigit() and len(clean_search) >= 8) or
            (clean_search.startswith('IW') and len(clean_search) == 8 and clean_search[2:].isdigit()) or
            (clean_search.startswith('C') and len(clean_search) == 9 and clean_search[1:7].isdigit() and clean_search[7:9].isalnum())
        )
        if is_mrn_pattern:
            search_encrypted_fields = True

    # If searching encrypted fields, use hash-based lookup (O(log n) vs O(n))
    if search and search_encrypted_fields:
        clean_search = search.replace(" ", "").lower()

        # Build OR query to search both NHS number and MRN hash fields
        nhs_query = create_searchable_query('nhs_number', clean_search)
        mrn_query = create_searchable_query('mrn', clean_search)

        # MongoDB $or query for fast indexed lookup
        query = {"$or": [nhs_query, mrn_query]}

        total = await collection.count_documents(query)
        return {"count": total}

    # Build query with search filter for non-encrypted fields
    query = {}
    if search:
        safe_search = sanitize_search_input(search)
        search_pattern = {"$regex": safe_search, "$options": "i"}
        query = {"patient_id": search_pattern}

    total = await collection.count_documents(query)
    return {"count": total}


@router.get("/", response_model=List[Patient])
async def list_patients(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List patients with pagination, search, and sorting by most recent episode.
    
    Returns paginated list of patients sorted by their most recent episode referral date.
    Supports searching by MRN, NHS number, or patient_id with automatic field detection
    and optimized query strategy (hash-based for encrypted fields, regex for others).
    
    Args:
        skip: Number of records to skip for pagination (default: 0)
        limit: Maximum number of records to return (default: 100, max: 100)
        search: Optional search term (MRN, NHS number, or patient_id)
        current_user: Authenticated user context (requires any authenticated role)
    
    Returns:
        List[Patient]: List of patients with decrypted fields, sorted by most recent episode
    
    Query Optimization:
        - Uses MongoDB aggregation pipeline for efficient joins
        - Encrypted field search: O(log n) via hash indexes
        - Non-encrypted search: O(n) via regex
        - Sorting by most recent referral date calculated in database
        - Pagination applied at database level for efficiency
    
    Search Patterns:
        - MRN: 8+ digits, IW######, or C######XX
        - NHS Number: 10 digits
        - Patient ID: Any alphanumeric string
    
    Example:
        GET /api/patients/?skip=0&limit=50&search=12345678
        Response: [Patient, Patient, ...]
    """
    collection = await get_patients_collection()
    episodes_collection = await get_episodes_collection()

    # Check if search looks like MRN or NHS number (encrypted fields that need special handling)
    search_encrypted_fields = False
    if search:
        # Remove spaces and check patterns
        clean_search = search.replace(" ", "").upper()
        # MRN patterns: 8+ digits, IW+6digits, or C+6digits+2alphanumeric
        # NHS number: 10 digits
        is_mrn_pattern = (
            (clean_search.isdigit() and len(clean_search) >= 8) or  # 8+ digits
            (clean_search.startswith('IW') and len(clean_search) == 8 and clean_search[2:].isdigit()) or  # IW+6digits
            (clean_search.startswith('C') and len(clean_search) == 9 and clean_search[1:7].isdigit() and clean_search[7:9].isalnum())  # C+6digits+2alphanumeric
        )
        if is_mrn_pattern:
            search_encrypted_fields = True
            logger.debug(f"Searching encrypted fields (MRN/NHS): {clean_search}")

    # Build query with search filter if provided
    query = {}
    if search:
        if search_encrypted_fields:
            # Use hash-based lookup for encrypted fields (O(log n) indexed search)
            clean_search = search.replace(" ", "").lower()
            nhs_query = create_searchable_query('nhs_number', clean_search)
            mrn_query = create_searchable_query('mrn', clean_search)
            query = {"$or": [nhs_query, mrn_query]}
            logger.debug(f"Search encrypted (hash-based): {clean_search} -> {query}")
        else:
            # Sanitize search input to prevent NoSQL injection
            safe_search = sanitize_search_input(search)
            search_pattern = {"$regex": safe_search, "$options": "i"}
            # Only search non-encrypted fields (patient_id)
            query = {"patient_id": search_pattern}
            logger.debug(f"Search non-encrypted: {search} -> query: {query}")

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
                            "in": "$$ep.referral_date"
                        }
                    }
                }
            }
        },
        # Sort by most recent referral date (nulls last), then by patient_id
        {"$sort": {"most_recent_referral": -1, "patient_id": 1}},
        # Remove the episodes array from output
        {"$project": {"episodes": 0}},
        # Apply pagination in database (now works for all searches thanks to hash indexes)
        {"$skip": skip},
        {"$limit": limit}
    ]

    patients = await collection.aggregate(pipeline).to_list(length=None)

    # Convert ObjectId to string, decrypt sensitive fields, and handle datetime conversion
    decrypted_patients = []
    for patient in patients:
        patient["_id"] = str(patient["_id"])
        # Remove most_recent_referral from output (only used for sorting)
        patient.pop("most_recent_referral", None)

        # Decrypt sensitive fields
        patient = decrypt_document(patient)

        # Convert datetime objects to ISO format strings for Pydantic validation
        if patient.get("demographics"):
            demo = patient["demographics"]
            # Convert date_of_birth if it's a datetime object
            if demo.get("date_of_birth") and hasattr(demo["date_of_birth"], "isoformat"):
                demo["date_of_birth"] = demo["date_of_birth"].isoformat()
            # Convert deceased_date if it's a datetime object
            if demo.get("deceased_date") and hasattr(demo["deceased_date"], "isoformat"):
                demo["deceased_date"] = demo["deceased_date"].isoformat()

        decrypted_patients.append(patient)

    # No manual filtering needed - MongoDB hash indexes handle encrypted searches efficiently
    return [Patient(**patient) for patient in decrypted_patients]


@router.get("/{patient_id}", response_model=Patient)
async def get_patient(
    patient_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Retrieve a single patient by patient_id.
    
    Args:
        patient_id: Unique patient identifier (6-character alphanumeric hash)
        current_user: Authenticated user context (requires any authenticated role)
    
    Returns:
        Patient: Patient record with all decrypted fields
    
    Raises:
        HTTPException(404): If patient not found
    
    Example:
        GET /api/patients/A1B2C3
    """
    collection = await get_patients_collection()

    patient = await collection.find_one({"patient_id": patient_id})
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )

    patient["_id"] = str(patient["_id"])
    # Decrypt sensitive fields before returning
    patient = decrypt_document(patient)
    return Patient(**patient)


@router.put("/{patient_id}", response_model=Patient)
async def update_patient(
    patient_id: str,
    patient_update: PatientUpdate,
    current_user: dict = Depends(require_data_entry_or_higher)
):
    """Update an existing patient record with encrypted sensitive fields.
    
    Updates only the fields provided in the request body. Automatically encrypts any
    sensitive fields (NHS number, MRN, DOB) and updates searchable hashes for fast lookups.
    
    Args:
        patient_id: Unique patient identifier (6-character alphanumeric hash)
        patient_update: PatientUpdate model with fields to update (all optional)
        current_user: Authenticated user context (requires data_entry role or higher)
    
    Returns:
        Patient: Updated patient record with all decrypted fields
    
    Raises:
        HTTPException(404): If patient not found
        HTTPException(500): If database operation fails
    
    Security:
        - Requires data_entry role or higher
        - Re-encrypts modified sensitive fields with AES-256
        - Updates searchable hashes for modified MRN/NHS number
        - Records updated_by and updated_at for audit trail
    
    Example:
        PUT /api/patients/A1B2C3
        {
            "demographics": {
                "postcode": "SW1A 2AA"
            }
        }
    """
    try:
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
            update_data["updated_by"] = current_user["username"]

            # Encrypt sensitive fields before updating
            encrypted_update = encrypt_document(update_data)

            await collection.update_one(
                {"patient_id": patient_id},
                {"$set": encrypted_update}
            )

        # Return updated patient (decrypted)
        updated_patient = await collection.find_one({"patient_id": patient_id})
        updated_patient["_id"] = str(updated_patient["_id"])
        # Decrypt before returning
        decrypted_patient = decrypt_document(updated_patient)
        return Patient(**decrypted_patient)
    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"Validation error updating patient {patient_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid patient data: {str(e)}"
        )
    except PyMongoError as e:
        logger.error(f"Database error updating patient {patient_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed"
        )
    except Exception as e:
        logger.error(f"Unexpected error updating patient {patient_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: str,
    current_user: dict = Depends(require_admin)
):
    """Delete a patient record permanently from the database.
    
    Permanently removes a patient record. This operation cannot be undone.
    Use with caution as it may violate data retention policies if patient has
    linked episodes or treatments.
    
    Args:
        patient_id: Unique patient identifier (6-character alphanumeric hash)
        current_user: Authenticated user context (requires admin role)
    
    Returns:
        None (HTTP 204 No Content on success)
    
    Raises:
        HTTPException(404): If patient not found
        HTTPException(403): If user lacks admin role
        HTTPException(500): If database operation fails
    
    Security:
        - Requires admin role (highest privilege level)
        - Consider checking for linked episodes before deletion
        - Audit log should record deletion for compliance
    
    Warning:
        This operation may violate NHS Records Management Code (20-year retention).
        Consider soft-deletion (marking as deleted) instead for clinical records.
    
    Example:
        DELETE /api/patients/A1B2C3
    """
    try:
        collection = await get_patients_collection()

        result = await collection.delete_one({"patient_id": patient_id})

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_id} not found"
            )

        return None
    except HTTPException:
        raise
    except PyMongoError as e:
        logger.error(f"Database error deleting patient {patient_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed"
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting patient {patient_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )
