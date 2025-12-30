#!/usr/bin/env python3
"""
Fix Numeric Prefixes and Date of Birth Issues

This script:
1. Strips numeric prefixes from Treatment Plan in episodes (e.g., "01 surgery" -> "surgery")
2. Strips numeric prefixes from Procedure Name in treatments (e.g., "6 Anterior resection" -> "Anterior resection")
3. Fixes DOB years that are 20XX and should be 19XX (e.g., 2050 -> 1950)

Author: IMPACT Data Migration
Date: 2025-12-30
"""

import os
import sys
import re
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

# Add backend to path for encryption utilities
sys.path.insert(0, '/root/impact/backend')
from app.utils.encryption import encrypt_field, decrypt_field, is_encrypted

# Load environment
load_dotenv('/etc/impact/secrets.env')
load_dotenv('.env')


def strip_numeric_prefix(value: str) -> str:
    """
    Strip numeric prefix from field values

    Removes patterns like "1 ", "17 " from start of string
    Examples:
        "6 Anterior resection" -> "Anterior resection"
        "01 surgery" -> "surgery"
        "Laparoscopic" -> "Laparoscopic" (unchanged)
    """
    if not value:
        return value

    value_str = str(value).strip()

    # Pattern: one or more digits followed by space at start of string
    cleaned = re.sub(r'^\d+\s+', '', value_str)

    return cleaned


