"""
Migrate existing IDs to new NHS Number-based format
Execution script to update all episodes, treatments, and tumours
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB_NAME", "surg_outcomes")


def generate_episode_id(nhs_number: str, count: int) -> str:
    """Generate episode ID in format EPI-NHSNUMBER-COUNT"""
    clean_nhs = nhs_number.replace(' ', '')
    incremental_num = str(count + 1).zfill(2)
    return f"EPI-{clean_nhs}-{incremental_num}"


def generate_treatment_id(treatment_type: str, nhs_number: str, count: int) -> str:
    """Generate treatment ID with type-specific prefix"""
    clean_nhs = nhs_number.replace(' ', '')
    incremental_num = str(count + 1).zfill(2)
    
    prefix_map = {
        'surgery': 'SUR',
        'chemotherapy': 'ONC',
        'radiotherapy': 'DXT',
        'immunotherapy': 'IMM'
    }
    
    prefix = prefix_map.get(treatment_type, 'TRE')
    return f"{prefix}-{clean_nhs}-{incremental_num}"


def generate_tumour_id(nhs_number: str, count: int) -> str:
    """Generate tumour ID in format TUM-NHSNUMBER-COUNT"""
    clean_nhs = nhs_number.replace(' ', '')
    incremental_num = str(count + 1).zfill(2)
    return f"TUM-{clean_nhs}-{incremental_num}"


async def migrate_ids():
    """Migrate all existing IDs to new format"""
    print(f"Connecting to MongoDB at {MONGODB_URI}...")
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    
    print(f"\n🔄 Starting ID migration for database: {DB_NAME}")
    print("=" * 60)
    
    # Get collections
    patients_col = db["patients"]
    episodes_col = db["episodes"]
    treatments_col = db["treatments"]
    tumours_col = db["tumours"]
    
    # Track changes
    stats = {
        'episodes_updated': 0,
        'treatments_updated': 0,
        'tumours_updated': 0,
        'errors': []
    }
    
    # 1. Migrate Episodes
    print("\n📋 Migrating Episodes...")
    print("-" * 60)
    
    # Get all patients
    patients = await patients_col.find({}).to_list(length=None)
    
    for patient in patients:
        patient_id = patient.get('record_number')
        nhs_number = patient.get('nhs_number')
        
        if not nhs_number:
            print(f"⚠️  Patient {patient_id} has no NHS number, skipping...")
            continue
        
        # Get episodes for this patient
        episodes = await episodes_col.find({'patient_id': patient_id}).sort('created_at', 1).to_list(length=None)
        
        for idx, episode in enumerate(episodes):
            old_episode_id = episode.get('episode_id')
            new_episode_id = generate_episode_id(nhs_number, idx)
            
            if old_episode_id == new_episode_id:
                continue  # Already in correct format
            
            print(f"  {old_episode_id} → {new_episode_id}")
            
            # Update episode ID
            await episodes_col.update_one(
                {'_id': episode['_id']},
                {
                    '$set': {
                        'episode_id': new_episode_id,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            # Update treatments that reference this episode
            await treatments_col.update_many(
                {'episode_id': old_episode_id},
                {'$set': {'episode_id': new_episode_id}}
            )
            
            # Update tumours that reference this episode
            await tumours_col.update_many(
                {'episode_id': old_episode_id},
                {'$set': {'episode_id': new_episode_id}}
            )
            
            stats['episodes_updated'] += 1
    
    # 2. Migrate Treatments
    print("\n💉 Migrating Treatments...")
    print("-" * 60)
    
    for patient in patients:
        patient_id = patient.get('record_number')
        nhs_number = patient.get('nhs_number')
        
        if not nhs_number:
            continue
        
        # Get all episodes for this patient
        episodes = await episodes_col.find({'patient_id': patient_id}).to_list(length=None)
        episode_ids = [ep['episode_id'] for ep in episodes]
        
        # Get treatments for this patient (across all episodes)
        treatments = await treatments_col.find(
            {'episode_id': {'$in': episode_ids}}
        ).sort('created_at', 1).to_list(length=None)
        
        # Group treatments by type for proper counting
        treatment_counts = {}
        
        for treatment in treatments:
            old_treatment_id = treatment.get('treatment_id')
            treatment_type = treatment.get('treatment_type', 'surgery')
            
            # Get count for this treatment type
            count = treatment_counts.get(treatment_type, 0)
            new_treatment_id = generate_treatment_id(treatment_type, nhs_number, count)
            treatment_counts[treatment_type] = count + 1
            
            if old_treatment_id == new_treatment_id:
                continue  # Already in correct format
            
            print(f"  {old_treatment_id} → {new_treatment_id}")
            
            # Update treatment ID
            await treatments_col.update_one(
                {'_id': treatment['_id']},
                {
                    '$set': {
                        'treatment_id': new_treatment_id,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            # Update tumours that reference this treatment
            await tumours_col.update_many(
                {'treated_by_treatment_ids': old_treatment_id},
                {
                    '$set': {
                        'treated_by_treatment_ids.$[elem]': new_treatment_id
                    }
                },
                array_filters=[{'elem': old_treatment_id}]
            )
            
            stats['treatments_updated'] += 1
    
    # 3. Migrate Tumours
    print("\n🎯 Migrating Tumours...")
    print("-" * 60)
    
    for patient in patients:
        patient_id = patient.get('record_number')
        nhs_number = patient.get('nhs_number')
        
        if not nhs_number:
            continue
        
        # Get all episodes for this patient
        episodes = await episodes_col.find({'patient_id': patient_id}).to_list(length=None)
        
        for episode in episodes:
            episode_id = episode['episode_id']
            
            # Get tumours for this episode
            tumours = await tumours_col.find(
                {'episode_id': episode_id}
            ).sort('created_at', 1).to_list(length=None)
            
            for idx, tumour in enumerate(tumours):
                old_tumour_id = tumour.get('tumour_id')
                new_tumour_id = generate_tumour_id(nhs_number, idx)
                
                if old_tumour_id == new_tumour_id:
                    continue  # Already in correct format
                
                print(f"  {old_tumour_id} → {new_tumour_id}")
                
                # Update tumour ID
                await tumours_col.update_one(
                    {'_id': tumour['_id']},
                    {
                        '$set': {
                            'tumour_id': new_tumour_id,
                            'updated_at': datetime.utcnow()
                        }
                    }
                )
                
                stats['tumours_updated'] += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("✅ Migration Complete!")
    print("=" * 60)
    print(f"Episodes updated:   {stats['episodes_updated']}")
    print(f"Treatments updated: {stats['treatments_updated']}")
    print(f"Tumours updated:    {stats['tumours_updated']}")
    
    if stats['errors']:
        print(f"\n⚠️  Errors encountered: {len(stats['errors'])}")
        for error in stats['errors'][:5]:  # Show first 5 errors
            print(f"  - {error}")
    
    client.close()


if __name__ == "__main__":
    print("\n⚠️  WARNING: This will update all IDs in the database!")
    response = input("Are you sure you want to proceed? (yes/no): ")
    
    if response.lower() == 'yes':
        asyncio.run(migrate_ids())
    else:
        print("Migration cancelled.")
