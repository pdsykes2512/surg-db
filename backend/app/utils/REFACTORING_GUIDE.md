# Code Refactoring Guide

This guide shows how to use the new utility functions to eliminate duplicate code.

## 1. Error Handling Decorator

### Before:
```python
@router.post("/patients/")
async def create_patient(patient: PatientCreate, current_user: dict = Depends(get_current_user)):
    try:
        # ... implementation ...
        return result
    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except PyMongoError as e:
        logger.error(f"Database error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error")
```

### After:
```python
from app.utils.route_decorators import handle_route_errors

@router.post("/patients/")
@handle_route_errors(entity_type="patient")
async def create_patient(patient: PatientCreate, current_user: dict = Depends(get_current_user)):
    # ... implementation only ...
    return result
```

## 2. Encrypted Field Search

### Before:
```python
search_encrypted_fields = False
if search:
    clean_search = search.replace(" ", "").upper()
    is_mrn_pattern = (
        (clean_search.isdigit() and len(clean_search) >= 8) or
        (clean_search.startswith('IW') and len(clean_search) == 8 and clean_search[2:].isdigit()) or
        (clean_search.startswith('C') and len(clean_search) == 9 and clean_search[1:7].isdigit() and clean_search[7:9].isalnum())
    )
    if is_mrn_pattern:
        search_encrypted_fields = True
        clean_search_lower = search.replace(" ", "").lower()
        nhs_query = create_searchable_query('nhs_number', clean_search_lower)
        mrn_query = create_searchable_query('mrn', clean_search_lower)
        query = {"$or": [nhs_query, mrn_query]}
        matching_patients = await patients_collection.find(query, {"patient_id": 1}).to_list(length=None)
        patient_ids = [p["patient_id"] for p in matching_patients]
```

### After:
```python
from app.utils.search_helpers import build_encrypted_field_query

_, patient_ids = await build_encrypted_field_query(search, patients_collection, create_searchable_query)
search_encrypted_fields = bool(patient_ids)
```

## 3. ObjectId Serialization

### Before:
```python
patient["_id"] = str(patient["_id"])
```

### After:
```python
from app.utils.serializers import serialize_object_id

patient = serialize_object_id(patient)
```

### For Lists:
```python
from app.utils.serializers import serialize_object_ids

patients = serialize_object_ids(patients)
```

## 4. DateTime Serialization

### Before:
```python
if patient.get("demographics"):
    demo = patient["demographics"]
    if demo.get("date_of_birth") and hasattr(demo["date_of_birth"], "isoformat"):
        demo["date_of_birth"] = demo["date_of_birth"].isoformat()
    if demo.get("deceased_date") and hasattr(demo["deceased_date"], "isoformat"):
        demo["deceased_date"] = demo["deceased_date"].isoformat()
```

### After:
```python
from app.utils.serializers import serialize_datetime_fields

patient = serialize_datetime_fields(patient)
```

## 5. Clinician Name Resolution

### Before:
```python
# Strategy 1: Resolve by clinician ID
surgeon_name = None
if clinician_map and primary_surgeon_id:
    surgeon_name = clinician_map.get(primary_surgeon_id)

# Strategy 2: Match by surname (case-insensitive)
if not surgeon_name and surname_map and primary_surgeon_text:
    surgeon_name = surname_map.get(primary_surgeon_text.upper())

# Fallback: Use the text value as-is
if not surgeon_name:
    surgeon_name = primary_surgeon_text or primary_surgeon_id
```

### After:
```python
from app.utils.clinician_helpers import resolve_clinician_name

surgeon_name = resolve_clinician_name(
    clinician_id=primary_surgeon_id,
    clinician_text=primary_surgeon_text,
    clinician_map=clinician_map,
    surname_map=surname_map
)
```

## 6. Entity Existence Validation

### Before:
```python
existing = await collection.find_one({"episode_id": episode_id})
if not existing:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Episode {episode_id} not found"
    )
```

### After:
```python
from app.utils.validation_helpers import check_entity_exists

existing = await check_entity_exists(
    collection=collection,
    query_filter={"episode_id": episode_id},
    entity_name="Episode",
    entity_id=episode_id
)
```

## 7. Uniqueness Validation (for Creates)

### Before:
```python
existing = await collection.find_one({"mrn_hash": mrn_hash})
if existing:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="A patient with this MRN already exists"
    )
```

### After:
```python
from app.utils.validation_helpers import check_entity_not_exists

await check_entity_not_exists(
    collection=collection,
    query_filter={"mrn_hash": mrn_hash},
    entity_name="Patient",
    conflict_message="A patient with this MRN already exists"
)
```

## Summary of Savings

- **Error handling**: ~15 lines → 1 line decorator (per endpoint)
- **Encrypted field search**: ~15 lines → 2 lines
- **ObjectId serialization**: ~1 line → 1 line (but consistent and maintainable)
- **DateTime serialization**: ~8 lines → 1 line
- **Clinician resolution**: ~15 lines → 5 lines
- **Entity validation**: ~5 lines → 4 lines (but more readable and consistent)

**Total estimated savings**: ~400 lines of code across all endpoints
