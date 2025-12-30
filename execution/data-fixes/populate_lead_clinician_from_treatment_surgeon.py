#!/usr/bin/env python3
"""
⚠️ DO NOT USE THIS SCRIPT ⚠️

This script creates INCORRECT MAPPINGS using overly broad fuzzy matching.

KNOWN ISSUES:
- Matches "Senapati" → "Dan O'Leary" (completely wrong)
- Matches "Curtis" → "Dan O'Leary" (incorrect)
- Matches historical surgeons to wrong current clinicians

REASON:
The fuzzy matching logic (`if known_name in lead_clinician_lower or
lead_clinician_lower in known_name`) is too aggressive and matches
unrelated surgeon names.

USE INSTEAD:
- restore_lead_clinician_from_surgfirm.py (authoritative SurgFirm source)

HISTORICAL CONTEXT:
This script was created 2025-12-30 and immediately caused data corruption.
It was replaced with restore_lead_clinician_from_surgfirm.py on the same day.

Original Description:
Populate Lead Clinician from Treatment Surgeon
Updates episode lead_clinician to match the surgeon from the treatment's team fields
when there's a match in the clinicians table.

Uses all team fields for matching:
- primary_surgeon (clinician ID)
- primary_surgeon_text (text name)
- assistant_surgeons (list of IDs)
- assistant_surgeons_text (list of text names)

Author: IMPACT Data Migration
Date: 2025-12-30
"""

import os
import sys
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional, Dict

# Load environment
load_dotenv('/etc/impact/secrets.env')
load_dotenv('.env')


def load_clinicians_mapping(client) -> tuple[Dict[str, str], Dict[str, str]]:
    """
    Load clinicians from impact_system database and create mappings

    Returns:
        Tuple of (id_to_name_map, name_to_name_map) where:
        - id_to_name_map: clinician_id -> full name
        - name_to_name_map: various name formats -> full name (for fuzzy matching)
    """
    system_db = client['impact_system']
    clinicians = list(system_db.clinicians.find({}))

    id_to_name_map = {}
    name_to_name_map = {}

    for clinician in clinicians:
        clinician_id = str(clinician.get('_id'))
        first_name = str(clinician.get('first_name', '')).strip()
        surname = str(clinician.get('surname', '')).strip()

        if not surname:
            continue

        # Create full name
        full_name = f"{first_name} {surname}".strip()

        # Map ID to name
        id_to_name_map[clinician_id] = full_name

        # Map various name formats to full name (case-insensitive)
        name_to_name_map[full_name.lower()] = full_name
        name_to_name_map[surname.lower()] = full_name

        # Also try surname first
        if first_name:
            surname_first = f"{surname} {first_name}".strip()
            name_to_name_map[surname_first.lower()] = full_name

            # Try with initials
            initial_name = f"{first_name[0]} {surname}".strip()
            name_to_name_map[initial_name.lower()] = full_name

            surname_initial = f"{surname} {first_name[0]}".strip()
            name_to_name_map[surname_initial.lower()] = full_name

    print(f"✅ Loaded {len(clinicians)} clinicians from impact_system with {len(name_to_name_map)} name variations")
    return id_to_name_map, name_to_name_map


def match_surgeon_to_clinician(surgeon_value: Optional[str], id_map: Dict[str, str], name_map: Dict[str, str]) -> Optional[str]:
    """
    Match surgeon value (ID or text) to a clinician's full name

    Args:
        surgeon_value: Clinician ID or text name
        id_map: Dict of clinician_id -> full name
        name_map: Dict of name variations -> full name

    Returns:
        Full clinician name if matched, None otherwise
    """
    if not surgeon_value or str(surgeon_value).strip() == '':
        return None

    surgeon_clean = str(surgeon_value).strip()

    # Try exact ID match first
    if surgeon_clean in id_map:
        return id_map[surgeon_clean]

    # Try name matching (case-insensitive)
    surgeon_lower = surgeon_clean.lower()
    if surgeon_lower in name_map:
        return name_map[surgeon_lower]

    # No match
    return None


