#!/usr/bin/env python3
"""
Fix urgency field in treatments by reading from the original CSV ModeOp field
"""

import os
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import hashlib

def generate_patient_id(hosp_no):
    """Generate consistent patient ID from hospital number"""
    return hashlib.md5(str(hosp_no).encode()).hexdigest()[:6].upper()

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

def fix_urgency():
    """Update treatment urgency from CSV data"""
    
    # Connect to MongoDB
    mongo_uri = os.getenv('MONGODB_URI', 'mongodb://admin:admin123@localhost:27017')
    client = MongoClient(mongo_uri)
    db = client.surgdb
    
    treatments_collection = db.treatments
    
    print("FIXING URGENCY FIELD FROM CSV")
    print("="*80)
    
    # Read CSV
    df = pd.read_csv('surgeries_export_new.csv')
    print(f"\nLoaded {len(df)} records from CSV")
    
    # Check ModeOp distribution
    print("\nModeOp distribution in CSV:")
    mode_counts = df['ModeOp'].value_counts()
    for mode, count in mode_counts.items():
        pct = (count / len(df)) * 100
        urgency = map_urgency(mode)
        print(f"  {mode}: {count} ({pct:.1f}%) -> {urgency}")
    
    print(f"\nNull ModeOp: {df['ModeOp'].isna().sum()}")
    
    # Build lookup by patient_id and Date_Th
    print("\nBuilding CSV lookup...")
    csv_lookup = {}
    for _, row in df.iterrows():
        hosp_no = row.get('Hosp_No')
        date_th = row.get('Date_Th')
        mode_op = row.get('ModeOp')
        
        if pd.notna(hosp_no) and pd.notna(date_th):
            patient_id = generate_patient_id(hosp_no)
            # Parse the date properly - CSV format is MM/DD/YY
            try:
                from dateutil import parser
                parsed_date = parser.parse(str(date_th))
                date_key = parsed_date.strftime('%Y-%m-%d')
                key = f"{patient_id}_{date_key}"
                csv_lookup[key] = map_urgency(mode_op)
            except:
                pass
    
    print(f"Built lookup with {len(csv_lookup)} entries")
    
    # Update treatments
    print("\nUpdating treatments...")
    updated = 0
    not_found = 0
    already_correct = 0
    null_urgency = 0
    
    all_treatments = list(treatments_collection.find({"treatment_type": "surgery"}))
    print(f"Found {len(all_treatments)} surgical treatments")
    
    for treatment in all_treatments:
        patient_id = treatment.get('patient_id')
        treatment_date = treatment.get('treatment_date')
        current_urgency = treatment.get('urgency')
        
        if not patient_id or not treatment_date:
            not_found += 1
            continue
        
        # Build key
        key = f"{patient_id}_{treatment_date}"
        new_urgency = csv_lookup.get(key)
        
        if new_urgency is None:
            null_urgency += 1
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
    print(f"CSV had null urgency: {null_urgency}")
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
    fix_urgency()
