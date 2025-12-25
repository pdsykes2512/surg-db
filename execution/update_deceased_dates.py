#!/usr/bin/env python3
"""
Update existing patients with deceased_date from Access database
"""
import subprocess
import csv
import sys
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv('/root/surg-db/.env')

# MongoDB connection
MONGO_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('MONGODB_DB_NAME')
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

def parse_access_date(date_str):
    """Parse Access date format MM/DD/YY HH:MM:SS"""
    if not date_str or date_str.strip() == '':
        return None
    try:
        dt = datetime.strptime(date_str.strip(), '%m/%d/%y %H:%M:%S')
        return dt.strftime('%Y-%m-%d')
    except:
        return None

def update_deceased_dates():
    """Update deceased_date for all patients"""
    
    print("Loading patient data from Access database...")
    patient_cmd = ["mdb-export", "/root/surg-db/acpdb/acpdata_v3_db.mdb", "tblPatient"]
    patient_output = subprocess.check_output(patient_cmd, text=True)
    patient_reader = csv.DictReader(patient_output.strip().split('\n'))
    
    # Build mapping of NHS_No to deceased_date
    deceased_map = {}
    for row in patient_reader:
        nhs_no = row.get('NHS_No', '').strip().replace(' ', '')
        death_date = parse_access_date(row.get('DeathDat', ''))
        if nhs_no and death_date:
            deceased_map[nhs_no] = death_date
    
    print(f"Found {len(deceased_map)} deceased patients in Access DB")
    
    # Update MongoDB patients
    updated_count = 0
    for nhs_number, deceased_date in deceased_map.items():
        result = db.patients.update_one(
            {'nhs_number': nhs_number},
            {'$set': {'demographics.deceased_date': deceased_date}}
        )
        if result.modified_count > 0:
            updated_count += 1
    
    print(f"\n✓ Updated {updated_count} patients with deceased_date")
    
    # Also set deceased_date to None for patients without it (clean migration)
    result = db.patients.update_many(
        {'demographics.deceased_date': {'$exists': False}},
        {'$set': {'demographics.deceased_date': None}}
    )
    print(f"✓ Set deceased_date to None for {result.modified_count} patients without death date")

if __name__ == '__main__':
    try:
        update_deceased_dates()
        print("\n✓ Migration completed successfully")
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
