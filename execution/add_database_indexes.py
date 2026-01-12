#!/usr/bin/env python3
"""
Add database indexes for improved query performance.

This script creates indexes on frequently queried fields to speed up:
- Episode searches (by episode_id, patient_id, cancer_type, lead_clinician)
- Treatment searches (by treatment_id, episode_id, treatment_type, date)
- Patient searches (by patient_id, MRN hash)
- Tumour searches (by tumour_id, episode_id)

Indexes provide 10-100x speedup on queries.

Usage:
    python3 execution/add_database_indexes.py
"""

import asyncio
import sys
import os

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING

# MongoDB connection with authentication
MONGODB_URI = "mongodb://admin:n6BKQEGYeD6wsn1ZT%40kict%3DD%25Irc7%23eF@localhost:27017/impact?authSource=admin"
DATABASE_NAME = "impact"


async def create_index_safe(collection, keys, **kwargs):
    """Create an index, skipping if it already exists."""
    name = kwargs.get('name', '_'.join([f"{k}_{v}" for k, v in keys]))
    try:
        await collection.create_index(keys, **kwargs)
        return f"✓ {name}"
    except Exception as e:
        if "already exists" in str(e).lower() or "IndexOptionsConflict" in str(e):
            return f"⊘ {name} (already exists)"
        else:
            return f"✗ {name} (error: {e})"


async def create_indexes():
    """Create database indexes for performance optimization."""
    print(f"Connecting to MongoDB...")
    print(f"Database: {DATABASE_NAME}\n")

    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DATABASE_NAME]

    try:
        # Episodes collection indexes
        print("📊 Creating indexes on 'episodes' collection...")
        episodes = db.episodes

        results = await asyncio.gather(
            create_index_safe(episodes, [("episode_id", ASCENDING)], unique=True, name="episode_id_unique"),
            create_index_safe(episodes, [("patient_id", ASCENDING)], name="patient_id"),
            create_index_safe(episodes, [("lead_clinician", ASCENDING)], name="lead_clinician"),
            create_index_safe(episodes, [("referral_date", DESCENDING)], name="referral_date_desc"),
            create_index_safe(episodes, [("cancer_type", ASCENDING)], name="cancer_type"),
            create_index_safe(episodes, [("episode_status", ASCENDING)], name="episode_status"),
            create_index_safe(episodes, [("condition_type", ASCENDING)], name="condition_type"),
            create_index_safe(episodes, [("last_modified_at", DESCENDING)], name="last_modified_at_desc"),
        )
        for result in results:
            print(f"  {result}")

        # Treatments collection indexes
        print("\n💊 Creating indexes on 'treatments' collection...")
        treatments = db.treatments

        results = await asyncio.gather(
            create_index_safe(treatments, [("treatment_id", ASCENDING)], unique=True, name="treatment_id_unique"),
            create_index_safe(treatments, [("episode_id", ASCENDING)], name="episode_id"),
            create_index_safe(treatments, [("patient_id", ASCENDING)], name="patient_id"),
            create_index_safe(treatments, [("treatment_type", ASCENDING)], name="treatment_type"),
            create_index_safe(treatments, [("treatment_date", DESCENDING)], name="treatment_date_desc"),
            create_index_safe(treatments, [("treatment_type", ASCENDING), ("treatment_date", DESCENDING)], name="treatment_type_date"),
            create_index_safe(treatments, [("opcs4_code", ASCENDING)], name="opcs4_code"),
            create_index_safe(treatments, [("parent_surgery_id", ASCENDING)], name="parent_surgery_id"),
        )
        for result in results:
            print(f"  {result}")

        # Patients collection indexes
        print("\n👤 Creating indexes on 'patients' collection...")
        patients = db.patients

        results = await asyncio.gather(
            create_index_safe(patients, [("patient_id", ASCENDING)], unique=True, name="patient_id_unique"),
            create_index_safe(patients, [("mrn_hash", ASCENDING)], name="mrn_hash"),
            create_index_safe(patients, [("nhs_number_hash", ASCENDING)], name="nhs_number_hash"),
        )
        for result in results:
            print(f"  {result}")

        # Tumours collection indexes
        print("\n🔬 Creating indexes on 'tumours' collection...")
        tumours = db.tumours

        results = await asyncio.gather(
            create_index_safe(tumours, [("tumour_id", ASCENDING)], unique=True, name="tumour_id_unique"),
            create_index_safe(tumours, [("episode_id", ASCENDING)], name="episode_id"),
            create_index_safe(tumours, [("patient_id", ASCENDING)], name="patient_id"),
        )
        for result in results:
            print(f"  {result}")

        # Investigations collection indexes
        print("\n🔍 Creating indexes on 'investigations' collection...")
        investigations = db.investigations

        results = await asyncio.gather(
            create_index_safe(investigations, [("investigation_id", ASCENDING)], unique=True, name="investigation_id_unique"),
            create_index_safe(investigations, [("episode_id", ASCENDING)], name="episode_id"),
            create_index_safe(investigations, [("patient_id", ASCENDING)], name="patient_id"),
        )
        for result in results:
            print(f"  {result}")

        # List all indexes for verification
        print("\n\n📋 Verifying indexes...")
        print("\nEpisodes:")
        async for index in episodes.list_indexes():
            print(f"  - {index['name']}: {index.get('key', {})}")

        print("\nTreatments:")
        async for index in treatments.list_indexes():
            print(f"  - {index['name']}: {index.get('key', {})}")

        print("\nPatients:")
        async for index in patients.list_indexes():
            print(f"  - {index['name']}: {index.get('key', {})}")

        print("\nTumours:")
        async for index in tumours.list_indexes():
            print(f"  - {index['name']}: {index.get('key', {})}")

        print("\nInvestigations:")
        async for index in investigations.list_indexes():
            print(f"  - {index['name']}: {index.get('key', {})}")

        print("\n\n✅ Index creation/verification complete!")
        print("\n⚡ Query performance should now be 10-100x faster on indexed fields.")

    except Exception as e:
        print(f"\n❌ Error creating indexes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    print("=" * 80)
    print("Database Index Creation Script")
    print("=" * 80)

    asyncio.run(create_indexes())
