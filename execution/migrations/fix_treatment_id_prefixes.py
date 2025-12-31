#!/usr/bin/env python3
"""
Migration: Update treatment IDs to use type-specific prefixes

Problem: All imported treatments use generic T- prefix instead of type-specific prefixes:
- surgery → SUR-
- chemotherapy → ONC-
- radiotherapy → DXT-
- immunotherapy → IMM-

Solution: Update all treatment_ids in treatments collection and corresponding references
in episodes' treatment_ids arrays.
"""

import asyncio
import sys
import os

# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv('/etc/impact/secrets.env')

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.app.database import Database, get_episodes_collection, get_treatments_collection


# Prefix mapping based on treatment type
PREFIX_MAP = {
    'surgery': 'SUR',
    'chemotherapy': 'ONC',
    'radiotherapy': 'DXT',
    'immunotherapy': 'IMM',
}


def get_new_treatment_id(old_id: str, treatment_type: str) -> str:
    """
    Generate new treatment ID with correct prefix.

    Examples:
        T-ABC123-01 (surgery) → SUR-ABC123-01
        T-XYZ789-02 (chemotherapy) → ONC-XYZ789-02
    """
    # Get the correct prefix
    prefix = PREFIX_MAP.get(treatment_type, 'TRE')

    # Replace T- prefix with type-specific prefix
    if old_id.startswith('T-'):
        return old_id.replace('T-', f'{prefix}-', 1)

    # Already has correct prefix, return as-is
    return old_id


async def main():
    """Run migration"""
    print("=" * 70)
    print("MIGRATION: Update treatment IDs to use type-specific prefixes")
    print("=" * 70)
    print()

    # Connect to database
    from backend.app.config import settings
    await Database.connect_db()
    print(f"Connected to database: {settings.mongodb_db_name}\n")

    treatments_collection = await get_treatments_collection()
    episodes_collection = await get_episodes_collection()

    try:
        # Step 1: Get all treatments that need updating (T- prefix)
        print("Step 1: Finding treatments with T- prefix...")
        t_treatments = await treatments_collection.find({
            "treatment_id": {"$regex": "^T-"}
        }).to_list(length=None)

        print(f"Found {len(t_treatments)} treatments to update\n")

        if len(t_treatments) == 0:
            print("No treatments to update. Migration complete.")
            return

        # Step 2: Update treatment IDs in treatments collection
        print("Step 2: Updating treatment IDs in treatments collection...")

        updated_count = 0
        mapping = {}  # old_id -> new_id mapping for episode updates

        for treatment in t_treatments:
            old_id = treatment['treatment_id']
            treatment_type = treatment.get('treatment_type', 'surgery')
            new_id = get_new_treatment_id(old_id, treatment_type)

            # Store mapping for episode updates
            mapping[old_id] = new_id

            # Update treatment document
            await treatments_collection.update_one(
                {"_id": treatment["_id"]},
                {"$set": {"treatment_id": new_id}}
            )

            updated_count += 1
            if updated_count % 1000 == 0:
                print(f"  Updated {updated_count}/{len(t_treatments)} treatments...")

        print(f"✓ Updated {updated_count} treatment IDs\n")

        # Step 3: Update treatment_ids arrays in episodes
        print("Step 3: Updating treatment_ids in episodes...")

        episodes = await episodes_collection.find({
            "treatment_ids": {"$exists": True, "$ne": []}
        }).to_list(length=None)

        print(f"Found {len(episodes)} episodes with treatments")

        episode_updated_count = 0
        for episode in episodes:
            treatment_ids = episode.get('treatment_ids', [])

            # Update any treatment IDs that were changed
            new_treatment_ids = [
                mapping.get(tid, tid) for tid in treatment_ids
            ]

            # Only update if something changed
            if new_treatment_ids != treatment_ids:
                await episodes_collection.update_one(
                    {"_id": episode["_id"]},
                    {"$set": {"treatment_ids": new_treatment_ids}}
                )
                episode_updated_count += 1

        print(f"✓ Updated {episode_updated_count} episodes\n")

        # Step 4: Show summary by treatment type
        print("Step 4: Summary of changes by treatment type:")
        type_counts = {}
        for old_id, new_id in mapping.items():
            prefix = new_id.split('-')[0]
            type_counts[prefix] = type_counts.get(prefix, 0) + 1

        for prefix in sorted(type_counts.keys()):
            count = type_counts[prefix]
            print(f"  {prefix}-: {count} treatments")

        print("\n" + "=" * 70)
        print(f"COMPLETE: Updated {updated_count} treatments, {episode_updated_count} episodes")
        print("=" * 70)

    finally:
        await Database.close_db()
        print("\nDatabase connection closed")


if __name__ == "__main__":
    asyncio.run(main())
