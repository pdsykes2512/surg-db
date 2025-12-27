#!/usr/bin/env python3
"""
Initialize episodes collection with proper indexes for the new episode-based system.
This replaces the surgeries-focused approach with a flexible episode system.
"""
import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.config import settings


async def init_episodes_collection():
    """Initialize the episodes collection with indexes"""
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]
    
    collection_name = "episodes"
    
    # Check if collection exists
    existing_collections = await db.list_collection_names()
    
    if collection_name in existing_collections:
        print(f"✓ Collection '{collection_name}' already exists")
    else:
        # Create collection
        await db.create_collection(collection_name)
        print(f"✓ Created collection '{collection_name}'")
    
    collection = db[collection_name]
    
    # Create indexes
    indexes = [
        # Unique index on episode_id
        {
            "keys": [("episode_id", 1)],
            "name": "episode_id_unique",
            "unique": True
        },
        # Index on patient_id for quick patient lookups
        {
            "keys": [("patient_id", 1)],
            "name": "patient_id_index"
        },
        # Index on condition_type for filtering
        {
            "keys": [("condition_type", 1)],
            "name": "condition_type_index"
        },
        # Compound index on condition_type and cancer_type
        {
            "keys": [("condition_type", 1), ("cancer_type", 1)],
            "name": "condition_cancer_type_index"
        },
        # Index on referral_date for date-based queries
        {
            "keys": [("referral_date", -1)],
            "name": "referral_date_index"
        },
        # Index on first_seen_date
        {
            "keys": [("first_seen_date", -1)],
            "name": "first_seen_date_index"
        },
        # Index on lead_clinician
        {
            "keys": [("lead_clinician", 1)],
            "name": "lead_clinician_index"
        },
        # Index on episode_status
        {
            "keys": [("episode_status", 1)],
            "name": "episode_status_index"
        },
        # Compound index for common queries
        {
            "keys": [
                ("patient_id", 1),
                ("condition_type", 1),
                ("referral_date", -1)
            ],
            "name": "patient_condition_date_index"
        },
        # Index on created_at for audit
        {
            "keys": [("created_at", -1)],
            "name": "created_at_index"
        },
        # Text index for searching in notes/plans
        {
            "keys": [
                ("cancer_data.mdt_treatment_plan", "text"),
                ("treatments.notes", "text")
            ],
            "name": "text_search_index",
            "default_language": "english"
        }
    ]
    
    # Create each index
    for index_spec in indexes:
        try:
            keys = index_spec.pop("keys")
            await collection.create_index(keys, **index_spec)
            print(f"✓ Created index: {index_spec.get('name', 'unnamed')}")
        except Exception as e:
            print(f"✗ Error creating index {index_spec.get('name', 'unnamed')}: {str(e)}")
    
    # Display collection stats
    stats = await db.command("collstats", collection_name)
    print(f"\n{'='*50}")
    print(f"Collection: {collection_name}")
    print(f"Document count: {stats.get('count', 0)}")
    print(f"Storage size: {stats.get('storageSize', 0)} bytes")
    print(f"Indexes: {stats.get('nindexes', 0)}")
    print(f"{'='*50}\n")
    
    client.close()


async def main():
    """Main function"""
    print("Initializing episodes collection...\n")
    try:
        await init_episodes_collection()
        print("\n✓ Episodes collection initialized successfully!")
    except Exception as e:
        print(f"\n✗ Error initializing episodes collection: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
