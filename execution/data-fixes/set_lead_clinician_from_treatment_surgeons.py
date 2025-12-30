#!/usr/bin/env python3
"""
Set Lead Clinician from Treatment Surgeons (Exact Matching - Colorectal Leads Only)

Uses EXACT surname matching to set lead_clinician from treatment surgeon fields.
ONLY matches against COLORECTAL CLINICAL LEADS (subspecialty_leads contains 'colorectal')
- excludes registrars, fellows, gastroenterologists, oncologists, and non-lead staff.

ONLY processes episodes with referral_date >= August 2020 (more reliable recent data).

This script uses PRIMARY SURGEON first, then ASSISTANTS as fallback.
OVERWRITES existing lead_clinician values if a match is found in treatment surgeons.

Author: IMPACT Data Migration
Date: 2025-12-30
"""

import os
import sys
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional, Dict
from collections import defaultdict

# Load environment
load_dotenv('/etc/impact/secrets.env')
load_dotenv('.env')


def load_clinicians_surname_mapping(client) -> Dict[str, str]:
    """
    Load COLORECTAL LEAD clinicians from impact_system and create surname → full_name mapping

    Only includes clinicians where 'colorectal' is in subspecialty_leads array

    Returns:
        Dict mapping lowercase surname to full name
    """
    system_db = client['impact_system']
    # ONLY load colorectal clinical leads (subspecialty_leads contains 'colorectal')
    clinicians = list(system_db.clinicians.find({'subspecialty_leads': 'colorectal'}))

    surname_map = {}  # lowercase surname → full name
    surname_conflicts = defaultdict(list)  # Track multiple clinicians with same surname

    for clinician in clinicians:
        first_name = str(clinician.get('first_name', '')).strip()
        surname = str(clinician.get('surname', '')).strip()

        if not surname:
            continue

        full_name = f"{first_name} {surname}".strip()
        surname_lower = surname.lower()

        # Track if multiple clinicians have same surname
        if surname_lower in surname_map:
            surname_conflicts[surname_lower].append(full_name)
            if surname_map[surname_lower] not in surname_conflicts[surname_lower]:
                surname_conflicts[surname_lower].insert(0, surname_map[surname_lower])
        else:
            surname_map[surname_lower] = full_name

    print(f"✅ Loaded {len(clinicians)} COLORECTAL LEAD clinicians (subspecialty_leads: 'colorectal')")
    print(f"  Unique surnames: {len(surname_map)}")

    if surname_conflicts:
        print(f"\n⚠️  WARNING: {len(surname_conflicts)} surnames match multiple clinicians:")
        for surname, names in surname_conflicts.items():
            print(f"  '{surname}' → {', '.join(names)}")
            # For conflicts, we'll skip matching to avoid ambiguity
            del surname_map[surname]
        print(f"\n  These surnames will be skipped to avoid ambiguity")
        print(f"  Usable surnames: {len(surname_map)}")

    return surname_map


def match_surgeon_name_exact(surgeon_name: str, surname_map: Dict[str, str]) -> Optional[str]:
    """
    Match surgeon name to clinician using EXACT surname matching

    Args:
        surgeon_name: Name from treatment (e.g., "O'Leary", "Khan")
        surname_map: Dict of lowercase surname → full name

    Returns:
        Full clinician name if exact match found, None otherwise
    """
    if not surgeon_name:
        return None

    surgeon_clean = surgeon_name.strip().lower()

    # Try exact surname match
    if surgeon_clean in surname_map:
        return surname_map[surgeon_clean]

    return None


