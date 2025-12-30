#!/usr/bin/env python3
"""
Populate Lead Clinician from SurgFirm Field

Uses the SurgFirm field from tblPatient.csv to populate lead_clinician in episodes.
SurgFirm represents the patient's consultant/firm, which is the appropriate value
for lead_clinician (rather than the operating surgeon).

Author: IMPACT Data Migration
Date: 2025-12-30
"""

import os
import sys
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional, Dict

# Add backend to path for utilities
sys.path.insert(0, '/root/impact/backend')
from app.utils.encryption import decrypt_field, is_encrypted

# Load environment
load_dotenv('/etc/impact/secrets.env')
load_dotenv('.env')


def load_clinicians_mapping(client) -> Dict[str, str]:
    """
    Load clinicians from impact_system database and create name→ID mapping

    Returns:
        Dict mapping surgeon name variations to clinician_id
    """
    system_db = client['impact_system']
    clinicians = list(system_db.clinicians.find({}))

    clinician_mapping = {}

    for clinician in clinicians:
        clinician_id = str(clinician.get('_id'))
        first_name = str(clinician.get('first_name', '')).strip()
        surname = str(clinician.get('surname', '')).strip()

        if not surname:
            continue

        # Create various name formats for matching
        full_name = f"{first_name} {surname}".strip()
        surname_first = f"{surname} {first_name}".strip()
        surname_only = surname

        # Map all variations to the clinician_id (case-insensitive)
        clinician_mapping[full_name.lower()] = clinician_id
        clinician_mapping[surname_first.lower()] = clinician_id
        clinician_mapping[surname_only.lower()] = clinician_id

        # Also try with initials
        if first_name:
            initial_name = f"{first_name[0]} {surname}".strip()
            clinician_mapping[initial_name.lower()] = clinician_id

            surname_initial = f"{surname} {first_name[0]}".strip()
            clinician_mapping[surname_initial.lower()] = clinician_id

    print(f"✅ Loaded {len(clinicians)} clinicians from impact_system with {len(clinician_mapping)} name variations")
    return clinician_mapping


def match_surgeon_to_clinician(surgeon_name: str, clinician_mapping: Dict[str, str]) -> tuple[Optional[str], Optional[str]]:
    """
    Match surgeon name to clinician ID

    Args:
        surgeon_name: Name from CSV
        clinician_mapping: Dict of name→clinician_id

    Returns:
        Tuple of (clinician_id or None, display_name in Title Case)
    """
    if not surgeon_name:
        return None, None

    surgeon_clean = surgeon_name.strip()
    surgeon_lower = surgeon_clean.lower()
    surgeon_title = surgeon_clean.title()  # Normalize to Title Case

    # Try exact match first
    clinician_id = clinician_mapping.get(surgeon_lower)

    if clinician_id:
        return clinician_id, surgeon_title

    # No match - return None for clinician_id but keep the text name in Title Case
    return None, surgeon_title


