"""
Route decorator utilities for consistent error handling and metadata injection.
"""
import functools
import logging
from typing import Callable, Any
from datetime import datetime
from fastapi import HTTPException, status
from pydantic import ValidationError
from pymongo.errors import PyMongoError


logger = logging.getLogger(__name__)


def handle_route_errors(entity_type: str = "entity"):
    """
    Decorator that wraps route handlers with consistent error handling.

    Catches common exceptions and converts them to appropriate HTTP responses:
    - HTTPException: Re-raises as-is (already formatted)
    - ValidationError: Returns 422 with validation details
    - PyMongoError: Returns 500 with database error message
    - Exception: Returns 500 with generic error message

    Args:
        entity_type: Name of the entity being operated on (for error messages)

    Example:
        @router.post("/patients/")
        @handle_route_errors(entity_type="patient")
        async def create_patient(patient: PatientCreate, current_user: dict = Depends(get_current_user)):
            # Implementation - errors handled automatically
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTPExceptions as-is
                raise
            except ValidationError as e:
                logger.error(f"Validation error in {func.__name__}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Validation error: {str(e)}"
                )
            except PyMongoError as e:
                logger.error(f"Database error in {func.__name__}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error while processing {entity_type}"
                )
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An unexpected error occurred while processing {entity_type}"
                )
        return wrapper
    return decorator


def inject_audit_metadata(current_user_key: str = "current_user", is_create: bool = True):
    """
    Decorator that automatically injects audit metadata into document.

    Adds created_at/updated_at timestamps and created_by/updated_by user info.
    For create operations, adds all four fields.
    For update operations, only adds updated_at and updated_by.

    Args:
        current_user_key: Name of the kwargs parameter containing current user dict
        is_create: True for create operations, False for updates

    Example:
        @router.post("/patients/")
        @inject_audit_metadata(is_create=True)
        async def create_patient(
            patient: PatientCreate,
            current_user: dict = Depends(get_current_user)
        ):
            # patient.dict() will automatically have created_at, updated_at, created_by, updated_by
            pass

    Note:
        This decorator expects the function to have a parameter that can be modified
        (typically a Pydantic model or dict). It modifies the object in-place.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            current_user = kwargs.get(current_user_key)
            if not current_user:
                logger.warning(f"No {current_user_key} found in kwargs for {func.__name__}")
                return await func(*args, **kwargs)

            now = datetime.utcnow()
            username = current_user.get("username", "unknown")

            # Find the first dict or Pydantic model in args/kwargs that we can modify
            # This is a simple heuristic - you may need to adjust based on your needs
            for arg in args:
                if isinstance(arg, dict):
                    if is_create:
                        arg["created_at"] = now
                        arg["created_by"] = username
                    arg["updated_at"] = now
                    arg["updated_by"] = username
                    break
                elif hasattr(arg, "__dict__"):
                    # Pydantic model
                    if is_create:
                        setattr(arg, "created_at", now)
                        setattr(arg, "created_by", username)
                    setattr(arg, "updated_at", now)
                    setattr(arg, "updated_by", username)
                    break

            return await func(*args, **kwargs)
        return wrapper
    return decorator