def set_lead_clinician_from_treatment_surgeons(db_name='impact', dry_run=True):
    """
    Set lead_clinician from treatment surgeon fields using exact matching

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
    print(f"SET LEAD CLINICIAN FROM TREATMENT SURGEONS - Database: {db_name}")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will modify database)'}")
    print(f"Date filter: Episodes with referral_date >= 2020-08-01")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Load clinicians for matching
    surname_map = load_clinicians_surname_mapping(client)

    stats = {
        'episodes_checked': 0,
        'episodes_with_treatments': 0,
        'lead_clinician_updated': 0,
        'lead_clinician_set_new': 0,
        'lead_clinician_overwritten': 0,
        'no_matching_surgeon': 0,
        'no_treatments': 0,
        'matched_from_primary': 0,
        'matched_from_assistant': 0
    }

    episodes_collection = db.episodes
    treatments_collection = db.treatments

    # Process episodes since August 2020 (will overwrite existing lead_clinician if match found)
    # Only apply to recent episodes where treatment surgeon matching is more reliable
    from datetime import datetime as dt
    cutoff_date = dt(2020, 8, 1)

    episodes = episodes_collection.find({
        'referral_date': {'$gte': cutoff_date.isoformat()}
    })

    for episode in episodes:
        stats['episodes_checked'] += 1

        episode_id = episode.get('episode_id')
        current_lead_clinician = episode.get('lead_clinician')

        # Get all treatments for this episode
        treatments = list(treatments_collection.find({
            'episode_id': episode_id,
            'treatment_type': 'surgery'
        }))

        if not treatments:
            stats['no_treatments'] += 1
            continue

        stats['episodes_with_treatments'] += 1

        # Try to find a matching surgeon from treatments
        matched_clinician = None
        match_source = None

        # Strategy: Check primary surgeon first, then assistants
        for treatment in treatments:
            team = treatment.get('team', {})

            # 1. Try primary surgeon
            primary_surgeon = team.get('primary_surgeon_text')
            if primary_surgeon:
                matched_clinician = match_surgeon_name_exact(primary_surgeon, surname_map)
                if matched_clinician:
                    match_source = f"primary surgeon '{primary_surgeon}'"
                    stats['matched_from_primary'] += 1
                    break

            # 2. Try assistant surgeons
            if not matched_clinician:
                assistants = team.get('assistant_surgeons_text', [])
                for assistant in assistants:
                    matched_clinician = match_surgeon_name_exact(assistant, surname_map)
                    if matched_clinician:
                        match_source = f"assistant surgeon '{assistant}'"
                        stats['matched_from_assistant'] += 1
                        break

            if matched_clinician:
                break

        if matched_clinician:
            # Determine if this is new or overwriting
            is_overwrite = current_lead_clinician is not None and current_lead_clinician != matched_clinician
            is_new = current_lead_clinician is None

            if dry_run:
                if stats['lead_clinician_updated'] < 20:  # Show first 20
                    if is_overwrite:
                        print(f"  Episode {episode_id}: OVERWRITE '{current_lead_clinician}' → '{matched_clinician}' (from {match_source})")
                    else:
                        print(f"  Episode {episode_id}: SET '{matched_clinician}' (from {match_source})")
            else:
                episodes_collection.update_one(
                    {'_id': episode['_id']},
                    {'$set': {
                        'lead_clinician': matched_clinician,
                        'updated_at': datetime.utcnow()
                    }}
                )

            stats['lead_clinician_updated'] += 1
            if is_new:
                stats['lead_clinician_set_new'] += 1
            elif is_overwrite:
                stats['lead_clinician_overwritten'] += 1
        else:
            stats['no_matching_surgeon'] += 1

        if stats['episodes_checked'] % 1000 == 0:
            print(f"  Processed {stats['episodes_checked']} episodes...")

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total episodes checked: {stats['episodes_checked']}")
    print(f"  Episodes with surgery treatments: {stats['episodes_with_treatments']}")
    print(f"  Lead clinician updated: {stats['lead_clinician_updated']}")
    print(f"    - New (was None): {stats['lead_clinician_set_new']}")
    print(f"    - Overwritten (replaced existing): {stats['lead_clinician_overwritten']}")
    print(f"    - From primary surgeon: {stats['matched_from_primary']}")
    print(f"    - From assistant surgeon: {stats['matched_from_assistant']}")
    print(f"  No matching current surgeon: {stats['no_matching_surgeon']}")
    print(f"  No surgery treatments: {stats['no_treatments']}")
    print("=" * 80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    if dry_run:
        print("\n⚠️  This was a DRY RUN - no changes were made")
        print("Run with --live to apply changes to the database\n")
    else:
        print(f"\n✅ Updated lead_clinician for {stats['lead_clinician_updated']} episodes from treatment surgeons!")
        print(f"   ({stats['lead_clinician_set_new']} new + {stats['lead_clinician_overwritten']} overwritten)\n")

    client.close()
    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Set lead_clinician from treatment surgeons (exact surname matching)')
    parser.add_argument('--database', default='impact', help='Database name (default: impact)')
    parser.add_argument('--live', action='store_true', help='Apply changes (default: dry run)')
    args = parser.parse_args()

    try:
        stats = set_lead_clinician_from_treatment_surgeons(
            db_name=args.database,
            dry_run=not args.live
        )
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        raise
