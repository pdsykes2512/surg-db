"""Utility functions for clinician name resolution and mapping."""
from typing import Dict, Tuple, Optional
from motor.motor_asyncio import AsyncIOMotorCollection


async def build_clinician_maps(clinicians_collection: AsyncIOMotorCollection) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Build clinician_map and surname_map for name resolution.

    Args:
        clinicians_collection: AsyncIOMotorCollection instance for clinicians

    Returns:
        tuple: (clinician_map, surname_map) where:
            - clinician_map: Dict[str, str] mapping ObjectId to full name
            - surname_map: Dict[str, str] mapping UPPERCASE surname to full name

    Example:
        clinician_map = {
            "507f1f77bcf86cd799439011": "John Smith",
            "507f1f77bcf86cd799439012": "Jane Doe"
        }
        surname_map = {
            "SMITH": "John Smith",
            "DOE": "Jane Doe"
        }
    """
    clinician_map = {}
    surname_map = {}

    clinicians = await clinicians_collection.find({}).to_list(length=None)

    for clinician in clinicians:
        # Build full name from first_name and surname
        full_name = f"{clinician.get('first_name', '')} {clinician.get('surname', '')}".strip()
        if not full_name:
            # Fallback to 'name' field or ObjectId
            full_name = clinician.get('name', str(clinician['_id']))

        # Map ObjectId to full name
        clinician_map[str(clinician['_id'])] = full_name

        # Also map by surname (case-insensitive) for text matching
        surname = clinician.get('surname', '').strip()
        if surname:
            surname_map[surname.upper()] = full_name

    return clinician_map, surname_map


def resolve_clinician_name(
    clinician_id: Optional[str] = None,
    clinician_text: Optional[str] = None,
    clinician_map: Optional[Dict[str, str]] = None,
    surname_map: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Resolve clinician name using multiple strategies.

    Resolution strategies (in order):
    1. If clinician_id provided and in clinician_map, use mapped full name
    2. If clinician_text provided and matches surname in surname_map (case-insensitive), use mapped full name
    3. Fallback: Use clinician_text or clinician_id as-is

    Args:
        clinician_id: ObjectId string of clinician (preferred)
        clinician_text: Text representation of clinician name (fallback)
        clinician_map: Dict mapping ObjectId to full name
        surname_map: Dict mapping UPPERCASE surname to full name

    Returns:
        Resolved clinician full name, or None if no valid input

    Example:
        >>> resolve_clinician_name(
        ...     clinician_id="507f1f77bcf86cd799439011",
        ...     clinician_text="SMITH",
        ...     clinician_map={"507f1f77bcf86cd799439011": "John Smith"},
        ...     surname_map={"SMITH": "John Smith"}
        ... )
        "John Smith"

        >>> resolve_clinician_name(
        ...     clinician_text="Jane Doe",
        ...     clinician_map={},
        ...     surname_map={}
        ... )
        "Jane Doe"
    """
    # Strategy 1: Resolve by clinician ID
    if clinician_map and clinician_id:
        surgeon_name = clinician_map.get(clinician_id)
        if surgeon_name:
            return surgeon_name

    # Strategy 2: Match by surname (case-insensitive)
    if surname_map and clinician_text:
        surgeon_name = surname_map.get(clinician_text.upper())
        if surgeon_name:
            return surgeon_name

    # Fallback: Use the text value or ID as-is
    return clinician_text or clinician_id
