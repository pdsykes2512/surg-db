#!/usr/bin/env python3
"""
Fix patients with future dates of birth (2026+) by subtracting 100 years.
The import script failed to handle 2-digit years properly for some patients.
"""

from pymongo import MongoClient
from datetime import datetime

# Connect to MongoDB
client = MongoClient('mongodb://admin:admin123@surg-db.vps:27017/surgdb?authSource=admin')
db = client['surgdb']
patients_collection = db.patients

print("Finding patients with future dates of birth...")

# Find all patients with age field
all_patients = list(patients_collection.find({'demographics.age': {'$exists': True}}))

problematic = []
for p in all_patients:
    dob = p.get('demographics', {}).get('date_of_birth')
    age = p.get('demographics', {}).get('age')
    
    # Check if age is negative
    if age is not None and age < 0:
        problematic.append(p)

print(f"Found {len(problematic)} patients with negative ages")
print()

# Fix each patient
fixed_count = 0
for patient in problematic:
    patient_id = patient.get('patient_id', 'N/A')
    dob = patient.get('demographics', {}).get('date_of_birth')
    current_age = patient.get('demographics', {}).get('age')
    
    # Parse the datetime object
    if isinstance(dob, datetime):
        dob_date = dob
    elif isinstance(dob, str):
        try:
            dob_date = datetime.strptime(dob, '%Y-%m-%d')
        except:
            print(f"  ! Cannot parse DOB for patient {patient_id}: {dob}")
            continue
    else:
        print(f"  ! Unknown DOB format for patient {patient_id}: {type(dob)}")
        continue
    
    # Subtract 100 years
    new_dob = dob_date.replace(year=dob_date.year - 100)
    
    # Calculate new age
    today = datetime.now()
    new_age = today.year - new_dob.year - ((today.month, today.day) < (new_dob.month, new_dob.day))
    
    print(f"Patient {patient_id}:")
    print(f"  Old DOB: {dob_date.strftime('%Y-%m-%d')}, Age: {current_age}")
    print(f"  New DOB: {new_dob.strftime('%Y-%m-%d')}, Age: {new_age}")
    
    # Update in database
    result = patients_collection.update_one(
        {'_id': patient['_id']},
        {
            '$set': {
                'demographics.date_of_birth': new_dob,
                'demographics.age': new_age,
                'updated_at': datetime.now()
            }
        }
    )
    
    if result.modified_count > 0:
        fixed_count += 1
        print(f"  ✓ Fixed")
    else:
        print(f"  ✗ Failed to update")
    print()

print(f"\n✓ Fixed {fixed_count} out of {len(problematic)} patients")
