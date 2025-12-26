#!/usr/bin/env python3
"""
Export episodes without lead_clinician to CSV for manual data entry.
Focuses on recent episodes (past 5 years) as priority.
"""

import csv
from datetime import datetime, timedelta
from pymongo import MongoClient

# MongoDB connection
client = MongoClient('mongodb://admin:admin123@localhost:27017')
db = client.surgdb

# Calculate 5-year cutoff
cutoff_date = datetime.now() - timedelta(days=5*365)

# Find episodes without lead_clinician
episodes_cursor = db.episodes.find({
    '$or': [
        {'lead_clinician': {'$exists': False}},
        {'lead_clinician': None},
        {'lead_clinician': ''}
    ]
})

episodes = []
recent_count = 0

for ep in episodes_cursor:
    # Get the most relevant date
    referral_date = ep.get('referral_date')
    first_seen_date = ep.get('first_seen_date')
    
    date_obj = None
    date_source = None
    
    if referral_date:
        if isinstance(referral_date, str):
            try:
                date_obj = datetime.fromisoformat(referral_date.replace('Z', '+00:00'))
            except:
                pass
        elif isinstance(referral_date, datetime):
            date_obj = referral_date
        date_source = 'referral'
    
    if not date_obj and first_seen_date:
        if isinstance(first_seen_date, str):
            try:
                date_obj = datetime.fromisoformat(first_seen_date.replace('Z', '+00:00'))
            except:
                pass
        elif isinstance(first_seen_date, datetime):
            date_obj = first_seen_date
        date_source = 'first_seen'
    
    # Check if recent (past 5 years)
    is_recent = date_obj and date_obj >= cutoff_date
    
    if is_recent:
        recent_count += 1
        
        # Get patient info
        patient_id = ep.get('patient_id', '')
        patient = db.patients.find_one({'patient_id': patient_id}) if patient_id else None
        
        # Get treatment info
        treatment_ids = ep.get('treatment_ids', [])
        treatments = list(db.treatments.find({'treatment_id': {'$in': treatment_ids}})) if treatment_ids else []
        
        # Extract surgery info if available
        surgeries = [t for t in treatments if t.get('treatment_type') == 'surgery']
        surgery_info = []
        for surg in surgeries:
            surgery_date = surg.get('treatment_date', '')
            surgery_type = surg.get('surgery_type', '')
            surgeon = surg.get('surgeon', '')
            if surgery_date or surgery_type:
                surgery_info.append(f"{surgery_type} on {surgery_date}" if surgery_date else surgery_type)
        
        episodes.append({
            'episode_id': ep.get('episode_id', ''),
            'patient_id': patient_id,
            'patient_nhs_number': patient.get('nhs_number', '') if patient else '',
            'patient_hospital_number': patient.get('hospital_number', '') if patient else '',
            'cancer_type': ep.get('cancer_type', ''),
            'date': date_obj.strftime('%Y-%m-%d') if date_obj else '',
            'date_source': date_source or '',
            'tumour_site': ep.get('tumour_site', ''),
            'stage': ep.get('stage', ''),
            'treatments_count': len(treatments),
            'surgeries_count': len(surgeries),
            'surgery_details': '; '.join(surgery_info) if surgery_info else '',
            'current_lead_clinician': ep.get('lead_clinician', ''),
            'notes': ''  # Empty column for manual entry
        })

# Sort by date (newest first)
episodes.sort(key=lambda x: x['date'], reverse=True)

# Write to CSV
output_file = '/root/.tmp/missing_lead_clinician_recent.csv'
fieldnames = [
    'episode_id', 'patient_id', 'patient_nhs_number', 'patient_hospital_number',
    'cancer_type', 'date', 'date_source', 'tumour_site', 'stage',
    'treatments_count', 'surgeries_count', 'surgery_details',
    'current_lead_clinician', 'notes'
]

with open(output_file, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(episodes)

print(f"Exported {len(episodes)} recent episodes without lead_clinician")
print(f"Output file: {output_file}")
print(f"\nColumns:")
for i, field in enumerate(fieldnames, 1):
    print(f"  {i}. {field}")
print(f"\nNext steps:")
print(f"1. Review CSV and add surgeon names to 'notes' column")
print(f"2. Use a follow-up script to import the data back to MongoDB")
