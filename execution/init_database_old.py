"""
Initialize MongoDB database with proper schemas and indexes
Execution script for database setup
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB_NAME", "surg_outcomes")


async def init_database():
    """Initialize database with collections, validation, and indexes"""
    print(f"Connecting to MongoDB at {MONGODB_URI}...")
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    
    print(f"Initializing database: {DB_NAME}")
    
    # Create patients collection with validation
    print("Creating patients collection...")
    try:
        await db.create_collection(
            "patients",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["patient_id", "demographics", "created_at", "updated_at"],
                    "properties": {
                        "patient_id": {
                            "bsonType": "string",
                            "description": "Unique patient identifier"
                        },
                        "demographics": {
                            "bsonType": "object",
                            "required": ["age", "gender"],
                            "properties": {
                                "age": {"bsonType": "int", "minimum": 0, "maximum": 150},
                                "gender": {"bsonType": "string"},
                                "ethnicity": {"bsonType": "string"}
                            }
                        },
                        "contact": {
                            "bsonType": "object",
                            "properties": {
                                "phone": {"bsonType": "string"},
                                "email": {"bsonType": "string"}
                            }
                        },
                        "medical_history": {
                            "bsonType": "object",
                            "properties": {
                                "conditions": {"bsonType": "array", "items": {"bsonType": "string"}},
                                "medications": {"bsonType": "array", "items": {"bsonType": "string"}},
                                "allergies": {"bsonType": "array", "items": {"bsonType": "string"}}
                            }
                        },
                        "created_at": {"bsonType": "date"},
                        "updated_at": {"bsonType": "date"}
                    }
                }
            }
        )
        print("✓ Patients collection created")
    except Exception as e:
        if "already exists" in str(e):
            print("✓ Patients collection already exists")
        else:
            print(f"✗ Error creating patients collection: {e}")
    
    # Create indexes for patients collection
    print("Creating indexes for patients...")
    patients_collection = db["patients"]
    await patients_collection.create_index("patient_id", unique=True)
    await patients_collection.create_index("created_at")
    print("✓ Patient indexes created")
    
    # Create surgeries collection with validation
    print("Creating surgeries collection...")
    try:
        await db.create_collection(
            "surgeries",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["surgery_id", "patient_id", "procedure", "team", "outcomes", "created_at", "updated_at"],
                    "properties": {
                        "surgery_id": {"bsonType": "string"},
                        "patient_id": {"bsonType": "string"},
                        "procedure": {
                            "bsonType": "object",
                            "required": ["type", "code", "description", "date", "duration_minutes"],
                            "properties": {
                                "type": {"bsonType": "string"},
                                "code": {"bsonType": "string"},
                                "description": {"bsonType": "string"},
                                "date": {"bsonType": "date"},
                                "duration_minutes": {"bsonType": "int", "minimum": 0}
                            }
                        },
                        "team": {
                            "bsonType": "object",
                            "required": ["surgeon"],
                            "properties": {
                                "surgeon": {"bsonType": "string"},
                                "anesthesiologist": {"bsonType": "string"},
                                "nurses": {"bsonType": "array", "items": {"bsonType": "string"}}
                            }
                        },
                        "outcomes": {
                            "bsonType": "object",
                            "properties": {
                                "success": {"bsonType": "bool"},
                                "complications": {"bsonType": "array"},
                                "length_of_stay_days": {"bsonType": "int", "minimum": 0},
                                "readmission_30day": {"bsonType": "bool"},
                                "mortality": {"bsonType": "bool"},
                                "patient_satisfaction": {"bsonType": "int", "minimum": 1, "maximum": 10}
                            }
                        },
                        "created_at": {"bsonType": "date"},
                        "updated_at": {"bsonType": "date"}
                    }
                }
            }
        )
        print("✓ Surgeries collection created")
    except Exception as e:
        if "already exists" in str(e):
            print("✓ Surgeries collection already exists")
        else:
            print(f"✗ Error creating surgeries collection: {e}")
    
    # Create indexes for surgeries collection
    print("Creating indexes for surgeries...")
    surgeries_collection = db["surgeries"]
    await surgeries_collection.create_index("surgery_id", unique=True)
    await surgeries_collection.create_index("patient_id")
    await surgeries_collection.create_index("procedure.date")
    await surgeries_collection.create_index("procedure.type")
    await surgeries_collection.create_index("team.surgeon")
    await surgeries_collection.create_index("created_at")
    print("✓ Surgery indexes created")
    
    print("\n✅ Database initialization complete!")
    print(f"Database: {DB_NAME}")
    print(f"Collections: patients, surgeries")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(init_database())
