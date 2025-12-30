#!/usr/bin/env python3
"""
Normalize Surgeon Names to Title Case

Problem: Surgeon names in treatments are stored with inconsistent casing:
- "Sykes", "SYKES", "sykes"
- "Khan", "KHAN", "khan"
- "Sagias", "SAGIAS"

This causes issues with matching and display consistency.

Solution: Normalize all surgeon text names to Title Case format.

Author: IMPACT Data Migration
Date: 2025-12-30
"""

import os
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv('/etc/impact/secrets.env')
load_dotenv('.env')


def normalize_surgeon_names(db_name='impact_test', dry_run=True):
    """
    Normalize all surgeon names in treatments to Title Case

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

    print("\n" + "=" * 80)
    print(f"NORMALIZE SURGEON NAMES TO TITLE CASE - Database: {db_name}")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will modify database)'}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    stats = {
        'treatments_checked': 0,
        'primary_surgeons_normalized': 0,
        'assistant_surgeons_normalized': 0,
        'lead_clinicians_normalized': 0
    }

    # Get all treatments
    treatments_collection = db.treatments
    all_treatments = treatments_collection.find({})

    print("\nNormalizing treatment surgeon names...")
    for treatment in all_treatments:
        stats['treatments_checked'] += 1

        updates = {}

        # Normalize primary_surgeon_text
        if 'team' in treatment and 'primary_surgeon_text' in treatment['team']:
            original = treatment['team']['primary_surgeon_text']
            if original and isinstance(original, str) and original.lower() != 'nan':
                normalized = original.strip().title()
                if normalized != original:
                    updates['team.primary_surgeon_text'] = normalized
                    stats['primary_surgeons_normalized'] += 1
                    if dry_run:
                        print(f"  Treatment {treatment['treatment_id']}: '{original}' → '{normalized}'")

        # Normalize assistant_surgeons_text (array)
        if 'team' in treatment and 'assistant_surgeons_text' in treatment['team']:
            assistants = treatment['team']['assistant_surgeons_text']
            if assistants and isinstance(assistants, list):
                normalized_assistants = []
                changed = False
                for assistant in assistants:
                    if assistant and isinstance(assistant, str) and assistant.lower() != 'nan':
                        normalized = assistant.strip().title()
                        normalized_assistants.append(normalized)
                        if normalized != assistant:
                            changed = True
                            stats['assistant_surgeons_normalized'] += 1
                    else:
                        normalized_assistants.append(assistant)

                if changed:
                    updates['team.assistant_surgeons_text'] = normalized_assistants
                    if dry_run:
                        print(f"  Treatment {treatment['treatment_id']}: assistants normalized")

        # Apply updates
        if updates and not dry_run:
            treatments_collection.update_one(
                {'_id': treatment['_id']},
                {'$set': updates}
            )

        if stats['treatments_checked'] % 500 == 0:
            print(f"  Processed {stats['treatments_checked']} treatments...")

    # Normalize lead_clinician in episodes
    print("\nNormalizing episode lead clinician names...")
    episodes_collection = db.episodes
    all_episodes = episodes_collection.find({})

    episodes_checked = 0
    for episode in all_episodes:
        episodes_checked += 1

        if 'lead_clinician' in episode:
            original = episode['lead_clinician']
            if original and isinstance(original, str) and original.lower() != 'nan':
                # Only normalize if it's a text name (not a UUID)
                if len(original) != 24:  # Not an ObjectId
                    normalized = original.strip().title()
                    if normalized != original:
                        stats['lead_clinicians_normalized'] += 1
                        if dry_run:
                            print(f"  Episode {episode['episode_id']}: '{original}' → '{normalized}'")
                        elif not dry_run:
                            episodes_collection.update_one(
                                {'_id': episode['_id']},
                                {'$set': {'lead_clinician': normalized}}
                            )

        if episodes_checked % 500 == 0:
            print(f"  Processed {episodes_checked} episodes...")

    # Print summary
    print("\n" + "=" * 80)
    print("NORMALIZATION SUMMARY")
    print("=" * 80)
    print(f"Treatments checked: {stats['treatments_checked']}")
    print(f"Primary surgeons normalized: {stats['primary_surgeons_normalized']}")
    print(f"Assistant surgeons normalized: {stats['assistant_surgeons_normalized']}")
    print(f"Episodes checked: {episodes_checked}")
    print(f"Lead clinicians normalized: {stats['lead_clinicians_normalized']}")
    print("=" * 80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    if dry_run:
        print("\n⚠️  This was a DRY RUN - no changes were made")
        print("Run with --live to apply changes to the database\n")
    else:
        print("\n✅ Normalization complete!\n")

    client.close()
    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Normalize surgeon names to Title Case')
    parser.add_argument('--database', default='impact_test', help='Database name (default: impact_test)')
    parser.add_argument('--live', action='store_true', help='Apply changes (default: dry run)')
    args = parser.parse_args()

    try:
        stats = normalize_surgeon_names(
            db_name=args.database,
            dry_run=not args.live
        )
    except Exception as e:
        print(f"\n❌ Normalization failed: {e}")
        raise
