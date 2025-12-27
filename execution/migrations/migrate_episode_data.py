#!/usr/bin/env python3
"""
Migrate episode-level data from Access database to MongoDB.

This script migrates:
- CNS involved dates (from tblSurgery - 1,127 records)
- First seen dates (from tblTumour Dt_Diag - 8,085 records)
- MDT discussion dates (from tblWaitingTimes - 4 records only)
- Referral sources (from tblWaitingTimes - 4 records only)
- Sets mdt_meeting_type='colorectal mdt' for records with MDT dates

Data sources:
- ~/.tmp/surgery_mdt_referral_export.csv (7,957 records from tblSurgery)
- ~/.tmp/tumour_export.csv (8,088 records from tblTumour)
- ~/.tmp/waiting_times_export.csv (4 records from tblWaitingTimes)

Matching strategy:
- Match by hospital number (Hosp_No in Access → mrn in MongoDB patients)
- For each matched patient, update ALL their episodes with the data
"""

import pandas as pd
import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.config import settings
from datetime import datetime

# Referral source code mappings (common NHS codes)
REFERRAL_SOURCE_MAP = {
    "01": "GP",
    "02": "Consultant",
    "03": "GP",
    "04": "Other",
    "05": "Self",
    "06": "Emergency",
    "07": "Screening",
    "08": "Other",
    "09": "Other",
    "10": "Transfer",
    "99": "Unknown"
}

def parse_access_date(date_str):
    """Parse Access database date format MM/DD/YY HH:MM:SS"""
    if pd.isna(date_str) or date_str == '':
        return None
    try:
        # Try parsing the date
        dt = pd.to_datetime(date_str, format='%m/%d/%y %H:%M:%S')
        return dt.strftime('%Y-%m-%d')
    except:
        try:
            # Try without time
            dt = pd.to_datetime(date_str, format='%m/%d/%y')
            return dt.strftime('%Y-%m-%d')
        except:
            print(f"Warning: Could not parse date: {date_str}")
            return None

