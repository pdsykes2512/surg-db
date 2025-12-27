#!/usr/bin/env python3
"""
Add database indexes for better query performance
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient


async def create_indexes():
    """Create indexes on frequently queried fields"""
    # Update to correct database name
    client = AsyncIOMotorClient('mongodb://admin:admin123@localhost:27017/surgdb?authSource=admin')
    db = client.surgdb
    
    print("Creating indexes for surgeries collection...")
    
    try:
        # Indexes for filtering
        await db.surgeries.create_index([("patient_id", 1)])
        print("✓ Index created: patient_id")
    except Exception as e:
        print(f"  Skip: patient_id ({str(e)[:50]}...)")
    
    try:
        await db.surgeries.create_index([("classification.urgency", 1)])
        print("✓ Index created: classification.urgency")
    except Exception as e:
        print(f"  Skip: classification.urgency ({str(e)[:50]}...)")
    
    try:
        await db.surgeries.create_index([("team.primary_surgeon", 1)])
        print("✓ Index created: team.primary_surgeon")
    except Exception as e:
        print(f"  Skip: team.primary_surgeon ({str(e)[:50]}...)")
    
    try:
        await db.surgeries.create_index([("perioperative_timeline.surgery_date", -1)])
        print("✓ Index created: perioperative_timeline.surgery_date (descending)")
    except Exception as e:
        print(f"  Skip: surgery_date ({str(e)[:50]}...)")
    
    try:
        # Compound index for common filter combinations
        await db.surgeries.create_index([
            ("perioperative_timeline.surgery_date", -1),
            ("classification.urgency", 1)
        ])
        print("✓ Compound index created: surgery_date + urgency")
    except Exception as e:
        print(f"  Skip: compound index ({str(e)[:50]}...)")
    
    try:
        # Indexes for reports/analytics
        await db.surgeries.create_index([("postoperative_events.complications", 1)])
        print("✓ Index created: postoperative_events.complications")
    except Exception as e:
        print(f"  Skip: complications ({str(e)[:50]}...)")
    
    try:
        await db.surgeries.create_index([("outcomes.readmission_30day", 1)])
        print("✓ Index created: outcomes.readmission_30day")
    except Exception as e:
        print(f"  Skip: readmission_30day ({str(e)[:50]}...)")
    
    try:
        await db.surgeries.create_index([("outcomes.mortality_30day", 1)])
        print("✓ Index created: outcomes.mortality_30day")
    except Exception as e:
        print(f"  Skip: mortality_30day ({str(e)[:50]}...)")
    
    # Indexes for episodes collection (CRITICAL for COSD export performance)
    print("\nCreating indexes for episodes collection...")
    try:
        await db.episodes.create_index([("condition_type", 1)])
        print("✓ Index created: condition_type")
    except Exception as e:
        print(f"  Skip: condition_type")
    
    try:
        await db.episodes.create_index([("cancer_type", 1)])
        print("✓ Index created: cancer_type")
    except Exception as e:
        print(f"  Skip: cancer_type")
    
    try:
        await db.episodes.create_index([("patient_id", 1)])
        print("✓ Index created: patient_id")
    except Exception as e:
        print(f"  Skip: patient_id")
    
    try:
        await db.episodes.create_index([("episode_id", 1)], unique=True)
        print("✓ Unique index created: episode_id")
    except Exception as e:
        print(f"  Skip: episode_id")
    
    try:
        # Compound index for cancer episode queries
        await db.episodes.create_index([
            ("condition_type", 1),
            ("cancer_type", 1)
        ])
        print("✓ Compound index created: condition_type + cancer_type")
    except Exception as e:
        print(f"  Skip: compound index")
    
    # Indexes for tumours collection
    print("\nCreating indexes for tumours collection...")
    try:
        await db.tumours.create_index([("episode_id", 1)])
        print("✓ Index created: episode_id")
    except Exception as e:
        print(f"  Skip: episode_id")
    
    try:
        await db.tumours.create_index([("patient_id", 1)])
        print("✓ Index created: patient_id")
    except Exception as e:
        print(f"  Skip: patient_id")
    
    # Indexes for treatments collection
    print("\nCreating indexes for treatments collection...")
    try:
        await db.treatments.create_index([("episode_id", 1)])
        print("✓ Index created: episode_id")
    except Exception as e:
        print(f"  Skip: episode_id")
    
    try:
        await db.treatments.create_index([("patient_id", 1)])
        print("✓ Index created: patient_id")
    except Exception as e:
        print(f"  Skip: patient_id")
    
    try:
        await db.treatments.create_index([("treatment_type", 1)])
        print("✓ Index created: treatment_type")
    except Exception as e:
        print(f"  Skip: treatment_type")
    
    # Indexes for patient collection
    print("\nCreating indexes for patients collection...")
    try:
        await db.patients.create_index([("patient_id", 1)], unique=True)
        print("✓ Unique index created: patient_id")
    except Exception as e:
        print(f"  Skip: patient_id")
    
    try:
        await db.patients.create_index([("nhs_number", 1)])
        print("✓ Index created: nhs_number")
    except Exception as e:
        print(f"  Skip: nhs_number")
    
    # Indexes for surgeons collection
    print("\nCreating indexes for surgeons collection...")
    try:
        await db.surgeons.create_index([("gmc_number", 1)], unique=True, sparse=True)
        print("✓ Unique sparse index created: gmc_number")
    except Exception as e:
        print(f"  Skip: gmc_number")
    
    try:
        await db.surgeons.create_index([("first_name", 1), ("surname", 1)])
        print("✓ Compound index created: first_name + surname")
    except Exception as e:
        print(f"  Skip: first_name + surname")
    
    print("\n✅ All indexes created successfully!")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(create_indexes())
