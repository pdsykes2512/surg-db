#!/usr/bin/env python3
"""
Restore Lead Clinician from SurgFirm (Force Overwrite)

This script FORCES restoration of lead_clinician values from the SurgFirm field,
overwriting any existing values to undo incorrect mappings.

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
    """Load clinicians from impact_system database and create name→ID mapping"""
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

        # Map all variations to the full name (we want names, not IDs)
        clinician_mapping[full_name.lower()] = full_name
        clinician_mapping[surname.lower()] = full_name

        if first_name:
            surname_first = f"{surname} {first_name}".strip()
            clinician_mapping[surname_first.lower()] = full_name

    print(f"✅ Loaded {len(clinicians)} clinicians with {len(clinician_mapping)} name variations")
    return clinician_mapping


def match_surgfirm_to_name(surgfirm: str, clinician_mapping: Dict[str, str]) -> str:
    """
    Match SurgFirm value to clinician name or return as Title Case

    Args:
        surgfirm: SurgFirm value from CSV
        clinician_mapping: Dict of name variations → full name

    Returns:
        Clinician full name if matched, otherwise Title Case surgfirm
    """
    if not surgfirm:
        return None

    surgfirm_clean = surgfirm.strip()
    surgfirm_lower = surgfirm_clean.lower()

    # Try to match to known clinician
    if surgfirm_lower in clinician_mapping:
        return clinician_mapping[surgfirm_lower]

    # Return as Title Case (historical surgeon)
    return surgfirm_clean.title()


def restore_lead_clinician(db_name='impact', dry_run=True):
    """
    FORCE restore lead_clinician from SurgFirm field

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
    print(f"RESTORE LEAD CLINICIAN FROM SURGFIRM - Database: {db_name}")
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

    # Build mapping: patient_id → SurgFirm name
    patients_collection = db.patients
    surgfirm_map = {}  # patient_id → surgfirm name

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
        try:
            nhs_str = str(int(float(nhs_number)))
        except (ValueError, TypeError):
            continue

        matching_rows = df_patient[df_patient['NHS_No'] == float(nhs_str)]
        if len(matching_rows) > 0:
            surgfirm = matching_rows.iloc[0].get('SurgFirm')
            if pd.notna(surgfirm) and str(surgfirm).strip() != '' and str(surgfirm) != 'nan':
                # Match to clinician name or use Title Case
                surgfirm_name = match_surgfirm_to_name(str(surgfirm).strip(), clinician_mapping)
                if surgfirm_name:
                    surgfirm_map[patient_id] = surgfirm_name

    print(f"  Built mapping for {len(surgfirm_map)} patients with SurgFirm")

    stats = {
        'episodes_checked': 0,
        'restored': 0,
        'no_surgfirm': 0
    }

    # Process ALL episodes - FORCE restore from SurgFirm
    episodes_collection = db.episodes
    all_episodes = episodes_collection.find({})

    for episode in all_episodes:
        stats['episodes_checked'] += 1

        patient_id = episode.get('patient_id')
        current_lead = episode.get('lead_clinician')

        if not patient_id:
            stats['no_surgfirm'] += 1
            continue

        # Look up SurgFirm
        surgfirm_name = surgfirm_map.get(patient_id)

        if surgfirm_name:
            # FORCE restore even if already set
            if dry_run:
                if stats['restored'] < 20:  # Show first 20
                    if current_lead != surgfirm_name:
                        print(f"  Episode {episode.get('episode_id')}: '{current_lead}' → '{surgfirm_name}'")
            else:
                episodes_collection.update_one(
                    {'_id': episode['_id']},
                    {'$set': {
                        'lead_clinician': surgfirm_name,
                        'updated_at': datetime.utcnow()
                    }}
                )

            stats['restored'] += 1
        else:
            stats['no_surgfirm'] += 1

        if stats['episodes_checked'] % 1000 == 0:
            print(f"  Processed {stats['episodes_checked']} episodes...")

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Episodes checked: {stats['episodes_checked']}")
    print(f"  Restored from SurgFirm: {stats['restored']}")
    print(f"  No SurgFirm found: {stats['no_surgfirm']}")
    print("=" * 80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    if dry_run:
        print("\n⚠️  This was a DRY RUN - no changes were made")
        print("Run with --live to apply changes to the database\n")
    else:
        print(f"\n✅ Restored {stats['restored']} episodes from SurgFirm!\n")

    client.close()
    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Restore lead_clinician from SurgFirm (force overwrite)')
    parser.add_argument('--database', default='impact', help='Database name (default: impact)')
    parser.add_argument('--live', action='store_true', help='Apply changes (default: dry run)')
    args = parser.parse_args()

    try:
        stats = restore_lead_clinician(
            db_name=args.database,
            dry_run=not args.live
        )
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        raise
