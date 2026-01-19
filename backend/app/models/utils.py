"""
Shared utility functions for data models
"""
from datetime import datetime, date
from typing import Union, Any
from bson import ObjectId


class PyObjectId(str):
    """
    Custom ObjectId type for Pydantic v2.

    This is a shared implementation used across all models to ensure consistency.
    Converts MongoDB ObjectId instances to strings for JSON serialization while
    maintaining validation.

    Usage:
        from app.models.utils import PyObjectId

        class MyModel(BaseModel):
            id: PyObjectId = Field(alias="_id")
    """
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        from pydantic_core import core_schema

        def validate(value):
            """Validate and convert MongoDB ObjectId to string.

            Accepts ObjectId instances or valid ObjectId strings and ensures
            the output is always a string representation of the ObjectId.

            Args:
                value: ObjectId instance, valid ObjectId string, or invalid value

            Returns:
                str: String representation of the ObjectId

            Raises:
                ValueError: If value is not a valid ObjectId or correct type
            """
            if isinstance(value, ObjectId):
                return str(value)
            if isinstance(value, str):
                if not ObjectId.is_valid(value):
                    raise ValueError("Invalid ObjectId")
                return value
            raise ValueError("Invalid ObjectId type")

        return core_schema.no_info_plain_validator_function(validate)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema, _handler):
        field_schema.update(type="string")
        return field_schema


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
