#!/usr/bin/env python3
"""
Link treatment surgeon fields to clinician IDs
Finds treatments where surgeon is a name string matching a clinician
and updates them to use the clinician's _id instead
"""

import os
import sys
from pymongo import MongoClient
from bson import ObjectId

def link_surgeons():
    """Link surgeon names in treatments to clinician IDs"""
    
    # Connect to MongoDB
    mongo_uri = os.getenv('MONGODB_URI', 'mongodb://admin:admin123@localhost:27017')
    client = MongoClient(mongo_uri)
    db = client.surgdb
    
    treatments_collection = db.treatments
    clinicians_collection = db.clinicians
    
    print("LINKING SURGEON NAMES TO CLINICIAN IDS")
    print("="*80)
    
    # Get all surgeons from clinician table
    clinicians = list(clinicians_collection.find({"clinical_role": "surgeon"}))
    
    print(f"\nFound {len(clinicians)} surgeons in clinician table")
    
    total_updated = 0
    
    for clinician in clinicians:
        first_name = clinician.get('first_name', '')
        surname = clinician.get('surname', '')
        full_name = f"{first_name} {surname}".strip()
        clinician_id_str = str(clinician['_id'])
        
        print(f"\n{full_name} (ID: {clinician_id_str})")
        print("-" * 80)
        
        # Create list of name patterns to search for
        patterns_to_check = [
            full_name,                                          # "Paul Sykes"
            f"{surname} {first_name}",                          # "Sykes Paul"
            f"{surname}, {first_name}",                         # "Sykes, Paul"
            f"{first_name[0]}. {surname}" if first_name else None,  # "P. Sykes"
            f"{surname} {first_name[0]}." if first_name else None,  # "Sykes P."
            surname,                                            # Just "Sykes"
        ]
        
        patterns_to_check = [p for p in patterns_to_check if p]
        
        clinician_updates = 0
        
        for pattern in patterns_to_check:
            # Find treatments with this exact pattern (case insensitive)
            matching_treatments = treatments_collection.count_documents({
                "surgeon": {"$regex": f"^{pattern}$", "$options": "i"}
            })
            
            if matching_treatments > 0:
                # Update all matching treatments
                result = treatments_collection.update_many(
                    {"surgeon": {"$regex": f"^{pattern}$", "$options": "i"}},
                    {"$set": {"surgeon": clinician_id_str}}
                )
                
                if result.modified_count > 0:
                    print(f"  Pattern '{pattern}': Updated {result.modified_count} treatments")
                    clinician_updates += result.modified_count
        
        if clinician_updates > 0:
            total_updated += clinician_updates
            print(f"  Total for {full_name}: {clinician_updates} treatments linked")
    
    print("\n" + "="*80)
    print(f"SUMMARY: Linked {total_updated} treatments to clinician IDs")
    print("="*80)
    
    # Verify the results
    print("\nVerification:")
    for clinician in clinicians:
        clinician_id_str = str(clinician['_id'])
        full_name = f"{clinician.get('first_name', '')} {clinician.get('surname', '')}".strip()
        
        count = treatments_collection.count_documents({"surgeon": clinician_id_str})
        print(f"  {full_name}: {count} treatments")

if __name__ == "__main__":
    link_surgeons()
