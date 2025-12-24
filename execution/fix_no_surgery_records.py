"""
Fix treatments collection by removing records where no surgery was performed.

The CSV has a 'NoSurg' field that indicates episodes where surgery was NOT performed.
These should not be in the treatments collection.

CSV breakdown:
- Total rows: 7,957
- Had surgery (NoSurg is NaN): 5,827
- No surgery (NoSurg has reason): 2,130
"""

import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import sys

# Check for --confirm flag
auto_confirm = '--confirm' in sys.argv

# MongoDB connection
client = MongoClient('mongodb://admin:admin123@localhost:27017')
db = client.surgdb

# Load CSV
print("Loading CSV data...")
surgeries_df = pd.read_csv('surgeries_export_new.csv')
patients_df = pd.read_csv('patients_export_new.csv')

# Merge to get NHS_No for matching
print("Merging with patients data to get NHS numbers...")
df = surgeries_df.merge(patients_df[['Hosp_No', 'NHS_No']], on='Hosp_No', how='left')

print("\n" + "="*80)
print("IDENTIFYING RECORDS WITHOUT SURGERY")
print("="*80)

# Records where NoSurg is populated (has a reason) = no surgery performed
no_surgery_records = df[df['NoSurg'].notna()].copy()
print(f"Records with NoSurg reason (no surgery): {len(no_surgery_records)}")

# Get the Hosp_No values for these records
no_surgery_hosp_nos = set(no_surgery_records['Hosp_No'].values)
print(f"Unique hospital numbers without surgery: {len(no_surgery_hosp_nos)}")

print("\n" + "="*80)
print("MATCHING TO MONGODB TREATMENTS")
print("="*80)

# Build lookup of patient_id to NHS_No
print("Building patient ID lookup...")
patient_lookup = {}

# Get all patients at once
all_patients = list(db.patients.find({}, {'nhs_number': 1, 'record_number': 1, 'patient_id': 1, '_id': 1}))
print(f"Loaded {len(all_patients)} patients from MongoDB")

for patient in all_patients:
    nhs_num = patient.get('nhs_number', '').replace(' ', '').upper()
    patient_id = patient.get('record_number') or patient.get('patient_id') or str(patient['_id'])
    if nhs_num:
        # Build reverse lookup from CSV NHS to patient_id
        patient_lookup[nhs_num] = patient_id

# Now build hosp_no to patient_id mapping from CSV
hosp_to_patient = {}
for _, row in patients_df.iterrows():
    hosp_no = str(row['Hosp_No']).strip().upper()
    nhs_no = row.get('NHS_No')
    
    if pd.notna(nhs_no):
        try:
            nhs_clean = str(int(float(nhs_no))).replace(' ', '').upper()
            patient_id = patient_lookup.get(nhs_clean)
            if patient_id:
                hosp_to_patient[hosp_no] = patient_id
        except (ValueError, TypeError):
            pass

print(f"Built lookup for {len(hosp_to_patient)} hospital numbers")

# Find treatments to delete
treatments_to_delete = []
not_found_count = 0
skipped_with_procedure = 0

for _, row in no_surgery_records.iterrows():
    hosp_no = str(row['Hosp_No']).strip().upper()
    patient_id = hosp_to_patient.get(hosp_no)
    
    if patient_id:
        # Find all treatments for this patient
        treatments = list(db.treatments.find({'patient_id': patient_id}))
        
        # For records with Su_SeqNo, try to match by sequence
        su_seq_no = row.get('Su_SeqNo')
        if pd.notna(su_seq_no) and treatments:
            # Try to match by sequence number in treatment_id
            seq_str = f"-{int(su_seq_no):02d}"
            for t in treatments:
                if seq_str in t.get('treatment_id', ''):
                    # Additional safety check: verify no procedure/OPCS code
                    opcs_code = t.get('opcs_code') or t.get('opcs4_code')
                    procedure_name = t.get('procedure_name')
                    
                    if opcs_code or procedure_name:
                        # This treatment has procedure data, don't delete
                        skipped_with_procedure += 1
                        print(f"  ⚠ Skipping {t.get('treatment_id')}: has procedure data (OPCS: {opcs_code}, Proc: {procedure_name})")
                    else:
                        treatments_to_delete.append(t['_id'])
                    break
            else:
                # If no sequence match and patient has only one treatment, check it
                if len(treatments) == 1:
                    t = treatments[0]
                    opcs_code = t.get('opcs_code') or t.get('opcs4_code')
                    procedure_name = t.get('procedure_name')
                    
                    if opcs_code or procedure_name:
                        skipped_with_procedure += 1
                        print(f"  ⚠ Skipping {t.get('treatment_id')}: has procedure data (OPCS: {opcs_code}, Proc: {procedure_name})")
                    else:
                        treatments_to_delete.append(treatments[0]['_id'])
        elif len(treatments) == 1:
            # Patient has only one treatment, check it
            t = treatments[0]
            opcs_code = t.get('opcs_code') or t.get('opcs4_code')
            procedure_name = t.get('procedure_name')
            
            if opcs_code or procedure_name:
                skipped_with_procedure += 1
                print(f"  ⚠ Skipping {t.get('treatment_id')}: has procedure data (OPCS: {opcs_code}, Proc: {procedure_name})")
            else:
                treatments_to_delete.append(treatments[0]['_id'])
    else:
        not_found_count += 1

print(f"\nTreatments to delete: {len(treatments_to_delete)}")
print(f"Skipped (have procedure data): {skipped_with_procedure}")
print(f"Records not found in DB: {not_found_count}")

# Show summary of NoSurg reasons
print("\n" + "="*80)
print("NO SURGERY REASONS:")
print("="*80)
reason_counts = no_surgery_records['NoSurg'].value_counts()
for reason, count in reason_counts.items():
    print(f"  {reason}: {count}")

# Confirmation before deletion
print("\n" + "="*80)
print("READY TO DELETE")
print("="*80)
print(f"Will delete {len(treatments_to_delete)} treatment records from MongoDB")
print("\nCurrent counts:")
print(f"  MongoDB treatments: {db.treatments.count_documents({})}")
print(f"  After deletion:     {db.treatments.count_documents({}) - len(treatments_to_delete)}")
print(f"  Expected (CSV):     5827")

if auto_confirm:
    response = 'yes'
    print("\n--confirm flag detected, proceeding automatically")
else:
    response = input("\nProceed with deletion? (yes/no): ")

if response.lower() == 'yes':
    print("\nDeleting treatments...")
    result = db.treatments.delete_many({'_id': {'$in': treatments_to_delete}})
    print(f"Deleted {result.deleted_count} treatment records")
    
    print("\n" + "="*80)
    print("VERIFICATION")
    print("="*80)
    remaining = db.treatments.count_documents({})
    print(f"Remaining treatments: {remaining}")
    print(f"Expected:             5827")
    print(f"Difference:           {remaining - 5827}")
    
    # Update episodes collection to reflect correct status
    print("\nUpdating episode statuses...")
    for hosp_no in no_surgery_hosp_nos:
        patient_id = hosp_to_patient.get(str(hosp_no).strip().upper())
        if patient_id:
            # Mark episodes for this patient as "no surgery performed"
            db.episodes.update_many(
                {'patient_id': patient_id},
                {'$set': {
                    'no_surgery_performed': True,
                    'last_modified_at': datetime.utcnow()
                }}
            )
    
    print("✓ Database updated successfully")
else:
    print("Deletion cancelled")
