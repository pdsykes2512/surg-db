"""Search and sanitization utilities for preventing NoSQL injection."""
import re
from typing import Dict, List, Tuple
from motor.motor_asyncio import AsyncIOMotorCollection


def sanitize_search_input(search: str) -> str:
    """
    Sanitize search input to prevent NoSQL injection via regex.

    This function removes spaces and escapes regex special characters
    to ensure safe use in MongoDB regex queries.

    Args:
        search: Raw search string from user input

    Returns:
        Escaped search string safe for use in MongoDB regex queries

    Example:
        >>> sanitize_search_input("A12 3456")
        'A123456'
        >>> sanitize_search_input("test[]*+")
        'test\\[\\]\\*\\+'
    """
    # Remove spaces and escape regex special characters
    return re.escape(search.replace(" ", ""))


def is_mrn_or_nhs_pattern(search: str) -> bool:
    """
    Detect if search term matches MRN or NHS number patterns.

    Patterns recognized:
    - Generic MRN: 8+ digits
    - Isle of Wight MRN: IW followed by 6 digits (e.g., IW123456)
    - NHS number: C followed by 6 digits and 2 alphanumeric chars (e.g., C123456AB)

    Args:
        search: Search string to check

    Returns:
        True if matches MRN/NHS pattern, False otherwise

    Example:
        >>> is_mrn_or_nhs_pattern("12345678")
        True
        >>> is_mrn_or_nhs_pattern("IW123456")
        True
        >>> is_mrn_or_nhs_pattern("C123456AB")
        True
        >>> is_mrn_or_nhs_pattern("Smith")
        False
    """
    clean_search = search.replace(" ", "").upper()

    # Pattern 1: Generic MRN (8+ digits)
    if clean_search.isdigit() and len(clean_search) >= 8:
        return True

    # Pattern 2: Isle of Wight MRN (IW + 6 digits)
    if (clean_search.startswith('IW') and
        len(clean_search) == 8 and
        clean_search[2:].isdigit()):
        return True

    # Pattern 3: NHS number (C + 6 digits + 2 alphanumeric)
    if (clean_search.startswith('C') and
        len(clean_search) == 9 and
        clean_search[1:7].isdigit() and
        clean_search[7:9].isalnum()):
        return True

    return False


async def build_encrypted_field_query(
    search: str,
    patients_collection: AsyncIOMotorCollection,
    create_searchable_query: callable
) -> Tuple[Dict, List[str]]:
    """
    Build MongoDB query for searching encrypted MRN/NHS fields and return matching patient IDs.

    This function:
    1. Checks if search matches MRN/NHS pattern
    2. If yes, searches encrypted fields using hash-based queries
    3. Returns both the query dict and list of matching patient IDs

    Args:
        search: Search string
        patients_collection: MongoDB collection for patients
        create_searchable_query: Function to create hash-based search queries

    Returns:
        Tuple of (query_dict, patient_ids_list)
        - query_dict: MongoDB query for encrypted fields
        - patient_ids_list: List of matching patient_id strings

    Example:
        query, patient_ids = await build_encrypted_field_query(
            "12345678",
            patients_collection,
            create_searchable_query
        )
        # query = {"$or": [{"nhs_number_hash": "..."}, {"mrn_hash": "..."}]}
        # patient_ids = ["PAT001", "PAT002"]
    """
    if not is_mrn_or_nhs_pattern(search):
        return {}, []

    # Build hash-based query for encrypted fields
    clean_search_lower = search.replace(" ", "").lower()
    nhs_query = create_searchable_query('nhs_number', clean_search_lower)
    mrn_query = create_searchable_query('mrn', clean_search_lower)
    query = {"$or": [nhs_query, mrn_query]}

    # Find matching patients
    matching_patients = await patients_collection.find(
        query,
        {"patient_id": 1}
    ).to_list(length=None)

    patient_ids = [p["patient_id"] for p in matching_patients]

    return query, patient_ids
