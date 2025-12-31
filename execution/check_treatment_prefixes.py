#!/usr/bin/env python3
"""Check treatment ID prefix patterns in the database"""

import asyncio
import sys
import os
from collections import Counter

# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv('/etc/impact/secrets.env')

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.database import Database, get_treatments_collection


async def main():
    from backend.app.config import settings
    await Database.connect_db()

    treatments_collection = await get_treatments_collection()

    # Get all treatments
    treatments = await treatments_collection.find({}).to_list(length=None)
    print(f"Total treatments: {len(treatments)}\n")

    # Count prefixes
    prefix_counter = Counter()
    type_counter = Counter()
    prefix_by_type = {}

    for treatment in treatments:
        treatment_id = treatment.get('treatment_id', '')
        treatment_type = treatment.get('treatment_type', 'unknown')

        # Extract prefix (everything before first hyphen)
        if '-' in treatment_id:
            prefix = treatment_id.split('-')[0]
            prefix_counter[prefix] += 1

            # Track what prefix is used for each type
            if treatment_type not in prefix_by_type:
                prefix_by_type[treatment_type] = Counter()
            prefix_by_type[treatment_type][prefix] += 1

        type_counter[treatment_type] += 1

    print("Treatment ID Prefixes:")
    for prefix, count in prefix_counter.most_common():
        print(f"  {prefix}-: {count} treatments")

    print("\nTreatment Types:")
    for ttype, count in type_counter.most_common():
        print(f"  {ttype}: {count} treatments")

    print("\nPrefix usage by treatment type:")
    for ttype, prefixes in sorted(prefix_by_type.items()):
        print(f"  {ttype}:")
        for prefix, count in prefixes.most_common():
            print(f"    {prefix}-: {count}")

    # Show sample of T- prefixed treatments
    print("\nSample of T- prefixed treatments (showing type):")
    t_treatments = [t for t in treatments if t.get('treatment_id', '').startswith('T-')][:5]
    for t in t_treatments:
        print(f"  {t.get('treatment_id')}: {t.get('treatment_type')}")

    await Database.close_db()


if __name__ == "__main__":
    asyncio.run(main())
