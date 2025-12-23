#!/usr/bin/env python3
"""
Fix complications field in database based on actual complication indicators.

True complications are defined as:
- MJ_Leak = 1 (Major anastomotic leak)
- MI_Leak = 1 (Minor anastomotic leak)  
- Cardio = 1 (Cardiovascular complications)
- MJ_Bleed = 1 (Major bleeding)
- MI_Bleed = 1 (Minor bleeding)

Readmission is tracked separately and should NOT be counted as a complication.
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
    
    print("FIXING COMPLICATIONS WITH NHS NUMBER MATCHING")
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
        patients_df[['Hosp_No', 'NHS_No']], 
        on='Hosp_No', 
        how='left'
    )
    
    print(f"Merged records: {len(merged_df)}")
    print(f"Records with NHS_No: {merged_df['NHS_No'].notna().sum()}")
    print(f"Records with Surgery date: {merged_df['Surgery'].notna().sum()}")
    
    # Build NHS number to patient_id lookup from database
    print("\nBuilding NHS number lookup from database...")
    nhs_to_patient = {}
    for patient in patients_collection.find({"nhs_number": {"$exists": True, "$ne": None}}):
        nhs_num = patient.get('nhs_number')
        patient_id = patient.get('patient_id')
        if nhs_num and patient_id:
            try:
                nhs_int = int(nhs_num)
                nhs_to_patient[nhs_int] = patient_id
            except:
                pass
    
    print(f"Built lookup with {len(nhs_to_patient)} NHS numbers")
    
    # Process merged data and build complication lookup
    print("\nBuilding treatment complication lookup...")
    treatment_lookup = {}
    
    for _, row in merged_df.iterrows():
        nhs_no = row.get('NHS_No')
        surgery_date = row.get('Surgery')
        
        # Check actual complication fields
        mj_leak = row.get('MJ_Leak')
        mi_leak = row.get('MI_Leak')
        cardio = row.get('Cardio')
        mj_bleed = row.get('MJ_Bleed')
        mi_bleed = row.get('MI_Bleed')
        
        # Has TRUE complications if any of these are 1
        has_complication = (
            (pd.notna(mj_leak) and mj_leak == 1) or
            (pd.notna(mi_leak) and mi_leak == 1) or
            (pd.notna(cardio) and cardio == 1) or
            (pd.notna(mj_bleed) and mj_bleed == 1) or
            (pd.notna(mi_bleed) and mi_bleed == 1)
        )
        
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
                    
                    # Build key
                    key = f"{patient_id}_{date_str}"
                    treatment_lookup[key] = has_complication
                    
            except Exception as e:
                continue
    
    print(f"Successfully matched {len(treatment_lookup)} records")
    
    # Count true complications in CSV
    with_complication = sum(1 for v in treatment_lookup.values() if v)
    without_complication = sum(1 for v in treatment_lookup.values() if not v)
    
    print(f"  With TRUE complications: {with_complication} ({with_complication/len(treatment_lookup)*100:.1f}%)")
    print(f"  Without complications: {without_complication} ({without_complication/len(treatment_lookup)*100:.1f}%)")
    
    # Perform updates
    print("\n" + "="*80)
    print("Updating treatments...")
    print("="*80 + "\n")
    
    updated_count = 0
    already_correct = 0
    set_to_true = 0
    set_to_false = 0
    no_date_count = 0
    not_found_count = 0
    
    all_treatments = list(treatments_collection.find({}))
    
    for i, treatment in enumerate(all_treatments):
        patient_id = treatment.get('patient_id')
        treatment_date = treatment.get('treatment_date')
        current_comp = treatment.get('complications')
        
        if not treatment_date:
            no_date_count += 1
            # Set to False if no date
            if current_comp is not False:
                treatments_collection.update_one(
                    {'_id': treatment['_id']},
                    {'$set': {'complications': False, 'updated_at': datetime.utcnow()}}
                )
                updated_count += 1
                set_to_false += 1
            else:
                already_correct += 1
            continue
        
        # Look up in our treatment_lookup
        key = f"{patient_id}_{treatment_date}"
        csv_has_comp = treatment_lookup.get(key)
        
        if csv_has_comp is None:
            # Not found in CSV - set to False
            not_found_count += 1
            if current_comp is not False:
                treatments_collection.update_one(
                    {'_id': treatment['_id']},
                    {'$set': {'complications': False, 'updated_at': datetime.utcnow()}}
                )
                updated_count += 1
                set_to_false += 1
            else:
                already_correct += 1
            continue
        
        # Found in CSV - update if different
        if current_comp == csv_has_comp:
            already_correct += 1
        else:
            treatments_collection.update_one(
                {'_id': treatment['_id']},
                {'$set': {'complications': csv_has_comp, 'updated_at': datetime.utcnow()}}
            )
            updated_count += 1
            if csv_has_comp:
                set_to_true += 1
            else:
                set_to_false += 1
        
        if (i + 1) % 500 == 0:
            print(f"  Processed {i + 1} treatments...")
    
    print("\n" + "="*80)
    print("SUMMARY:")
    print("="*80)
    print(f"Total treatments: {len(all_treatments)}")
    print(f"Updated: {updated_count}")
    print(f"  Set to TRUE: {set_to_true}")
    print(f"  Set to FALSE: {set_to_false}")
    print(f"Already correct: {already_correct}")
    print(f"No treatment date: {no_date_count}")
    print(f"Not found in CSV: {not_found_count}")
    
    # Verify
    print("\n" + "="*80)
    print("VERIFICATION - Database complication distribution:")
    print("="*80)
    total_treatments = treatments_collection.count_documents({})
    with_comps = treatments_collection.count_documents({'complications': True})
    without_comps = treatments_collection.count_documents({'complications': False})
    null_comps = treatments_collection.count_documents({'complications': None})
    
    print(f"Total treatments: {total_treatments}")
    if total_treatments > 0:
        print(f"  With complications: {with_comps} ({with_comps/total_treatments*100:.1f}%)")
        print(f"  Without complications: {without_comps} ({without_comps/total_treatments*100:.1f}%)")
        print(f"  Null: {null_comps} ({null_comps/total_treatments*100:.1f}%)")

if __name__ == '__main__':
    main()