def populate_lead_clinician(db_name='impact_test', dry_run=True):
    """
    Populate lead_clinician from SurgFirm field

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
    print(f"POPULATE LEAD CLINICIAN FROM SURGFIRM - Database: {db_name}")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will modify database)'}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Load clinicians for matching
    clinician_mapping = load_clinicians_mapping(client)

    # Read patient CSV to get SurgFirm
    patient_csv = '/root/.tmp/access_export_mapped/tblPatient.csv'
    print(f"\nReading patient data: {patient_csv}")
    df_patient = pd.read_csv(patient_csv, encoding='latin1', low_memory=False)
    print(f"  Loaded {len(df_patient)} patients")

    # Build mapping: patient_id → SurgFirm
    # We need to match patients by their ID stored in database
    patients_collection = db.patients
    surgfirm_map = {}  # patient_id → surgfirm

    print("\nBuilding patient_id → SurgFirm mapping...")
    for patient in patients_collection.find({}):
        patient_id = patient.get('patient_id')

        # Get NHS number to match with NHS_No in CSV
        nhs_raw = patient.get('nhs_number')

        if not nhs_raw:
            continue

        # Decrypt NHS number if encrypted
        if is_encrypted(nhs_raw):
            nhs_number = decrypt_field('nhs_number', nhs_raw)
        else:
            nhs_number = nhs_raw

        # Find matching row in patient CSV using NHS_No
        # CSV has NHS_No as float (e.g., 4184440118.0), need to convert to int then string
        try:
            nhs_str = str(int(float(nhs_number)))  # Convert to int to remove .0, then to string
        except (ValueError, TypeError):
            continue

        matching_rows = df_patient[df_patient['NHS_No'] == float(nhs_str)]
        if len(matching_rows) > 0:
            surgfirm = matching_rows.iloc[0].get('SurgFirm')
            if pd.notna(surgfirm) and str(surgfirm).strip() != '' and str(surgfirm) != 'nan':
                surgfirm_map[patient_id] = str(surgfirm).strip()

    print(f"  Built mapping for {len(surgfirm_map)} patients with SurgFirm")

    stats = {
        'episodes_checked': 0,
        'lead_clinician_populated': 0,
        'lead_clinician_already_set': 0,
        'no_surgfirm_found': 0,
        'matched_to_clinician_id': 0,
        'stored_as_text': 0
    }

    # Process episodes
    episodes_collection = db.episodes
    all_episodes = episodes_collection.find({})

    for episode in all_episodes:
        stats['episodes_checked'] += 1

        # Check if already has lead_clinician
        if episode.get('lead_clinician'):
            stats['lead_clinician_already_set'] += 1
            continue

        # Get patient_id
        patient_id = episode.get('patient_id')
        if not patient_id:
            stats['no_surgfirm_found'] += 1
            continue

        # Look up SurgFirm
        surgfirm = surgfirm_map.get(patient_id)
        if not surgfirm:
            stats['no_surgfirm_found'] += 1
            continue

        # Match to clinician
        clinician_id, display_name = match_surgeon_to_clinician(surgfirm, clinician_mapping)

        if clinician_id:
            lead_clinician_value = clinician_id
            stats['matched_to_clinician_id'] += 1
            match_type = "ID"
        else:
            lead_clinician_value = display_name or surgfirm.title()
            stats['stored_as_text'] += 1
            match_type = "Text"

        if dry_run:
            if stats['lead_clinician_populated'] < 20:  # Show first 20
                print(f"  Episode {episode.get('episode_id')}: Set lead_clinician = '{lead_clinician_value}' ({match_type}) from SurgFirm '{surgfirm}'")
        else:
            episodes_collection.update_one(
                {'_id': episode['_id']},
                {'$set': {
                    'lead_clinician': lead_clinician_value,
                    'updated_at': datetime.utcnow()
                }}
            )

        stats['lead_clinician_populated'] += 1

        if stats['episodes_checked'] % 1000 == 0:
            print(f"  Processed {stats['episodes_checked']} episodes...")

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Episodes checked: {stats['episodes_checked']}")
    print(f"Lead clinician populated: {stats['lead_clinician_populated']}")
    print(f"  - Matched to clinician ID: {stats['matched_to_clinician_id']}")
    print(f"  - Stored as text: {stats['stored_as_text']}")
    print(f"Lead clinician already set: {stats['lead_clinician_already_set']}")
    print(f"No SurgFirm found: {stats['no_surgfirm_found']}")
    print("=" * 80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    if dry_run:
        print("\n⚠️  This was a DRY RUN - no changes were made")
        print("Run with --live to apply changes to the database\n")
    else:
        print("\n✅ Lead clinician populated from SurgFirm!\n")

    client.close()
    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Populate lead_clinician from SurgFirm field')
    parser.add_argument('--database', default='impact_test', help='Database name (default: impact_test)')
    parser.add_argument('--live', action='store_true', help='Apply changes (default: dry run)')
    args = parser.parse_args()

    try:
        stats = populate_lead_clinician(
            db_name=args.database,
            dry_run=not args.live
        )
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        raise
