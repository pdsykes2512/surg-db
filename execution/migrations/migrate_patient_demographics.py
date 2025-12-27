#!/usr/bin/env python3
"""
Migrate complete patient demographics and medical history from CSV
Includes: DOB, sex, postcode, BMI, height, weight, family history, death data
"""

import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import argparse
import hashlib

def connect_db():
    """Connect to MongoDB"""
    client = MongoClient('mongodb://admin:admin123@localhost:27017')
    return client.surgdb

def generate_patient_id(hosp_no):
    """Generate patient ID from hospital number"""
    return hashlib.md5(str(hosp_no).lower().encode()).hexdigest()[:6].upper()

def parse_date(date_str):
    """Parse date from CSV format"""
    if pd.isna(date_str):
        return None
    try:
        from dateutil import parser
        return parser.parse(str(date_str))
    except:
        return None

def migrate_patient_data(dry_run=False):
    """Migrate full patient demographics and medical history"""
    
    print("MIGRATING PATIENT DEMOGRAPHICS AND MEDICAL HISTORY")
    print("="*80)
    
    # Load CSV
    csv_path = '/root/surg-db/patients_export_new.csv'
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} patients from CSV")
    
    # Connect to database
    db = connect_db()
    patients = db.patients
    
    # Statistics
    stats = {
        'total_csv': len(df),
        'matched': 0,
        'not_found': 0,
        'dob_added': 0,
        'gender_added': 0,
        'postcode_added': 0,
        'bmi_added': 0,
        'height_added': 0,
        'weight_added': 0,
        'family_history_added': 0,
        'death_date_added': 0,
        'cause_of_death_added': 0,
    }
    
    print("\nProcessing patients...")
    for idx, row in df.iterrows():
        if idx % 1000 == 0:
            print(f"  Processed {idx}/{len(df)}...")
        
        # Generate patient_id
        hosp_no = row['Hosp_No']
        patient_id = generate_patient_id(hosp_no)
        
        # Find patient in database
        patient = patients.find_one({'patient_id': patient_id})
        
        if not patient:
            stats['not_found'] += 1
            continue
        
        stats['matched'] += 1
        
        # Build update document
        update = {'$set': {}}
        
        # Date of birth
        dob = parse_date(row.get('P_DOB'))
        if dob:
            update['$set']['demographics.date_of_birth'] = dob
            # Calculate age
            age = (datetime.now() - dob).days // 365
            update['$set']['demographics.age'] = age
            stats['dob_added'] += 1
        
        # Gender
        if pd.notna(row.get('Sex')):
            sex_value = str(row['Sex']).strip().upper()
            gender_map = {
                'M': 'male',
                'MALE': 'male',
                'F': 'female',
                'FEMALE': 'female',
                '1': 'male',
                '2': 'female'
            }
            gender = gender_map.get(sex_value, sex_value.lower())
            update['$set']['demographics.gender'] = gender
            stats['gender_added'] += 1
        
        # Postcode
        if pd.notna(row.get('Postcode')):
            update['$set']['demographics.postcode'] = str(row['Postcode']).strip()
            stats['postcode_added'] += 1
        
        # Height (cm)
        if pd.notna(row.get('Height')):
            try:
                height = float(row['Height'])
                if height > 0 and height < 300:  # Sanity check
                    update['$set']['demographics.height_cm'] = height
                    stats['height_added'] += 1
            except:
                pass
        
        # Weight (kg)
        if pd.notna(row.get('Weight')):
            try:
                weight = float(row['Weight'])
                if weight > 0 and weight < 500:  # Sanity check
                    update['$set']['demographics.weight_kg'] = weight
                    stats['weight_added'] += 1
            except:
                pass
        
        # BMI
        if pd.notna(row.get('BMI')):
            try:
                bmi = float(row['BMI'])
                if bmi > 0 and bmi < 100:  # Sanity check
                    update['$set']['demographics.bmi'] = round(bmi, 1)
                    stats['bmi_added'] += 1
            except:
                pass
        
        # Family history
        has_fam_hist = False
        if pd.notna(row.get('Fam_Hist')):
            fam_hist_val = str(row['Fam_Hist']).strip()
            if fam_hist_val in ['1', 'Yes', 'yes', 'YES', 'Y']:
                has_fam_hist = True
        
        if pd.notna(row.get('Fam_Hist_positive')):
            fam_hist_pos = str(row['Fam_Hist_positive']).strip()
            if fam_hist_pos in ['1', 'Yes', 'yes', 'YES', 'Y']:
                has_fam_hist = True
        
        if has_fam_hist:
            update['$set']['medical_history.family_history_colorectal_cancer'] = True
            stats['family_history_added'] += 1
        
        # Death information
        death_date = parse_date(row.get('DeathDat'))
        if death_date:
            update['$set']['deceased_date'] = death_date
            update['$set']['deceased'] = True
            stats['death_date_added'] += 1
        
        # Cause of death
        if pd.notna(row.get('CauseDth')):
            cause = str(row['CauseDth']).strip()
            if cause:
                update['$set']['cause_of_death'] = cause
                stats['cause_of_death_added'] += 1
        
        # Apply update if we have changes
        if update['$set'] and not dry_run:
            patients.update_one(
                {'_id': patient['_id']},
                update
            )
    
    print(f"\nProcessed {len(df)} patients")
    
    # Print statistics
    print("\n" + "="*80)
    print("MIGRATION STATISTICS")
    print("="*80)
    print(f"Total CSV records: {stats['total_csv']}")
    print(f"Matched in database: {stats['matched']} ({stats['matched']/stats['total_csv']*100:.1f}%)")
    print(f"Not found: {stats['not_found']} ({stats['not_found']/stats['total_csv']*100:.1f}%)")
    print(f"\nDemographics added:")
    print(f"  Date of birth: {stats['dob_added']}")
    print(f"  Gender: {stats['gender_added']}")
    print(f"  Postcode: {stats['postcode_added']}")
    print(f"  Height: {stats['height_added']}")
    print(f"  Weight: {stats['weight_added']}")
    print(f"  BMI: {stats['bmi_added']}")
    print(f"\nMedical history added:")
    print(f"  Family history: {stats['family_history_added']}")
    print(f"\nDeath information added:")
    print(f"  Death date: {stats['death_date_added']}")
    print(f"  Cause of death: {stats['cause_of_death_added']}")
    
    if dry_run:
        print("\n⚠️  DRY RUN - No database changes made")
    else:
        print("\n✅ Migration complete")
    
    return stats

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Migrate patient demographics from CSV')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying them')
    
    args = parser.parse_args()
    
    migrate_patient_data(dry_run=args.dry_run)
