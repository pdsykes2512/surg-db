#!/usr/bin/env python3
"""
Populate ASA Scores from Source Data

Reads ASA grades from tblSurgery.csv and populates them in the treatments collection.

Author: IMPACT Data Migration
Date: 2025-12-30
"""

import os
import sys
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

# Add backend to path for encryption utilities
sys.path.insert(0, '/root/impact/backend')
from app.utils.encryption import decrypt_field, is_encrypted

# Load environment
load_dotenv('/etc/impact/secrets.env')
load_dotenv('.env')


def map_asa(asa_val) -> int:
    """Map ASA grade to integer (1-5)"""
    if pd.isna(asa_val):
        return None

    asa_str = str(asa_val).strip().upper()

    # Map Roman numerals and numbers
    asa_map = {
        '1': 1, 'I': 1,
        '2': 2, 'II': 2,
        '3': 3, 'III': 3,
        '4': 4, 'IV': 4,
        '5': 5, 'V': 5
    }

    return asa_map.get(asa_str)


def populate_asa_scores(db_name='impact_test', dry_run=True):
    """
    Populate ASA scores from source CSV data

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
    print(f"POPULATE ASA SCORES - Database: {db_name}")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will modify database)'}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Read source CSVs - need both surgery and patient data
    surgery_csv = '/root/.tmp/access_export_mapped/tblSurgery.csv'
    patient_csv = '/root/.tmp/access_export_mapped/tblPatient.csv'

    print(f"\nReading source data:")
    print(f"  Surgery: {surgery_csv}")
    df_surgery = pd.read_csv(surgery_csv, encoding='latin1', low_memory=False)
    print(f"    Loaded {len(df_surgery)} rows")

    print(f"  Patient: {patient_csv}")
    df_patient = pd.read_csv(patient_csv, encoding='latin1', low_memory=False)
    print(f"    Loaded {len(df_patient)} rows")

    # Join surgery with patient on Hosp_No to get NHS_No
    df = df_surgery.merge(df_patient[['Hosp_No', 'NHS_No']], on='Hosp_No', how='left')
    print(f"  Joined: {len(df)} rows with NHS numbers")

    # Check ASA column
    asa_counts = df['ASA'].value_counts(dropna=False)
    print(f"\nASA values in source data:")
    for asa, count in asa_counts.head(10).items():
        mapped = map_asa(asa)
        print(f"  '{asa}' → {mapped}: {count} rows")

    stats = {
        'treatments_checked': 0,
        'asa_populated': 0,
        'asa_already_set': 0,
        'no_match_found': 0,
        'invalid_asa': 0
    }

    # Build lookup: (NHS_No, Date_Th) -> ASA score
    # Use NHS number + treatment date as composite key
    surgery_asa_map = {}
    for _, row in df.iterrows():
        nhs_no_raw = row.get('NHS_No')
        date_th_raw = row.get('Date_Th')
        asa_val = row.get('ASA')

        if not pd.isna(nhs_no_raw) and not pd.isna(date_th_raw) and asa_val:
            # Convert NHS number to string (strip .0 if it's a float)
            try:
                nhs_no = str(int(float(nhs_no_raw)))
            except:
                nhs_no = str(nhs_no_raw).strip()
            # Convert date from MM/DD/YY format to YYYY-MM-DD
            try:
                date_th = pd.to_datetime(date_th_raw, errors='coerce')
                if pd.notna(date_th):
                    date_th = date_th.strftime('%Y-%m-%d')
                else:
                    continue
            except:
                continue

            asa_score = map_asa(asa_val)
            if asa_score:
                key = (nhs_no, date_th)
                surgery_asa_map[key] = asa_score

    print(f"\nBuilt ASA lookup for {len(surgery_asa_map)} surgeries")

    # Show sample lookup keys
    print(f"\nSample ASA lookup keys (first 5):")
    for key in list(surgery_asa_map.keys())[:5]:
        nhs, date = key
        asa = surgery_asa_map[key]
        print(f"  NHS={nhs}, Date={date} → ASA={asa}")

    # Process treatments - need to get patient NHS number to match with CSV NHS_No
    treatments_collection = db.treatments
    patients_collection = db.patients

    # Build patient_id -> NHS number lookup (decrypted)
    patient_nhs_map = {}
    for patient in patients_collection.find({}):
        patient_id = patient.get('patient_id')

        # Get NHS number (top-level field, matches NHS_No in CSV)
        nhs_number = patient.get('nhs_number')
        if nhs_number:
            # Decrypt if needed
            if is_encrypted(nhs_number):
                nhs_number = decrypt_field('nhs_number', nhs_number)
            patient_nhs_map[patient_id] = nhs_number

    print(f"Built patient NHS number lookup for {len(patient_nhs_map)} patients")

    all_treatments = treatments_collection.find({'treatment_type': 'surgery'})

    # Track samples for debugging
    sample_lookups = []

    for treatment in all_treatments:
        stats['treatments_checked'] += 1

        # Check if already has ASA
        if treatment.get('asa_score') is not None:
            stats['asa_already_set'] += 1
            continue

        # Get patient NHS number and treatment date
        patient_id = treatment.get('patient_id')
        treatment_date = treatment.get('treatment_date')

        if not patient_id or not treatment_date:
            stats['no_match_found'] += 1
            continue

        # Look up patient NHS number (decrypted)
        nhs_no = patient_nhs_map.get(patient_id)
        if not nhs_no:
            stats['no_match_found'] += 1
            continue

        # Look up ASA score using (NHS_No, treatment_date) as key
        key = (nhs_no, treatment_date)

        # Save sample lookups for debugging
        if len(sample_lookups) < 5:
            sample_lookups.append((key, treatment.get('treatment_id')))

        asa_score = surgery_asa_map.get(key)

        if asa_score:
            if dry_run:
                if stats['asa_populated'] < 10:  # Show first 10
                    print(f"  Treatment {treatment.get('treatment_id')}: Would set ASA = {asa_score}")
            else:
                # Update treatment
                treatments_collection.update_one(
                    {'_id': treatment['_id']},
                    {'$set': {
                        'asa_score': asa_score,
                        'updated_at': datetime.utcnow()
                    }}
                )

            stats['asa_populated'] += 1
        else:
            stats['invalid_asa'] += 1

        if stats['treatments_checked'] % 1000 == 0:
            print(f"  Processed {stats['treatments_checked']} treatments...")

    # Print summary
    print("\n" + "=" * 80)
    print("ASA POPULATION SUMMARY")
    print("=" * 80)
    print(f"Treatments checked: {stats['treatments_checked']}")
    print(f"ASA scores populated: {stats['asa_populated']}")
    print(f"ASA already set: {stats['asa_already_set']}")
    print(f"No match found: {stats['no_match_found']}")
    print(f"Invalid/unknown ASA: {stats['invalid_asa']}")

    # Show sample lookup attempts
    print(f"\nSample treatment lookup attempts (first 5):")
    for key, treatment_id in sample_lookups:
        nhs, date = key
        found = "✓" if key in surgery_asa_map else "✗"
        print(f"  {found} Treatment {treatment_id}: NHS={nhs}, Date={date}")

    print("=" * 80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    if dry_run:
        print("\n⚠️  This was a DRY RUN - no changes were made")
        print("Run with --live to apply changes to the database\n")
    else:
        print("\n✅ ASA scores populated!\n")

    client.close()
    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Populate ASA scores from source data')
    parser.add_argument('--database', default='impact_test', help='Database name (default: impact_test)')
    parser.add_argument('--live', action='store_true', help='Apply changes (default: dry run)')
    args = parser.parse_args()

    try:
        stats = populate_asa_scores(
            db_name=args.database,
            dry_run=not args.live
        )
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        raise
