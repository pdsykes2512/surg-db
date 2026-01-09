"""Date formatting utilities for COSD export and API responses."""
from datetime import datetime
from typing import Dict, Any


def format_date_for_cosd(date_value) -> str:
    """
    Format datetime/date to YYYY-MM-DD for COSD XML export.

    Args:
        date_value: Date value (datetime, str, or None)

    Returns:
        String in YYYY-MM-DD format, or empty string if None

    Example:
        >>> format_date_for_cosd(datetime(2024, 1, 15))
        '2024-01-15'
        >>> format_date_for_cosd('2024-01-15T10:30:00Z')
        '2024-01-15'
        >>> format_date_for_cosd(None)
        ''
    """
    if not date_value:
        return ""

    if isinstance(date_value, str):
        # Try to parse if it's already a string
        try:
            dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
        except:
            # Return first 10 chars if already formatted, otherwise return as-is
            return date_value[:10] if len(date_value) >= 10 else date_value

    if isinstance(date_value, datetime):
        return date_value.strftime('%Y-%m-%d')

    # Fallback to string conversion
    return str(date_value)[:10] if str(date_value) else ""


def serialize_datetime_fields(document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert datetime objects to ISO strings in a document.

    This function recursively processes a document and converts all
    datetime objects to ISO format strings for JSON serialization.

    Args:
        document: Dictionary potentially containing datetime objects

    Returns:
        Dictionary with datetime objects converted to ISO strings

    Example:
        >>> doc = {"date": datetime(2024, 1, 15), "nested": {"time": datetime.now()}}
        >>> serialize_datetime_fields(doc)
        {"date": "2024-01-15T00:00:00", "nested": {"time": "2024-01-15T10:30:00"}}
    """
    for key, value in document.items():
        if hasattr(value, "isoformat"):
            # Convert datetime to ISO string
            document[key] = value.isoformat()
        elif isinstance(value, dict):
            # Recursively process nested dictionaries
            document[key] = serialize_datetime_fields(value)
        elif isinstance(value, list):
            # Process lists (check each item)
            document[key] = [
                serialize_datetime_fields(item) if isinstance(item, dict)
                else item.isoformat() if hasattr(item, "isoformat")
                else item
                for item in value
            ]

    return document
