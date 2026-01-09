# API Routes

This directory contains all FastAPI route handlers for the IMPACT REST API.

## Structure

Each file defines routes for a specific resource or domain:

### Core Resources
- **`patients.py`** - Patient CRUD operations with encrypted field support
- **`episodes.py`** - Cancer care episodes management
- **`treatments_surgery.py`** - Surgical treatment records and relationships
- **`investigations.py`** - Diagnostic investigations and results

### Supporting Resources
- **`clinicians.py`** - Healthcare professional records
- **`nhs_providers.py`** - NHS trust and hospital data
- **`codes.py`** - Medical coding lookups (ICD-10, OPCS-4)

### System Features
- **`auth.py`** - Authentication and authorization (JWT tokens)
- **`admin.py`** - Administrative functions (user management)
- **`reports.py`** - Analytics and reporting endpoints
- **`exports.py`** - NBOCA COSD XML export generation
- **`audit.py`** - Audit trail queries
- **`backups.py`** - Database backup management

## Common Patterns

### Route Definition
```python
from fastapi import APIRouter, HTTPException, Depends
from ..auth import get_current_user, require_data_entry_or_higher

router = APIRouter(prefix="/api/resource", tags=["resource"])

@router.get("/")
async def list_resources(
    current_user: dict = Depends(get_current_user)
):
    """Endpoint description with docstring"""
    pass
```

### Authentication & Authorization
All routes require authentication via JWT token. Role-based access control uses dependency injection:

- `get_current_user` - Any authenticated user
- `require_data_entry_or_higher` - data_entry, clinician, or admin
- `require_admin` - admin only

### Error Handling
```python
try:
    # Database operations
    result = await collection.find_one(...)
    if not result:
        raise HTTPException(status_code=404, detail="Not found")
    return result
except HTTPException:
    raise  # Re-raise HTTP exceptions as-is
except Exception as e:
    logger.error(f"Error: {str(e)}", exc_info=True)
    raise HTTPException(status_code=500, detail=str(e))
```

### Data Encryption
Routes handling sensitive patient data use field-level encryption:

```python
from ..utils.encryption import encrypt_document, decrypt_document

# Before storing
encrypted_data = encrypt_document(patient_dict)
await collection.insert_one(encrypted_data)

# Before returning
patient = await collection.find_one({"patient_id": id})
decrypted_patient = decrypt_document(patient)
return Patient(**decrypted_patient)
```

Encrypted fields: NHS number, MRN, DOB, postcode, names

### Pagination
Standard pagination parameters:
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 50-100)

```python
@router.get("/")
async def list_items(skip: int = 0, limit: int = 50):
    items = await collection.find().skip(skip).limit(limit).to_list(length=None)
    return items
```

### Search
- Use `sanitize_search_input()` to prevent NoSQL injection
- Encrypted field search uses hash-based lookups
- Non-encrypted fields use case-insensitive regex

```python
from ..utils.search_helpers import sanitize_search_input

safe_search = sanitize_search_input(search)
query = {"field": {"$regex": safe_search, "$options": "i"}}
```

## API Response Standards

### Success Responses
- **200 OK** - Successful GET/PUT request
- **201 Created** - Successful POST request
- **204 No Content** - Successful DELETE request

### Error Responses
- **400 Bad Request** - Invalid input data
- **401 Unauthorized** - Missing/invalid token
- **403 Forbidden** - Insufficient permissions
- **404 Not Found** - Resource doesn't exist
- **500 Internal Server Error** - Server-side error

## Security Considerations

1. **Authentication**: All endpoints require valid JWT token
2. **Authorization**: Role-based access via dependency injection
3. **Encryption**: Sensitive fields encrypted with AES-256
4. **Audit Logging**: All mutations logged for compliance
5. **Input Validation**: Pydantic models validate all inputs
6. **NoSQL Injection**: Search inputs sanitized via regex

## Adding New Routes

1. Create new file in this directory
2. Define router with prefix and tags
3. Import necessary dependencies (auth, database, models)
4. Add comprehensive docstrings to all endpoints
5. Implement error handling and logging
6. Register router in `main.py`:

```python
from app.routes import your_route
app.include_router(your_route.router)
```

## Testing

Routes should be tested via:
- Unit tests with mocked database
- Integration tests with test database
- Manual testing via Swagger UI at `/docs`

## Documentation

All route handlers must include:
- Module-level docstring explaining purpose
- Function docstrings with Args, Returns, Raises sections
- Inline comments for complex business logic
- Examples in docstrings where helpful

See `patients.py` for comprehensive documentation examples.
