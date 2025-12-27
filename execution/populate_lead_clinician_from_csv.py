#!/usr/bin/env python3
"""
Populate missing lead_clinician fields by matching episodes to CSV surgeries.
Uses patient ID and date proximity to find matching surgeries.
"""

import pandas as pd
from pymongo import MongoClient
from datetime import datetime, timedelta
from dateutil import parser

def main():
    # MongoDB connection
    client = MongoClient('mongodb://admin:admin123@localhost:27017')
    db = client.surgdb
    
    print("POPULATING LEAD CLINICIANS FROM CSV")
    print("=" * 80)
    
    # Load CSV files
    print("\n1. Loading CSV files...")
    surgeries_df = pd.read_csv('~/.tmp/surgery_mdt_referral_export.csv')
    patients_df = pd.read_csv('~/.tmp/patient_export.csv')
    print(f"   Surgeries CSV: {len(surgeries_df)} records")
    print(f"   Patients CSV: {len(patients_df)} records")
    
    # Build Hosp_No to patient_id lookup via PAS_No -> mrn mapping
    print("\n2. Building patient lookup...")
    
    # First build PAS_No (MRN in MongoDB) to patient_id
    mrn_to_patient = {}
    for patient in db.patients.find({'mrn': {'$exists': True}}):
        mrn = patient.get('mrn')
        patient_id = patient.get('patient_id')
        if mrn and patient_id:
            mrn_to_patient[str(mrn)] = patient_id
    
    # Then map Hosp_No -> PAS_No -> patient_id using patient CSV
    hosp_to_patient = {}
    for _, row in patients_df.iterrows():
        hosp_no = str(row.get('Hosp_No', '')).strip()
        pas_no = str(row.get('PAS_No', '')).strip()
        
        if hosp_no and pas_no:
            patient_id = mrn_to_patient.get(pas_no)
            if patient_id:
                hosp_to_patient[hosp_no] = patient_id
    
    print(f"   Built lookup with {len(hosp_to_patient)} Hosp_No -> patient_id mappings")
    
    # Build CSV lookup: patient_id -> list of surgeries with surgeon and date
    print("\n3. Building CSV surgery lookup...")
    patient_surgeries = {}
    
    for _, row in surgeries_df.iterrows():
        hosp_no = str(row.get('Hosp_No', '')).strip()
        surgery_date = row.get('Surgery')
        surgeon = row.get('Surgeon')
        
        if hosp_no and pd.notna(surgery_date) and pd.notna(surgeon):
            patient_id = hosp_to_patient.get(hosp_no)
            if patient_id:
                try:
                    parsed_date = parser.parse(str(surgery_date))
                    
                    if patient_id not in patient_surgeries:
                        patient_surgeries[patient_id] = []
                    
                    patient_surgeries[patient_id].append({
                        'date': parsed_date,
                        'surgeon': str(surgeon).strip()
                    })
                except:
                    pass
    
    print(f"   Mapped {len(patient_surgeries)} patients with surgeries")
    total_surgeries = sum(len(v) for v in patient_surgeries.values())
    print(f"   Total surgeries: {total_surgeries}")
    
    # Find episodes without lead_clinician
    print("\n4. Finding episodes without lead clinician...")
    episodes_to_update = list(db.episodes.find({
        '$or': [
            {'lead_clinician': None},
            {'lead_clinician': ''},
            {'lead_clinician': {'$exists': False}}
        ]
    }))
    
    print(f"   Found {len(episodes_to_update)} episodes without lead clinician")
    
    # Process updates
    print("\n5. Processing updates...")
    updated = 0
    no_surgeries = 0
    no_match = 0
    
    for episode in episodes_to_update:
        episode_id = episode.get('episode_id')
        patient_id = episode.get('patient_id')
        referral_date = episode.get('referral_date')
        first_seen_date = episode.get('first_seen_date')
        
        if not patient_id:
            continue
        
        # Get surgeries for this patient
        surgeries = patient_surgeries.get(patient_id, [])
        
        if not surgeries:
            no_surgeries += 1
            continue
        
        # Try to match based on dates
        surgeon_name = None
        
        # Strategy 1: Use referral date
        if referral_date and surgeries:
            try:
                ref_date = parser.parse(referral_date)
                # Find surgery closest to referral (typically after referral)
                closest = min(surgeries, key=lambda s: abs((s['date'] - ref_date).days))
                if abs((closest['date'] - ref_date).days) <= 365:  # Within 1 year
                    surgeon_name = closest['surgeon']
            except:
                pass
        
        # Strategy 2: Use first seen date
        if not surgeon_name and first_seen_date:
            try:
                first_date = parser.parse(first_seen_date)
                closest = min(surgeries, key=lambda s: abs((s['date'] - first_date).days))
                if abs((closest['date'] - first_date).days) <= 365:
                    surgeon_name = closest['surgeon']
            except:
                pass
        
        # Strategy 3: Just use the first surgery for this patient
        if not surgeon_name and surgeries:
            surgeon_name = surgeries[0]['surgeon']
        
        if surgeon_name:
            db.episodes.update_one(
                {'episode_id': episode_id},
                {'$set': {'lead_clinician': surgeon_name}}
            )
            updated += 1
            
            if updated % 500 == 0:
                print(f"   Updated {updated} episodes...")
        else:
            no_match += 1
    
    print(f"\n   Final update count: {updated}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    print(f"Total episodes processed: {len(episodes_to_update)}")
    print(f"Successfully updated: {updated}")
    print(f"No surgeries found for patient: {no_surgeries}")
    print(f"Could not match: {no_match}")
    
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
    
    # Show some statistics
    completeness = ((7957 - remaining) / 7957 * 100) if remaining < 7957 else 0
    print(f"Lead clinician completeness: {completeness:.1f}%")

if __name__ == '__main__':
    main()
