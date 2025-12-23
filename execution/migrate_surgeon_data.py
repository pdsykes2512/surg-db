#!/usr/bin/env python3
"""
Migrate and standardize surgeon data:
1. Set surgeon to lead_clinician when surgeon is missing
2. Format all surgeon names to Title Case
3. Create/update surgeon records in a separate historical_surgeons collection
"""

import os
import re
from pymongo import MongoClient
from datetime import datetime

# MongoDB connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://admin:admin123@localhost:27017')
client = MongoClient(MONGODB_URI)
db = client.surgdb

def format_name_title_case(name):
    """Format name to proper Title Case with special handling"""
    if not name or not isinstance(name, str):
        return None
    
    name = name.strip()
    
    # Handle all caps names
    if name.isupper():
        name = name.title()
    
    # Special cases
    special_cases = {
        "O'leary": "O'Leary",
        "O'LEARY": "O'Leary",
        "Mcdonald": "McDonald",
        "Mccarthy": "McCarthy",
        "Macgregor": "MacGregor",
    }
    
    for wrong, correct in special_cases.items():
        if name.lower() == wrong.lower():
            return correct
    
    # Handle hyphenated names
    if '-' in name:
        parts = name.split('-')
        name = '-'.join(p.capitalize() for p in parts)
    
    # Handle names with apostrophes (O'Brien, etc.)
    if "'" in name:
        parts = name.split("'")
        name = "'".join([parts[0].capitalize()] + [p.capitalize() for p in parts[1:]])
    
    # Standard title case
    if not name[0].isupper():
        name = name.capitalize()
    
    return name

