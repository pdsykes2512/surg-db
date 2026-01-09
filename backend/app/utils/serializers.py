"""
MongoDB serialization utilities for consistent document handling
"""
from typing import List, Dict, Any
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