def fix_prefixes_and_dob(db_name='impact_test', dry_run=True):
    """
    Fix numeric prefixes in treatment plans and procedure names, and fix DOB issues

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
    print(f"FIX NUMERIC PREFIXES AND DOB - Database: {db_name}")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will modify database)'}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    stats = {
        'treatments_checked': 0,
        'procedures_fixed': 0,
        'episodes_checked': 0,
        'treatment_plans_fixed': 0,
        'patients_checked': 0,
        'dobs_fixed': 0
    }

    # ========================================================================
    # 1. Fix procedure names in treatments
    # ========================================================================
    print("\n[1/3] Fixing procedure names in treatments...")
    treatments_collection = db.treatments

    # Find treatments with primary_procedure that starts with digits
    treatments_with_prefix = treatments_collection.find({
        'procedure.primary_procedure': {'$regex': r'^\d+\s+'}
    })

    for treatment in treatments_with_prefix:
        stats['treatments_checked'] += 1

        old_procedure = treatment.get('procedure', {}).get('primary_procedure')
        if old_procedure:
            new_procedure = strip_numeric_prefix(old_procedure)

            if old_procedure != new_procedure:
                if dry_run:
                    if stats['procedures_fixed'] < 10:  # Show first 10
                        print(f"  Treatment {treatment.get('treatment_id')}: \"{old_procedure}\" -> \"{new_procedure}\"")
                else:
                    treatments_collection.update_one(
                        {'_id': treatment['_id']},
                        {'$set': {
                            'procedure.primary_procedure': new_procedure,
                            'updated_at': datetime.utcnow()
                        }}
                    )

                stats['procedures_fixed'] += 1

        if stats['treatments_checked'] % 1000 == 0:
            print(f"  Processed {stats['treatments_checked']} treatments...")

    print(f"  ✓ Fixed {stats['procedures_fixed']} procedure names")

    # ========================================================================
    # 2. Fix treatment plans in episodes
    # ========================================================================
    print("\n[2/3] Fixing treatment plans in episodes...")
    episodes_collection = db.episodes

    # Find episodes with treatment_plan that starts with digits
    episodes_with_prefix = episodes_collection.find({
        'treatment_plan': {'$regex': r'^\d+\s+'}
    })

    for episode in episodes_with_prefix:
        stats['episodes_checked'] += 1

        old_plan = episode.get('treatment_plan')
        if old_plan:
            new_plan = strip_numeric_prefix(old_plan)

            if old_plan != new_plan:
                if dry_run:
                    if stats['treatment_plans_fixed'] < 10:  # Show first 10
                        print(f"  Episode {episode.get('episode_id')}: \"{old_plan}\" -> \"{new_plan}\"")
                else:
                    episodes_collection.update_one(
                        {'_id': episode['_id']},
                        {'$set': {
                            'treatment_plan': new_plan,
                            'updated_at': datetime.utcnow()
                        }}
                    )

                stats['treatment_plans_fixed'] += 1

        if stats['episodes_checked'] % 1000 == 0:
            print(f"  Processed {stats['episodes_checked']} episodes...")

    print(f"  ✓ Fixed {stats['treatment_plans_fixed']} treatment plans")

    # ========================================================================
    # 3. Fix DOB years (20XX -> 19XX)
    # ========================================================================
    print("\n[3/3] Fixing date of birth years (20XX -> 19XX)...")
    patients_collection = db.patients

    all_patients = patients_collection.find({})

    for patient in all_patients:
        stats['patients_checked'] += 1

        dob_field = patient.get('demographics', {}).get('date_of_birth')
        if not dob_field:
            continue

        # Decrypt if encrypted
        if is_encrypted(dob_field):
            dob_str = decrypt_field('date_of_birth', dob_field)
        else:
            dob_str = dob_field

        # Check if year is >= 2000
        try:
            dob_dt = datetime.strptime(dob_str, '%Y-%m-%d')

            if dob_dt.year >= 2000:
                # Convert to 19XX
                old_year = dob_dt.year
                new_year = dob_dt.year - 100
                new_dob_dt = dob_dt.replace(year=new_year)
                new_dob_str = new_dob_dt.strftime('%Y-%m-%d')

                # Calculate correct age
                today = datetime.now()
                age = today.year - new_dob_dt.year
                # Adjust if birthday hasn't occurred yet this year
                if today.month < new_dob_dt.month or (today.month == new_dob_dt.month and today.day < new_dob_dt.day):
                    age -= 1
                # Ensure age is within valid range
                age = max(0, min(age, 150))

                # Re-encrypt if it was encrypted
                if is_encrypted(dob_field):
                    new_dob_encrypted = encrypt_field('date_of_birth', new_dob_str)
                    update_value = new_dob_encrypted
                else:
                    update_value = new_dob_str

                if dry_run:
                    if stats['dobs_fixed'] < 10:  # Show first 10
                        print(f"  Patient {patient.get('patient_id')}: {old_year} -> {new_year} (Age: {age})")
                else:
                    patients_collection.update_one(
                        {'_id': patient['_id']},
                        {'$set': {
                            'demographics.date_of_birth': update_value,
                            'demographics.age': age,
                            'updated_at': datetime.utcnow()
                        }}
                    )

                stats['dobs_fixed'] += 1

        except (ValueError, AttributeError):
            # Invalid date format or missing field, skip
            pass

        if stats['patients_checked'] % 1000 == 0:
            print(f"  Processed {stats['patients_checked']} patients...")

    print(f"  ✓ Fixed {stats['dobs_fixed']} date of birth entries")

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Treatments checked: {stats['treatments_checked']}")
    print(f"  Procedure names fixed: {stats['procedures_fixed']}")
    print(f"Episodes checked: {stats['episodes_checked']}")
    print(f"  Treatment plans fixed: {stats['treatment_plans_fixed']}")
    print(f"Patients checked: {stats['patients_checked']}")
    print(f"  DOB entries fixed: {stats['dobs_fixed']}")
    print("=" * 80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    if dry_run:
        print("\n⚠️  This was a DRY RUN - no changes were made")
        print("Run with --live to apply changes to the database\n")
    else:
        print("\n✅ Fixes applied successfully!\n")

    client.close()
    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Fix numeric prefixes and DOB issues')
    parser.add_argument('--database', default='impact_test', help='Database name (default: impact_test)')
    parser.add_argument('--live', action='store_true', help='Apply changes (default: dry run)')
    args = parser.parse_args()

    try:
        stats = fix_prefixes_and_dob(
            db_name=args.database,
            dry_run=not args.live
        )
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        raise
