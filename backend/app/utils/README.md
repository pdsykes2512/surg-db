# Utility Modules

This directory contains reusable utility functions for the IMPACT backend application.

## Modules

### Security & Encryption
- **`encryption.py`** - Field-level AES-256 encryption for sensitive patient data
  - Encrypts NHS numbers, MRN, DOB, postcodes, names
  - Generates searchable hashes for encrypted fields
  - UK GDPR Article 32 and NHS Caldicott Principles compliance
  - Functions: `encrypt_field()`, `decrypt_field()`, `encrypt_document()`, `decrypt_document()`

### Data Processing
- **`serializers.py`** - MongoDB ObjectId and datetime serialization
  - Convert ObjectId to string for JSON responses
  - Handle nested documents and arrays
  - Functions: `serialize_object_id()`, `serialize_object_ids()`, `serialize_nested_object_ids()`

- **`date_formatters.py`** - Date/datetime formatting utilities
  - COSD XML export date formatting
  - ISO datetime conversion
  - Functions: `format_date_for_cosd()`, `serialize_datetime_fields()`

### Search & Query
- **`search_helpers.py`** - NoSQL injection prevention
  - Sanitize user search inputs
  - Escape special regex characters
  - Functions: `sanitize_search_input()`

- **`clinician_helpers.py`** - Clinician data resolution
  - Build clinician lookup maps
  - Resolve clinician codes to names
  - Functions: `build_clinician_maps()`

### Clinical Logic
- **`mortality.py`** - Mortality flag calculation
  - Calculate 30-day and 90-day mortality from treatment dates
  - Hospital vs community death tracking
  - Functions: `calculate_mortality_flags()`

- **`update_mortality_flags.py`** - Batch mortality flag updates
  - Recalculate mortality for all patients
  - Run after deceased date changes
  - Functions: `update_all_mortality_flags()`

### Audit & Compliance
- **`audit.py`** - Audit trail logging
  - Log all data mutations for compliance
  - NHS Records Management Code compliance
  - Functions: `log_audit_event()`

## Usage Examples

### Encryption
```python
from app.utils.encryption import encrypt_document, decrypt_document

# Encrypt before storing
patient_data = {"nhs_number": "1234567890", "mrn": "12345678"}
encrypted = encrypt_document(patient_data)
await collection.insert_one(encrypted)

# Decrypt after retrieving
patient = await collection.find_one({"patient_id": id})
decrypted = decrypt_document(patient)
```

### Search Sanitization
```python
from app.utils.search_helpers import sanitize_search_input

# Prevent NoSQL injection
user_input = "$ne' OR '1'='1"
safe_input = sanitize_search_input(user_input)  # Escapes special chars
query = {"name": {"$regex": safe_input, "$options": "i"}}
```

### Serialization
```python
from app.utils.serializers import serialize_object_id

# Convert ObjectId to string for JSON response
patient = await collection.find_one({"patient_id": id})
patient = serialize_object_id(patient)  # _id now string
return Patient(**patient)
```

### Date Formatting
```python
from app.utils.date_formatters import format_date_for_cosd

# Format date for COSD XML export (YYYY-MM-DD)
treatment_date = datetime(2024, 3, 15)
cosd_date = format_date_for_cosd(treatment_date)  # "2024-03-15"
```

### Clinician Resolution
```python
from app.utils.clinician_helpers import build_clinician_maps

# Build lookup maps for efficient resolution
clinician_list = await get_clinicians()
name_map, code_map = await build_clinician_maps(clinician_list)

# Resolve code to name
surgeon_name = name_map.get(surgeon_code, "Unknown")
```

### Mortality Calculation
```python
from app.utils.mortality import calculate_mortality_flags

# Calculate mortality flags from treatment date
treatment_date = datetime(2024, 1, 1)
deceased_date = datetime(2024, 1, 25)
deceased_location = "hospital"

flags = calculate_mortality_flags(treatment_date, deceased_date, deceased_location)
# Returns: {"mortality_30d": True, "mortality_30d_hospital": True, ...}
```

## Adding New Utilities

When adding new utility functions:

1. **Create focused module** - One module per domain (e.g., date_utils.py)
2. **Add comprehensive docstrings** - Document all parameters and return values
3. **Include examples** - Show common usage patterns
4. **Handle errors** - Validate inputs and raise meaningful exceptions
5. **Unit test** - Test edge cases and error conditions
6. **Update this README** - Document the new module

### Template
```python
"""
Module Description

Provides utilities for [specific purpose].

Usage:
    from app.utils.your_module import your_function
    
    result = your_function(input_data)

Functions:
    your_function() - Brief description
    another_function() - Brief description
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


def your_function(param: str) -> dict:
    """
    Brief description of function purpose.
    
    Detailed explanation of what the function does, including any important
    algorithms, side effects, or special behaviors.
    
    Args:
        param: Description of parameter
    
    Returns:
        dict: Description of return value
    
    Raises:
        ValueError: When parameter is invalid
        TypeError: When parameter has wrong type
    
    Example:
        >>> result = your_function("test")
        >>> print(result)
        {"key": "value"}
    """
    try:
        # Implementation
        return {"key": "value"}
    except Exception as e:
        logger.error(f"Error in your_function: {str(e)}", exc_info=True)
        raise
```

## Best Practices

1. **Pure functions** - Avoid side effects when possible
2. **Type hints** - Always use type annotations
3. **Error handling** - Validate inputs and handle exceptions
4. **Logging** - Log errors with exc_info=True for stack traces
5. **Documentation** - Comprehensive docstrings with examples
6. **DRY principle** - Extract common patterns into utilities
7. **Single responsibility** - Each function does one thing well
8. **Testing** - Unit test all utility functions

## Security Considerations

### Encryption Module
- Encryption keys stored in `/root/.field-encryption-key` (600 permissions)
- Keys never committed to version control
- Uses PBKDF2 key derivation with random salt
- AES-256 encryption in Fernet mode
- Searchable hashes use SHA-256 with field-specific salts

### Search Sanitization
- Always sanitize user inputs before MongoDB queries
- Escape regex special characters: `$^*+?{}\[]|()`
- Prevents NoSQL injection attacks
- Required for UK GDPR Article 32 compliance

### Audit Logging
- All data mutations logged with username and timestamp
- Audit logs stored separately from operational data
- 20-year retention per NHS Records Management Code
- Never log decrypted sensitive fields

## Performance Considerations

### Encryption
- Encryption adds ~1ms overhead per document
- Bulk operations should batch encrypt/decrypt
- Searchable hashes enable O(log n) indexed lookups
- Cache decrypted values when safe to do so

### Serialization
- Use `serialize_object_ids()` for lists (optimized)
- Avoid recursive serialization of large nested documents
- Convert datetimes to ISO strings for JSON compatibility

### Search
- Regex searches are O(n) - use sparingly
- Hash-based searches are O(log n) - prefer for encrypted fields
- Consider full-text indexes for large text fields

## Testing

All utility functions should have unit tests:

```python
import pytest
from app.utils.your_module import your_function

def test_your_function_valid_input():
    result = your_function("valid")
    assert result["key"] == "value"

def test_your_function_invalid_input():
    with pytest.raises(ValueError):
        your_function("")
```

## Import Conventions

```python
# Preferred: Import specific functions
from app.utils.encryption import encrypt_field, decrypt_field

# Avoid: Wildcard imports
from app.utils.encryption import *  # Don't do this
```
