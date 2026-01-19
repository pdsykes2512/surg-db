"""
RStudio Integration API Routes

Provides authentication and data access endpoints for RStudio Server integration.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import Optional, List, Dict, Any
from datetime import datetime
from ..auth import get_current_user
from ..database import Database
from ..utils.encryption import decrypt_field
import httpx
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rstudio", tags=["rstudio"])

RSTUDIO_BASE_URL = "http://localhost:8787"  # RStudio Server URL (internal)
RSTUDIO_PROXY_PATH = "/rstudio-server/"  # nginx reverse proxy path (separate from React route)


def convert_value_for_r(value: Any) -> Any:
    """
    Convert MongoDB values to R-compatible types with consistent typing.

    The key challenge: MongoDB documents have inconsistent types across records.
    For example, clinical_n might be boolean True in one record and string "N1" in another.
    R's bind_rows() requires consistent types, so we standardize here.

    Args:
        value: Value from MongoDB

    Returns:
        Value converted for R compatibility:
        - Booleans → strings ("TRUE"/"FALSE") for consistency
        - Empty strings → None (becomes NA in R)
        - All other values unchanged (strings, numbers, None, etc.)
    """
    if isinstance(value, bool):
        # Convert booleans to strings to prevent type mismatches
        # (Some fields have boolean in some records, string in others)
        return "TRUE" if value else "FALSE"
    elif isinstance(value, str):
        # Empty string becomes None (NA in R)
        return None if value.strip() == '' else value
    else:
        # Pass through numbers, None, dates, etc.
        return value


def flatten_dict(data: Any, prefix: str = '', separator: str = '_') -> Dict[str, Any]:
    """
    Recursively flatten nested dictionaries and lists into a flat dictionary.
    Converts values to R-compatible types.

    Args:
        data: The data to flatten (dict, list, or primitive)
        prefix: Current key prefix
        separator: String to separate nested keys

    Returns:
        Flat dictionary with all nested structures expanded

    Examples:
        {"a": {"b": 1}} -> {"a_b": 1}
        {"a": [1, 2]} -> {"a": "1, 2"}  (arrays as comma-separated strings)
        {"a": {"b": {"c": 1}}} -> {"a_b_c": 1}
        {"occurred": True} -> {"occurred": "TRUE"}  (booleans as strings)
    """
    result = {}

    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{prefix}{separator}{key}" if prefix else key

            if isinstance(value, dict):
                # Recursively flatten nested dict
                result.update(flatten_dict(value, new_key, separator))
            elif isinstance(value, list):
                # Convert list to comma-separated string
                # Handle lists of primitives and lists of dicts
                if len(value) == 0:
                    result[new_key] = ""
                elif all(isinstance(item, (str, int, float, bool, type(None))) for item in value):
                    # List of primitives - join as comma-separated string
                    result[new_key] = ", ".join(str(v) if v is not None else "" for v in value)
                else:
                    # List of dicts/complex objects - flatten each with index
                    for idx, item in enumerate(value):
                        if isinstance(item, dict):
                            result.update(flatten_dict(item, f"{new_key}{separator}{idx}", separator))
                        else:
                            result[f"{new_key}{separator}{idx}"] = convert_value_for_r(item)
            else:
                # Primitive value - convert for R
                result[new_key] = convert_value_for_r(value)
    elif isinstance(data, list):
        # Handle top-level list
        if len(data) == 0:
            result[prefix] = ""
        elif all(isinstance(item, (str, int, float, bool, type(None))) for item in data):
            result[prefix] = ", ".join(str(v) if v is not None else "" for v in data)
        else:
            for idx, item in enumerate(data):
                if isinstance(item, dict):
                    result.update(flatten_dict(item, f"{prefix}{separator}{idx}", separator))
                else:
                    result[f"{prefix}{separator}{idx}"] = convert_value_for_r(item)
    else:
        # Primitive at top level - convert for R
        if prefix:
            result[prefix] = convert_value_for_r(data)

    return result


@router.get("/auth")
async def rstudio_auth(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Create authenticated session for RStudio Server.
    Returns redirect URL and user info for RStudio access.

    Only surgeons and admins can access RStudio.

    Also saves the JWT token to ~/.impact_token for automatic R library authentication.
    Automatically signs in to RStudio as rstudio-user.
    """
    import httpx
    import os
    import subprocess

    # Check if user has permission to use RStudio
    allowed_roles = ["admin", "surgeon"]
    if current_user["role"] not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail="RStudio access is restricted to surgeons and administrators"
        )

    # Extract JWT token from Authorization header
    auth_header = request.headers.get("authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix

    # Save token to RStudio user's home directory for automatic R authentication
    if token:
        try:
            token_file = "/home/rstudio-user/.impact_token"

            # Write token to file with restricted permissions
            with open(token_file, 'w') as f:
                f.write(token)

            # Set file permissions to 600 (read/write for owner only)
            os.chmod(token_file, 0o600)

            # Change ownership to rstudio-user
            subprocess.run(['chown', 'rstudio-user:rstudio-user', token_file], check=False)
        except Exception as e:
            # Log error but don't fail the request
            logger.warning(f"Failed to save RStudio token: {e}")

    # Get RStudio password from environment (stored in /etc/impact/secrets.env)
    rstudio_password = os.getenv("RSTUDIO_PASSWORD", "")
    if not rstudio_password:
        raise HTTPException(status_code=500, detail="RStudio password not configured")

    # Automatically sign in to RStudio as rstudio-user
    try:
        async with httpx.AsyncClient() as client:
            # Sign in to RStudio Server
            sign_in_response = await client.post(
                f"{RSTUDIO_BASE_URL}/auth-do-sign-in",
                data={
                    "username": "rstudio-user",
                    "password": rstudio_password,
                    "persist": "1",
                    "appUri": ""
                },
                follow_redirects=False
            )

            # Get session cookie from response
            session_cookie = None
            if "set-cookie" in sign_in_response.headers:
                cookies = sign_in_response.headers.get_list("set-cookie")
                for cookie in cookies:
                    if "user-id=" in cookie:
                        session_cookie = cookie.split(";")[0]
                        break
    except Exception as e:
        logger.warning(f"Failed to auto-sign-in to RStudio: {e}")

    # Construct RStudio URL for nginx proxy
    # Use the Host header directly, which should be the public-facing host:port
    # Nginx forwards the original Host header, so this should be correct
    host = request.headers.get("host", "localhost")

    # Check if we're behind a proxy (X-Forwarded-* headers)
    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    forwarded_host = request.headers.get("x-forwarded-host", host)

    # If the host includes a backend port (8000), strip it - we want the nginx port
    if ":8000" in forwarded_host:
        forwarded_host = forwarded_host.split(":")[0]

    rstudio_url = f"{forwarded_proto}://{forwarded_host}{RSTUDIO_PROXY_PATH}"

    # Return RStudio URL, user info, and credentials
    # Password is returned so frontend can display it (already authenticated users only)
    return {
        "redirect_url": rstudio_url,
        "username": "rstudio-user",  # All users share this account
        "password": rstudio_password,  # Secure password from secrets
        "full_name": current_user["full_name"],
        "role": current_user["role"],
        "message": "Sign in to RStudio with the credentials shown below"
    }


@router.get("/datasets")
async def list_available_datasets(
    current_user: dict = Depends(get_current_user)
):
    """
    List available datasets that can be loaded into RStudio.
    Provides metadata about collections and typical use cases.
    """
    # Ensure user has RStudio access
    allowed_roles = ["admin", "surgeon"]
    if current_user["role"] not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail="RStudio access is restricted to surgeons and administrators"
        )

    datasets = [
        {
            "name": "patients",
            "description": "Patient demographics and medical history",
            "fields": [
                "patient_id", "mrn", "nhs_number", "date_of_birth",
                "gender", "ethnicity", "bmi", "height", "weight",
                "smoking_status", "comorbidities"
            ],
            "row_count_estimate": "~1000-5000",
            "r_function": "get_patients()",
            "example": "patients <- get_patients()\nhead(patients)"
        },
        {
            "name": "episodes",
            "description": "Clinical episodes (cancer, IBD, benign conditions)",
            "fields": [
                "episode_id", "patient_id", "condition_type", "cancer_type",
                "referral_date", "first_seen_date", "mdt_discussion_date",
                "lead_clinician", "episode_status"
            ],
            "row_count_estimate": "~1500-7000",
            "r_function": "get_episodes(condition_type = 'cancer')",
            "example": "cancer_eps <- get_episodes(condition_type = 'cancer')\nbowel_eps <- get_episodes(condition_type = 'cancer', cancer_type = 'bowel')"
        },
        {
            "name": "treatments",
            "description": "Surgical and oncology treatments",
            "fields": [
                "treatment_id", "episode_id", "treatment_type", "admission_date",
                "surgeon", "asa_score", "surgical_approach", "urgency_classification",
                "complications", "readmission_30day", "mortality_30day", "mortality_90day"
            ],
            "row_count_estimate": "~2000-10000",
            "r_function": "get_treatments(treatment_type = 'surgery_primary')",
            "example": "surgeries <- get_treatments(treatment_type = 'surgery_primary')\nsurgeon_cases <- get_treatments(surgeon = 'Dr. Smith')"
        },
        {
            "name": "tumours",
            "description": "Tumour staging and pathology data",
            "fields": [
                "tumour_id", "episode_id", "diagnosis_date",
                "tnm_clinical_t", "tnm_clinical_n", "tnm_clinical_m",
                "tnm_pathological_t", "tnm_pathological_n", "tnm_pathological_m",
                "grade", "crm_status", "lymph_nodes_examined", "lymph_nodes_positive"
            ],
            "row_count_estimate": "~800-4000",
            "r_function": "get_tumours(cancer_type = 'bowel')",
            "example": "bowel_tumours <- get_tumours(cancer_type = 'bowel')\nhead(bowel_tumours)"
        },
        {
            "name": "surgical_outcomes",
            "description": "Joined dataset: patients + episodes + treatments (surgery only)",
            "fields": [
                "patient_id", "episode_id", "treatment_id",
                "age_at_surgery", "gender", "bmi",
                "asa_score", "surgical_approach", "urgency_classification",
                "complications", "had_complication", "had_readmission",
                "had_mortality_30day", "had_mortality_90day",
                "had_rtt", "had_icu", "los_days"
            ],
            "row_count_estimate": "~1000-5000",
            "r_function": "get_surgical_outcomes(condition_type = 'cancer')",
            "example": "outcomes <- get_surgical_outcomes(condition_type = 'cancer')\nsummary <- calculate_outcome_summary(outcomes)\nprint(summary)"
        }
    ]

    return {
        "datasets": datasets,
        "total_datasets": len(datasets),
        "note": "All datasets are read-only. IMPACT database functions are auto-loaded on startup - just call them directly (e.g., get_patients())."
    }


