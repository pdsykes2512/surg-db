"""
Pytest configuration and fixtures for backend tests
"""
import pytest
import asyncio
from typing import AsyncGenerator
from datetime import timedelta, datetime
from motor.motor_asyncio import AsyncIOMotorClient
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import settings
from app.database import Database
from app.auth import get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.models.user import UserRole
from app.middleware import limiter


# Override settings for testing
settings.mongodb_db_name = f"{settings.mongodb_db_name}_test"
settings.mongodb_system_db_name = f"{settings.mongodb_system_db_name}_test"

# Disable rate limiting for tests
limiter.enabled = False


@pytest.fixture(scope="session")
def event_loop():
    """
    Create event loop for async tests.
    Scope: session - one loop for all tests.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db():
    """
    Create test database connection.
    Uses impact_test database to avoid affecting production data.
    Initializes Database singleton for app to use.
    """
    # Initialize the Database singleton (will use test settings)
    await Database.connect_db()

    db = Database.get_database()

    yield db

    # Cleanup: drop test databases after all tests
    await Database.client.drop_database(settings.mongodb_db_name)
    await Database.client.drop_database(settings.mongodb_system_db_name)
    await Database.close_db()


@pytest.fixture
async def clean_db(test_db):
    """
    Clean test database before each test.
    Drops all collections to ensure test isolation.
    """
    db = Database.get_database()
    system_db = Database.get_system_database()

    # Drop all collections in both databases before test
    for collection_name in await db.list_collection_names():
        await db.drop_collection(collection_name)

    for collection_name in await system_db.list_collection_names():
        await system_db.drop_collection(collection_name)

    yield db


@pytest.fixture
async def client() -> AsyncGenerator:
    """
    Create test HTTP client for API testing.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def admin_user(clean_db) -> dict:
    """
    Create an admin user directly in the database (bypassing auth-protected registration).
    Returns user data dict.
    """
    system_db = Database.get_system_database()

    admin_data = {
        "email": "admin@test.com",
        "full_name": "Test Admin",
        "hashed_password": get_password_hash("adminpass123"),
        "role": UserRole.ADMIN.value,
        "is_active": True,
        "department": "Test Department",
        "job_title": "Test Admin",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "last_login": None
    }

    result = await system_db.users.insert_one(admin_data)
    admin_data["_id"] = result.inserted_id

    return {
        "email": "admin@test.com",
        "password": "adminpass123",  # Plain password for login
        "full_name": "Test Admin",
        "role": UserRole.ADMIN.value
    }


@pytest.fixture
async def auth_headers(client: AsyncClient, admin_user: dict) -> dict:
    """
    Get authentication headers with valid JWT token.
    Uses admin user created directly in database.
    """
    # Login with admin user
    login_response = await client.post(
        "/api/auth/login",
        data={
            "username": admin_user["email"],  # OAuth2PasswordRequestForm uses 'username'
            "password": admin_user["password"]
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    assert login_response.status_code == 200, f"Login failed: {login_response.text}"

    token = login_response.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_patient_data() -> dict:
    """
    Sample patient data for testing.
    """
    return {
        "patient_id": "TEST01",
        "mrn": "12345678",
        "nhs_number": "9876543210",
        "demographics": {
            "date_of_birth": "1975-03-15",
            "age": 48,
            "gender": "male",
            "ethnicity": "White British",
            "postcode": "SW1A 1AA",
            "bmi": 25.5,
            "weight_kg": 75.0,
            "height_cm": 175.0
        },
        "medical_history": {
            "conditions": ["Hypertension"],
            "previous_surgeries": [],
            "medications": ["Lisinopril"],
            "allergies": [],
            "smoking_status": "never",
            "alcohol_use": "social"
        }
    }


@pytest.fixture
def sample_episode_data() -> dict:
    """
    Sample episode data for testing.
    """
    return {
        "episode_id": "E-TEST-001",
        "patient_id": "TEST01",
        "condition_type": "cancer",
        "cancer_type": "bowel",
        "lead_clinician": "Test Surgeon",
        "diagnosis_date": "2023-01-15",
        "episode_status": "active"
    }
