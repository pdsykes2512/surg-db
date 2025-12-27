#!/usr/bin/env python3
"""
Set admission_date to treatment_date for surgeries where admission_date is not specified.
"""

import os
from pymongo import MongoClient
from datetime import datetime

# MongoDB connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://admin:admin123@localhost:27017')
client = MongoClient(MONGODB_URI)
db = client.surgdb

def update_admission_dates(dry_run=False):
    """Update admission dates to match treatment dates where not specified"""
    
    # Find surgeries with treatment_date but no admission_date
    query = {
        'treatment_type': 'surgery',
        'treatment_date': {'$exists': True, '$ne': None},
        '$or': [
            {'admission_date': {'$exists': False}},
            {'admission_date': None}
        ]
    }
    
    treatments = list(db.treatments.find(query))
    print(f"Found {len(treatments):,} surgery treatments without admission_date")
    
    if len(treatments) == 0:
        print("No treatments need updating")
        return 0
    
    # Show sample before
    print("\nSample treatments before update:")
    print("="*80)
    for t in treatments[:3]:
        print(f"Treatment: {t.get('treatment_id')}")
        print(f"  treatment_date: {t.get('treatment_date')}")
        print(f"  admission_date: {t.get('admission_date')}")
    
    if dry_run:
        print(f"\nDRY RUN: Would update {len(treatments):,} treatments")
        return len(treatments)
    
    # Update treatments
    updated = 0
    for treatment in treatments:
        treatment_date = treatment.get('treatment_date')
        if treatment_date:
            result = db.treatments.update_one(
                {'_id': treatment['_id']},
                {
                    '$set': {
                        'admission_date': treatment_date,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            if result.modified_count > 0:
                updated += 1
        
        if updated % 100 == 0 and updated > 0:
            print(f"Updated {updated:,} treatments...")
    
    print("\n" + "="*80)
    print(f"Update completed!")
    print(f"  Total treatments: {len(treatments):,}")
    print(f"  Updated: {updated:,}")
    print("="*80)
    
    # Show sample after
    sample_ids = [t['_id'] for t in treatments[:3]]
    updated_samples = list(db.treatments.find({'_id': {'$in': sample_ids}}))
    
    print("\nSample treatments after update:")
    print("="*80)
    for t in updated_samples:
        print(f"Treatment: {t.get('treatment_id')}")
        print(f"  treatment_date: {t.get('treatment_date')}")
        print(f"  admission_date: {t.get('admission_date')}")
    
    return updated

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Update admission dates to match treatment dates')
    parser.add_argument('--dry-run', action='store_true', help='Dry run - show what would change')
    
    args = parser.parse_args()
    
    update_admission_dates(dry_run=args.dry_run)
