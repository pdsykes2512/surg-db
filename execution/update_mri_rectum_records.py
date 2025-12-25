#!/usr/bin/env python3
"""
Update all investigations with 'MRI Rectum' to 'MRI Pelvis/Rectum'
"""

import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection
MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://admin:admin123@surg-db.vps:27017/surgdb?authSource=admin')

def update_mri_rectum_records():
    """Update all investigations with 'MRI Rectum' to 'MRI Pelvis/Rectum'"""
    
    client = MongoClient(MONGODB_URL)
    db = client.surgdb
    
    # Find all investigations with subtype containing 'MRI Rectum'
    # Check for various possible formats
    queries = [
        {'type': 'imaging', 'subtype': 'MRI Rectum'},
        {'type': 'imaging', 'subtype': 'mri_rectum'},
        {'subtype': 'MRI Rectum'},
        {'subtype': 'mri_rectum'},
    ]
    
    total_updated = 0
    
    for query in queries:
        count_before = db.investigations.count_documents(query)
        if count_before > 0:
            print(f"Found {count_before} investigations matching: {query}")
            
            # Update the records
            result = db.investigations.update_many(
                query,
                {'$set': {'subtype': 'mri_pelvis_rectum'}}
            )
            
            print(f"  Updated {result.modified_count} records")
            total_updated += result.modified_count
    
    if total_updated == 0:
        print("No 'MRI Rectum' records found to update.")
        print("\nChecking what imaging subtypes exist:")
        imaging_subtypes = db.investigations.distinct('subtype', {'type': 'imaging'})
        for subtype in sorted(imaging_subtypes) if imaging_subtypes else []:
            count = db.investigations.count_documents({'type': 'imaging', 'subtype': subtype})
            print(f"  {subtype}: {count}")
    else:
        print(f"\nTotal updated: {total_updated} investigations")
        
        # Verify the update
        new_count = db.investigations.count_documents({'subtype': 'mri_pelvis_rectum'})
        print(f"'mri_pelvis_rectum' records now: {new_count}")
    
    client.close()

if __name__ == '__main__':
    update_mri_rectum_records()
