"""
FastAPI application configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # MongoDB settings
    mongodb_uri: str = "mongodb://surg-db.vps:27017"
    mongodb_db_name: str = "impact"  # Clinical audit data
    mongodb_system_db_name: str = "impact_system"  # System data (users, clinicians)
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_title: str = "IMPACT API"
    api_version: str = "1.0.0"
    
    # Security settings
    secret_key: str = "your-secret-key-change-in-production-min-32-characters-long"
    
    # CORS settings
    cors_origins: list = [
        "http://localhost:3000",
        "http://surg-db.vps:3000"
    ]
    
    # CORS regex for both network ranges (192.168.10.0/24 and 192.168.11.0/24)
    cors_origin_regex: str = r"http://192\.168\.(10|11)\.\d{1,3}:\d+"
    
    class Config:
        env_file = "../.env"  # .env is in parent directory
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env


settings = Settings()