@router.get("/health")
async def rstudio_health_check():
    """
    Check if RStudio Server is running and accessible.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{RSTUDIO_BASE_URL}/",
                timeout=5.0,
                follow_redirects=False
            )

            # RStudio returns 302 redirect to sign-in when not authenticated
            # or 200 when running
            if response.status_code in [200, 302]:
                return {
                    "status": "healthy",
                    "message": "RStudio Server is running",
                    "url": RSTUDIO_BASE_URL
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": f"RStudio returned status {response.status_code}",
                    "url": RSTUDIO_BASE_URL
                }
    except httpx.ConnectError:
        return {
            "status": "error",
            "message": "Cannot connect to RStudio Server - service may be down",
            "url": RSTUDIO_BASE_URL
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error checking RStudio: {str(e)}",
            "url": RSTUDIO_BASE_URL
        }


@router.get("/quick-start")
async def get_quick_start_guide(
    current_user: dict = Depends(get_current_user)
):
    """
    Get quick start guide for using IMPACT R library.
    """
    # Ensure user has RStudio access
    allowed_roles = ["admin", "surgeon"]
    if current_user["role"] not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail="RStudio access is restricted to surgeons and administrators"
        )

    return {
        "title": "IMPACT RStudio Quick Start Guide",
        "note": "IMPACT database functions are auto-loaded on startup - no library() call needed!",
        "steps": [
            {
                "step": 1,
                "title": "Fetch surgical outcomes",
                "code": "outcomes <- get_surgical_outcomes(condition_type = 'cancer')",
                "description": "Gets all surgical outcomes for cancer patients (joined data). Functions are ready to use immediately!"
            },
            {
                "step": 2,
                "title": "Calculate summary statistics",
                "code": "summary <- calculate_outcome_summary(outcomes)\nprint(summary)",
                "description": "Calculates complication rates, mortality, readmissions, etc."
            },
            {
                "step": 3,
                "title": "Visualize data",
                "code": "library(ggplot2)\nggplot(outcomes, aes(x=asa_score)) + \n  geom_bar(fill='steelblue') + \n  labs(title='Surgeries by ASA Score', x='ASA Score', y='Count') + \n  theme_minimal()",
                "description": "Create visualizations with ggplot2"
            },
            {
                "step": 4,
                "title": "Survival analysis example",
                "code": "library(survival)\nlibrary(survminer)\n\nsurv_obj <- Surv(time = rep(90, nrow(outcomes)), \n                 event = outcomes$had_mortality_90day)\nkm_fit <- survfit(surv_obj ~ asa_score, data = outcomes)\nggsurvplot(km_fit, data = outcomes, pval = TRUE, \n           risk.table = TRUE, title = '90-Day Survival by ASA Score')",
                "description": "Perform Kaplan-Meier survival analysis"
            }
        ],
        "common_functions": [
            "get_patients() - Get patient demographics",
            "get_episodes() - Get clinical episodes",
            "get_treatments() - Get treatment records",
            "get_tumours() - Get tumour staging data",
            "get_surgical_outcomes() - Get joined surgical outcome data",
            "calculate_outcome_summary() - Calculate summary statistics"
        ],
        "tips": [
            "IMPACT functions are auto-loaded - don't use library(impactdb), just call the functions directly!",
            "All functions support filtering - check function documentation with ?function_name",
            "Data is read-only - you cannot modify the database from RStudio",
            "Use dplyr for data manipulation: filter(), mutate(), group_by(), summarise()",
            "Use ggplot2 for visualizations",
            "Use survival package for Kaplan-Meier and Cox regression",
            "Save your R scripts to your workspace - they persist between sessions"
        ]
    }

# ============================================================================
# DATA ACCESS ENDPOINTS FOR RSTUDIO
# ============================================================================
# These endpoints provide decrypted, privacy-preserving data access for RStudio
# - Backend handles decryption (RStudio never sees encrypted values)
# - Sensitive fields (names, full dates) are stripped before returning
# - Derived fields (years, ages) are calculated from decrypted data

# List of encrypted fields that should NEVER be sent to RStudio
ENCRYPTED_FIELDS = {
    'nhs_number', 'mrn', 'hospital_number',
    'nhs_number_hash', 'mrn_hash',
    'first_name', 'last_name',
    'date_of_birth', 'deceased_date', 'postcode'
}

def strip_encrypted_fields(doc: dict) -> dict:
    """Remove all encrypted fields from document before sending to RStudio"""
    if not doc:
        return doc
    
    # Remove top-level encrypted fields
    for field in ENCRYPTED_FIELDS:
        doc.pop(field, None)
    
    # Clean demographics nested object
    if 'demographics' in doc and isinstance(doc['demographics'], dict):
        for field in ENCRYPTED_FIELDS:
            doc['demographics'].pop(field, None)
    
    return doc

def calculate_year_from_date(date_str: Optional[str]) -> Optional[int]:
    """
    Convert date string to year only.
    Handles encrypted dates by decrypting first.
    Returns None if date is None or invalid.
    """
    if not date_str:
        return None
    
    try:
        # If encrypted, decrypt first
        if isinstance(date_str, str) and date_str.startswith('ENC:'):
            date_str = decrypt_field('deceased_date', date_str)
            if not date_str:
                return None
        
        # Parse date and extract year
        if isinstance(date_str, datetime):
            return date_str.year
        elif isinstance(date_str, str):
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.year
        return None
    except Exception:
        return None

def calculate_age_at_date(dob_str: Optional[str], event_date_str: Optional[str]) -> Optional[float]:
    """
    Calculate age in years at a specific event date.
    Handles encrypted dates by decrypting first.
    Returns age as float (e.g., 45.3 years) or None if dates invalid.
    """
    if not dob_str or not event_date_str:
        return None
    
    try:
        # Decrypt if needed
        if isinstance(dob_str, str) and dob_str.startswith('ENC:'):
            dob_str = decrypt_field('date_of_birth', dob_str)
        if isinstance(event_date_str, str) and event_date_str.startswith('ENC:'):
            event_date_str = decrypt_field('first_seen_date', event_date_str)
        
        if not dob_str or not event_date_str:
            return None
        
        # Parse dates
        if isinstance(dob_str, str):
            dob = datetime.fromisoformat(dob_str.replace('Z', '+00:00'))
        else:
            dob = dob_str
            
        if isinstance(event_date_str, str):
            event_date = datetime.fromisoformat(event_date_str.replace('Z', '+00:00'))
        else:
            event_date = event_date_str
        
        # Calculate age
        age_days = (event_date - dob).days
        return age_days / 365.25
    except Exception:
        return None


@router.get("/data/patients")
async def get_patients_for_rstudio(
    limit: int = Query(0, description="Max records (0 = all)"),
    skip: int = Query(0, description="Records to skip"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get patient data for RStudio analysis.

    Security:
    - All encrypted fields are removed before returning
    - date_of_birth is converted to birth_year only (full DOB never returned)
    - deceased_date is converted to deceased_year only
    - Static 'age' field is excluded (use age_at_diagnosis from episodes instead)
    - Structure is flattened for easy use in R
    """
    # Check permissions
    allowed_roles = ["admin", "surgeon"]
    if current_user["role"] not in allowed_roles:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get data from MongoDB
    patients_coll = Database.get_collection("patients")
    cursor = patients_coll.find({}).skip(skip)
    if limit > 0:
        cursor = cursor.limit(limit)

    patients = await cursor.to_list(length=None if limit == 0 else limit)

    # Process and flatten each patient
    flattened_patients = []
    for patient in patients:
        # Start with top-level fields
        flat_patient = {
            'patient_id': patient.get('patient_id', '')
        }

        # Flatten demographics to top level (no prefix)
        if 'demographics' in patient and isinstance(patient['demographics'], dict):
            demo = patient['demographics']

            # Convert date_of_birth to year only (for birth_year)
            if 'date_of_birth' in demo:
                year = calculate_year_from_date(demo['date_of_birth'])
                if year:
                    flat_patient['birth_year'] = year

            # Convert deceased_date to year only
            if 'deceased_date' in demo:
                year = calculate_year_from_date(demo['deceased_date'])
                if year:
                    flat_patient['deceased_year'] = year

            # Flatten other demographics fields (excluding encrypted ones and dates)
            for key, value in demo.items():
                if key not in ENCRYPTED_FIELDS and key not in ['deceased_date', 'date_of_birth', 'age']:
                    # Recursively flatten nested structures
                    if isinstance(value, (list, dict)):
                        flattened = flatten_dict(value, prefix=key)
                        flat_patient.update(flattened)
                    else:
                        flat_patient[key] = convert_value_for_r(value)

        # Add other top-level fields (recursively flatten nested structures)
        # Exclude medical_history - not needed for clinical analysis
        for key, value in patient.items():
            if key not in ['_id', 'patient_id', 'demographics', 'medical_history', 'created_at', 'updated_at', 'updated_by']:
                if key not in ENCRYPTED_FIELDS:
                    # Recursively flatten nested structures
                    if isinstance(value, (list, dict)):
                        flattened = flatten_dict(value, prefix=key)
                        flat_patient.update(flattened)
                    else:
                        flat_patient[key] = convert_value_for_r(value)

        flattened_patients.append(flat_patient)

    return flattened_patients


