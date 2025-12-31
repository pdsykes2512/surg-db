#!/usr/bin/env python3
"""Quick script to check what's in the treatments and tumours collections"""

import asyncio
import sys
import os

# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv('/etc/impact/secrets.env')

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.database import Database, get_episodes_collection, get_treatments_collection, get_tumours_collection


async def main():
    from backend.app.config import settings
    await Database.connect_db()

    treatments_collection = await get_treatments_collection()
    tumours_collection = await get_tumours_collection()
    episodes_collection = await get_episodes_collection()

    treatment_count = await treatments_collection.count_documents({})
    tumour_count = await tumours_collection.count_documents({})
    episode_count = await episodes_collection.count_documents({})

    print(f"Episodes: {episode_count}")
    print(f"Treatments (separate collection): {treatment_count}")
    print(f"Tumours (separate collection): {tumour_count}")

    # Check a sample episode
    episode = await episodes_collection.find_one({"episode_id": "E-BDC741-01"})
    if episode:
        print(f"\nSample episode E-BDC741-01:")
        print(f"  - treatment_ids: {episode.get('treatment_ids', [])}")
        print(f"  - tumour_ids: {episode.get('tumour_ids', [])}")
        print(f"  - treatments (embedded): {len(episode.get('treatments', []))}")
        print(f"  - tumours (embedded): {len(episode.get('tumours', []))}")

    # Check for treatments with this episode
    treatments = await treatments_collection.find({"episode_id": "E-BDC741-01"}).to_list(length=None)
    print(f"\nTreatments in separate collection for E-BDC741-01: {len(treatments)}")
    for t in treatments:
        print(f"  - {t.get('treatment_id')}: {t.get('treatment_type')}")

    await Database.close_db()


if __name__ == "__main__":
    asyncio.run(main())
