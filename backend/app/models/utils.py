"""
Shared utility functions for data models
"""
from datetime import datetime, date
from typing import Union, Any


def parse_date_string(v: Any) -> Union[datetime, date, str, None]:
    """
    Parse date/datetime strings consistently across all models.
    Handles:
    - YYYY-MM-DD format (converts to datetime at midnight)
    - ISO format with T separator
    - Already parsed datetime/date objects
    """
    if v is None:
        return None
    
    if isinstance(v, (datetime, date)):
        return v
    
    if isinstance(v, str) and v:
        try:
            # Handle YYYY-MM-DD format
            if len(v) == 10 and 'T' not in v:
                return datetime.fromisoformat(v + 'T00:00:00')
            # Handle ISO format
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            # Return as-is if parsing fails
            return v
    
    return v
