#!/usr/bin/env python3
"""
Populate missing lead_clinician fields in episodes.

Strategy:
1. Check original CSV (surgery_mdt_referral_export.csv) for Surgeon field
2. Fall back to primary surgeon from treatments collection
3. Match surgeon names to clinicians in the database
"""

import pandas as pd
from pymongo import MongoClient
from datetime import datetime

def main():
    # MongoDB connection
    client = MongoClient('mongodb://admin:admin123@localhost:27017')
    db = client.surgdb
    
    print("POPULATING MISSING LEAD CLINICIANS")
    print("=" * 80)
    
    # Load CSV files
    print("\n1. Loading CSV files...")
    try:
        surgeries_df = pd.read_csv('~/.tmp/surgery_mdt_referral_export.csv')
        patients_df = pd.read_csv('~/.tmp/patient_export.csv')
        print(f"   Surgeries CSV: {len(surgeries_df)} records")
        print(f"   Patients CSV: {len(patients_df)} records")
    except FileNotFoundError:
        print("   CSV files not found in ~/.tmp/")
        print("   Trying local directory...")
        surgeries_df = pd.read_csv('surgery_mdt_referral_export.csv')
        patients_df = pd.read_csv('patient_export.csv')
        print(f"   Surgeries CSV: {len(surgeries_df)} records")
        print(f"   Patients CSV: {len(patients_df)} records")
    
    # Build NHS number to patient_id lookup
    print("\n2. Building patient lookup...")
    nhs_to_patient = {}
    for patient in db.patients.find({"nhs_number": {"$exists": True, "$ne": None}}):
        nhs_num = patient.get('nhs_number')
        patient_id = patient.get('patient_id')
        if nhs_num and patient_id:
            try:
                nhs_to_patient[int(nhs_num)] = patient_id
            except:
                pass
    print(f"   Built lookup with {len(nhs_to_patient)} NHS numbers")
    
    # Build clinician name lookup (both full name and surname)
    print("\n3. Building clinician lookup...")
    clinician_lookup = {}
    clinician_id_by_name = {}
    
    for clinician in db.clinicians.find({}):
        clinician_id = str(clinician['_id'])
        first_name = clinician.get('first_name', '')
        surname = clinician.get('surname', '')
        full_name = f"{first_name} {surname}".strip()
        
        # Store by various formats
        if full_name:
            clinician_lookup[full_name.lower()] = clinician_id
            clinician_id_by_name[full_name.lower()] = full_name
        if surname:
            clinician_lookup[surname.lower()] = clinician_id
            clinician_id_by_name[surname.lower()] = full_name
    
    print(f"   Found {len(set(clinician_lookup.values()))} clinicians")
    
    # Join surgeries with patients to get episode mapping
    print("\n4. Building CSV episode lookup...")
    merged_df = surgeries_df.merge(
        patients_df[['Hosp_No', 'NHS_No']], 
        on='Hosp_No', 
        how='left'
    )
    
    csv_episode_data = {}
    for _, row in merged_df.iterrows():
        nhs_no = row.get('NHS_No')
        surgery_date = row.get('Surgery')
        surgeon_name = row.get('Surgeon')
        
        if pd.notna(nhs_no) and pd.notna(surgery_date) and pd.notna(surgeon_name):
            try:
                nhs_int = int(nhs_no)
                patient_id = nhs_to_patient.get(nhs_int)
                
                if patient_id:
                    # Parse date
                    from dateutil import parser
                    parsed_date = parser.parse(str(surgery_date))
                    date_str = parsed_date.strftime('%Y-%m-%d')
                    
                    key = f"{patient_id}_{date_str}"
                    csv_episode_data[key] = surgeon_name.strip()
            except:
                continue
    
    print(f"   Mapped {len(csv_episode_data)} surgery records")
    
    # Find episodes without lead_clinician
    print("\n5. Finding episodes without lead clinician...")
    episodes_to_update = list(db.episodes.find({
        '$or': [
            {'lead_clinician': None},
            {'lead_clinician': ''},
            {'lead_clinician': {'$exists': False}}
        ]
    }))
    
    print(f"   Found {len(episodes_to_update)} episodes without lead clinician")
    
    # Process updates
    print("\n6. Processing updates...")
    updated_from_csv = 0
    updated_from_treatment = 0
    matched_to_clinician = 0
    not_matched = 0
    
    for episode in episodes_to_update:
        episode_id = episode.get('episode_id')
        patient_id = episode.get('patient_id')
        
        surgeon_name = None
        source = None
        
        # Strategy 1: Check CSV for surgeon name from surgery records
        if patient_id:
            # Get all treatments for this episode to find surgery dates
            treatment_ids = episode.get('treatment_ids', [])
            if treatment_ids:
                treatments = list(db.treatments.find({'treatment_id': {'$in': treatment_ids}}))
                
                for treatment in treatments:
                    treatment_date = treatment.get('treatment_date')
                    if treatment_date:
                        key = f"{patient_id}_{treatment_date}"
                        if key in csv_episode_data:
                            surgeon_name = csv_episode_data[key]
                            source = 'CSV'
                            updated_from_csv += 1
                            break
        
        # Strategy 2: Fall back to primary surgeon from first surgery treatment
        if not surgeon_name:
            if treatment_ids:
                surgery_treatments = list(db.treatments.find({
                    'treatment_id': {'$in': treatment_ids},
                    'treatment_type': 'surgery'
                }).sort('treatment_date', 1))
                
                if surgery_treatments:
                    first_surgery = surgery_treatments[0]
                    surgeon_id = first_surgery.get('surgeon')
                    
                    if surgeon_id and surgeon_id in clinician_id_by_name.values():
                        # Already a valid clinician ID
                        db.episodes.update_one(
                            {'episode_id': episode_id},
                            {'$set': {'lead_clinician': surgeon_id, 'updated_at': datetime.utcnow()}}
                        )
                        updated_from_treatment += 1
                        matched_to_clinician += 1
                        continue
                    elif surgeon_id:
                        # It's a name, try to match
                        surgeon_name = surgeon_id
                        source = 'Treatment'
                        updated_from_treatment += 1
        
        # Try to match surgeon name to clinician
        if surgeon_name:
            # Try exact match first
            surgeon_lower = surgeon_name.lower()
            clinician_id = clinician_lookup.get(surgeon_lower)
            
            # Try partial matches (surname only)
            if not clinician_id:
                parts = surgeon_name.split()
                if len(parts) > 1:
                    # Try last name
                    clinician_id = clinician_lookup.get(parts[-1].lower())
            
            if clinician_id:
                db.episodes.update_one(
                    {'episode_id': episode_id},
                    {'$set': {'lead_clinician': clinician_id, 'updated_at': datetime.utcnow()}}
                )
                matched_to_clinician += 1
            else:
                # Store the surgeon name directly if we can't match to clinician
                db.episodes.update_one(
                    {'episode_id': episode_id},
                    {'$set': {'lead_clinician': surgeon_name, 'updated_at': datetime.utcnow()}}
                )
                not_matched += 1
                if not_matched <= 10:
                    print(f"   Stored surgeon name (no clinician match): '{surgeon_name}' from {source}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    print(f"Total episodes processed: {len(episodes_to_update)}")
    print(f"Updated from CSV: {updated_from_csv}")
    print(f"Updated from Treatment: {updated_from_treatment}")
    print(f"Successfully matched to clinician: {matched_to_clinician}")
    print(f"Could not match: {not_matched}")
    
    # Verify final count
    remaining = db.episodes.count_documents({
        '$or': [
            {'lead_clinician': None},
            {'lead_clinician': ''},
            {'lead_clinician': {'$exists': False}}
        ]
    })
    
    print(f"\nRemaining episodes without lead clinician: {remaining}")
    print(f"Improvement: {len(episodes_to_update) - remaining} episodes now have lead clinician")

if __name__ == '__main__':
    main()
