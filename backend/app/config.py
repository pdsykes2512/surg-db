"""
FastAPI application configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # MongoDB settings
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "surg_outcomes"
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_title: str = "Surgical Outcomes Database API"
    api_version: str = "1.0.0"
    
    # Security settings
    secret_key: str = "your-secret-key-change-in-production-min-32-characters-long"
    
    # CORS settings
    cors_origins: list = ["http://localhost:3000", "http://localhost:3001", "http://localhost:5173"]
    
    class Config:
        env_file = "../.env"  # .env is in parent directory
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env


settings = Settings()
