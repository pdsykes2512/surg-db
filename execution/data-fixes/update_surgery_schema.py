"""
Update the surgeries collection schema to match the current Surgery model
"""
import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'surg_outcomes')


async def update_schema():
    """Drop and recreate surgeries collection without old validation"""
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    
    print("Updating surgeries collection schema...")
    
    try:
        # Drop the existing collection to remove old validation
        print("Dropping old surgeries collection...")
        await db.surgeries.drop()
        print("✓ Old collection dropped")
        
        # Create new collection without strict validation
        # (Pydantic handles validation in the API layer)
        print("Creating new surgeries collection...")
        await db.create_collection("surgeries")
        print("✓ New collection created")
        
        # Create indexes
        print("Creating indexes...")
        await db.surgeries.create_index("surgery_id", unique=True)
        await db.surgeries.create_index("patient_id")
        await db.surgeries.create_index([("perioperative_timeline.surgery_date", -1)])
        await db.surgeries.create_index([("classification.urgency", 1)])
        await db.surgeries.create_index([("classification.category", 1)])
        await db.surgeries.create_index([("team.primary_surgeon", 1)])
        print("✓ Indexes created")
        
        print("\n✓ Schema update complete!")
        
    except Exception as e:
        print(f"✗ Error updating schema: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(update_schema())