async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Migrate episode data from Access to MongoDB')
    parser.add_argument('--confirm', action='store_true', help='Actually perform the migration')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without making changes')
    args = parser.parse_args()
    
    if not args.confirm and not args.dry_run:
        print("ERROR: Must specify --confirm to perform migration or --dry-run to preview")
        sys.exit(1)
    
    # Load data files
    print("Loading data from Access database exports...")
    surgery_csv = os.path.expanduser('~/.tmp/surgery_mdt_referral_export.csv')
    tumour_csv = os.path.expanduser('~/.tmp/tumour_export.csv')
    waiting_csv = os.path.expanduser('~/.tmp/waiting_times_export.csv')
    patient_csv = os.path.expanduser('~/.tmp/patient_export.csv')
    
    if not os.path.exists(surgery_csv):
        print(f"ERROR: {surgery_csv} not found. Run: mdb-export /root/surg-db/acpdb/acpdata_v3_db.mdb tblSurgery > {surgery_csv}")
        sys.exit(1)
    
    if not os.path.exists(tumour_csv):
        print(f"ERROR: {tumour_csv} not found. Run: mdb-export /root/surg-db/acpdb/acpdata_v3_db.mdb tblTumour > {tumour_csv}")
        sys.exit(1)
    
    if not os.path.exists(waiting_csv):
        print(f"ERROR: {waiting_csv} not found. Run: mdb-export /root/surg-db/acpdb/acpdata_v3_db.mdb tblWaitingTimes > {waiting_csv}")
        sys.exit(1)
    
    if not os.path.exists(patient_csv):
        print(f"ERROR: {patient_csv} not found. Run: mdb-export /root/surg-db/acpdb/acpdata_v3_db.mdb tblPatient > {patient_csv}")
        sys.exit(1)
    
    surgery_df = pd.read_csv(surgery_csv, dtype={'Hosp_No': str})
    tumour_df = pd.read_csv(tumour_csv, dtype={'Hosp_No': str})
    waiting_df = pd.read_csv(waiting_csv, dtype={'Hosp_No': str, 'Source': str})
    patient_df = pd.read_csv(patient_csv, dtype={'Hosp_No': str, 'PAS_No': str})
    
    print(f"Loaded {len(surgery_df)} records from tblSurgery")
    print(f"Loaded {len(tumour_df)} records from tblTumour")
    print(f"Loaded {len(waiting_df)} records from tblWaitingTimes")
    print(f"Loaded {len(patient_df)} records from tblPatient")
    
    # Build Hosp_No to PAS_No mapping from tblPatient
    print("\nBuilding hospital number mappings...")
    hosp_to_pas = {}
    for _, row in patient_df.iterrows():
        hosp_no = str(row.get('Hosp_No', '')).lower().strip()
        pas_no = str(row.get('PAS_No', '')).strip()
        if hosp_no and pas_no and pas_no != 'nan':
            hosp_to_pas[hosp_no] = pas_no
    print(f"Built mapping for {len(hosp_to_pas)} hospital numbers")
    
    # Connect to MongoDB
    print("\nConnecting to MongoDB...")
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]
    episodes_collection = db.episodes
    patients_collection = db.patients
    
    # Build patient lookup
    print("\nBuilding patient lookup...")
    patients = await patients_collection.find({}, {'patient_id': 1, 'mrn': 1}).to_list(length=None)
    patient_mrn_to_id = {p['mrn'].lower().strip(): p['patient_id'] 
                         for p in patients if 'mrn' in p and p.get('mrn')}
    
    # Get all episodes
    print("Loading all episodes...")
    all_episodes = await episodes_collection.find({}, {'episode_id': 1, 'patient_id': 1}).to_list(length=None)
    episode_by_patient = {}
    for ep in all_episodes:
        patient_id = ep.get('patient_id')
        if patient_id:
            if patient_id not in episode_by_patient:
                episode_by_patient[patient_id] = []
            episode_by_patient[patient_id].append(ep)
    
    print(f"Found {len(all_episodes)} episodes across {len(episode_by_patient)} patients")
    
    # Process updates
    updates_applied = 0
    patients_matched = 0
    episodes_updated = 0
    cns_dates_added = 0
    mdt_dates_added = 0
    first_seen_added = 0
    referral_source_added = 0
    
    # Process surgery data (CNS dates)
    print("\n=== Processing CNS dates from tblSurgery ===")
    surgery_with_cns = surgery_df[surgery_df['CNS_date'].notna()].copy()
    print(f"Found {len(surgery_with_cns)} records with CNS dates")
    
    for idx, row in surgery_with_cns.iterrows():
        hosp_no = str(row['Hosp_No']).lower().strip()
        
        # Look up PAS number first
        pas_no = hosp_to_pas.get(hosp_no)
        if not pas_no:
            continue
        
        # Look up patient by PAS number (MRN)
        patient_id = patient_mrn_to_id.get(pas_no)
        if not patient_id:
            continue
        
        patients_matched += 1
        patient_episodes = episode_by_patient.get(patient_id, [])
        
        if not patient_episodes:
            continue
        
        # Parse CNS date
        cns_date = parse_access_date(row['CNS_date'])
        if not cns_date:
            continue
        
        # Update all episodes for this patient
        for ep in patient_episodes:
            episode_id = ep['episode_id']
            
            update_data = {
                'cns_involved': cns_date
            }
            
            if args.confirm:
                result = await episodes_collection.update_one(
                    {'episode_id': episode_id},
                    {'$set': update_data}
                )
                if result.modified_count > 0:
                    episodes_updated += 1
                    cns_dates_added += 1
            else:
                print(f"  Would update episode {episode_id} with CNS date: {cns_date}")
                episodes_updated += 1
                cns_dates_added += 1
    
    print(f"Matched {patients_matched} patients with CNS dates")
    print(f"Updated {episodes_updated} episodes with CNS dates")
    
    # Process tumour data (first seen date from Dt_Diag)
    print("\n=== Processing first seen dates from tblTumour ===")
    tumour_with_diag = tumour_df[tumour_df['Dt_Diag'].notna()].copy()
    print(f"Found {len(tumour_with_diag)} records with diagnosis dates")
    
    patients_matched_tumour = 0
    episodes_updated_tumour = 0
    
    for idx, row in tumour_with_diag.iterrows():
        hosp_no = str(row['Hosp_No']).lower().strip()
        
        # Look up PAS number first
        pas_no = hosp_to_pas.get(hosp_no)
        if not pas_no:
            continue
        
        # Look up patient by PAS number (MRN)
        patient_id = patient_mrn_to_id.get(pas_no)
        if not patient_id:
            continue
        
        patients_matched_tumour += 1
        patient_episodes = episode_by_patient.get(patient_id, [])
        
        if not patient_episodes:
            continue
        
        # Parse diagnosis date as first seen date
        first_seen = parse_access_date(row['Dt_Diag'])
        if not first_seen:
            continue
        
        # Update all episodes for this patient
        for ep in patient_episodes:
            episode_id = ep['episode_id']
            
            update_data = {
                'first_seen_date': first_seen
            }
            
            if args.confirm:
                result = await episodes_collection.update_one(
                    {'episode_id': episode_id},
                    {'$set': update_data}
                )
                if result.modified_count > 0:
                    episodes_updated_tumour += 1
                    first_seen_added += 1
            else:
                if idx < 20:  # Only print first 20 in dry-run
                    print(f"  Would update episode {episode_id} with first seen date: {first_seen}")
                episodes_updated_tumour += 1
                first_seen_added += 1
    
    print(f"Matched {patients_matched_tumour} patients with diagnosis dates")
    print(f"Updated {episodes_updated_tumour} episodes with first seen dates")
    
    # Process waiting times data (MDT and referral)
    print("\n=== Processing MDT and referral data from tblWaitingTimes ===")
    patients_matched_wt = 0
    episodes_updated_wt = 0
    
    for idx, row in waiting_df.iterrows():
        hosp_no = str(row['Hosp_No']).lower().strip()
        
        # Look up patient
        patient_id = patient_mrn_to_id.get(hosp_no)
        if not patient_id:
            print(f"  No match for hospital number: {hosp_no}")
            continue
        
        patients_matched_wt += 1
        patient_episodes = episode_by_patient.get(patient_id, [])
        
        if not patient_episodes:
            print(f"  Patient {patient_id} has no episodes")
            continue
        
        # Build update data
        update_data = {}
        
        # MDT date
        mdt_date = parse_access_date(row.get('MDT_Date'))
        if mdt_date:
            update_data['mdt_discussion_date'] = mdt_date
            update_data['mdt_meeting_type'] = 'colorectal mdt'
        
        # Referral source
        source_code = str(row.get('Source', '')).strip()
        if source_code and source_code in REFERRAL_SOURCE_MAP:
            update_data['referral_source'] = REFERRAL_SOURCE_MAP[source_code]
        
        if not update_data:
            continue
        
        # Update all episodes for this patient
        for ep in patient_episodes:
            episode_id = ep['episode_id']
            
            if args.confirm:
                result = await episodes_collection.update_one(
                    {'episode_id': episode_id},
                    {'$set': update_data}
                )
                if result.modified_count > 0:
                    episodes_updated_wt += 1
                    if 'mdt_discussion_date' in update_data:
                        mdt_dates_added += 1
                    if 'referral_source' in update_data:
                        referral_source_added += 1
            else:
                print(f"  Would update episode {episode_id} with: {update_data}")
                episodes_updated_wt += 1
                if 'mdt_discussion_date' in update_data:
                    mdt_dates_added += 1
                if 'referral_source' in update_data:
                    referral_source_added += 1
    
    print(f"Matched {patients_matched_wt} patients from waiting times table")
    print(f"Updated {episodes_updated_wt} episodes with MDT/referral data")
    
    # Summary
    print("\n" + "="*60)
    print("MIGRATION SUMMARY")
    print("="*60)
    print(f"CNS dates added: {cns_dates_added}")
    print(f"MDT dates added: {mdt_dates_added}")
    print(f"First seen dates added: {first_seen_added}")
    print(f"Referral sources added: {referral_source_added}")
    print(f"Total episodes updated: {episodes_updated + episodes_updated_tumour + episodes_updated_wt}")
    
    if args.dry_run:
        print("\nDRY RUN - No changes were made to the database")
        print("Run with --confirm to apply these changes")
    elif args.confirm:
        print("\nChanges have been applied to the database")
        
        # Show sample of updated records
        print("\nSample of updated records:")
        sample = await episodes_collection.find(
            {'$or': [
                {'cns_involved': {'$exists': True}},
                {'mdt_discussion_date': {'$exists': True}},
                {'first_seen_date': {'$exists': True}}
            ]},
            {'episode_id': 1, 'cns_involved': 1, 'mdt_discussion_date': 1, 
             'first_seen_date': 1, 'referral_source': 1}
        ).limit(5).to_list(length=None)
        
        for rec in sample:
            print(f"  Episode {rec['episode_id']}:")
            if rec.get('cns_involved'):
                print(f"    CNS involved: {rec['cns_involved']}")
            if rec.get('mdt_discussion_date'):
                print(f"    MDT date: {rec['mdt_discussion_date']}")
            if rec.get('first_seen_date'):
                print(f"    First seen: {rec['first_seen_date']}")
            if rec.get('referral_source'):
                print(f"    Referral: {rec['referral_source']}")

if __name__ == '__main__':
    asyncio.run(main())
