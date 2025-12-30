#!/usr/bin/env python3
"""
Populate Mortality Flags from Deceased Patients

Reads deceased_date from patients (decrypts if needed) and calculates
30-day and 90-day mortality flags for all surgical treatments.

Author: IMPACT Data Migration
Date: 2025-12-30
"""

import os
import sys
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

# Add backend to path for encryption utilities
sys.path.insert(0, '/root/impact/backend')
from app.utils.encryption import decrypt_field, is_encrypted

# Load environment
load_dotenv('/etc/impact/secrets.env')
load_dotenv('.env')


def populate_mortality_flags(db_name='impact_test', dry_run=True):
    """
    Calculate and populate 30-day and 90-day mortality flags for treatments

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
    print(f"POPULATE MORTALITY FLAGS - Database: {db_name}")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will modify database)'}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    stats = {
        'patients_checked': 0,
        'deceased_patients_found': 0,
        'treatments_checked': 0,
        'mortality_30day_set': 0,
        'mortality_90day_set': 0,
        'errors': 0
    }

    # Get all patients with deceased_date in demographics
    patients_collection = db.patients
    deceased_patients_cursor = patients_collection.find({
        "demographics.deceased_date": {"$exists": True, "$ne": None}
    })

    deceased_patients = list(deceased_patients_cursor)
    print(f"Found {len(deceased_patients)} deceased patients")

    # Build deceased patient lookup
    patient_deceased_dates = {}
    for patient in deceased_patients:
        patient_id = patient.get('patient_id')
        deceased_date_raw = patient.get('demographics', {}).get('deceased_date')

        if not patient_id or not deceased_date_raw:
            continue

        try:
            # Decrypt if encrypted
            if is_encrypted(deceased_date_raw):
                deceased_date_str = decrypt_field('deceased_date', deceased_date_raw)
            else:
                deceased_date_str = deceased_date_raw

            # Parse the date
            deceased_date = datetime.strptime(deceased_date_str, '%Y-%m-%d')
            patient_deceased_dates[patient_id] = deceased_date
            stats['deceased_patients_found'] += 1

        except Exception as e:
            stats['errors'] += 1
            if dry_run:
                print(f"  ⚠️  Error parsing deceased date for patient {patient_id}: {e}")

    print(f"Successfully parsed {stats['deceased_patients_found']} deceased dates\n")

    # Process treatments for deceased patients
    treatments_collection = db.treatments

    for patient_id, deceased_date in patient_deceased_dates.items():
        stats['patients_checked'] += 1

        # Get all surgical treatments for this patient
        treatments = treatments_collection.find({
            'patient_id': patient_id,
            'treatment_type': 'surgery'
        })

        for treatment in treatments:
            stats['treatments_checked'] += 1
            treatment_date_str = treatment.get('treatment_date')

            if not treatment_date_str:
                continue

            try:
                treatment_date = datetime.strptime(treatment_date_str, '%Y-%m-%d')
                days_to_death = (deceased_date - treatment_date).days

                if days_to_death >= 0:  # Death after treatment
                    mortality_30day = days_to_death <= 30
                    mortality_90day = days_to_death <= 90

                    if dry_run:
                        if mortality_30day or mortality_90day:
                            print(f"  Treatment {treatment.get('treatment_id')}: "
                                  f"patient died {days_to_death} days after surgery "
                                  f"(30d: {mortality_30day}, 90d: {mortality_90day})")
                    else:
                        # Update treatment with mortality flags
                        treatments_collection.update_one(
                            {'_id': treatment['_id']},
                            {'$set': {
                                'mortality_30day': mortality_30day,
                                'mortality_90day': mortality_90day,
                                'updated_at': datetime.utcnow()
                            }}
                        )

                    if mortality_30day:
                        stats['mortality_30day_set'] += 1
                    if mortality_90day:
                        stats['mortality_90day_set'] += 1

            except Exception as e:
                stats['errors'] += 1
                if dry_run:
                    print(f"  ⚠️  Error processing treatment {treatment.get('treatment_id')}: {e}")

        if stats['patients_checked'] % 100 == 0:
            print(f"  Processed {stats['patients_checked']} patients...")

    # Print summary
    print("\n" + "=" * 80)
    print("MORTALITY FLAG SUMMARY")
    print("=" * 80)
    print(f"Patients checked: {stats['patients_checked']}")
    print(f"Deceased patients found: {stats['deceased_patients_found']}")
    print(f"Treatments checked: {stats['treatments_checked']}")
    print(f"30-day mortality flags set: {stats['mortality_30day_set']}")
    print(f"90-day mortality flags set: {stats['mortality_90day_set']}")
    print(f"Errors: {stats['errors']}")
    print("=" * 80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    if dry_run:
        print("\n⚠️  This was a DRY RUN - no changes were made")
        print("Run with --live to apply changes to the database\n")
    else:
        print("\n✅ Mortality flags populated!\n")

    client.close()
    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Populate mortality flags from deceased patients')
    parser.add_argument('--database', default='impact_test', help='Database name (default: impact_test)')
    parser.add_argument('--live', action='store_true', help='Apply changes (default: dry run)')
    args = parser.parse_args()

    try:
        stats = populate_mortality_flags(
            db_name=args.database,
            dry_run=not args.live
        )
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        raise
