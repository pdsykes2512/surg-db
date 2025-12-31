#!/usr/bin/env python3
"""
Migration: Fix episode treatment_ids and tumour_ids arrays

Problem: Treatments and tumours were added to separate collections but their IDs
weren't added to the parent episode's treatment_ids/tumour_ids arrays. This caused
them to not show up when fetching episode data.

Solution: For each episode, find all treatments/tumours that reference it and ensure
their IDs are in the episode's arrays.
"""

import asyncio
import sys
import os

# Load environment variables FIRST before importing any backend code
from dotenv import load_dotenv
load_dotenv('/etc/impact/secrets.env')

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.app.database import Database, get_episodes_collection, get_treatments_collection, get_tumours_collection


async def fix_treatment_ids():
    """Fix missing treatment_ids in episodes and wrong episode_id format in treatments"""
    episodes_collection = await get_episodes_collection()
    treatments_collection = await get_treatments_collection()

    print("Fixing treatment_ids arrays and episode_id formats...")

    # Get all episodes
    episodes = await episodes_collection.find({}).to_list(length=None)
    print(f"Found {len(episodes)} episodes")

    fixed_count = 0
    fixed_format_count = 0
    for episode in episodes:
        episode_id = episode.get('episode_id')
        episode_oid = str(episode.get('_id'))
        if not episode_id:
            continue

        # Find treatments by semantic ID
        treatments_semantic = await treatments_collection.find({"episode_id": episode_id}).to_list(length=None)

        # Find treatments by ObjectId format (wrong)
        treatments_oid = await treatments_collection.find({"episode_id": episode_oid}).to_list(length=None)

        # Fix treatments with wrong episode_id format
        if treatments_oid:
            for treatment in treatments_oid:
                await treatments_collection.update_one(
                    {"_id": treatment['_id']},
                    {"$set": {"episode_id": episode_id}}
                )
            print(f"  ✓ Fixed {len(treatments_oid)} treatments with wrong episode_id format for {episode_id}")
            fixed_format_count += len(treatments_oid)

        # Combine all treatments
        all_treatments = treatments_semantic + treatments_oid
        treatment_ids = [t['treatment_id'] for t in all_treatments if 'treatment_id' in t]

        if treatment_ids:
            # Update episode with all treatment IDs
            result = await episodes_collection.update_one(
                {"episode_id": episode_id},
                {"$set": {"treatment_ids": treatment_ids}}
            )
            if result.modified_count > 0:
                print(f"  ✓ Episode {episode_id}: Added {len(treatment_ids)} treatment IDs")
                fixed_count += 1

    print(f"\nFixed {fixed_count} episodes with treatment_ids")
    print(f"Fixed {fixed_format_count} treatments with wrong episode_id format")
    return fixed_count


async def fix_tumour_ids():
    """Fix missing tumour_ids in episodes"""
    episodes_collection = await get_episodes_collection()
    tumours_collection = await get_tumours_collection()

    print("\nFixing tumour_ids arrays...")

    # Get all episodes
    episodes = await episodes_collection.find({}).to_list(length=None)
    print(f"Found {len(episodes)} episodes")

    fixed_count = 0
    for episode in episodes:
        episode_id = episode.get('episode_id')
        if not episode_id:
            continue

        # Find all tumours for this episode
        tumours = await tumours_collection.find({"episode_id": episode_id}).to_list(length=None)
        tumour_ids = [t['tumour_id'] for t in tumours if 'tumour_id' in t]

        if tumour_ids:
            # Update episode with all tumour IDs
            result = await episodes_collection.update_one(
                {"episode_id": episode_id},
                {"$set": {"tumour_ids": tumour_ids}}
            )
            if result.modified_count > 0:
                print(f"  ✓ Episode {episode_id}: Added {len(tumour_ids)} tumour IDs")
                fixed_count += 1

    print(f"\nFixed {fixed_count} episodes with tumour_ids")
    return fixed_count


async def main():
    """Run migration"""
    print("=" * 60)
    print("MIGRATION: Fix episode treatment_ids and tumour_ids arrays")
    print("=" * 60)
    print()

    # Connect to database
    from backend.app.config import settings
    await Database.connect_db()
    print(f"Connected to database: {settings.mongodb_db_name}\n")

    try:
        treatments_fixed = await fix_treatment_ids()
        tumours_fixed = await fix_tumour_ids()

        print("\n" + "=" * 60)
        print(f"COMPLETE: Fixed {treatments_fixed} episodes (treatments), {tumours_fixed} episodes (tumours)")
        print("=" * 60)
    finally:
        await Database.close_db()
        print("\nDatabase connection closed")


if __name__ == "__main__":
    asyncio.run(main())
