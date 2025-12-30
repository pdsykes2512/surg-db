#!/usr/bin/env python3
"""
Populate Provider Codes for All Episodes and Treatments

Sets provider_first_seen (CR1410) for all episodes and provider_organisation (CR1450)
for all treatments to RHU (Portsmouth Hospitals University NHS Trust).

Author: IMPACT Data Migration
Date: 2025-12-30
"""

import os
import sys
import argparse
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment
load_dotenv('/etc/impact/secrets.env')
load_dotenv('.env')


def populate_provider_codes(db_name='impact_test', provider_code='RHU', dry_run=True):
    """
    Populate provider codes for all episodes and treatments

    Args:
        db_name: Database name
        provider_code: NHS Trust code to assign (default: RHU)
        dry_run: If True, only print what would be done (default: True)
    """
    # Connect to MongoDB
    mongo_uri = os.getenv('MONGODB_URI')
    if not mongo_uri:
        raise ValueError("MONGODB_URI not found in environment")

    client = MongoClient(mongo_uri)
    db = client[db_name]

    print(f"\n{'DRY RUN - ' if dry_run else ''}Populating provider codes with: {provider_code}")
    print(f"Database: {db_name}\n")

    # Update episodes
    print("=" * 80)
    print("UPDATING EPISODES (provider_first_seen)")
    print("=" * 80)

    total_episodes = db.episodes.count_documents({})
    episodes_with_correct_provider = db.episodes.count_documents({"provider_first_seen": provider_code})
    episodes_with_different_provider = db.episodes.count_documents({
        "provider_first_seen": {"$exists": True, "$ne": provider_code, "$ne": None}
    })
    episodes_without_provider = total_episodes - episodes_with_correct_provider - episodes_with_different_provider

    print(f"Total episodes: {total_episodes}")
    print(f"Already have provider_first_seen = {provider_code}: {episodes_with_correct_provider}")
    print(f"Have different provider_first_seen: {episodes_with_different_provider}")
    print(f"Missing provider_first_seen: {episodes_without_provider}")

    # Show what values exist
    existing_providers = db.episodes.distinct("provider_first_seen")
    print(f"\nExisting provider values: {existing_providers}")

    if not dry_run:
        # Update ALL episodes to have the specified provider code
        result = db.episodes.update_many(
            {},  # Match all episodes
            {"$set": {"provider_first_seen": provider_code}}
        )
        print(f"\n✓ Updated {result.modified_count} episodes to provider_first_seen = {provider_code}")
    else:
        episodes_to_update = episodes_with_different_provider + episodes_without_provider
        print(f"\n[DRY RUN] Would update {episodes_to_update} episodes")

    # Update treatments
    print("\n" + "=" * 80)
    print("UPDATING TREATMENTS (provider_organisation)")
    print("=" * 80)

    total_treatments = db.treatments.count_documents({})
    treatments_with_correct_provider = db.treatments.count_documents({"provider_organisation": provider_code})
    treatments_with_different_provider = db.treatments.count_documents({
        "provider_organisation": {"$exists": True, "$ne": provider_code, "$ne": None}
    })
    treatments_without_provider = total_treatments - treatments_with_correct_provider - treatments_with_different_provider

    print(f"Total treatments: {total_treatments}")
    print(f"Already have provider_organisation = {provider_code}: {treatments_with_correct_provider}")
    print(f"Have different provider_organisation: {treatments_with_different_provider}")
    print(f"Missing provider_organisation: {treatments_without_provider}")

    # Show what values exist
    existing_providers = db.treatments.distinct("provider_organisation")
    print(f"\nExisting provider values: {existing_providers}")

    if not dry_run:
        # Update ALL treatments to have the specified provider code
        result = db.treatments.update_many(
            {},  # Match all treatments
            {"$set": {"provider_organisation": provider_code}}
        )
        print(f"\n✓ Updated {result.modified_count} treatments to provider_organisation = {provider_code}")
    else:
        treatments_to_update = treatments_with_different_provider + treatments_without_provider
        print(f"\n[DRY RUN] Would update {treatments_to_update} treatments")

    # Verify results
    if not dry_run:
        print("\n" + "=" * 80)
        print("VERIFICATION")
        print("=" * 80)

        final_episodes_with_provider = db.episodes.count_documents({"provider_first_seen": provider_code})
        final_treatments_with_provider = db.treatments.count_documents({"provider_organisation": provider_code})

        print(f"Episodes with provider_first_seen = {provider_code}: {final_episodes_with_provider}/{total_episodes}")
        print(f"Treatments with provider_organisation = {provider_code}: {final_treatments_with_provider}/{total_treatments}")

        # Show sample
        print("\nSample episode:")
        sample_episode = db.episodes.find_one({"provider_first_seen": provider_code}, {"episode_id": 1, "provider_first_seen": 1})
        if sample_episode:
            print(f"  Episode {sample_episode['episode_id']}: provider_first_seen = {sample_episode['provider_first_seen']}")

        print("\nSample treatment:")
        sample_treatment = db.treatments.find_one({"provider_organisation": provider_code}, {"treatment_id": 1, "provider_organisation": 1})
        if sample_treatment:
            print(f"  Treatment {sample_treatment['treatment_id']}: provider_organisation = {sample_treatment['provider_organisation']}")

    client.close()

    print("\n" + "=" * 80)
    if dry_run:
        print("DRY RUN COMPLETE - No changes made")
        print("Run with --live to apply changes")
    else:
        print("LIVE RUN COMPLETE - Changes applied")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Populate provider codes for all episodes and treatments"
    )
    parser.add_argument(
        '--database',
        default='impact_test',
        help='Database name (default: impact_test)'
    )
    parser.add_argument(
        '--provider',
        default='RHU',
        help='NHS Trust code to assign (default: RHU - Portsmouth Hospitals University NHS Trust)'
    )
    parser.add_argument(
        '--live',
        action='store_true',
        help='Actually perform the updates (default is dry-run)'
    )

    args = parser.parse_args()

    populate_provider_codes(
        db_name=args.database,
        provider_code=args.provider,
        dry_run=not args.live
    )
