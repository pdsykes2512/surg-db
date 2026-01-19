"""
Tests for Authentication

Critical security functionality - JWT tokens, login, registration.
"""
import pytest
from httpx import AsyncClient


class TestAuthentication:
    """Test authentication endpoints"""

    @pytest.mark.asyncio
    async def test_register_user(self, client: AsyncClient, auth_headers: dict, clean_db):
        """Test user registration (requires admin auth)"""
        user_data = {
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "full_name": "New User",
            "role": "data_entry"
        }

        response = await client.post("/api/auth/register", json=user_data, headers=auth_headers)

        assert response.status_code in [200, 201]
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert "password" not in data  # Password should not be in response

    @pytest.mark.asyncio
    async def test_register_duplicate_email_fails(self, client: AsyncClient, auth_headers: dict, clean_db):
        """Test that registering duplicate email fails"""
        user_data = {
            "email": "duplicate@example.com",
            "password": "SecurePass123!",
            "full_name": "User One",
            "role": "data_entry"
        }

        # Register first user
        response1 = await client.post("/api/auth/register", json=user_data, headers=auth_headers)
        assert response1.status_code in [200, 201]

        # Try to register duplicate
        response2 = await client.post("/api/auth/register", json=user_data, headers=auth_headers)
        assert response2.status_code in [400, 409]

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, admin_user: dict, clean_db):
        """Test successful login"""
        # Login with admin user created in fixture
        login_response = await client.post(
            "/api/auth/login",
            data={
                "username": admin_user["email"],  # OAuth2 uses 'username'
                "password": admin_user["password"]
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert login_response.status_code == 200
        data = login_response.json()

        # Should return access token
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    @pytest.mark.asyncio
    async def test_login_wrong_password_fails(self, client: AsyncClient, admin_user: dict, clean_db):
        """Test that wrong password fails"""
        # Try login with wrong password
        response = await client.post(
            "/api/auth/login",
            data={
                "username": admin_user["email"],
                "password": "WrongPassword123!"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 401  # Unauthorized

    @pytest.mark.asyncio
    async def test_login_nonexistent_user_fails(self, client: AsyncClient, clean_db):
        """Test that login with non-existent user fails"""
        response = await client.post(
            "/api/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "SomePassword123!"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 401  # Unauthorized

    @pytest.mark.asyncio
    async def test_protected_endpoint_requires_auth(self, client: AsyncClient, clean_db):
        """Test that protected endpoints require authentication"""
        # Try to access patients without auth
        response = await client.get("/api/patients/")

        assert response.status_code == 401  # Unauthorized

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_valid_token(
        self,
        client: AsyncClient,
        auth_headers: dict,
        clean_db
    ):
        """Test that protected endpoints work with valid token"""
        # Try to access patients with auth
        response = await client.get("/api/patients/", headers=auth_headers)

        assert response.status_code == 200  # Should succeed

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_invalid_token(self, client: AsyncClient, clean_db):
        """Test that invalid token is rejected"""
        invalid_headers = {"Authorization": "Bearer invalid_token_123"}

        response = await client.get("/api/patients/", headers=invalid_headers)

        assert response.status_code == 401  # Unauthorized
