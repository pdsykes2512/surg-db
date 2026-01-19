"""
MongoDB serialization utilities for consistent document handling
"""
from typing import List, Dict, Any
from datetime import datetime
from bson import ObjectId


def serialize_object_id(document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert ObjectId to string in a single document.

    Args:
        document: Dictionary potentially containing ObjectId _id field

    Returns:
        Dictionary with _id converted to string

    Example:
        >>> doc = {"_id": ObjectId("507f1f77bcf86cd799439011"), "name": "Test"}
        >>> serialize_object_id(doc)
        {"_id": "507f1f77bcf86cd799439011", "name": "Test"}
    """
    if document and "_id" in document and isinstance(document["_id"], ObjectId):
        document["_id"] = str(document["_id"])
    return document


def serialize_object_ids(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert ObjectId to string in a list of documents.

    Args:
        documents: List of dictionaries potentially containing ObjectId _id fields

    Returns:
        List of dictionaries with _id converted to string

    Example:
        >>> docs = [
        ...     {"_id": ObjectId("507f1f77bcf86cd799439011"), "name": "Test1"},
        ...     {"_id": ObjectId("507f1f77bcf86cd799439012"), "name": "Test2"}
        ... ]
        >>> serialize_object_ids(docs)
        [
            {"_id": "507f1f77bcf86cd799439011", "name": "Test1"},
            {"_id": "507f1f77bcf86cd799439012", "name": "Test2"}
        ]
    """
    return [serialize_object_id(doc) for doc in documents]


def serialize_nested_object_ids(data: Any) -> Any:
    """
    Recursively convert all ObjectId instances to strings in nested structures.

    Handles dictionaries, lists, and nested combinations.

    Args:
        data: Any data structure (dict, list, or primitive)

    Returns:
        Data structure with all ObjectId instances converted to strings

    Example:
        >>> data = {
        ...     "_id": ObjectId("507f1f77bcf86cd799439011"),
        ...     "items": [
        ...         {"_id": ObjectId("507f1f77bcf86cd799439012"), "name": "Item1"}
        ...     ]
        ... }
        >>> serialize_nested_object_ids(data)
        {
            "_id": "507f1f77bcf86cd799439011",
            "items": [
                {"_id": "507f1f77bcf86cd799439012", "name": "Item1"}
            ]
        }
    """
    if isinstance(data, ObjectId):
        return str(data)
    elif isinstance(data, dict):
        return {key: serialize_nested_object_ids(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [serialize_nested_object_ids(item) for item in data]
    else:
        return data


def convert_datetime_to_iso(document: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
    """
    Convert specified datetime fields to ISO format strings.

    Recursively checks nested dictionaries for datetime fields and converts them.
    Only converts fields that have the isoformat() method (datetime objects).

    Args:
        document: Dictionary potentially containing datetime fields
        fields: List of field names that might contain datetime values

    Returns:
        Dictionary with datetime fields converted to ISO strings

    Example:
        >>> from datetime import datetime
        >>> doc = {
        ...     "demographics": {
        ...         "date_of_birth": datetime(1990, 1, 1),
        ...         "deceased_date": datetime(2020, 12, 31)
        ...     }
        ... }
        >>> convert_datetime_to_iso(doc, ["date_of_birth", "deceased_date"])
        {
            "demographics": {
                "date_of_birth": "1990-01-01T00:00:00",
                "deceased_date": "2020-12-31T00:00:00"
            }
        }
    """
    if not document:
        return document

    def convert_nested(obj: Any) -> Any:
        """Recursively convert datetime fields in nested structures"""
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if key in fields and hasattr(value, "isoformat"):
                    result[key] = value.isoformat()
                else:
                    result[key] = convert_nested(value)
            return result
        elif isinstance(obj, list):
            return [convert_nested(item) for item in obj]
        else:
            return obj

    return convert_nested(document)


def serialize_datetime_fields(document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert common datetime fields to ISO format strings.

    This is a convenience wrapper around convert_datetime_to_iso that handles
    the most common datetime fields in the IMPACT database.

    Common fields converted:
    - date_of_birth, deceased_date (demographics)
    - admission_date, discharge_date (episodes)
    - surgery_date, diagnosis_date (treatments)
    - created_at, updated_at (audit fields)

    Args:
        document: Dictionary potentially containing datetime fields

    Returns:
        Dictionary with datetime fields converted to ISO strings

    Example:
        >>> doc = {"created_at": datetime.utcnow(), "name": "Test"}
        >>> serialize_datetime_fields(doc)
        {"created_at": "2024-01-01T00:00:00", "name": "Test"}
    """
    common_date_fields = [
        "date_of_birth", "deceased_date",
        "admission_date", "discharge_date",
        "surgery_date", "diagnosis_date",
        "created_at", "updated_at", "last_login",
        "date_of_death", "procedure_date"
    ]
    return convert_datetime_to_iso(document, common_date_fields)
