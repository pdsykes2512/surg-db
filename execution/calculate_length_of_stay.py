#!/usr/bin/env python3
"""
Calculate and update length_of_stay where admission and discharge dates are available.
"""

import os
from pymongo import MongoClient
from datetime import datetime

# MongoDB connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://admin:admin123@localhost:27017')
client = MongoClient(MONGODB_URI)
db = client.surgdb

def calculate_length_of_stay(dry_run=False):
    """Calculate length of stay from admission and discharge dates"""
    
    # Find treatments with both dates but no LOS recorded
    query = {
        'treatment_type': 'surgery',
        'admission_date': {'$exists': True, '$ne': None},
        'discharge_date': {'$exists': True, '$ne': None},
        '$or': [
            {'length_of_stay': {'$exists': False}},
            {'length_of_stay': None}
        ]
    }
    
    treatments = list(db.treatments.find(query))
    print(f"Found {len(treatments):,} treatments with dates but no length_of_stay")
    
    if len(treatments) == 0:
        print("No treatments need updating")
        return 0
    
    # Show sample before
    print("\nSample calculations:")
    print("="*80)
    for t in treatments[:5]:
        adm = t.get('admission_date')
        dis = t.get('discharge_date')
        if adm and dis:
            try:
                adm_dt = datetime.strptime(adm, '%Y-%m-%d')
                dis_dt = datetime.strptime(dis, '%Y-%m-%d')
                los = (dis_dt - adm_dt).days
                print(f"Treatment: {t.get('treatment_id')}")
                print(f"  Admission: {adm}, Discharge: {dis} → LOS: {los} days")
            except:
                pass
    
    if dry_run:
        print(f"\nDRY RUN: Would update {len(treatments):,} treatments")
        return len(treatments)
    
    # Calculate and update
    updated = 0
    errors = 0
    
    for treatment in treatments:
        try:
            adm = treatment.get('admission_date')
            dis = treatment.get('discharge_date')
            
            if not adm or not dis:
                continue
            
            adm_dt = datetime.strptime(adm, '%Y-%m-%d')
            dis_dt = datetime.strptime(dis, '%Y-%m-%d')
            los = (dis_dt - adm_dt).days
            
            # Only update if LOS is reasonable (0-365 days)
            if 0 <= los <= 365:
                result = db.treatments.update_one(
                    {'_id': treatment['_id']},
                    {
                        '$set': {
                            'length_of_stay': los,
                            'updated_at': datetime.utcnow()
                        }
                    }
                )
                if result.modified_count > 0:
                    updated += 1
            else:
                errors += 1
                if errors <= 5:
                    print(f"Skipping {treatment.get('treatment_id')}: LOS {los} days is unreasonable")
        
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"Error processing {treatment.get('treatment_id')}: {e}")
            continue
        
        if updated % 100 == 0 and updated > 0:
            print(f"Updated {updated:,} treatments...")
    
    print("\n" + "="*80)
    print(f"Update completed!")
    print(f"  Total candidates: {len(treatments):,}")
    print(f"  Updated: {updated:,}")
    print(f"  Errors/Skipped: {errors}")
    print("="*80)
    
    # Statistics
    los_stats = db.treatments.aggregate([
        {'$match': {'treatment_type': 'surgery', 'length_of_stay': {'$exists': True}}},
        {'$group': {
            '_id': None,
            'count': {'$sum': 1},
            'avg': {'$avg': '$length_of_stay'},
            'min': {'$min': '$length_of_stay'},
            'max': {'$max': '$length_of_stay'}
        }}
    ])
    
    for stat in los_stats:
        print(f"\nLength of Stay Statistics:")
        print(f"  Treatments with LOS: {stat['count']:,}")
        print(f"  Average: {stat['avg']:.1f} days")
        print(f"  Range: {stat['min']}-{stat['max']} days")
    
    return updated

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Calculate length of stay from dates')
    parser.add_argument('--dry-run', action='store_true', help='Dry run - show what would change')
    
    args = parser.parse_args()
    
    calculate_length_of_stay(dry_run=args.dry_run)
