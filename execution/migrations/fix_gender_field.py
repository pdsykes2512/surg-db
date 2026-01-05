#!/usr/bin/env python3
"""
Fix Gender Field Import Bug

The parse_gender function in import_comprehensive.py had a bug where it checked
'male' in sex_str before checking for 'female', causing all "2 Female" values
to be incorrectly classified as 'male' (because 'female' contains 'male').

This script:
1. Re-reads the original CSV
2. Applies the CORRECTED parse_gender logic
3. Updates all patient documents with correct gender values

Bug details:
- Original CSV: 4420 males, 3552 females
- Database before fix: 7970 males, 1 female
- Database after fix: Should match CSV
"""

import os
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

    # Create mapping: Hosp_No → corrected gender
    gender_mapping = {}
    for _, row in df.iterrows():
        hosp_no = str(row.get('Hosp_No', '')).strip()
        if not hosp_no or hosp_no == 'nan':
            continue

        gender = parse_gender_FIXED(row.get('Sex'))
        if gender:
            gender_mapping[hosp_no] = gender

    print(f"\n✅ Created gender mapping for {len(gender_mapping)} patients")

    # Count expected distribution
    gender_counts_expected = {}
    for gender in gender_mapping.values():
        gender_counts_expected[gender] = gender_counts_expected.get(gender, 0) + 1

    print("\n📊 Expected distribution after fix:")
    for gender, count in sorted(gender_counts_expected.items(), key=lambda x: x[1], reverse=True):
        print(f"  {gender}: {count}")

    # Update patients
    print("\n🔄 Updating patient records...")
    updated_count = 0
    corrected_count = 0

    for hosp_no, correct_gender in gender_mapping.items():
        # Find patient by original hosp_no (stored in some field - check patient structure)
        # We need to match on patient_id which is a hash, so we'll use the import metadata

        # Actually, let's match on MRN or NHS number if available
        # For now, let's get all patients and match by checking the CSV row
        patient = db.patients.find_one({'demographics.first_name': {'$exists': True}})

        # Better approach: iterate through all patients and match by index
        pass

    # Alternative approach: Use the patient_id mapping from import
    # Let's instead update by re-running the import logic for just the gender field

    print("\n🔄 Updating all patients with corrected gender values...")

    # Load all patients
    all_patients = list(db.patients.find({}))
    print(f"  Found {len(all_patients)} patients in database")

    # We need to match patients to CSV rows
    # The import script uses HospNo to create patient_id hash
    # Let's recreate that logic

    import hashlib

    def generate_patient_id(hosp_no: str) -> str:
        """Generate 6-character patient ID from hospital number (same as import script)"""
        hash_obj = hashlib.md5(str(hosp_no).encode())
        return hash_obj.hexdigest()[:6].upper()

    # Create mapping: patient_id → gender
    patient_id_to_gender = {}
    for hosp_no, gender in gender_mapping.items():
        patient_id = generate_patient_id(hosp_no)
        patient_id_to_gender[patient_id] = gender

    # Update patients
    for patient in all_patients:
        patient_id = patient.get('patient_id')
        if not patient_id:
            continue

        correct_gender = patient_id_to_gender.get(patient_id)
        if not correct_gender:
            continue

        current_gender = patient.get('demographics', {}).get('gender')

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
