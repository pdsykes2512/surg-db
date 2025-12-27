#!/usr/bin/env python3
"""
Fix patients with invalid dates of birth that result in negative ages.
This script:
1. Finds all patients with DOBs that result in negative ages
2. Corrects the year by subtracting 100 years (2044 -> 1944, etc.)
3. Updates the patient records in MongoDB
"""

import os
import sys
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

def calculate_age(dob_str: str) -> int:
    """Calculate age from DOB string"""
    try:
        dob = datetime.strptime(dob_str, '%Y-%m-%d')
        today = datetime.now()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return age
    except:
        return 0

def main():
    # Load environment variables
    load_dotenv()
    
    # Connect to MongoDB
    mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    client = MongoClient(mongodb_uri)
    db = client['surg_db']
    patients_collection = db.patients
    
    print("Scanning for patients with invalid dates of birth...")
    print()
    
    # Find all patients
    all_patients = list(patients_collection.find())
    total_patients = len(all_patients)
    
    problematic_patients = []
    
    for patient in all_patients:
        dob_str = patient.get('demographics', {}).get('date_of_birth')
        
        if not dob_str:
            continue
        
        age = calculate_age(dob_str)
        
        # Check if age is negative or unreasonably high (future date)
        if age < 0 or age > 150:
            problematic_patients.append({
                'patient': patient,
                'current_dob': dob_str,
                'calculated_age': age
            })
    
    if not problematic_patients:
        print("✓ No patients with invalid dates of birth found!")
        return 0
    
    print(f"Found {len(problematic_patients)} patients with invalid DOBs:")
    print()
    
    for item in problematic_patients:
        patient = item['patient']
        current_dob = item['current_dob']
        calculated_age = item['calculated_age']
        
        print(f"Patient: {patient.get('hospital_number', 'N/A')}")
        print(f"  Current DOB: {current_dob}")
        print(f"  Calculated Age: {calculated_age}")
        
        # Parse and fix the DOB
        try:
            dob = datetime.strptime(current_dob, '%Y-%m-%d')
            
            # Subtract 100 years if the date results in negative age or future date
            if calculated_age < 0 or dob.year > datetime.now().year:
                new_dob = dob.replace(year=dob.year - 100)
                new_dob_str = new_dob.strftime('%Y-%m-%d')
                new_age = calculate_age(new_dob_str)
                
                print(f"  Fixed DOB: {new_dob_str}")
                print(f"  New Age: {new_age}")
                print()
                
                # Update in database
                result = patients_collection.update_one(
                    {'_id': patient['_id']},
                    {
                        '$set': {
                            'demographics.date_of_birth': new_dob_str,
                            'updated_at': datetime.now()
                        }
                    }
                )
                
                if result.modified_count > 0:
                    print(f"  ✓ Updated in database")
                else:
                    print(f"  ✗ Failed to update in database")
            else:
                print(f"  ! Could not determine fix for this patient")
        
        except Exception as e:
            print(f"  ✗ Error processing: {e}")
        
        print()
    
    print(f"\n✓ Fixed {len(problematic_patients)} patients")
    return 0

if __name__ == '__main__':
    sys.exit(main())