def get_or_create_historical_surgeon(name, gmc_number=None):
    """Get or create a surgeon in the historical_surgeons collection"""
    if not name:
        return None
    
    formatted_name = format_name_title_case(name)
    
    # Check if surgeon already exists
    existing = db.historical_surgeons.find_one({
        'name': formatted_name
    })
    
    if existing:
        return existing
    
    # Create new historical surgeon record
    surgeon = {
        'name': formatted_name,
        'original_name': name,
        'gmc_number': gmc_number,
        'is_historical': True,
        'source': 'legacy_data',
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    
    result = db.historical_surgeons.insert_one(surgeon)
    surgeon['_id'] = result.inserted_id
    
    return surgeon

def migrate_surgeon_data(dry_run=False):
    """Migrate surgeon data from treatments and episodes"""
    
    print("Surgeon Data Migration")
    print("="*80)
    
    # Step 1: Set surgeon from lead_clinician where missing
    print("\nStep 1: Setting surgeon from lead_clinician...")
    
    treatments_without_surgeon = list(db.treatments.find({
        'treatment_type': 'surgery',
        '$or': [
            {'surgeon': {'$exists': False}},
            {'surgeon': None}
        ]
    }))
    
    print(f"Found {len(treatments_without_surgeon):,} treatments without surgeon")
    
    updated_from_lead = 0
    
    for treatment in treatments_without_surgeon:
        episode_id = treatment.get('episode_id')
        if not episode_id:
            continue
        
        episode = db.episodes.find_one({'episode_id': episode_id})
        if not episode:
            continue
        
        lead_clinician = episode.get('lead_clinician')
        if not lead_clinician:
            continue
        
        if not dry_run:
            db.treatments.update_one(
                {'_id': treatment['_id']},
                {
                    '$set': {
                        'surgeon': lead_clinician,
                        'surgeon_source': 'lead_clinician',
                        'updated_at': datetime.utcnow()
                    }
                }
            )
        
        updated_from_lead += 1
        
        if updated_from_lead % 100 == 0:
            print(f"  Updated {updated_from_lead:,} treatments...")
    
    print(f"Updated {updated_from_lead:,} treatments with lead_clinician")
    
    # Step 2: Collect all unique surgeons and format names
    print("\nStep 2: Collecting and formatting surgeon names...")
    
    pipeline = [
        {'$match': {'treatment_type': 'surgery', 'surgeon': {'$exists': True, '$ne': None}}},
        {'$group': {'_id': '$surgeon', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}}
    ]
    
    surgeon_stats = list(db.treatments.aggregate(pipeline))
    print(f"Found {len(surgeon_stats)} unique surgeons")
    
    # Create historical surgeon records and update treatment records
    print("\nStep 3: Creating historical surgeon records...")
    
    surgeon_map = {}  # original -> formatted
    created_surgeons = 0
    updated_treatments = 0
    
    for stat in surgeon_stats:
        original_name = stat['_id']
        formatted_name = format_name_title_case(original_name)
        
        if formatted_name:
            surgeon_map[original_name] = formatted_name
            
            # Create/get historical surgeon record
            if not dry_run:
                surgeon_record = get_or_create_historical_surgeon(original_name)
                if surgeon_record and surgeon_record.get('_id'):
                    created_surgeons += 1
    
    print(f"Created/updated {created_surgeons} historical surgeon records")
    
    # Step 4: Update all treatment records with formatted names
    print("\nStep 4: Updating treatment records with formatted names...")
    
    for original, formatted in surgeon_map.items():
        if original != formatted:
            if not dry_run:
                result = db.treatments.update_many(
                    {'treatment_type': 'surgery', 'surgeon': original},
                    {
                        '$set': {
                            'surgeon': formatted,
                            'original_surgeon_name': original,
                            'updated_at': datetime.utcnow()
                        }
                    }
                )
                updated_treatments += result.modified_count
    
    print(f"Updated {updated_treatments:,} treatment records with formatted names")
    
    # Summary statistics
    print("\n" + "="*80)
    print(f"Migration {'(DRY RUN) ' if dry_run else ''}Summary:")
    print(f"  Treatments updated from lead_clinician: {updated_from_lead:,}")
    print(f"  Historical surgeons created: {created_surgeons}")
    print(f"  Treatment names formatted: {updated_treatments:,}")
    
    # Show sample surgeons
    print("\nSample Historical Surgeons:")
    print("-" * 80)
    for surgeon in db.historical_surgeons.find().limit(20):
        original = surgeon.get('original_name')
        formatted = surgeon.get('name')
        if original != formatted:
            print(f"  {original:20s} → {formatted}")
        else:
            print(f"  {formatted}")
    
    return {
        'updated_from_lead': updated_from_lead,
        'created_surgeons': created_surgeons,
        'updated_treatments': updated_treatments
    }

def show_surgeon_statistics():
    """Show statistics about surgeon data"""
    print("\n" + "="*80)
    print("Final Surgeon Statistics:")
    print("="*80)
    
    total_surgeries = db.treatments.count_documents({'treatment_type': 'surgery'})
    has_surgeon = db.treatments.count_documents({
        'treatment_type': 'surgery',
        'surgeon': {'$exists': True, '$ne': None}
    })
    
    print(f"Total surgeries: {total_surgeries:,}")
    print(f"With surgeon data: {has_surgeon:,} ({has_surgeon/total_surgeries*100:.1f}%)")
    
    from_lead = db.treatments.count_documents({
        'treatment_type': 'surgery',
        'surgeon_source': 'lead_clinician'
    })
    print(f"  From lead_clinician: {from_lead:,}")
    print(f"  From original data: {has_surgeon - from_lead:,}")
    
    historical_count = db.historical_surgeons.count_documents({})
    print(f"\nHistorical surgeons: {historical_count}")
    
    # Top surgeons
    print("\nTop 10 surgeons by case volume:")
    pipeline = [
        {'$match': {'treatment_type': 'surgery', 'surgeon': {'$exists': True, '$ne': None}}},
        {'$group': {'_id': '$surgeon', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 10}
    ]
    
    for stat in db.treatments.aggregate(pipeline):
        print(f"  {stat['_id']:20s} {stat['count']:>4,} cases")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate and standardize surgeon data')
    parser.add_argument('--dry-run', action='store_true', help='Dry run - show what would change')
    parser.add_argument('--stats', action='store_true', help='Show statistics only')
    
    args = parser.parse_args()
    
    if args.stats:
        show_surgeon_statistics()
    else:
        result = migrate_surgeon_data(dry_run=args.dry_run)
        if not args.dry_run:
            show_surgeon_statistics()