@router.get("/data/episodes")
async def get_episodes_for_rstudio(
    condition_type: Optional[str] = Query(None, description="Filter by condition type"),
    cancer_type: Optional[str] = Query(None, description="Filter by cancer type"),
    limit: int = Query(0, description="Max records (0 = all)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get episode data for RStudio analysis with age_at_diagnosis.
    
    Age calculation:
    - Uses first_seen_date (most reliable field)
    - Calculated from encrypted date_of_birth (which is then removed)
    
    Security:
    - All encrypted fields removed before returning
    - DOB used only for age calculation, never returned
    """
    # Check permissions
    allowed_roles = ["admin", "surgeon"]
    if current_user["role"] not in allowed_roles:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Build query
    query = {}
    if condition_type:
        query['condition_type'] = condition_type
    if cancer_type:
        query['cancer_type'] = cancer_type
    
    # Get episodes
    episodes_coll = Database.get_collection("episodes")
    cursor = episodes_coll.find(query)
    if limit > 0:
        cursor = cursor.limit(limit)
    
    episodes = await cursor.to_list(length=None if limit == 0 else limit)
    
    # Get patient IDs for age calculation
    patient_ids = list(set(str(ep.get('patient_id')) for ep in episodes if ep.get('patient_id')))
    
    # Get patients (for DOB)
    patients_coll = Database.get_collection("patients")
    patients = await patients_coll.find({'patient_id': {'$in': patient_ids}}).to_list(length=None)
    
    # Build patient DOB map
    patient_dob_map = {}
    for patient in patients:
        pid = str(patient.get('patient_id'))
        if 'demographics' in patient and isinstance(patient['demographics'], dict):
            dob = patient['demographics'].get('date_of_birth')
            if dob:
                patient_dob_map[pid] = dob
    
    # Process and flatten each episode
    flattened_episodes = []
    for episode in episodes:
        # Start with basic fields
        flat_episode = {
            'episode_id': episode.get('episode_id', ''),
            'patient_id': episode.get('patient_id', '')
        }

        # Calculate age_at_diagnosis from first_seen_date
        patient_id = str(episode.get('patient_id'))
        first_seen = episode.get('first_seen_date')

        if patient_id in patient_dob_map and first_seen:
            age = calculate_age_at_date(patient_dob_map[patient_id], first_seen)
            if age is not None:
                flat_episode['age_at_diagnosis'] = round(age, 1)

        # Add other top-level fields (recursively flatten nested structures)
        for key, value in episode.items():
            if key not in ['_id', 'episode_id', 'patient_id', 'created_at', 'updated_at', 'updated_by']:
                if key not in ENCRYPTED_FIELDS:
                    # Recursively flatten nested structures
                    if isinstance(value, (list, dict)):
                        flattened = flatten_dict(value, prefix=key)
                        flat_episode.update(flattened)
                    else:
                        flat_episode[key] = convert_value_for_r(value)

        flattened_episodes.append(flat_episode)

    return flattened_episodes


@router.get("/data/treatments")
async def get_treatments_for_rstudio(
    treatment_type: Optional[str] = Query(None, description="Filter by treatment type"),
    surgeon: Optional[str] = Query(None, description="Filter by surgeon"),
    limit: int = Query(0, description="Max records (0 = all)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get treatment data for RStudio analysis.
    
    Security:
    - All encrypted fields removed before returning
    """
    # Check permissions
    allowed_roles = ["admin", "surgeon"]
    if current_user["role"] not in allowed_roles:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Build query
    query = {}
    if treatment_type:
        query['treatment_type'] = treatment_type
    if surgeon:
        query['surgeon'] = surgeon
    
    # Get treatments
    treatments_coll = Database.get_collection("treatments")
    cursor = treatments_coll.find(query)
    if limit > 0:
        cursor = cursor.limit(limit)
    
    treatments = await cursor.to_list(length=None if limit == 0 else limit)

    # Process and flatten each treatment
    flattened_treatments = []
    for treatment in treatments:
        # Start with basic fields
        flat_treatment = {
            'treatment_id': treatment.get('treatment_id', ''),
            'episode_id': treatment.get('episode_id', ''),
            'patient_id': treatment.get('patient_id', '')
        }

        # Add other top-level fields (recursively flatten nested structures)
        for key, value in treatment.items():
            if key not in ['_id', 'treatment_id', 'episode_id', 'patient_id', 'created_at', 'updated_at', 'updated_by']:
                if key not in ENCRYPTED_FIELDS:
                    # Recursively flatten nested structures
                    if isinstance(value, (list, dict)):
                        flattened = flatten_dict(value, prefix=key)
                        flat_treatment.update(flattened)
                    else:
                        flat_treatment[key] = convert_value_for_r(value)

        flattened_treatments.append(flat_treatment)

    return flattened_treatments


@router.get("/data/tumours")
async def get_tumours_for_rstudio(
    cancer_type: Optional[str] = Query(None, description="Filter by cancer type"),
    limit: int = Query(0, description="Max records (0 = all)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get tumour data for RStudio analysis.
    
    Security:
    - All encrypted fields removed before returning
    """
    # Check permissions
    allowed_roles = ["admin", "surgeon"]
    if current_user["role"] not in allowed_roles:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Build query
    query = {}
    if cancer_type:
        query['cancer_type'] = cancer_type
    
    # Get tumours
    tumours_coll = Database.get_collection("tumours")
    cursor = tumours_coll.find(query)
    if limit > 0:
        cursor = cursor.limit(limit)
    
    tumours = await cursor.to_list(length=None if limit == 0 else limit)

    # Process and flatten each tumour
    flattened_tumours = []
    for tumour in tumours:
        # Start with basic fields
        flat_tumour = {
            'tumour_id': tumour.get('tumour_id', ''),
            'episode_id': tumour.get('episode_id', ''),
            'patient_id': tumour.get('patient_id', '')
        }

        # Add other top-level fields (recursively flatten nested structures)
        for key, value in tumour.items():
            if key not in ['_id', 'tumour_id', 'episode_id', 'patient_id', 'created_at', 'updated_at', 'updated_by']:
                if key not in ENCRYPTED_FIELDS:
                    # Recursively flatten nested structures
                    if isinstance(value, (list, dict)):
                        flattened = flatten_dict(value, prefix=key)
                        flat_tumour.update(flattened)
                    else:
                        flat_tumour[key] = convert_value_for_r(value)

        flattened_tumours.append(flat_tumour)

    return flattened_tumours
