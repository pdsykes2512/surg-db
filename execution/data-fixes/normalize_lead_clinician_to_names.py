#!/usr/bin/env python3
"""
Normalize Lead Clinician to Names

Converts all lead_clinician ObjectId strings to full names for uniformity.
Currently episodes have a mix of:
- ObjectId strings (e.g., "694ac3d44536cc3ca6577776")
- Free text names (e.g., "Parvaiz", "Senapati")
- None

This script converts all ObjectId strings to full names so the field is uniform.

Author: IMPACT Data Migration
Date: 2025-12-30
"""

import os
import sys
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
from bson import ObjectId

# Load environment
load_dotenv('/etc/impact/secrets.env')
load_dotenv('.env')


def normalize_lead_clinician(db_name='impact', dry_run=True):
    """
    Convert all lead_clinician ObjectId strings to full names

    Args:
        db_name: Database name
        dry_run: If True, only print what would be done (default: True)
    """
    # Connect to MongoDB
    mongo_uri = os.getenv('MONGODB_URI')
    if not mongo_uri:
        raise ValueError("MONGODB_URI not found in environment")

    client = MongoClient(mongo_uri)
    db = client[db_name]
    system_db = client['impact_system']

    print("\n" + "=" * 80)
    print(f"NORMALIZE LEAD CLINICIAN TO NAMES - Database: {db_name}")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will modify database)'}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Build clinician ID → name mapping
    clinicians = list(system_db.clinicians.find({}))
    clinician_map = {}

    for clinician in clinicians:
        clinician_id = str(clinician['_id'])
        first_name = clinician.get('first_name', '').strip()
        surname = clinician.get('surname', '').strip()
        full_name = f"{first_name} {surname}".strip()

        if full_name:
            clinician_map[clinician_id] = full_name

    print(f"\nLoaded {len(clinician_map)} clinicians from impact_system")
    print(f"Sample mappings:")
    for cid, name in list(clinician_map.items())[:5]:
        print(f"  {cid} → {name}")

    stats = {
        'episodes_checked': 0,
        'converted_to_name': 0,
        'already_name': 0,
        'none_value': 0,
        'unknown_id': 0
    }

    # Process episodes
    episodes_collection = db.episodes
    all_episodes = episodes_collection.find({'lead_clinician': {'$ne': None}})

    for episode in all_episodes:
        stats['episodes_checked'] += 1

        lead_clinician = episode.get('lead_clinician')

        # Check if it's a 24-char hex string (ObjectId)
        if len(lead_clinician) == 24 and all(c in '0123456789abcdef' for c in lead_clinician.lower()):
            # This is an ObjectId string - convert to name
            full_name = clinician_map.get(lead_clinician)

            if full_name:
                if dry_run:
                    if stats['converted_to_name'] < 10:  # Show first 10
                        print(f"\n  Episode {episode.get('episode_id')}:")
                        print(f"    FROM: {lead_clinician}")
                        print(f"    TO:   {full_name}")
                else:
                    episodes_collection.update_one(
                        {'_id': episode['_id']},
                        {'$set': {
                            'lead_clinician': full_name,
                            'updated_at': datetime.utcnow()
                        }}
                    )

                stats['converted_to_name'] += 1
            else:
                # ObjectId not found in clinicians table
                stats['unknown_id'] += 1
                if dry_run and stats['unknown_id'] <= 3:
                    print(f"\n  ⚠️  Episode {episode.get('episode_id')}: Unknown clinician ID {lead_clinician}")
        else:
            # Already a text name - no change needed
            stats['already_name'] += 1

        if stats['episodes_checked'] % 1000 == 0:
            print(f"  Processed {stats['episodes_checked']} episodes...")

    # Count episodes with None
    none_count = episodes_collection.count_documents({'lead_clinician': None})
    stats['none_value'] = none_count

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Episodes checked: {stats['episodes_checked']}")
    print(f"  Converted ObjectId → Name: {stats['converted_to_name']}")
    print(f"  Already text name: {stats['already_name']}")
    print(f"  Unknown ObjectId: {stats['unknown_id']}")
    print(f"Episodes with None: {stats['none_value']}")
    print("=" * 80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    if dry_run:
        print("\n⚠️  This was a DRY RUN - no changes were made")
        print("Run with --live to apply changes to the database\n")
    else:
        print(f"\n✅ Normalized {stats['converted_to_name']} lead_clinician values to names!\n")

    client.close()
    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Normalize lead_clinician to names')
    parser.add_argument('--database', default='impact', help='Database name (default: impact)')
    parser.add_argument('--live', action='store_true', help='Apply changes (default: dry run)')
    args = parser.parse_args()

    try:
        stats = normalize_lead_clinician(
            db_name=args.database,
            dry_run=not args.live
        )
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        raise
