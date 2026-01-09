"""Utility functions for clinician name resolution and mapping."""
from typing import Dict, Tuple
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
