#!/usr/bin/env python3
"""Check for patients with negative ages on pages 7-8"""
import os
import sys
os.chdir('/root/surg-db/backend')

from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = client['surg_db']

total = db.patients.count_documents({})
print(f'Total patients: {total}')

# Check all patients with stored age field
print('\n=== Checking ALL patients with age field ===')
patients_with_age = list(db.patients.find({'demographics.age': {'$exists': True}}))
print(f'Patients with age field: {len(patients_with_age)}')

for p in patients_with_age:
    dob = p.get('demographics', {}).get('date_of_birth')
    age = p.get('demographics', {}).get('age')
    hosp = p.get('hospital_number', 'N/A')
    patient_id = p.get('patient_id', 'N/A')
    
    calc_age = None
    if dob:
        try:
            dob_date = datetime.strptime(dob, '%Y-%m-%d')
            today = datetime.now()
            calc_age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
        except Exception as e:
            print(f'  Parse error for {hosp}: {e}')
    
    if age is not None and age < 0:
        print(f'*** NEGATIVE AGE: Patient {patient_id}, Hosp: {hosp}, DOB: {dob}, Age: {age}, Calculated: {calc_age}')
    elif calc_age is not None and calc_age < 0:
        print(f'*** FUTURE DOB: Patient {patient_id}, Hosp: {hosp}, DOB: {dob}, Age: {age}, Calculated: {calc_age}')

print('\nDone.')