def populate_lead_clinician_from_surgeon(db_name='impact', dry_run=True):
    """
    Update lead_clinician from treatment surgeon when there's a match

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
    print(f"POPULATE LEAD CLINICIAN FROM TREATMENT SURGEON - Database: {db_name}")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will modify database)'}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Load clinicians for matching
    id_map, name_map = load_clinicians_mapping(client)

    stats = {
        'episodes_checked': 0,
        'episodes_with_treatments': 0,
        'lead_clinician_updated': 0,
        'lead_clinician_already_set': 0,
        'no_surgeon_match': 0,
        'no_treatments': 0
    }

    # Process episodes
    episodes_collection = db.episodes
    treatments_collection = db.treatments

    all_episodes = episodes_collection.find({})

    for episode in all_episodes:
        stats['episodes_checked'] += 1

        episode_id = episode.get('episode_id')
        current_lead_clinician = episode.get('lead_clinician')
        treatment_ids = episode.get('treatment_ids', [])

        # Check if episode has treatments
        if not treatment_ids:
            stats['no_treatments'] += 1
            continue

        stats['episodes_with_treatments'] += 1

        # Get the first treatment for this episode
        treatment = treatments_collection.find_one({'treatment_id': treatment_ids[0]})

        if not treatment:
            stats['no_treatments'] += 1
            continue

        # Try to match surgeon from team fields
        team = treatment.get('team', {})
        matched_name = None

        # Priority 1: primary_surgeon (clinician ID)
        primary_surgeon_id = team.get('primary_surgeon')
        if primary_surgeon_id:
            matched_name = match_surgeon_to_clinician(primary_surgeon_id, id_map, name_map)

        # Priority 2: primary_surgeon_text
        if not matched_name:
            primary_surgeon_text = team.get('primary_surgeon_text')
            if primary_surgeon_text:
                matched_name = match_surgeon_to_clinician(primary_surgeon_text, id_map, name_map)

        # Priority 3: assistant_surgeons (if no primary surgeon)
        if not matched_name:
            assistant_ids = team.get('assistant_surgeons', [])
            for asst_id in assistant_ids:
                matched_name = match_surgeon_to_clinician(asst_id, id_map, name_map)
                if matched_name:
                    break

        # Priority 4: assistant_surgeons_text
        if not matched_name:
            assistant_texts = team.get('assistant_surgeons_text', [])
            for asst_text in assistant_texts:
                matched_name = match_surgeon_to_clinician(asst_text, id_map, name_map)
                if matched_name:
                    break

        # Update lead_clinician if we found a match
        if matched_name:
            # Check if lead_clinician is already set to a known clinician
            current_is_known = current_lead_clinician and (
                current_lead_clinician in id_map.values() or
                current_lead_clinician.lower() in name_map
            )

            if current_is_known:
                # Already has a valid clinician - don't override
                stats['lead_clinician_already_set'] += 1
            else:
                # Update to the matched clinician
                if dry_run:
                    if stats['lead_clinician_updated'] < 20:  # Show first 20
                        print(f"\n  Episode {episode_id}:")
                        print(f"    FROM: {current_lead_clinician if current_lead_clinician else 'None'}")
                        print(f"    TO:   {matched_name}")
                else:
                    episodes_collection.update_one(
                        {'_id': episode['_id']},
                        {'$set': {
                            'lead_clinician': matched_name,
                            'updated_at': datetime.utcnow()
                        }}
                    )

                stats['lead_clinician_updated'] += 1
        else:
            # No match found in clinicians table
            stats['no_surgeon_match'] += 1

        if stats['episodes_checked'] % 1000 == 0:
            print(f"  Processed {stats['episodes_checked']} episodes...")

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Episodes checked: {stats['episodes_checked']}")
    print(f"  With treatments: {stats['episodes_with_treatments']}")
    print(f"  Without treatments: {stats['no_treatments']}")
    print(f"\nLead clinician updates:")
    print(f"  Updated to matched surgeon: {stats['lead_clinician_updated']}")
    print(f"  Already had valid clinician: {stats['lead_clinician_already_set']}")
    print(f"  No surgeon match found: {stats['no_surgeon_match']}")
    print("=" * 80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    if dry_run:
        print("\n⚠️  This was a DRY RUN - no changes were made")
        print("Run with --live to apply changes to the database\n")
    else:
        print(f"\n✅ Updated {stats['lead_clinician_updated']} episodes with matched surgeons!\n")

    client.close()
    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Populate lead_clinician from treatment surgeon')
    parser.add_argument('--database', default='impact', help='Database name (default: impact)')
    parser.add_argument('--live', action='store_true', help='Apply changes (default: dry run)')
    args = parser.parse_args()

    try:
        stats = populate_lead_clinician_from_surgeon(
            db_name=args.database,
            dry_run=not args.live
        )
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        raise
