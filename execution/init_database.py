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
    
    # Drop existing collections for fresh start (optional - comment out to preserve data)
    # await db["patients"].drop()
    # await db["surgeries"].drop()
    
    # Create patients collection with enhanced validation
    print("Creating patients collection...")
    try:
        await db.create_collection(
            "patients",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["patient_id", "demographics", "created_at", "created_by", "updated_at"],
                    "properties": {
                        "patient_id": {
                            "bsonType": "string",
                            "description": "Unique patient identifier (MRN)"
                        },
                        "demographics": {
                            "bsonType": "object",
                            "required": ["age", "gender"],
                            "properties": {
                                "age": {"bsonType": "int", "minimum": 0, "maximum": 150},
                                "gender": {"bsonType": "string"},
                                "ethnicity": {"bsonType": ["string", "null"]},
                                "bmi": {"bsonType": ["double", "null"], "minimum": 10, "maximum": 80},
                                "weight_kg": {"bsonType": ["double", "null"]},
                                "height_cm": {"bsonType": ["double", "null"]}
                            }
                        },
                        "contact": {
                            "bsonType": ["object", "null"],
                            "properties": {
                                "phone": {"bsonType": ["string", "null"]},
                                "email": {"bsonType": ["string", "null"]}
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
    await patients_collection.create_index("patient_id", unique=True)
    await patients_collection.create_index("created_at")
    await patients_collection.create_index("updated_at")
    await patients_collection.create_index([("demographics.age", 1)])
    print("✓ Patient indexes created")
    
    # Create surgeries collection with comprehensive validation
    print("Creating surgeries collection...")
    try:
        await db.create_collection(
            "surgeries",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": [
                        "surgery_id", "patient_id", "classification", "procedure",
                        "perioperative_timeline", "team", "audit_trail"
                    ],
                    "properties": {
                        "surgery_id": {
                            "bsonType": "string",
                            "description": "Unique surgery identifier"
                        },
                        "patient_id": {
                            "bsonType": "string",
                            "description": "Reference to patient MRN"
                        },
                        "classification": {
                            "bsonType": "object",
                            "required": ["urgency", "category", "primary_diagnosis"],
                            "properties": {
                                "urgency": {
                                    "bsonType": "string",
                                    "enum": ["elective", "emergency", "urgent"]
                                },
                                "category": {
                                    "bsonType": "string",
                                    "enum": ["major_resection", "proctology", "hernia", "cholecystectomy", "other"]
                                },
                                "complexity": {
                                    "bsonType": ["string", "null"],
                                    "enum": ["routine", "intermediate", "complex", None]
                                },
                                "primary_diagnosis": {"bsonType": "string"},
                                "indication": {
                                    "bsonType": ["string", "null"],
                                    "enum": ["cancer", "ibd", "diverticular", "benign", "other", None]
                                }
                            }
                        },
                        "procedure": {
                            "bsonType": "object",
                            "required": ["primary_procedure", "approach"],
                            "properties": {
                                "primary_procedure": {"bsonType": "string"},
                                "additional_procedures": {"bsonType": "array"},
                                "cpt_codes": {"bsonType": "array"},
                                "icd10_codes": {"bsonType": "array"},
                                "approach": {
                                    "bsonType": "string",
                                    "enum": ["open", "laparoscopic", "robotic", "converted"]
                                },
                                "description": {"bsonType": ["string", "null"]}
                            }
                        },
                        "perioperative_timeline": {
                            "bsonType": "object",
                            "required": ["admission_date", "surgery_date"],
                            "properties": {
                                "admission_date": {"bsonType": "date"},
                                "surgery_date": {"bsonType": "date"},
                                "surgery_start_time": {"bsonType": ["date", "null"]},
                                "surgery_end_time": {"bsonType": ["date", "null"]},
                                "discharge_date": {"bsonType": ["date", "null"]},
                                "length_of_stay_days": {"bsonType": ["int", "null"], "minimum": 0}
                            }
                        },
                        "team": {
                            "bsonType": "object",
                            "required": ["primary_surgeon"],
                            "properties": {
                                "primary_surgeon": {"bsonType": "string"},
                                "assistant_surgeons": {"bsonType": "array"},
                                "anesthesiologist": {"bsonType": ["string", "null"]},
                                "scrub_nurse": {"bsonType": ["string", "null"]},
                                "circulating_nurse": {"bsonType": ["string", "null"]}
                            }
                        },
                        "audit_trail": {
                            "bsonType": "object",
                            "required": ["created_at", "created_by", "updated_at"],
                            "properties": {
                                "created_at": {"bsonType": "date"},
                                "created_by": {"bsonType": "string"},
                                "updated_at": {"bsonType": "date"},
                                "updated_by": {"bsonType": ["string", "null"]},
                                "modifications": {"bsonType": "array"}
                            }
                        }
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
    
    # Create comprehensive indexes for surgeries collection
    print("Creating indexes for surgeries...")
    surgeries_collection = db["surgeries"]
    
    # Unique and lookup indexes
    await surgeries_collection.create_index("surgery_id", unique=True)
    await surgeries_collection.create_index("patient_id")
    
    # Classification indexes for filtering
    await surgeries_collection.create_index([("classification.urgency", 1)])
    await surgeries_collection.create_index([("classification.category", 1)])
    await surgeries_collection.create_index([("classification.complexity", 1)])
    await surgeries_collection.create_index([("classification.indication", 1)])
    
    # Procedure indexes
    await surgeries_collection.create_index([("procedure.primary_procedure", 1)])
    await surgeries_collection.create_index([("procedure.approach", 1)])
    
    # Timeline indexes
    await surgeries_collection.create_index([("perioperative_timeline.admission_date", 1)])
    await surgeries_collection.create_index([("perioperative_timeline.surgery_date", -1)])
    await surgeries_collection.create_index([("perioperative_timeline.discharge_date", 1)])
    
    # Team indexes for surgeon performance
    await surgeries_collection.create_index([("team.primary_surgeon", 1)])
    await surgeries_collection.create_index([("team.primary_surgeon", 1), ("perioperative_timeline.surgery_date", -1)])
    
    # Cancer-specific indexes
    await surgeries_collection.create_index([("cancer_specific.applicable", 1)])
    await surgeries_collection.create_index([("cancer_specific.cancer_type", 1)])
    
    # Outcome indexes
    await surgeries_collection.create_index([("outcomes.readmission_30day", 1)])
    await surgeries_collection.create_index([("outcomes.mortality_30day", 1)])
    await surgeries_collection.create_index([("postoperative_events.return_to_theatre.occurred", 1)])
    await surgeries_collection.create_index([("postoperative_events.escalation_of_care.occurred", 1)])
    
    # Audit trail indexes
    await surgeries_collection.create_index([("audit_trail.created_at", -1)])
    await surgeries_collection.create_index([("audit_trail.created_by", 1)])
    await surgeries_collection.create_index([("audit_trail.updated_at", -1)])
    
    # Compound indexes for common queries
    await surgeries_collection.create_index([
        ("classification.category", 1),
        ("perioperative_timeline.surgery_date", -1)
    ])
    await surgeries_collection.create_index([
        ("team.primary_surgeon", 1),
        ("classification.category", 1)
    ])
    
    print("✓ Surgery indexes created")
    
    print("\n✅ Database initialization complete!")
    print(f"Database: {DB_NAME}")
    print(f"Collections: patients, surgeries")
    print("\n📊 Indexes created for optimized queries:")
    print("   - Patient lookups and filtering")
    print("   - Surgery classification and urgency")
    print("   - Surgeon performance tracking")
    print("   - Date-based queries and timelines")
    print("   - Cancer staging and outcomes")
    print("   - Complication and readmission tracking")
    print("   - Audit trail for data governance")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(init_database())
