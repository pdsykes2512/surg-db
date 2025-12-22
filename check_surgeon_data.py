#!/usr/bin/env python3
"""Check surgeon field formats in the database"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    # Get MongoDB credentials
    mongo_user = os.getenv('MONGO_INITDB_ROOT_USERNAME', 'admin')
    mongo_pass = os.getenv('MONGO_INITDB_ROOT_PASSWORD', 'password')
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(f'mongodb://{mongo_user}:{mongo_pass}@localhost:27017/')
    db = client['surgical_database']
    
    print("Checking surgeon field formats in database...\n")
    
    # Check treatments
    episodes_with_treatments = await db.episodes.find({
        'treatments': {'$exists': True, '$ne': []}
    }).limit(3).to_list(length=3)
    
    print("=" * 60)
    print("TREATMENT SURGEON FIELDS:")
    print("=" * 60)
    for ep in episodes_with_treatments:
        print(f"\nEpisode: {ep.get('episode_id', 'N/A')}")
        for idx, treatment in enumerate(ep.get('treatments', [])[:2], 1):
            print(f"  Treatment {idx}:")
            surgeon = treatment.get('surgeon', '')
            oncologist = treatment.get('oncologist', '')
            if surgeon:
                print(f"    surgeon: '{surgeon}' (length: {len(surgeon)})")
            if oncologist:
                print(f"    oncologist: '{oncologist}' (length: {len(oncologist)})")
    
    # Check lead_clinician
    print("\n" + "=" * 60)
    print("LEAD CLINICIAN FIELDS:")
    print("=" * 60)
    episodes = await db.episodes.find({}).limit(5).to_list(length=5)
    for ep in episodes:
        lc = ep.get('lead_clinician', '')
        eid = ep.get('episode_id', 'N/A')
        if lc:
            print(f"Episode {eid}: '{lc}' (length: {len(lc)})")
    
    client.close()

if __name__ == '__main__':
    asyncio.run(main())
