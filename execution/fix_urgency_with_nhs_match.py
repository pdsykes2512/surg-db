#!/usr/bin/env python3
"""
Fix urgency field in treatments by joining CSV data using NHS numbers
Similar approach to outcomes migration - join surgeries and patients CSVs
"""

import os
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
from dateutil import parser

def map_urgency(mode_op):
    """Map ModeOp field to urgency"""
    if pd.isna(mode_op):
        return None
    val = str(mode_op).lower()
    if 'elective' in val or val.startswith('1'):
        return 'elective'
    elif 'urgent' in val or val.startswith('3'):
        return 'urgent'
    elif 'emergency' in val or val.startswith('4'):
        return 'emergency'
    elif 'scheduled' in val or val.startswith('2'):
        return 'elective'
    return None

def fix_urgency_with_nhs():
    """Update treatment urgency using NHS number matching"""
    
    # Connect to MongoDB
    mongo_uri = os.getenv('MONGODB_URI', 'mongodb://admin:admin123@localhost:27017')
    client = MongoClient(mongo_uri)
    db = client.surgdb
    
    treatments_collection = db.treatments
    patients_collection = db.patients
    
    print("FIXING URGENCY WITH NHS NUMBER MATCHING")
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
    
    # Process merged data and build treatment lookup
    print("\nBuilding treatment lookup by patient + date + urgency...")
    treatment_lookup = {}
    matched_count = 0
    null_urgency_count = 0
    
    for _, row in merged_df.iterrows():
        nhs_no = row.get('NHS_No')
        surgery_date = row.get('Surgery')
        mode_op = row.get('ModeOp')
        
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
                    
                    # Get urgency
                    urgency = map_urgency(mode_op)
                    
                    if urgency:
                        key = f"{patient_id}_{date_str}"
                        treatment_lookup[key] = urgency
                        matched_count += 1
                    else:
                        null_urgency_count += 1
            except:
                pass
    
    print(f"Successfully matched {matched_count} records with urgency")
    print(f"Matched but no urgency in CSV: {null_urgency_count}")
    
    # Check ModeOp distribution in matched records
    print("\nModeOp distribution in matched records:")
    matched_records = merged_df[merged_df['NHS_No'].notna() & merged_df['Date_Th'].notna()]
    mode_counts = matched_records['ModeOp'].value_counts()
    for mode, count in mode_counts.head(10).items():
        pct = (count / len(matched_records)) * 100
        urgency = map_urgency(mode)
        print(f"  {mode}: {count} ({pct:.1f}%) -> {urgency}")
    
    # Update treatments
    print("\n" + "="*80)
    print("Updating treatments...")
    print("="*80)
    
    updated = 0
    not_found = 0
    already_correct = 0
    no_date = 0
    
    all_treatments = list(treatments_collection.find({"treatment_type": "surgery"}))
    print(f"\nFound {len(all_treatments)} surgical treatments")
    
    for treatment in all_treatments:
        patient_id = treatment.get('patient_id')
        treatment_date = treatment.get('treatment_date')
        current_urgency = treatment.get('urgency')
        
        if not treatment_date:
            no_date += 1
            continue
        
        if not patient_id:
            not_found += 1
            continue
        
        # Build key
        key = f"{patient_id}_{treatment_date}"
        new_urgency = treatment_lookup.get(key)
        
        if new_urgency is None:
            not_found += 1
            continue
        
        if current_urgency == new_urgency:
            already_correct += 1
            continue
        
        # Update the treatment
        treatments_collection.update_one(
            {"_id": treatment["_id"]},
            {
                "$set": {
                    "urgency": new_urgency,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        updated += 1
        
        if updated % 500 == 0:
            print(f"  Updated {updated} treatments...")
    
    print("\n" + "="*80)
    print("SUMMARY:")
    print("="*80)
    print(f"Total treatments: {len(all_treatments)}")
    print(f"Updated: {updated}")
    print(f"Already correct: {already_correct}")
    print(f"No treatment date: {no_date}")
    print(f"Not found in CSV: {not_found}")
    
    # Verify the results
    print("\n" + "="*80)
    print("VERIFICATION - Database urgency distribution:")
    print("="*80)
    
    urgency_counts = {}
    for t in treatments_collection.find({"treatment_type": "surgery"}):
        urgency = t.get('urgency', 'unknown')
        urgency_counts[urgency] = urgency_counts.get(urgency, 0) + 1
    
    total = sum(urgency_counts.values())
    for urgency, count in sorted(urgency_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total) * 100
        print(f"  {urgency}: {count} ({pct:.1f}%)")

if __name__ == "__main__":
    fix_urgency_with_nhs()
