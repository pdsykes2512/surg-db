#!/usr/bin/env python3
"""Check what episode_id format is used in treatments"""

import asyncio
import sys
import os

# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv('/etc/impact/secrets.env')

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.database import Database, get_episodes_collection, get_treatments_collection


async def main():
    from backend.app.config import settings
    await Database.connect_db()

    treatments_collection = await get_treatments_collection()
    episodes_collection = await get_episodes_collection()

    # Get the episode document to see its _id
    episode = await episodes_collection.find_one({"episode_id": "E-BDC741-01"})
    if episode:
        print(f"Episode E-BDC741-01:")
        print(f"  - _id (ObjectId): {episode.get('_id')}")
        print(f"  - episode_id (semantic): {episode.get('episode_id')}")

    # Check what treatments exist with episode_id matching the ObjectId
    print(f"\nSearching treatments by episode_id = ObjectId('{episode.get('_id')}')")
    treatments_by_oid = await treatments_collection.find({"episode_id": str(episode.get('_id'))}).to_list(length=None)
    print(f"  Found {len(treatments_by_oid)} treatments")
    for t in treatments_by_oid[:3]:
        print(f"    - {t.get('treatment_id')}: {t.get('treatment_type')} (episode_id = {t.get('episode_id')})")

    # Check what treatments exist with episode_id matching the semantic ID
    print(f"\nSearching treatments by episode_id = 'E-BDC741-01'")
    treatments_by_semantic = await treatments_collection.find({"episode_id": "E-BDC741-01"}).to_list(length=None)
    print(f"  Found {len(treatments_by_semantic)} treatments")
    for t in treatments_by_semantic[:3]:
        print(f"    - {t.get('treatment_id')}: {t.get('treatment_type')} (episode_id = {t.get('episode_id')})")

    # Sample a few treatments to see what episode_id format they use
    print(f"\nSample of 5 random treatments to see episode_id format:")
    sample_treatments = await treatments_collection.find({}).limit(5).to_list(length=None)
    for t in sample_treatments:
        print(f"  - treatment_id: {t.get('treatment_id')}, episode_id: {t.get('episode_id')}")

    await Database.close_db()


if __name__ == "__main__":
    asyncio.run(main())
