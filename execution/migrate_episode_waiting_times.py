#!/usr/bin/env python3
"""
Migrate episode data from Access database tblWaitingTimes table
- MDT discussion date
- First seen date  
- Referral source
- Set MDT meeting type to 'colorectal mdt' for all
"""

import pandas as pd
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database import Database
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

async def migrate_waiting_times():
    """Migrate waiting times data to episodes collection"""
    
    # Connect to MongoDB using backend database connection
    await Database.connect_db()
    db = Database.get_database()
    
    # Load CSV export from Access database
    print("Loading waiting times data from Access database export...")
    csv_path = os.path.expanduser('~/.tmp/waiting_times_export.csv')
    df = pd.read_csv(csv_path, dtype={'Hosp_No': str, 'Source': str})
    print(f"Loaded {len(df)} waiting times records")
    
    # Get all episodes to build hospital number lookup
    print("\nBuilding hospital number to episode ID mapping...")
    all_episodes = await episodes_collection.find({}, {'episode_id': 1, 'patient_id': 1}).to_list(length=None)
    
    # Get collections
    episodes_collection = db.episodes
    patients_collection = db.patients
    
    # Get all episodes to build hospital number lookup
    print("\nBuilding hospital number to episode ID mapping...")
    all_episodes = await episodes_collection.find({}, {'episode_id': 1, 'patient_id': 1}).to_list(length=None)
    
    # Get all patients to build MRN to patient ID mapping
    patients = await patients_collection.find({}, {'patient_id': 1, 'mrn': 1}).to_list(length=None)
    patient_mrn_to_id = {p['mrn']: p['patient_id'] for p in patients if 'mrn' in p}
    
    # Build episode lookup by patient_id (since we need to match by hospital number)
    episode_by_patient = {}
    for ep in all_episodes:
        patient_id = ep.get('patient_id')
        if patient_id:
            if patient_id not in episode_by_patient:
                episode_by_patient[patient_id] = []
            episode_by_patient[patient_id].append(ep)
    
    print(f"Found {len(all_episodes)} episodes across {len(episode_by_patient)} patients")
    
    # Process records
    updated_count = 0
    skipped_no_match = 0
    skipped_no_data = 0
    
    for idx, row in df.iterrows():
        hosp_no = str(row['Hosp_No']).strip().upper() if pd.notna(row['Hosp_No']) else None
        if not hosp_no:
            skipped_no_data += 1
            continue
        
        # Try to find matching patient by MRN (hospital number)
        patient_id = patient_mrn_to_id.get(hosp_no)
        if not patient_id or patient_id not in episode_by_patient:
            skipped_no_match += 1
            continue
        
        # Get episodes for this patient - usually just one, but could be multiple
        patient_episodes = episode_by_patient[patient_id]
        
        # Prepare update data
        update_data = {}
        
        # MDT discussion date
        mdt_date = row['MDT_Date']
        if pd.notna(mdt_date) and mdt_date:
            try:
                # Handle various date formats from Access
                if isinstance(mdt_date, str):
                    # Parse date like "01/07/05 00:00:00"
                    mdt_dt = pd.to_datetime(mdt_date, format='%m/%d/%y %H:%M:%S', errors='coerce')
                    if pd.notna(mdt_dt):
                        update_data['mdt_discussion_date'] = mdt_dt.strftime('%Y-%m-%d')
                        update_data['mdt_meeting_type'] = 'colorectal mdt'
            except Exception as e:
                print(f"  Warning: Could not parse MDT date '{mdt_date}': {e}")
        
        # First seen date
        fs_date = row['FS_Date']
        if pd.notna(fs_date) and fs_date:
            try:
                if isinstance(fs_date, str):
                    fs_dt = pd.to_datetime(fs_date, format='%m/%d/%y %H:%M:%S', errors='coerce')
                    if pd.notna(fs_dt):
                        update_data['first_seen_date'] = fs_dt.strftime('%Y-%m-%d')
            except Exception as e:
                print(f"  Warning: Could not parse first seen date '{fs_date}': {e}")
        
        # Referral source
        source_code = str(row['Source']).strip() if pd.notna(row['Source']) else None
        if source_code:
            referral_source = REFERRAL_SOURCE_MAP.get(source_code, f"Code {source_code}")
            update_data['referral_source'] = referral_source
        
        # If we have any data to update, apply it to all episodes for this patient
        if update_data:
            update_data['last_modified_at'] = datetime.utcnow()
            
            for episode in patient_episodes:
                episode_id = episode['episode_id']
                result = await episodes_collection.update_one(
                    {'episode_id': episode_id},
                    {'$set': update_data}
                )
                
                if result.modified_count > 0:
                    updated_count += 1
                    if updated_count % 100 == 0:
                        print(f"  Updated {updated_count} episodes...")
        else:
            skipped_no_data += 1
    
    print(f"\nMigration complete!")
    print(f"  Episodes updated: {updated_count}")
    print(f"  Skipped (no matching patient): {skipped_no_match}")
    print(f"  Skipped (no data to update): {skipped_no_data}")
    
    # Show sample of updated data
    print("\nSample of updated episodes:")
    sample = await episodes_collection.find(
        {'mdt_discussion_date': {'$exists': True}},
        {'episode_id': 1, 'mdt_discussion_date': 1, 'first_seen_date': 1, 'referral_source': 1}
    ).limit(5).to_list(length=5)
    
    for ep in sample:
        print(f"  {ep.get('episode_id')}: MDT={ep.get('mdt_discussion_date')}, FS={ep.get('first_seen_date')}, Ref={ep.get('referral_source')}")
    
    client.close()

if __name__ == '__main__':
    if '--confirm' not in sys.argv:
        print("This script will update episode records with waiting times data.")
        print("Run with --confirm to proceed.")
        sys.exit(0)
    
    asyncio.run(migrate_waiting_times())
