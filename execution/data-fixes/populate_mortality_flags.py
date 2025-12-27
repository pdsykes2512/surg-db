"""
Populate mortality_30day and mortality_90day boolean fields in treatments
based on patient deceased_date and treatment date.

This script calculates mortality for all existing treatments and sets the boolean flags.
"""

import os
import sys
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.utils.mortality import calculate_mortality_30d, calculate_mortality_90d


def populate_mortality_flags(dry_run=False):
    """
    Calculate and populate mortality_30day and mortality_90day flags for all treatments
    """
    load_dotenv()
    mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    
    client = MongoClient(mongo_uri)
    db = client['surgdb']
    
    patients_collection = db.patients
    treatments_collection = db.treatments
    
    print("=" * 80)
    print("POPULATING MORTALITY FLAGS")
    print("=" * 80)
    
    # Get all patients with deceased_date
    deceased_patients = list(patients_collection.find(
        {"deceased_date": {"$exists": True, "$ne": None}},
        {"patient_id": 1, "deceased_date": 1}
    ))
    
    print(f"\nFound {len(deceased_patients)} patients with deceased_date")
    
    # Build patient_id -> deceased_date mapping
    patient_deceased_dates = {
        p['patient_id']: p['deceased_date'] 
        for p in deceased_patients
    }
    
    # Get all treatments for these patients
    patient_ids = list(patient_deceased_dates.keys())
    treatments = list(treatments_collection.find({
        "patient_id": {"$in": patient_ids},
        "treatment_type": "surgery",
        "treatment_date": {"$exists": True, "$ne": None}
    }))
    
    print(f"Found {len(treatments)} surgical treatments for deceased patients")
    
    stats = {
        'total_treatments': len(treatments),
        'mortality_30day_set': 0,
        'mortality_90day_set': 0,
        'no_mortality': 0,
        'errors': 0
    }
    
    # Process each treatment
    for treatment in treatments:
        patient_id = treatment.get('patient_id')
        treatment_date = treatment.get('treatment_date')
        deceased_date = patient_deceased_dates.get(patient_id)
        
        if not treatment_date or not deceased_date:
            stats['errors'] += 1
            continue
        
        try:
            # Calculate mortality
            is_30d = calculate_mortality_30d(treatment_date, deceased_date)
            is_90d = calculate_mortality_90d(treatment_date, deceased_date)
            
            # Set boolean flags
            update_fields = {}
            
            if is_30d:
                update_fields['mortality_30day'] = True
                stats['mortality_30day_set'] += 1
            else:
                update_fields['mortality_30day'] = False
            
            if is_90d:
                update_fields['mortality_90day'] = True
                stats['mortality_90day_set'] += 1
            else:
                update_fields['mortality_90day'] = False
            
            if not is_30d and not is_90d:
                stats['no_mortality'] += 1
            
            # Update database
            if not dry_run and update_fields:
                treatments_collection.update_one(
                    {"_id": treatment['_id']},
                    {"$set": update_fields}
                )
                
        except Exception as e:
            print(f"Error processing treatment {treatment.get('treatment_id')}: {e}")
            stats['errors'] += 1
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total treatments processed: {stats['total_treatments']}")
    print(f"Treatments with 30-day mortality: {stats['mortality_30day_set']}")
    print(f"Treatments with 90-day mortality: {stats['mortality_90day_set']}")
    print(f"Treatments with no mortality (>90 days): {stats['no_mortality']}")
    print(f"Errors: {stats['errors']}")
    
    if dry_run:
        print("\n⚠️  DRY RUN - No changes made to database")
    else:
        print("\n✅ Mortality flags updated successfully")
    
    return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Populate mortality flags')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
    args = parser.parse_args()
    
    populate_mortality_flags(dry_run=args.dry_run)
