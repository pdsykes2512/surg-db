#!/usr/bin/env python3
"""
Fix treatment dates in the database using the Surgery date field from CSV.

The Surgery field is the accurate surgery date (76.6% populated) and should be
used as the treatment_date in the database. This fixes date mismatches where
the database has incorrect or missing dates.
"""

import pandas as pd
from pymongo import MongoClient
from dateutil import parser
from datetime import datetime

def main():
    # MongoDB connection
    client = MongoClient('mongodb://admin:admin123@localhost:27017')
    db = client.surgdb
    treatments_collection = db.treatments
    patients_collection = db.patients
    
    print("FIXING TREATMENT DATES WITH NHS NUMBER MATCHING")
    print("="*80)
    
    # Read CSVs
    print("\nLoading CSV files...")
    surgeries_df = pd.read_csv('surgeries_export_new.csv')
    patients_df = pd.read_csv('patients_export_new.csv')
    
    print(f"Surgeries CSV: {len(surgeries_df)} records")
    print(f"Patients CSV: {len(patients_df)} records")
    
    # Join surgeries with patients on Hosp_No to get NHS_No
    print("\nJoining CSVs on Hosp_No...")
    merged_df = surgeries_df.merge(
        patients_df[['Hosp_No', 'NHS_No', 'PAS_No']], 
        on='Hosp_No', 
        how='left'
    )
    
    print(f"Merged records: {len(merged_df)}")
    print(f"Records with NHS_No: {merged_df['NHS_No'].notna().sum()}")
    print(f"Records with Surgery date: {merged_df['Surgery'].notna().sum()}")
    print(f"Records with both NHS_No and Surgery: {(merged_df['NHS_No'].notna() & merged_df['Surgery'].notna()).sum()}")
    
    # Build NHS number to patient_id lookup from database
    print("\nBuilding NHS number lookup from database...")
    nhs_to_patient = {}
    for patient in patients_collection.find({"nhs_number": {"$exists": True, "$ne": None}}):
        nhs_num = patient.get('nhs_number')
        patient_id = patient.get('patient_id')
        if nhs_num and patient_id:
            # Convert NHS number to int for consistent matching
            try:
                nhs_int = int(nhs_num)
                nhs_to_patient[nhs_int] = patient_id
            except:
                pass
    
    print(f"Built lookup with {len(nhs_to_patient)} NHS numbers")
    
    # Build patient_id to treatments lookup (for patients with single treatment)
    print("\nBuilding patient treatments lookup...")
    patient_treatments = {}
    for treatment in treatments_collection.find({}, {'patient_id': 1, 'treatment_date': 1}):
        patient_id = treatment.get('patient_id')
        if patient_id:
            if patient_id not in patient_treatments:
                patient_treatments[patient_id] = []
            patient_treatments[patient_id].append({
                '_id': treatment['_id'],
                'treatment_date': treatment.get('treatment_date')
            })
    
    print(f"Found treatments for {len(patient_treatments)} patients")
    
    # Process merged data and build date updates
    print("\nBuilding treatment date updates...")
    updates = []
    
    for _, row in merged_df.iterrows():
        nhs_no = row.get('NHS_No')
        surgery_date = row.get('Surgery')
        
        if pd.notna(nhs_no) and pd.notna(surgery_date):
            try:
                # Convert NHS number to int
                nhs_int = int(nhs_no)
                
                # Get patient_id from NHS number
                patient_id = nhs_to_patient.get(nhs_int)
                
                if patient_id:
                    # Parse date
                    parsed_date = parser.parse(str(surgery_date))
                    date_str = parsed_date.strftime('%Y-%m-%d')
                    
                    # Get treatments for this patient
                    patient_tx = patient_treatments.get(patient_id, [])
                    
                    if len(patient_tx) == 1:
                        # Single treatment - update it
                        updates.append({
                            'treatment_id': patient_tx[0]['_id'],
                            'old_date': patient_tx[0]['treatment_date'],
                            'new_date': date_str,
                            'patient_id': patient_id
                        })
                    elif len(patient_tx) > 1:
                        # Multiple treatments - try to match by existing date
                        # If existing date is within 90 days of CSV date, update it
                        for tx in patient_tx:
                            existing_date = tx.get('treatment_date')
                            if existing_date:
                                try:
                                    existing_dt = datetime.strptime(existing_date, '%Y-%m-%d')
                                    csv_dt = parsed_date
                                    days_diff = abs((existing_dt - csv_dt).days)
                                    if days_diff <= 90:  # Within 3 months
                                        updates.append({
                                            'treatment_id': tx['_id'],
                                            'old_date': existing_date,
                                            'new_date': date_str,
                                            'patient_id': patient_id
                                        })
                                        break
                                except:
                                    pass
                            else:
                                # No existing date, use the first treatment
                                updates.append({
                                    'treatment_id': tx['_id'],
                                    'old_date': None,
                                    'new_date': date_str,
                                    'patient_id': patient_id
                                })
                                break
                    
            except Exception as e:
                continue
    
    print(f"Found {len(updates)} treatment dates to update")
    
    # Show sample updates
    if updates:
        print("\nSample updates:")
        print("-" * 80)
        for i, update in enumerate(updates[:10]):
            print(f"{i+1}. Patient {update['patient_id']}: {update['old_date']} -> {update['new_date']}")
    
    # Perform updates
    print("\n" + "="*80)
    print("Updating treatment dates...")
    print("="*80 + "\n")
    
    updated_count = 0
    same_count = 0
    new_date_count = 0
    
    for i, update in enumerate(updates):
        old_date = update['old_date']
        new_date = update['new_date']
        
        if old_date == new_date:
            same_count += 1
        elif old_date is None:
            new_date_count += 1
        else:
            updated_count += 1
        
        # Update the treatment
        treatments_collection.update_one(
            {'_id': update['treatment_id']},
            {
                '$set': {
                    'treatment_date': new_date,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        if (i + 1) % 500 == 0:
            print(f"  Processed {i + 1} treatments...")
    
    print("\n" + "="*80)
    print("SUMMARY:")
    print("="*80)
    print(f"Total updates processed: {len(updates)}")
    print(f"Dates changed: {updated_count}")
    print(f"Dates added (was None): {new_date_count}")
    print(f"Already correct: {same_count}")
    
    # Verify
    print("\n" + "="*80)
    print("VERIFICATION - Treatment dates populated:")
    print("="*80)
    total_treatments = treatments_collection.count_documents({})
    with_dates = treatments_collection.count_documents({'treatment_date': {'$exists': True, '$ne': None}})
    without_dates = total_treatments - with_dates
    
    print(f"Total treatments: {total_treatments}")
    print(f"  With dates: {with_dates} ({with_dates/total_treatments*100:.1f}%)")
    print(f"  Without dates: {without_dates} ({without_dates/total_treatments*100:.1f}%)")

if __name__ == '__main__':
    main()
