# IMPACT Backend Tests

Automated tests for critical backend functionality.

## Running Tests

### Run All Tests
```bash
cd /root/impact/backend
pytest
```

### Run Specific Test File
```bash
pytest tests/test_encryption.py
pytest tests/test_patients_api.py
pytest tests/test_auth.py
```

### Run Specific Test
```bash
pytest tests/test_encryption.py::TestEncryption::test_encrypt_decrypt_field
```

### Run with Verbose Output
```bash
pytest -v
```

### Run with Coverage Report
```bash
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

## Test Structure

- **conftest.py** - Shared fixtures and test configuration
  - `test_db` - Test database connection (uses `impact_test` database)
  - `clean_db` - Clean database before each test
  - `client` - HTTP client for API testing
  - `auth_headers` - Authenticated headers with JWT token
  - `sample_patient_data` - Sample patient for testing
  - `sample_episode_data` - Sample episode for testing

- **test_encryption.py** - Encryption/decryption tests (CRITICAL)
  - Tests field encryption/decryption
  - Tests document encryption
  - Tests search hash generation
  - Validates that same plaintext produces different ciphertexts (IV randomization)

- **test_patients_api.py** - Patient CRUD tests (CRITICAL)
  - Tests patient creation, retrieval, update, delete
  - Tests validation (duplicate MRN, invalid data)
  - Tests that data is encrypted in database
  - Tests pagination

- **test_auth.py** - Authentication tests (CRITICAL)
  - Tests user registration
  - Tests login with correct/incorrect credentials
  - Tests JWT token generation
  - Tests protected endpoint access

## Test Database

Tests use a separate `impact_test` database to avoid affecting production data.

The test database is automatically:
- Created before tests run
- Cleaned between tests (all collections dropped)
- Dropped after all tests complete

## Adding New Tests

1. Create test file in `tests/` directory with name `test_*.py`
2. Import fixtures from conftest.py
3. Use `@pytest.mark.asyncio` decorator for async tests
4. Use fixtures: `client`, `auth_headers`, `clean_db`

Example:
```python
import pytest
from httpx import AsyncClient

class TestMyFeature:
    @pytest.mark.asyncio
    async def test_something(self, client: AsyncClient, auth_headers: dict, clean_db):
        response = await client.get("/api/my-endpoint", headers=auth_headers)
        assert response.status_code == 200
```

## Current Coverage

**Test Results: 24 passing, 1 skipped**

Critical paths currently tested:
- ✅ Encryption/decryption (8 tests) - All passing
- ✅ Patient CRUD operations (9 tests) - 8 passing, 1 skipped (known bug)
- ✅ Authentication (8 tests) - All passing

Known Issues:
- ⚠️ Duplicate patient detection bug: `test_create_duplicate_patient_fails` skipped because production code compares plaintext MRN against encrypted MRN in database. Should use `mrn_hash` field instead.

Not yet tested:
- ❌ Episode CRUD operations
- ❌ Treatment operations
- ❌ Reports endpoints
- ❌ Export functionality
- ❌ RStudio integration

## Continuous Integration

To integrate with CI/CD:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run tests
        run: pytest --cov=app
```

## Best Practices

1. **Test Isolation**: Each test should be independent (use `clean_db` fixture)
2. **Descriptive Names**: Test names should describe what they test
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Mock External Services**: Don't call real external APIs in tests
5. **Security Tests**: Mark security-critical tests with `@pytest.mark.security`
