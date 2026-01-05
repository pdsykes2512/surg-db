#!/usr/bin/env python3
"""
Fix Gender Field Import Bug

The parse_gender function in import_comprehensive.py had a bug where it checked
'male' in sex_str before checking for 'female', causing all "2 Female" values
to be incorrectly classified as 'male' (because 'female' contains 'male').

This script:
1. Re-reads the original CSV
2. Applies the CORRECTED parse_gender logic
3. Matches patients using NHS number or MRN (PAS_No) hashes
4. Updates all patient documents with correct gender values

Bug details:
- Original CSV: 4420 males, 3552 females
- Database before fix: 7970 males, 1 female
- Database after fix: Should match CSV
"""

import os
import hashlib
import pandas as pd
from pymongo import MongoClient
from typing import Optional
from dotenv import load_dotenv

# Load environment
load_dotenv('/etc/impact/secrets.env')
load_dotenv('.env')

CSV_PATH = os.path.expanduser('~/.tmp/access_export_comprehensive/patients.csv')


def parse_gender_FIXED(sex_val) -> Optional[str]:
    """
    Parse gender field - CORRECTED LOGIC

    Fix: Check for 'female' BEFORE checking 'male' to avoid substring match
    """
    if pd.isna(sex_val):
        return None

    sex_str = str(sex_val).strip().lower()

    # IMPORTANT: Check 'female' FIRST (before 'male') to avoid substring match
    if sex_str.startswith('2') or 'female' in sex_str:
        return 'female'
    elif sex_str.startswith('1') or sex_str == 'male':  # Use == for 'male' to be safe
        return 'male'

    return None


def create_hash(value: str) -> str:
    """Create SHA256 hash of a value (same as used for nhs_number_hash and mrn_hash)"""
    if not value or pd.isna(value) or str(value).strip() == '' or str(value) == 'nan':
        return None
    return hashlib.sha256(str(value).encode()).hexdigest()


def fix_gender_field():
    """Re-import gender field with corrected logic"""

    # Connect to MongoDB
    mongodb_uri = os.getenv('MONGODB_URI')
    if not mongodb_uri:
        raise ValueError("MONGODB_URI not found in environment")

    client = MongoClient(mongodb_uri)
    db = client['impact']

    print("=" * 80)
    print("FIXING GENDER FIELD IMPORT BUG")
    print("=" * 80)

    # Check current state
    print("\n📊 Current database state:")
    gender_counts = list(db.patients.aggregate([
        {'$group': {'_id': '$demographics.gender', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}}
    ]))
    for g in gender_counts:
        print(f"  {g['_id']}: {g['count']}")

    # Load CSV
    print(f"\n📁 Loading CSV: {CSV_PATH}")
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH, low_memory=False)
    print(f"  ✅ Loaded {len(df)} rows")

    # Check CSV sex distribution
    print("\n📊 CSV Sex column distribution:")
    print(df['Sex'].value_counts())

    # Create mappings by NHS number hash and MRN hash
    print("\n🔄 Creating identifier mappings...")
    nhs_to_gender = {}
    mrn_to_gender = {}

    for _, row in df.iterrows():
        gender = parse_gender_FIXED(row.get('Sex'))
        if not gender:
            continue

        # NHS number
        nhs_no = row.get('NHS_No')
        if nhs_no and not pd.isna(nhs_no):
            # Remove decimal if present
            nhs_str = str(nhs_no).strip()
            if '.' in nhs_str:
                nhs_str = nhs_str.split('.')[0]
            nhs_hash = create_hash(nhs_str)
            if nhs_hash:
                nhs_to_gender[nhs_hash] = gender

        # MRN (PAS_No)
        mrn = row.get('PAS_No')
        if mrn and not pd.isna(mrn):
            mrn_str = str(mrn).strip()
            if '.' in mrn_str:
                mrn_str = mrn_str.split('.')[0]
            mrn_hash = create_hash(mrn_str)
            if mrn_hash:
                mrn_to_gender[mrn_hash] = gender

    print(f"  ✅ Created {len(nhs_to_gender)} NHS number → gender mappings")
    print(f"  ✅ Created {len(mrn_to_gender)} MRN → gender mappings")

    # Count expected distribution
    all_genders = list(nhs_to_gender.values()) + list(mrn_to_gender.values())
    gender_counts_expected = {}
    for gender in all_genders:
        gender_counts_expected[gender] = gender_counts_expected.get(gender, 0) + 1

    print("\n📊 Expected distribution after fix:")
    for gender, count in sorted(gender_counts_expected.items(), key=lambda x: x[1], reverse=True):
        print(f"  {gender}: {count}")

    # Load all patients
    print("\n🔄 Loading all patients...")
    all_patients = list(db.patients.find({}))
    print(f"  Found {len(all_patients)} patients in database")

    # Update patients
    print("\n🔄 Updating patients with corrected gender values...")
    updated_count = 0
    corrected_count = 0
    no_match_count = 0

    for patient in all_patients:
        patient_id = patient.get('patient_id')
        if not patient_id:
            continue

        current_gender = patient.get('demographics', {}).get('gender')

        # Try to find correct gender by NHS hash or MRN hash
        correct_gender = None
        nhs_hash = patient.get('nhs_number_hash')
        mrn_hash = patient.get('mrn_hash')

        if nhs_hash and nhs_hash in nhs_to_gender:
            correct_gender = nhs_to_gender[nhs_hash]
        elif mrn_hash and mrn_hash in mrn_to_gender:
            correct_gender = mrn_to_gender[mrn_hash]

        if not correct_gender:
            no_match_count += 1
            continue

        if current_gender != correct_gender:
            result = db.patients.update_one(
                {'patient_id': patient_id},
                {'$set': {'demographics.gender': correct_gender}}
            )
            if result.modified_count > 0:
                corrected_count += 1

        updated_count += 1

    print(f"  ✅ Processed {updated_count} patients")
    print(f"  ✅ Corrected {corrected_count} patients")
    print(f"  ⚠️  No match found for {no_match_count} patients")

    # Verify final state
    print("\n📊 Final database state:")
    gender_counts_final = list(db.patients.aggregate([
        {'$group': {'_id': '$demographics.gender', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}}
    ]))
    for g in gender_counts_final:
        print(f"  {g['_id']}: {g['count']}")

    print("\n✅ Gender field fix complete!")

    return corrected_count


if __name__ == '__main__':
    fixed_count = fix_gender_field()
    print(f"\n🎉 Fixed {fixed_count} patient gender values")
