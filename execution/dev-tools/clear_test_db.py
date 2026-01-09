#!/usr/bin/env python3
"""
Clear all data from the impact_test database
"""
import asyncio
import sys
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
secrets_path = Path("/etc/impact/secrets.env")

load_dotenv(env_path)
load_dotenv(secrets_path)

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "impact_test")

async def clear_test_database():
    """Clear all collections in the test database"""
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]

    print(f"Clearing database: {MONGODB_DB_NAME}")

    collections = ["patients", "episodes", "tumours", "investigations", "treatments"]

    for collection_name in collections:
        collection = db[collection_name]
        result = await collection.delete_many({})
        print(f"  Deleted {result.deleted_count} documents from {collection_name}")

    client.close()
    print("✅ Test database cleared")

if __name__ == "__main__":
    asyncio.run(clear_test_database())
