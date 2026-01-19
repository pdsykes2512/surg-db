#!/usr/bin/env python3
"""
Fix duplicate surgeon names in episodes collection.

This script standardizes lead_clinician names to match the canonical names
from the clinicians collection, eliminating name variants that cause
duplicate entries in reports.

Usage:
    python execution/fix_duplicate_surgeon_names.py [--dry-run]
"""
import asyncio
import argparse
from motor.motor_asyncio import AsyncIOMotorClient
import sys
import os

# Add backend directory to path to import app modules
backend_dir = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_dir)

from app.config import settings


# Mapping of incorrect variants to canonical names
# IMPORTANT: Only include true duplicates (surname-only variants of full names)
# Do NOT include different people who happen to share a surname
NAME_CORRECTIONS = {
    # Dan O'Leary variants (surname only)
    "O'Leary": "Dan O'Leary",

    # Filippos Sagias variants (surname only)
    "Sagias": "Filippos Sagias",

    # Jim Khan variants (surname only)
    # NOTE: "Khan L" and "Khan Omar" are DIFFERENT surgeons, not variants of Jim Khan
    "Khan": "Jim Khan",

    # John Conti variants (surname only)
    "Conti": "John Conti",

    # John Richardson variants (surname only)
    "Richardson": "John Richardson",

    # Paul Sykes variants (surname only)
    "Sykes": "Paul Sykes"
}


async def fix_surgeon_names(dry_run: bool = False):
    """Fix duplicate surgeon names in episodes collection"""
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]

    print("\n" + "="*70)
    print("SURGEON NAME STANDARDIZATION")
    print("="*70)

    if dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made\n")
    else:
        print("\n⚠️  LIVE MODE - Database will be modified\n")

    total_updated = 0

    for incorrect_name, canonical_name in NAME_CORRECTIONS.items():
        # Count episodes with incorrect name
        count = await db.episodes.count_documents({"lead_clinician": incorrect_name})

        if count == 0:
            print(f"✓ '{incorrect_name}' -> '{canonical_name}': No episodes found (already fixed)")
            continue

        print(f"\n📝 '{incorrect_name}' -> '{canonical_name}': {count} episodes")

        if not dry_run:
            # Update all episodes with this incorrect name
            result = await db.episodes.update_many(
                {"lead_clinician": incorrect_name},
                {"$set": {"lead_clinician": canonical_name}}
            )

            print(f"   ✅ Updated {result.modified_count} episodes")
            total_updated += result.modified_count
        else:
            print(f"   (would update {count} episodes)")
            total_updated += count

    print("\n" + "="*70)
    if dry_run:
        print(f"DRY RUN COMPLETE: Would update {total_updated} total episodes")
    else:
        print(f"✅ COMPLETE: Updated {total_updated} total episodes")
    print("="*70 + "\n")

    await client.close()

    return total_updated


async def verify_fixes():
    """Verify that no duplicate variants remain"""
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]
    system_db = client[settings.mongodb_system_db_name]

    print("\n" + "="*70)
    print("VERIFICATION")
    print("="*70 + "\n")

    # Get all surgeons
    clinicians = await system_db.clinicians.find(
        {"clinical_role": "surgeon"},
        {"first_name": 1, "surname": 1}
    ).to_list(length=None)

    canonical_names = set()
    for clinician in clinicians:
        first = clinician.get('first_name', '')
        surname = clinician.get('surname', '')
        if first and surname:
            canonical_names.add(f"{first} {surname}")

    # Check for any remaining variants
    pipeline = [
        {"$match": {"lead_clinician": {"$ne": None}}},
        {"$group": {"_id": "$lead_clinician", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]

    lead_clinicians = await db.episodes.aggregate(pipeline).to_list(length=None)

    issues_found = False
    for item in lead_clinicians:
        name = item['_id']
        count = item['count']

        # Check if this matches any canonical name
        if name not in canonical_names:
            issues_found = True
            print(f"⚠️  Non-canonical name found: '{name}' ({count} episodes)")

    if not issues_found:
        print("✅ All lead_clinician names match canonical surgeon names!")

    print("\n" + "="*70 + "\n")

    await client.close()


def main():
    parser = argparse.ArgumentParser(
        description="Fix duplicate surgeon names in episodes collection"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Show what would be changed without modifying database"
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help="Only verify data, don't make changes"
    )

    args = parser.parse_args()

    if args.verify_only:
        asyncio.run(verify_fixes())
    else:
        asyncio.run(fix_surgeon_names(dry_run=args.dry_run))

        if not args.dry_run:
            # Verify after fixing
            asyncio.run(verify_fixes())


if __name__ == "__main__":
    main()
