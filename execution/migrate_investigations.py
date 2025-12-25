#!/usr/bin/env python3
"""
Migration script to import investigation data from Access database.

Maps investigation date fields from tblTumour to Investigation documents:
- Date_Col -> Colonoscopy
- Date_Fle -> Flexible Sigmoidoscopy  
- Dt_CT_Abdo -> CT Abdomen/Pelvis
- Dt_CT_pneumo -> CT Colonography
- Dt_MRI1, Dt_MRI2 -> MRI Rectum
- Dt_Endo -> Endoscopy
- Date_Bar -> Barium Enema

Classifications:
- pre_treatment: Investigation performed before first surgery
- surveillance: Investigation performed after surgery
"""

import subprocess
import csv
import sys
import os
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection
MONGO_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
DB_NAME = os.getenv('MONGODB_DB_NAME', 'surg_db')
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

def parse_access_date(date_str):
    """Parse Access date format MM/DD/YY HH:MM:SS"""
    if not date_str or date_str.strip() == '':
        return None
    try:
        return datetime.strptime(date_str.strip(), '%m/%d/%y %H:%M:%S')
    except:
        return None

def get_surgery_dates():
    """Extract first surgery date for each patient from tblSurgery"""
    print("Extracting surgery dates...")
    surgery_cmd = ["mdb-export", "/root/surg-db/acpdb/acpdata_v3_db.mdb", "tblSurgery"]
    surgery_output = subprocess.check_output(surgery_cmd, text=True)
    surgery_reader = csv.DictReader(surgery_output.strip().split('\n'))
    
    surgery_dates = {}
    for row in surgery_reader:
        hosp_no = row.get('Hosp_No', '').strip()
        surgery_date = parse_access_date(row.get('Surgery', ''))
        
        if hosp_no and surgery_date:
            # Keep earliest surgery date
            if hosp_no not in surgery_dates or surgery_date < surgery_dates[hosp_no]:
                surgery_dates[hosp_no] = surgery_date
    
    print(f"Found surgery dates for {len(surgery_dates)} patients")
    return surgery_dates

def get_patient_mapping():
    """Get mapping of NHS_No to MongoDB patient_id"""
    print("Loading patient mappings...")
    patient_mapping = {}
    
    for patient in db.patients.find({}, {'patient_id': 1, 'nhs_number': 1}):
        # Map by NHS number (which matches NHS_No in Access DB)
        nhs_number = patient.get('nhs_number')
        if nhs_number:
            # Store NHS number as string, with and without spaces
            nhs_str = str(nhs_number).strip().replace(' ', '')
            patient_mapping[nhs_str] = patient['patient_id']
    
    print(f"Loaded {len(patient_mapping)} patient mappings")
    return patient_mapping

def get_hosp_no_to_nhs_mapping():
    """Get mapping of Hosp_No to NHS_No from Access tblPatient"""
    print("Loading Hosp_No to NHS_No mappings from Access DB...")
    
    patient_cmd = ["mdb-export", "/root/surg-db/acpdb/acpdata_v3_db.mdb", "tblPatient"]
    patient_output = subprocess.check_output(patient_cmd, text=True)
    patient_reader = csv.DictReader(patient_output.strip().split('\n'))
    
    hosp_to_nhs = {}
    for row in patient_reader:
        hosp_no = row.get('Hosp_No', '').strip()
        nhs_no = row.get('NHS_No', '').strip().replace(' ', '')
        if hosp_no and nhs_no:
            hosp_to_nhs[hosp_no] = nhs_no
    
    print(f"Loaded {len(hosp_to_nhs)} Hosp_No to NHS_No mappings")
    return hosp_to_nhs

def get_episode_mapping():
    """Get mapping of patient_id to episode_id"""
    print("Loading episode mappings...")
    episode_mapping = {}
    
    for episode in db.episodes.find({}, {'episode_id': 1, 'patient_id': 1}):
        patient_id = episode.get('patient_id')
        if patient_id:
            episode_mapping[patient_id] = episode['episode_id']
    
    print(f"Loaded {len(episode_mapping)} episode mappings")
    return episode_mapping

def generate_investigation_id(patient_id, counter):
    """Generate unique investigation ID"""
    return f"INV-{patient_id}-{counter:03d}"

