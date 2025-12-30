#!/usr/bin/env python3
"""
Fix urgency field and populate ASA grade in the impact database.

Current issue:
- urgency field contains ASA grades (i, ii, iii, iv, v) instead of elective/emergency
- ASA grade is not imported at all

Fix:
- Import urgency from ModeOp field (1=Elective, 3=Urgent, 4=Emergency)
- Import ASA grade from ASA field (I, II, III, IV, V)
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


def map_urgency(mode_op):
    """Map ModeOp field to urgency"""
    if pd.isna(mode_op):
        return None

    mode_op_str = str(mode_op).strip().lower()

    if mode_op_str.startswith('1') or 'elective' in mode_op_str:
        return 'elective'
    elif mode_op_str.startswith('3') or 'urgent' in mode_op_str:
        return 'urgent'
    elif mode_op_str.startswith('4') or 'emergency' in mode_op_str:
        return 'emergency'
    elif mode_op_str.startswith('2') or 'scheduled' in mode_op_str:
        return 'elective'  # Scheduled is essentially elective

    return None


def map_asa_grade(asa):
    """Map ASA field to ASA grade"""
    if pd.isna(asa):
        return None

    asa_str = str(asa).strip().upper()

    # Handle numeric and Roman numeral formats
    if asa_str in ['1', 'I']:
        return 'I'
    elif asa_str in ['2', 'II']:
        return 'II'
    elif asa_str in ['3', 'III']:
        return 'III'
    elif asa_str in ['4', 'IV']:
        return 'IV'
    elif asa_str in ['5', 'V']:
        return 'V'
    elif asa_str in ['99', '7']:  # Unknown/missing
        return None

    return None


def fix_urgency_and_asa(db_name='impact', dry_run=False):
    """
    Fix urgency and populate ASA grade from Access database export
    """
    # MongoDB connection
    mongo_uri = os.getenv('MONGODB_URI')
    if not mongo_uri:
        raise ValueError("MONGODB_URI not found in environment")

    client = MongoClient(mongo_uri)
    db = client[db_name]

    print("=" * 80)
    print(f"FIXING URGENCY & POPULATING ASA GRADE - Database: {db_name}")
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
        'urgency_updated': 0,
        'urgency_elective': 0,
        'urgency_urgent': 0,
        'urgency_emergency': 0,
        'asa_updated': 0,
        'asa_i': 0,
        'asa_ii': 0,
        'asa_iii': 0,
        'asa_iv': 0,
        'asa_v': 0,
        'not_found': 0,
    }

    # Process each surgery record
    for idx, row in df.iterrows():
        hosp_no = str(row.get('Hosp_No', '')).strip()
        surgery_date = parse_date(row.get('Surgery'))
        mode_op = row.get('ModeOp')
        asa = row.get('ASA')

        if not hosp_no or hosp_no == 'nan':
            continue

        if not surgery_date:
            continue

        # Get patient_id
        patient_id = hosp_no_to_patient_id.get(hosp_no)
        if not patient_id:
            stats['not_found'] += 1
            continue

        # Map urgency and ASA
        urgency = map_urgency(mode_op)
        asa_grade = map_asa_grade(asa)

        if not urgency and not asa_grade:
            continue

        # Find matching treatment by patient_id and surgery date
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

        stats['total_processed'] += 1

        # Build update
        update_fields = {}

        if urgency:
            update_fields['urgency'] = urgency
            stats['urgency_updated'] += 1
            if urgency == 'elective':
                stats['urgency_elective'] += 1
            elif urgency == 'urgent':
                stats['urgency_urgent'] += 1
            elif urgency == 'emergency':
                stats['urgency_emergency'] += 1

        if asa_grade:
            update_fields['asa_grade'] = asa_grade
            stats['asa_updated'] += 1
            if asa_grade == 'I':
                stats['asa_i'] += 1
            elif asa_grade == 'II':
                stats['asa_ii'] += 1
            elif asa_grade == 'III':
                stats['asa_iii'] += 1
            elif asa_grade == 'IV':
                stats['asa_iv'] += 1
            elif asa_grade == 'V':
                stats['asa_v'] += 1

        # Update database
        if not dry_run and update_fields:
            db.treatments.update_one(
                {'_id': treatment['_id']},
                {'$set': update_fields}
            )

        # Progress indicator
        if stats['total_processed'] % 500 == 0:
            print(f"  Processed {stats['total_processed']} treatments...")

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total treatments processed: {stats['total_processed']}")
    print()
    print("Urgency:")
    print(f"  Updated: {stats['urgency_updated']}")
    print(f"    Elective: {stats['urgency_elective']}")
    print(f"    Urgent: {stats['urgency_urgent']}")
    print(f"    Emergency: {stats['urgency_emergency']}")
    print()
    print("ASA Grade:")
    print(f"  Updated: {stats['asa_updated']}")
    print(f"    ASA I: {stats['asa_i']}")
    print(f"    ASA II: {stats['asa_ii']}")
    print(f"    ASA III: {stats['asa_iii']}")
    print(f"    ASA IV: {stats['asa_iv']}")
    print(f"    ASA V: {stats['asa_v']}")
    print()
    print(f"Not found: {stats['not_found']}")

    if dry_run:
        print("\n⚠️  DRY RUN - No changes made to database")
    else:
        print("\n✅ Urgency and ASA grade updated successfully")

        # Verification
        total = db.treatments.count_documents({'treatment_type': 'surgery'})
        elective = db.treatments.count_documents({'urgency': 'elective'})
        urgent = db.treatments.count_documents({'urgency': 'urgent'})
        emergency = db.treatments.count_documents({'urgency': 'emergency'})

        print(f"\nVerification (urgency):")
        print(f"  Elective: {elective} ({elective/total*100:.1f}%)")
        print(f"  Urgent: {urgent} ({urgent/total*100:.1f}%)")
        print(f"  Emergency: {emergency} ({emergency/total*100:.1f}%)")

        asa_i = db.treatments.count_documents({'asa_grade': 'I'})
        asa_ii = db.treatments.count_documents({'asa_grade': 'II'})
        asa_iii = db.treatments.count_documents({'asa_grade': 'III'})
        asa_iv = db.treatments.count_documents({'asa_grade': 'IV'})
        asa_v = db.treatments.count_documents({'asa_grade': 'V'})

        print(f"\nVerification (ASA grade):")
        print(f"  ASA I: {asa_i} ({asa_i/total*100:.1f}%)")
        print(f"  ASA II: {asa_ii} ({asa_ii/total*100:.1f}%)")
        print(f"  ASA III: {asa_iii} ({asa_iii/total*100:.1f}%)")
        print(f"  ASA IV: {asa_iv} ({asa_iv/total*100:.1f}%)")
        print(f"  ASA V: {asa_v} ({asa_v/total*100:.1f}%)")

    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Fix urgency and populate ASA grade')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
    parser.add_argument('--database', default='impact', help='Database name (default: impact)')
    args = parser.parse_args()

    fix_urgency_and_asa(db_name=args.database, dry_run=args.dry_run)
