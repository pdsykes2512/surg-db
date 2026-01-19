"""
Validation helper functions for common database operations.
"""
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorCollection


async def check_entity_exists(
    collection: AsyncIOMotorCollection,
    query_filter: Dict[str, Any],
    entity_name: str,
    entity_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Check if an entity exists in the database and raise 404 if not found.

    Args:
        collection: MongoDB collection to search
        query_filter: MongoDB query filter
        entity_name: Human-readable name of entity type (e.g., "Patient", "Episode")
        entity_id: Optional entity identifier for error message

    Returns:
        The found document

    Raises:
        HTTPException: 404 if entity not found

    Example:
        >>> patient = await check_entity_exists(
        ...     collection=patients_collection,
        ...     query_filter={"patient_id": "PAT001"},
        ...     entity_name="Patient",
        ...     entity_id="PAT001"
        ... )
        # Returns patient doc if found, raises 404 if not found
    """
    existing = await collection.find_one(query_filter)
    if not existing:
        if entity_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{entity_name} '{entity_id}' not found"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{entity_name} not found"
            )
    return existing


async def check_entity_not_exists(
    collection: AsyncIOMotorCollection,
    query_filter: Dict[str, Any],
    entity_name: str,
    conflict_message: Optional[str] = None
) -> None:
    """
    Check that an entity does NOT exist in the database and raise 409 if it does.

    Useful for validating uniqueness constraints before creating new entities.

    Args:
        collection: MongoDB collection to search
        query_filter: MongoDB query filter
        entity_name: Human-readable name of entity type (e.g., "Patient", "Episode")
        conflict_message: Optional custom conflict message

    Raises:
        HTTPException: 409 if entity already exists

    Example:
        >>> await check_entity_not_exists(
        ...     collection=patients_collection,
        ...     query_filter={"mrn_hash": mrn_hash},
        ...     entity_name="Patient",
        ...     conflict_message="A patient with this MRN already exists"
        ... )
        # Raises 409 if patient exists, otherwise returns None
    """
    existing = await collection.find_one(query_filter)
    if existing:
        message = conflict_message or f"{entity_name} already exists"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message
        )