def import_investigations():
    """Import all investigations from Access database"""
    
    # Get mappings
    surgery_dates = get_surgery_dates()
    hosp_to_nhs = get_hosp_no_to_nhs_mapping()
    patient_mapping = get_patient_mapping()
    episode_mapping = get_episode_mapping()
    
    # Investigation field mappings
    inv_fields = [
        ('Date_Col', 'endoscopy', 'colonoscopy', 'Colonoscopy'),
        ('Date_Fle', 'endoscopy', 'flexible_sigmoidoscopy', 'Flexible Sigmoidoscopy'),
        ('Dt_CT_Abdo', 'imaging', 'ct_abdomen', 'CT Abdomen/Pelvis'),
        ('Dt_CT_pneumo', 'imaging', 'ct_colonography', 'CT Colonography'),
        ('Dt_MRI1', 'imaging', 'mri_rectum', 'MRI Rectum'),
        ('Dt_MRI2', 'imaging', 'mri_rectum', 'MRI Rectum'),
        ('Dt_Endo', 'endoscopy', 'endoscopy', 'Endoscopy'),
        ('Date_Bar', 'imaging', 'barium_enema', 'Barium Enema')
    ]
    
    # Extract tumour data
    print("Extracting investigations from tblTumour...")
    tumour_cmd = ["mdb-export", "/root/surg-db/acpdb/acpdata_v3_db.mdb", "tblTumour"]
    tumour_output = subprocess.check_output(tumour_cmd, text=True)
    tumour_reader = csv.DictReader(tumour_output.strip().split('\n'))
    
    # Track patient investigation counters
    patient_counters = {}
    investigations = []
    skipped_no_patient = 0
    skipped_no_episode = 0
    
    for row in tumour_reader:
        hosp_no = row.get('Hosp_No', '').strip()
        
        # Get NHS number from hosp_no
        nhs_no = hosp_to_nhs.get(hosp_no)
        if not nhs_no:
            skipped_no_patient += 1
            continue
        
        # Get patient_id from NHS number
        patient_id = patient_mapping.get(nhs_no)
        if not patient_id:
            skipped_no_patient += 1
            continue
        
        # Get episode_id from mapping
        episode_id = episode_mapping.get(patient_id)
        if not episode_id:
            skipped_no_episode += 1
            continue
        
        # Initialize counter for this patient
        if patient_id not in patient_counters:
            patient_counters[patient_id] = 1
        
        # Get surgery date for classification
        surgery_date = surgery_dates.get(hosp_no)
        
        # Process each investigation field
        for field, inv_type, subtype, description in inv_fields:
            inv_date = parse_access_date(row.get(field, ''))
            
            if inv_date:
                # Classify as pre-treatment or surveillance
                if surgery_date and inv_date >= surgery_date:
                    classification = 'surveillance'
                else:
                    classification = 'pre_treatment'
                
                # Generate investigation ID
                investigation_id = generate_investigation_id(patient_id, patient_counters[patient_id])
                patient_counters[patient_id] += 1
                
                # Create investigation document
                investigation = {
                    'investigation_id': investigation_id,
                    'patient_id': patient_id,
                    'episode_id': episode_id,
                    'type': inv_type,
                    'subtype': subtype,
                    'date': inv_date,
                    'result': None,  # Not available in Access DB
                    'findings': f"{description} - {classification}",
                    'notes': f"Imported from Access DB. Classification: {classification}",
                    'report_url': None,
                    'ordering_clinician': None,
                    'migrated_from_access': True
                }
                
                investigations.append(investigation)
    
    # Insert into MongoDB
    if investigations:
        print(f"\nInserting {len(investigations)} investigations...")
        result = db.investigations.insert_many(investigations)
        print(f"Successfully inserted {len(result.inserted_ids)} investigations")
    else:
        print("No investigations to insert")
    
    # Summary statistics
    print(f"\n=== Migration Summary ===")
    print(f"Total investigations imported: {len(investigations)}")
    print(f"Skipped (no patient mapping): {skipped_no_patient}")
    print(f"Skipped (no episode mapping): {skipped_no_episode}")
    
    # Count by type
    by_type = {}
    by_classification = {'pre_treatment': 0, 'surveillance': 0}
    
    for inv in investigations:
        subtype = inv['subtype']
        by_type[subtype] = by_type.get(subtype, 0) + 1
        
        if 'surveillance' in inv['notes']:
            by_classification['surveillance'] += 1
        else:
            by_classification['pre_treatment'] += 1
    
    print(f"\nBy investigation type:")
    for subtype, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
        print(f"  {subtype}: {count}")
    
    print(f"\nBy classification:")
    print(f"  Pre-treatment: {by_classification['pre_treatment']}")
    print(f"  Surveillance: {by_classification['surveillance']}")

if __name__ == '__main__':
    try:
        import_investigations()
        print("\n✓ Migration completed successfully")
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
