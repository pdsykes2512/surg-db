#!/usr/bin/env python3
"""
Migrate outcomes data from CSV to treatments collection
Focuses on: readmission, return to theatre, 30-day mortality, ICU, complications
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
    """Generate patient ID from hospital number (matches original import logic)"""
    return hashlib.md5(str(hosp_no).lower().encode()).hexdigest()[:6].upper()

def migrate_outcomes(dry_run=False):
    """Migrate outcomes data from CSV to treatments"""
    
    print("MIGRATING OUTCOMES DATA FROM CSV")
    print("="*80)
    
    # Read CSVs
    df_surgeries = pd.read_csv('surgeries_export_new.csv')
    df_patients = pd.read_csv('patients_export_new.csv')
    
    # Join surgeries with patients to get NHS numbers and death dates
    df = df_surgeries.merge(
        df_patients[['Hosp_No', 'NHS_No', 'PAS_No', 'DeathDat']],
        on='Hosp_No',
        how='left'
    )
    
    print(f"Loaded {len(df)} surgeries from CSV")
    print(f"Surgeries with NHS_No: {df['NHS_No'].notna().sum()}")
    
    # Connect to database
    db = connect_db()
    treatments = db.treatments
    patients = db.patients
    
    # Build NHS number to patient_id lookup
    print("\nBuilding NHS number lookup...")
    nhs_to_patient = {}
    for patient in patients.find({'nhs_number': {'$exists': True}}):
        nhs_num = patient.get('nhs_number')
        if nhs_num:
            nhs_to_patient[int(nhs_num)] = patient.get('patient_id')
    
    print(f"Found {len(nhs_to_patient)} patients with NHS numbers in database")
    
    # Track statistics
    stats = {
        'total_csv': len(df),
        'matched': 0,
        'not_found': 0,
        'return_to_theatre_added': 0,
        'complications_added': 0,
        'readmission_added': 0,
        'leak_from_major_c': 0,
        'cardio_added': 0,
        'leak_major_added': 0,
        'leak_minor_added': 0,
        'mi_added': 0,
        'ileus_added': 0,
        'mortality_30d_added': 0,
        'mortality_90d_added': 0,
    }
    
    not_found_ids = []
    
    print("\nProcessing surgeries...")
    for idx, row in df.iterrows():
        if idx % 1000 == 0:
            print(f"  Processed {idx}/{len(df)}...")
        
        # Get NHS number and look up patient_id
        nhs_no = row.get('NHS_No')
        if pd.isna(nhs_no):
            stats['not_found'] += 1
            not_found_ids.append(str(row['Su_SeqNo']))
            continue
        
        nhs_int = int(nhs_no)
        patient_id = nhs_to_patient.get(nhs_int)
        
        if not patient_id:
            stats['not_found'] += 1
            not_found_ids.append(str(row['Su_SeqNo']))
            continue
        
        # Find treatments for this patient
        patient_treatments = list(treatments.find({
            'patient_id': patient_id,
            'treatment_type': 'surgery'
        }))
        
        if not patient_treatments:
            stats['not_found'] += 1
            not_found_ids.append(str(row['Su_SeqNo']))
            continue
        
        # If multiple treatments, try to match by date or use first one
        treatment = patient_treatments[0]
        if len(patient_treatments) > 1:
            # Try to match by treatment date if available
            csv_date = row.get('Date_Th')
            if pd.notna(csv_date):
                # Parse CSV date (format: MM/DD/YY HH:MM:SS)
                try:
                    from dateutil import parser
                    csv_date_parsed = parser.parse(str(csv_date))
                    for t in patient_treatments:
                        if t.get('treatment_date'):
                            t_date = t['treatment_date'] if isinstance(t['treatment_date'], datetime) else parser.parse(t['treatment_date'])
                            if t_date.date() == csv_date_parsed.date():
                                treatment = t
                                break
                except:
                    pass  # Use first treatment if date matching fails
        
        stats['matched'] += 1
        
        # Build update document
        update = {}
        
        # Major_C field - contains coded complications including readmission and leak
        if 'Major_C' in row and pd.notna(row['Major_C']):
            major_c = str(row['Major_C']).lower()
            
            # "6 Readmission" or "6 readmission"
            if 'readmission' in major_c:
                update['readmission_30d'] = True
                stats['readmission_added'] += 1
                if 'complications' not in update:
                    update['complications'] = True
                    stats['complications_added'] += 1
            
            # "2 Leak"
            if '2 leak' in major_c or major_c == '2 leak':
                stats['leak_from_major_c'] += 1
                if 'complications' not in update:
                    update['complications'] = True
                    stats['complications_added'] += 1
            
            # "4 Bleed"
            if '4 bleed' in major_c or major_c == '4 bleed':
                if 'complications' not in update:
                    update['complications'] = True
                    stats['complications_added'] += 1
            
            # "3 Abscess"
            if '3 abscess' in major_c or major_c == '3 abscess':
                if 'complications' not in update:
                    update['complications'] = True
                    stats['complications_added'] += 1
            
            # "5 Obstruction"
            if '5 obstruction' in major_c or major_c == '5 obstruction':
                if 'complications' not in update:
                    update['complications'] = True
                    stats['complications_added'] += 1
        
        # Return to theatre (re_op field)
        if 're_op' in row and pd.notna(row['re_op']):
            re_op_value = bool(int(row['re_op'])) if row['re_op'] in [0, 1] else False
            if re_op_value:
                update['return_to_theatre'] = True
                stats['return_to_theatre_added'] += 1
        
        # Cardiovascular complications
        if 'Cardio' in row and pd.notna(row['Cardio']):
            cardio_value = bool(int(row['Cardio'])) if row['Cardio'] in [0, 1] else False
            if cardio_value:
                stats['cardio_added'] += 1
                # Mark as having complications
                if 'complications' not in update:
                    update['complications'] = True
                    stats['complications_added'] += 1
        
        # Major anastomotic leak
        if 'MJ_Leak' in row and pd.notna(row['MJ_Leak']):
            leak_value = bool(int(row['MJ_Leak'])) if row['MJ_Leak'] in [0, 1] else False
            if leak_value:
                stats['leak_major_added'] += 1
                if 'complications' not in update:
                    update['complications'] = True
                    stats['complications_added'] += 1
        
        # Minor anastomotic leak  
        if 'MI_Leak' in row and pd.notna(row['MI_Leak']):
            leak_value = bool(int(row['MI_Leak'])) if row['MI_Leak'] in [0, 1] else False
            if leak_value:
                stats['leak_minor_added'] += 1
                if 'complications' not in update:
                    update['complications'] = True
                    stats['complications_added'] += 1
        
        # Myocardial infarction
        if 'MI' in row and pd.notna(row['MI']):
            mi_value = bool(int(row['MI'])) if row['MI'] in [0, 1] else False
            if mi_value:
                stats['mi_added'] += 1
                if 'complications' not in update:
                    update['complications'] = True
                    stats['complications_added'] += 1
        
        # Post-op ileus
        if 'PO_ileus' in row and pd.notna(row['PO_ileus']):
            ileus_value = bool(int(row['PO_ileus'])) if row['PO_ileus'] in [0, 1] else False
            if ileus_value:
                stats['ileus_added'] += 1
                if 'complications' not in update:
                    update['complications'] = True
                    stats['complications_added'] += 1
        
        # Calculate 30-day and 90-day mortality
        death_date = row.get('DeathDat')
        surgery_date = row.get('Date_Th')
        
        if pd.notna(death_date) and pd.notna(surgery_date):
            try:
                from dateutil import parser
                death_dt = parser.parse(str(death_date))
                surgery_dt = parser.parse(str(surgery_date))
                
                days_to_death = (death_dt - surgery_dt).days
                
                # 30-day mortality
                if 0 <= days_to_death <= 30:
                    update['mortality_30day'] = True
                    stats['mortality_30d_added'] += 1
                    if 'complications' not in update:
                        update['complications'] = True
                        stats['complications_added'] += 1
                
                # 90-day mortality
                if 0 <= days_to_death <= 90:
                    update['mortality_90day'] = True
                    stats['mortality_90d_added'] += 1
            except:
                pass  # Skip if date parsing fails
        
        # Apply update if we have changes
        if update and not dry_run:
            treatments.update_one(
                {'_id': treatment['_id']},
                {'$set': update}
            )
    
    print(f"\nProcessed {len(df)} surgeries")
    
    # Print statistics
    print("\n" + "="*80)
    print("MIGRATION STATISTICS")
    print("="*80)
    print(f"Total CSV records: {stats['total_csv']}")
    print(f"Matched in database: {stats['matched']} ({stats['matched']/stats['total_csv']*100:.1f}%)")
    print(f"Not found: {stats['not_found']} ({stats['not_found']/stats['total_csv']*100:.1f}%)")
    print(f"\nOutcomes added:")
    print(f"  Return to theatre: {stats['return_to_theatre_added']}")
    print(f"  30-day readmissions: {stats['readmission_added']}")
    print(f"  30-day mortality: {stats['mortality_30d_added']}")
    print(f"  90-day mortality: {stats['mortality_90d_added']}")
    print(f"  Complications flagged: {stats['complications_added']}")
    print(f"  - Anastomotic leak (from Major_C): {stats['leak_from_major_c']}")
    print(f"  - Cardiovascular: {stats['cardio_added']}")
    print(f"  - Major anastomotic leak (MJ_Leak): {stats['leak_major_added']}")
    print(f"  - Minor anastomotic leak (MI_Leak): {stats['leak_minor_added']}")
    print(f"  - Myocardial infarction: {stats['mi_added']}")
    print(f"  - Post-op ileus: {stats['ileus_added']}")
    
    if dry_run:
        print("\n⚠️  DRY RUN - No database changes made")
    else:
        print("\n✅ Migration complete")
    
    # Show sample of not found IDs
    if not_found_ids and len(not_found_ids) <= 20:
        print(f"\nSurgery IDs not found in database:")
        for sid in not_found_ids[:20]:
            print(f"  {sid}")
    elif not_found_ids:
        print(f"\nFirst 20 surgery IDs not found:")
        for sid in not_found_ids[:20]:
            print(f"  {sid}")
    
    return stats

def show_stats():
    """Show current database statistics"""
    db = connect_db()
    treatments = db.treatments
    
    print("CURRENT DATABASE STATISTICS")
    print("="*80)
    
    total = treatments.count_documents({'treatment_type': 'surgery'})
    return_theatre = treatments.count_documents({'return_to_theatre': True})
    complications = treatments.count_documents({'complications': True})
    readmissions = treatments.count_documents({'readmission_30d': True})
    mortality_30d = treatments.count_documents({'mortality_30day': True})
    mortality_90d = treatments.count_documents({'mortality_90day': True})
    
    print(f"Total surgeries: {total}")
    print(f"Return to theatre: {return_theatre} ({return_theatre/total*100:.1f}%)")
    print(f"With complications: {complications} ({complications/total*100:.1f}%)")
    print(f"30-day readmissions: {readmissions} ({readmissions/total*100:.1f}%)")
    print(f"30-day mortality: {mortality_30d} ({mortality_30d/total*100:.1f}%)")
    print(f"90-day mortality: {mortality_90d} ({mortality_90d/total*100:.1f}%)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Migrate outcomes data from CSV to treatments')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying them')
    parser.add_argument('--stats', action='store_true', help='Show current database statistics')
    
    args = parser.parse_args()
    
    if args.stats:
        show_stats()
    else:
        migrate_outcomes(dry_run=args.dry_run)
