#!/usr/bin/env python3
"""
Migration script to convert surgeon surname-only fields to full names.
Looks up surnames in the surgeons collection and updates treatment records.
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

async def main():
    # Use the correct database name
    mongo_uri = 'mongodb://admin:admin123@localhost:27017/surg_outcomes?authSource=admin'
    db_name = 'surg_outcomes'
    
    print(f"Connecting to MongoDB database: {db_name}...")
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    try:
        # First, get all surgeons to create a lookup map
        print("Loading surgeons...")
        surgeons = await db.surgeons.find({}).to_list(length=1000)
        
        # Create lookup: surname -> full name
        surgeon_lookup = {}
        for surgeon in surgeons:
            surname = surgeon.get('surname', '').strip()
            first_name = surgeon.get('first_name', '').strip()
            if surname and first_name:
                full_name = f"{first_name} {surname}"
                surgeon_lookup[surname.lower()] = full_name
                # Also store the full name mapping to itself for idempotency
                surgeon_lookup[full_name.lower()] = full_name
        
        print(f"Loaded {len(surgeons)} surgeons, created {len(surgeon_lookup)} lookup entries")
        
        # Update episodes with lead_clinician
        print("\nUpdating lead_clinician fields...")
        episodes = await db.episodes.find({
            'lead_clinician': {'$exists': True, '$ne': ''}
        }).to_list(length=10000)
        
        lead_clinician_updates = 0
        for episode in episodes:
            lead_clinician = episode.get('lead_clinician', '').strip()
            if not lead_clinician:
                continue
            
            # Check if it's already a full name (contains space) or needs updating
            full_name = surgeon_lookup.get(lead_clinician.lower())
            
            if full_name and full_name != lead_clinician:
                await db.episodes.update_one(
                    {'_id': episode['_id']},
                    {
                        '$set': {
                            'lead_clinician': full_name,
                            'last_modified_at': datetime.utcnow()
                        }
                    }
                )
                lead_clinician_updates += 1
                print(f"  Updated episode {episode.get('episode_id', 'N/A')}: '{lead_clinician}' → '{full_name}'")
        
        print(f"✓ Updated {lead_clinician_updates} lead_clinician fields")
        
        # Update treatment surgeon fields
        print("\nUpdating treatment surgeon/oncologist fields...")
        episodes_with_treatments = await db.episodes.find({
            'treatments': {'$exists': True, '$ne': []}
        }).to_list(length=10000)
        
        treatment_updates = 0
        for episode in episodes_with_treatments:
            treatments = episode.get('treatments', [])
            updated = False
            
            for treatment in treatments:
                # Update surgeon field
                surgeon = treatment.get('surgeon', '').strip()
                if surgeon:
                    full_name = surgeon_lookup.get(surgeon.lower())
                    if full_name and full_name != surgeon:
                        treatment['surgeon'] = full_name
                        updated = True
                        print(f"  Episode {episode.get('episode_id')}, Treatment {treatment.get('treatment_id')}: surgeon '{surgeon}' → '{full_name}'")
                
                # Update oncologist field
                oncologist = treatment.get('oncologist', '').strip()
                if oncologist:
                    full_name = surgeon_lookup.get(oncologist.lower())
                    if full_name and full_name != oncologist:
                        treatment['oncologist'] = full_name
                        updated = True
                        print(f"  Episode {episode.get('episode_id')}, Treatment {treatment.get('treatment_id')}: oncologist '{oncologist}' → '{full_name}'")
            
            if updated:
                await db.episodes.update_one(
                    {'_id': episode['_id']},
                    {
                        '$set': {
                            'treatments': treatments,
                            'last_modified_at': datetime.utcnow()
                        }
                    }
                )
                treatment_updates += 1
        
        print(f"✓ Updated treatments in {treatment_updates} episodes")
        
        print("\n" + "="*60)
        print("Migration completed successfully!")
        print(f"  Lead clinician fields updated: {lead_clinician_updates}")
        print(f"  Episodes with treatment updates: {treatment_updates}")
        print("="*60)
        
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == '__main__':
    asyncio.run(main())
