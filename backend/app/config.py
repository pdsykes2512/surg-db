"""
FastAPI application configuration
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # Server hostname (configurable for different deployments)
    server_hostname: str = "impact.vps"  # Default hostname, override via SERVER_HOSTNAME env var
    frontend_port: int = 3000  # Frontend port for CORS

    # MongoDB settings
    mongodb_uri: str = "mongodb://localhost:27017"  # Override via MONGODB_URI env var
    mongodb_db_name: str = "impact"  # Clinical audit data
    mongodb_system_db_name: str = "impact_system"  # System data (users, clinicians)

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_title: str = "IMPACT API"
    api_version: str = "1.12.0"

    # Security settings
    secret_key: str = "your-secret-key-change-in-production-min-32-characters-long"
    access_token_expire_minutes: int = 30  # 30 minutes of inactivity
    refresh_token_expire_days: int = 7  # 7 days for refresh token
    session_warning_minutes: int = 5  # Warning 5 minutes before timeout

    # CORS settings - built dynamically from server_hostname
    @property
    def cors_origins(self) -> list:
        """Dynamic CORS origins based on server hostname"""
        return [
            "http://localhost:3000",
            f"http://{self.server_hostname}:{self.frontend_port}"
        ]

    # CORS regex for both network ranges (192.168.10.0/24 and 192.168.11.0/24)
    cors_origin_regex: str = r"http://192\.168\.(10|11)\.\d{1,3}:\d+"

    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key for security"""
        if v == "your-secret-key-change-in-production-min-32-characters-long":
            raise ValueError(
                "🚨 SECURITY ERROR: Default secret key detected!\n"
                "Set SECRET_KEY environment variable to a secure random key.\n"
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        if len(v) < 32:
            raise ValueError(
                f"🚨 SECURITY ERROR: Secret key too short (length: {len(v)}).\n"
                "Secret key must be at least 32 characters for security.\n"
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        return v

    @field_validator('mongodb_uri')
    @classmethod
    def validate_mongodb_uri(cls, v: str) -> str:
        """Validate MongoDB URI format"""
        if not v.startswith('mongodb://') and not v.startswith('mongodb+srv://'):
            raise ValueError(
                "Invalid MongoDB URI format. Must start with 'mongodb://' or 'mongodb+srv://'\n"
                f"Current value: {v[:50]}..."
            )
        return v

    class Config:
        env_file = "/etc/impact/secrets.env"  # Secrets stored in /etc/impact
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env


settings = Settings()
