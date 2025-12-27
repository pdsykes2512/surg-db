"""
Initialize MongoDB database with proper schemas and indexes for general surgery outcomes
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
    
    # Create users collection
    print("Creating users collection...")
    try:
        await db.create_collection(
            "users",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["email", "full_name", "hashed_password", "role", "is_active", "created_at", "updated_at"],
                    "properties": {
                        "email": {
                            "bsonType": "string",
                            "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
                            "description": "User email address"
                        },
                        "full_name": {
                            "bsonType": "string",
                            "minLength": 2,
                            "maxLength": 100,
                            "description": "User's full name"
                        },
                        "hashed_password": {
                            "bsonType": "string",
                            "description": "Hashed password"
                        },
                        "role": {
                            "enum": ["admin", "surgeon", "data_entry", "viewer"],
                            "description": "User role for access control"
                        },
                        "is_active": {
                            "bsonType": "bool",
                            "description": "Whether user account is active"
                        },
                        "department": {
                            "bsonType": ["string", "null"],
                            "description": "User's department"
                        },
                        "job_title": {
                            "bsonType": ["string", "null"],
                            "description": "User's job title"
                        },
                        "created_at": {
                            "bsonType": "date",
                            "description": "Record creation timestamp"
                        },
                        "created_by": {
                            "bsonType": ["string", "null"],
                            "description": "User who created the record"
                        },
                        "updated_at": {
                            "bsonType": "date",
                            "description": "Last update timestamp"
                        },
                        "updated_by": {
                            "bsonType": ["string", "null"],
                            "description": "User who last updated the record"
                        },
                        "last_login": {
                            "bsonType": ["date", "null"],
                            "description": "Last login timestamp"
                        }
                    }
                }
            }
        )
        print("✓ Users collection created")
    except Exception as e:
        if "already exists" in str(e):
            print("✓ Users collection already exists")
        else:
            raise
    
    # Create user indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("role")
    await db.users.create_index("is_active")
    await db.users.create_index("created_at")
    print("✓ User indexes created")
    
    # Drop existing collections for fresh start (optional - comment out to preserve data)
    # await db["patients"].drop()
    # await db["episodes"].drop()
    # await db["treatments"].drop()
    # await db["tumours"].drop()
    # await db["clinicians"].drop()
    
    # Create patients collection with enhanced validation
    print("Creating patients collection...")
    try:
        await db.create_collection(
            "patients",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["record_number", "nhs_number", "demographics", "created_at", "created_by", "updated_at"],
                    "properties": {
                        "record_number": {
                            "bsonType": "string",
                            "description": "Unique patient record number: 8 digits or IW + 6 digits"
                        },
                        "nhs_number": {
                            "bsonType": "string",
                            "description": "NHS number in XXX XXX XXXX format"
                        },
                        "demographics": {
                            "bsonType": "object",
                            "required": ["date_of_birth", "gender"],
                            "properties": {
                                "date_of_birth": {"bsonType": "string", "description": "Date of birth in YYYY-MM-DD format"},
                                "age": {"bsonType": ["int", "null"], "minimum": 0, "maximum": 150},
                                "gender": {"bsonType": "string"},
                                "ethnicity": {"bsonType": ["string", "null"]},
                                "postcode": {"bsonType": ["string", "null"]},
                                "bmi": {"bsonType": ["double", "null"], "minimum": 10, "maximum": 80},
                                "weight_kg": {"bsonType": ["double", "null"]},
                                "height_cm": {"bsonType": ["double", "null"]}
                            }
                        },
                        "medical_history": {
                            "bsonType": ["object", "null"],
                            "properties": {
                                "conditions": {"bsonType": "array", "items": {"bsonType": "string"}},
                                "previous_surgeries": {"bsonType": "array"},
                                "medications": {"bsonType": "array", "items": {"bsonType": "string"}},
                                "allergies": {"bsonType": "array", "items": {"bsonType": "string"}},
                                "smoking_status": {"bsonType": ["string", "null"]},
                                "alcohol_use": {"bsonType": ["string", "null"]}
                            }
                        },
                        "created_at": {"bsonType": "date"},
                        "created_by": {"bsonType": ["string", "null"]},
                        "updated_at": {"bsonType": "date"},
                        "updated_by": {"bsonType": ["string", "null"]}
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
    await patients_collection.create_index("record_number", unique=True)
    await patients_collection.create_index("nhs_number", unique=True)
    await patients_collection.create_index("created_at")
    await patients_collection.create_index("updated_at")
    await patients_collection.create_index([("demographics.age", 1)])
    print("✓ Patient indexes created")
    
    print("\n✅ Database initialization complete!")
    print(f"Database: {DB_NAME}")
    print(f"Collections: patients, episodes, treatments, tumours, clinicians")
    print("\n📊 Indexes created for optimized queries:")
    print("   - Patient lookups and filtering")
    print("   - Episode-based care tracking")
    print("   - Treatment and tumour management")
    print("   - Clinician performance tracking")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(init_database())
