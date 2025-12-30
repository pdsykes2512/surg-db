#!/usr/bin/env python3
"""
Populate readmission and return_to_theatre fields in the impact database
from the Access database tblSurgery table.

Fields to import:
- re_op (1 = return to theatre)
- Major_C (contains "Readmission" text)
"""

import os
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment
load_dotenv('/etc/impact/secrets.env')
load_dotenv('.env')


def parse_date(date_val):
    """Parse date from various formats"""
    if pd.isna(date_val) or date_val == '' or date_val is None:
        return None

    if isinstance(date_val, datetime):
        return date_val.strftime('%Y-%m-%d')

    date_str = str(date_val).strip()

    formats = [
        '%m/%d/%y %H:%M:%S',
        '%m/%d/%Y %H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
        '%m/%d/%y',
        '%m/%d/%Y',
        '%d/%m/%Y'
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.year > 2050:
                dt = dt.replace(year=dt.year - 100)
            return dt.strftime('%Y-%m-%d')
        except:
            continue

    return None


def populate_readmission_return_theatre(db_name='impact', dry_run=False):
    """
    Populate readmission and return_to_theatre flags from Access database export
    """
    # MongoDB connection
    mongo_uri = os.getenv('MONGODB_URI')
    if not mongo_uri:
        raise ValueError("MONGODB_URI not found in environment")

    client = MongoClient(mongo_uri)
    db = client[db_name]

    print("=" * 80)
    print(f"POPULATING READMISSION & RETURN TO THEATRE - Database: {db_name}")
    print("=" * 80)

    # Read surgery CSV export
    surgery_csv = '/root/.tmp/surgery_full_export.csv'
    df = pd.read_csv(surgery_csv, low_memory=False)

    print(f"\nLoaded {len(df)} surgery records from Access database")

    # Build Hosp_No to patient_id mapping
    patients = list(db.patients.find({}, {'patient_id': 1, 'hospital_number': 1}))
    hosp_no_to_patient_id = {
        p['hospital_number']: p['patient_id']
        for p in patients if p.get('hospital_number')
    }

    print(f"Built mapping for {len(hosp_no_to_patient_id)} patients")

    stats = {
        'total_processed': 0,
        'return_to_theatre_set': 0,
        'readmission_set': 0,
        'both_set': 0,
        'not_found': 0,
        'no_date': 0,
    }

    # Process each surgery record
    for idx, row in df.iterrows():
        hosp_no = str(row.get('Hosp_No', '')).strip()
        surgery_date = parse_date(row.get('Surgery'))
        re_op = row.get('re_op')
        major_c = str(row.get('Major_C', '')).strip()

        if not hosp_no or hosp_no == 'nan':
            continue

        if not surgery_date:
            stats['no_date'] += 1
            continue

        # Get patient_id
        patient_id = hosp_no_to_patient_id.get(hosp_no)
        if not patient_id:
            stats['not_found'] += 1
            continue

        # Determine flags
        is_return_to_theatre = re_op in [1, '1', 'yes', 'Yes', True]
        is_readmission = 'readmission' in major_c.lower()

        # Only update if at least one flag is true
        if not is_return_to_theatre and not is_readmission:
            continue

        stats['total_processed'] += 1

        # Find matching treatment by patient_id and surgery date
        # Match within 1 day to account for date parsing variations
        surgery_dt = datetime.strptime(surgery_date, '%Y-%m-%d')
        date_min = (surgery_dt - timedelta(days=1)).strftime('%Y-%m-%d')
        date_max = (surgery_dt + timedelta(days=1)).strftime('%Y-%m-%d')

        treatment = db.treatments.find_one({
            'patient_id': patient_id,
            'treatment_type': 'surgery',
            'treatment_date': {'$gte': date_min, '$lte': date_max}
        })

        if not treatment:
            stats['not_found'] += 1
            continue

        # Build update
        update_fields = {}

        if is_return_to_theatre:
            update_fields['return_to_theatre'] = True
            stats['return_to_theatre_set'] += 1

        if is_readmission:
            update_fields['readmission_30d'] = True
            stats['readmission_set'] += 1

        if is_return_to_theatre and is_readmission:
            stats['both_set'] += 1

        # Update database
        if not dry_run and update_fields:
            db.treatments.update_one(
                {'_id': treatment['_id']},
                {'$set': update_fields}
            )

        # Progress indicator
        if stats['total_processed'] % 100 == 0:
            print(f"  Processed {stats['total_processed']} cases...")

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total cases processed: {stats['total_processed']}")
    print(f"Return to theatre set: {stats['return_to_theatre_set']}")
    print(f"Readmission set: {stats['readmission_set']}")
    print(f"Both flags set: {stats['both_set']}")
    print(f"Not found (no matching treatment): {stats['not_found']}")
    print(f"No surgery date: {stats['no_date']}")

    if dry_run:
        print("\n⚠️  DRY RUN - No changes made to database")
    else:
        print("\n✅ Readmission and return to theatre flags updated successfully")

        # Verification
        total_return_theatre = db.treatments.count_documents({'return_to_theatre': True})
        total_readmission = db.treatments.count_documents({'readmission_30d': True})
        print(f"\nVerification:")
        print(f"  Treatments with return_to_theatre=True: {total_return_theatre}")
        print(f"  Treatments with readmission=True: {total_readmission}")

    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Populate readmission and return to theatre flags')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
    parser.add_argument('--database', default='impact', help='Database name (default: impact)')
    args = parser.parse_args()

    populate_readmission_return_theatre(db_name=args.database, dry_run=args.dry_run)
