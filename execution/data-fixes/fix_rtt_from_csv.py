"""
Fix Return to Theatre (RTT) data from CSV
CSV field: re_op (0 = no, 1 = yes)
Expected: 1.6% RTT rate (126 cases)
"""
import pandas as pd
from pymongo import MongoClient
from dateutil import parser

# Connect to MongoDB
client = MongoClient('mongodb://admin:admin123@localhost:27017')
db = client.surgdb

print("="*80)
print("FIXING RETURN TO THEATRE DATA FROM CSV")
print("="*80)

# Load CSVs
print("\nLoading CSV files...")
surgeries_df = pd.read_csv('surgeries_export_new.csv')
patients_df = pd.read_csv('patients_export_new.csv')

print(f"Surgeries CSV: {len(surgeries_df)} records")
print(f"Patients CSV: {len(patients_df)} records")

# Join surgeries with patients on Hosp_No to get NHS_No
print("\nJoining CSVs on Hosp_No...")
df = surgeries_df.merge(
    patients_df[['Hosp_No', 'NHS_No']], 
    on='Hosp_No', 
    how='left'
)

print(f"Merged records: {len(df)}")
print(f"Records with NHS_No: {df['NHS_No'].notna().sum()}")

# Build NHS number to patient_id lookup from database
print("\nBuilding NHS to patient_id lookup...")
nhs_to_patient_id = {}
all_patients = db.patients.find({})
for patient in all_patients:
    nhs_clean = str(patient.get('nhs_number', '')).replace(' ', '').upper()
    if nhs_clean:
        nhs_to_patient_id[nhs_clean] = patient.get('patient_id')

print(f"Built lookup for {len(nhs_to_patient_id)} patients")

# Track statistics
total_processed = 0
rtt_true_count = 0
rtt_false_count = 0
not_found = 0
matched_count = 0

print("\nProcessing treatments...")

for idx, row in df.iterrows():
    nhs_no = row.get('NHS_No')
    surgery_date = row.get('Surgery')
    re_op = row.get('re_op', 0)
    
    # Skip if missing key fields
    if pd.isna(nhs_no) or pd.isna(surgery_date):
        not_found += 1
        continue
    
    # Clean NHS number - handle float conversion
    nhs_clean = str(int(float(nhs_no))).replace(' ', '').upper()
    
    # Lookup patient_id
    patient_id = nhs_to_patient_id.get(nhs_clean)
    if not patient_id:
        not_found += 1
        continue
    
    # Parse surgery date to match treatment date
    try:
        surgery_dt = parser.parse(str(surgery_date))
        surgery_date_str = surgery_dt.strftime('%Y-%m-%d')
    except:
        not_found += 1
        continue
    
    # Find matching treatment
    treatment = db.treatments.find_one({
        "patient_id": patient_id,
        "treatment_date": surgery_date_str
    })
    
    if treatment:
        # Determine RTT value
        rtt_value = bool(re_op == 1)
        
        # Update the treatment
        result = db.treatments.update_one(
            {"_id": treatment['_id']},
            {
                "$set": {
                    "return_to_theatre": rtt_value
                }
            }
        )
        
        matched_count += 1
        total_processed += 1
        if rtt_value:
            rtt_true_count += 1
            if rtt_true_count <= 5:  # Show first 5 RTT cases
                print(f"  ✓ {treatment.get('treatment_id')}: return_to_theatre = True")
        else:
            rtt_false_count += 1
    else:
        not_found += 1

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Total CSV records: {len(df)}")
print(f"Treatments processed: {total_processed}")
print(f"  - RTT = True:  {rtt_true_count} ({rtt_true_count/total_processed*100:.1f}%)")
print(f"  - RTT = False: {rtt_false_count} ({rtt_false_count/total_processed*100:.1f}%)")
print(f"Not found in DB: {not_found}")

# Verify the results
print("\n" + "="*80)
print("VERIFICATION")
print("="*80)

rtt_true_mongo = db.treatments.count_documents({"return_to_theatre": True})
rtt_false_mongo = db.treatments.count_documents({"return_to_theatre": False})
total_mongo = db.treatments.count_documents({})

print(f"MongoDB RTT = True:  {rtt_true_mongo} ({rtt_true_mongo/total_mongo*100:.1f}%)")
print(f"MongoDB RTT = False: {rtt_false_mongo} ({rtt_false_mongo/total_mongo*100:.1f}%)")
print(f"Total treatments: {total_mongo}")

# Expected from CSV
csv_rtt_true = df['re_op'].eq(1).sum()
csv_rtt_false = df['re_op'].eq(0).sum()

print(f"\nExpected from CSV:")
print(f"  RTT = True:  {csv_rtt_true} ({csv_rtt_true/len(df)*100:.1f}%)")
print(f"  RTT = False: {csv_rtt_false} ({csv_rtt_false/len(df)*100:.1f}%)")

match_status = "✓ MATCH" if rtt_true_mongo == csv_rtt_true else "✗ MISMATCH"
print(f"\n{match_status}: MongoDB RTT count {'matches' if rtt_true_mongo == csv_rtt_true else 'does not match'} CSV")

print("\n" + "="*80)
print("COMPLETE")
print("="*80)
