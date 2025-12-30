#!/usr/bin/env python3
"""
Consolidate Synchronous Episodes

Problem: The import script created separate episodes for each tumour row,
even when tumours were diagnosed on the same date (synchronous tumours).

Solution: For each patient, consolidate episodes that have tumours with
the same diagnosis date into a single episode.

Metachronous tumours (different diagnosis dates) remain as separate episodes.

Author: IMPACT Data Migration
Date: 2025-12-30
"""

import os
from pymongo import MongoClient
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv
from collections import defaultdict

# Load environment
load_dotenv('/etc/impact/secrets.env')
load_dotenv('.env')


def consolidate_synchronous_episodes(db_name='impact_test', dry_run=True):
    """
    Consolidate episodes for patients with multiple episodes where tumours
    have the same diagnosis date.

    Args:
        db_name: Database name
        dry_run: If True, only print what would be done (default: True)
    """
    # Connect to MongoDB
    mongo_uri = os.getenv('MONGODB_URI')
    if not mongo_uri:
        raise ValueError("MONGODB_URI not found in environment")

    client = MongoClient(mongo_uri)
    db = client[db_name]

    print("\n" + "=" * 80)
    print(f"CONSOLIDATE SYNCHRONOUS EPISODES - Database: {db_name}")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will modify database)'}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    stats = {
        'patients_checked': 0,
        'patients_with_multiple_episodes': 0,
        'patients_needing_consolidation': 0,
        'episodes_consolidated': 0,
        'episodes_deleted': 0,
        'tumours_moved': 0,
        'treatments_moved': 0
    }

    # Find all patients with multiple episodes
    pipeline = [
        {"$group": {
            "_id": "$patient_id",
            "episode_count": {"$sum": 1},
            "episode_ids": {"$push": "$episode_id"}
        }},
        {"$match": {"episode_count": {"$gt": 1}}},
        {"$sort": {"_id": 1}}
    ]

    patients_with_multiple = list(db.episodes.aggregate(pipeline))
    print(f"\nFound {len(patients_with_multiple)} patients with multiple episodes")

    for patient_data in patients_with_multiple:
        patient_id = patient_data['_id']
        episode_ids = patient_data['episode_ids']

        stats['patients_checked'] += 1
        stats['patients_with_multiple_episodes'] += 1

        # Get all episodes for this patient with tumour data
        episodes = []
        for ep_id in episode_ids:
            episode = db.episodes.find_one({"episode_id": ep_id})
            if not episode:
                continue

            # Get tumour diagnosis dates
            tumour_dates = []
            for tumour_id in episode.get('tumour_ids', []):
                tumour = db.tumours.find_one({"tumour_id": tumour_id})
                if tumour and tumour.get('diagnosis_date'):
                    tumour_dates.append(tumour['diagnosis_date'])

            # Use earliest tumour date as episode date
            episode_date = min(tumour_dates) if tumour_dates else None

            episodes.append({
                'episode_id': ep_id,
                'episode': episode,
                'diagnosis_date': episode_date,
                'tumour_ids': episode.get('tumour_ids', []),
                'treatment_ids': episode.get('treatment_ids', [])
            })

        # Group episodes by diagnosis date
        episodes_by_date = defaultdict(list)
        for ep_data in episodes:
            date = ep_data['diagnosis_date']
            if date:  # Only group episodes with a diagnosis date
                episodes_by_date[date].append(ep_data)

        # Check if any date has multiple episodes (needs consolidation)
        for date, eps in episodes_by_date.items():
            if len(eps) <= 1:
                continue  # Only one episode for this date

            stats['patients_needing_consolidation'] += 1

            print(f"\nPatient {patient_id}: {len(eps)} episodes on {date}")

            # Sort episodes by episode_id to keep the first one
            eps.sort(key=lambda x: x['episode_id'])

            # Primary episode (keep this one)
            primary = eps[0]
            redundant = eps[1:]

            print(f"  PRIMARY: {primary['episode_id']} (keeping this one)")
            print(f"    Tumours: {len(primary['tumour_ids'])}")
            print(f"    Treatments: {len(primary['treatment_ids'])}")

            # Consolidate data from redundant episodes
            all_tumour_ids = list(primary['tumour_ids'])
            all_treatment_ids = list(primary['treatment_ids'])

            for red in redundant:
                print(f"  REDUNDANT: {red['episode_id']} (will be deleted)")
                print(f"    Tumours: {len(red['tumour_ids'])}")
                print(f"    Treatments: {len(red['treatment_ids'])}")

                all_tumour_ids.extend(red['tumour_ids'])
                all_treatment_ids.extend(red['treatment_ids'])

                stats['tumours_moved'] += len(red['tumour_ids'])
                stats['treatments_moved'] += len(red['treatment_ids'])

            print(f"  CONSOLIDATED:")
            print(f"    Total tumours: {len(all_tumour_ids)}")
            print(f"    Total treatments: {len(all_treatment_ids)}")

            if not dry_run:
                # Update primary episode with all tumours and treatments
                db.episodes.update_one(
                    {'episode_id': primary['episode_id']},
                    {
                        '$set': {
                            'tumour_ids': all_tumour_ids,
                            'treatment_ids': all_treatment_ids,
                            'updated_at': datetime.utcnow()
                        }
                    }
                )

                # Update all tumours to point to primary episode
                for tumour_id in all_tumour_ids:
                    db.tumours.update_one(
                        {'tumour_id': tumour_id},
                        {
                            '$set': {
                                'episode_id': primary['episode_id'],
                                'updated_at': datetime.utcnow()
                            }
                        }
                    )

                # Update all treatments to point to primary episode
                for treatment_id in all_treatment_ids:
                    db.treatments.update_one(
                        {'treatment_id': treatment_id},
                        {
                            '$set': {
                                'episode_id': primary['episode_id'],
                                'updated_at': datetime.utcnow()
                            }
                        }
                    )

                # Delete redundant episodes
                for red in redundant:
                    db.episodes.delete_one({'episode_id': red['episode_id']})
                    stats['episodes_deleted'] += 1

                stats['episodes_consolidated'] += 1
                print(f"  ✅ Consolidated into {primary['episode_id']}")
            else:
                print(f"  [DRY RUN] Would consolidate into {primary['episode_id']}")

    # Print summary
    print("\n" + "=" * 80)
    print("CONSOLIDATION SUMMARY")
    print("=" * 80)
    print(f"Patients checked: {stats['patients_checked']}")
    print(f"Patients with multiple episodes: {stats['patients_with_multiple_episodes']}")
    print(f"Patients needing consolidation: {stats['patients_needing_consolidation']}")
    print(f"Episodes consolidated: {stats['episodes_consolidated']}")
    print(f"Episodes deleted: {stats['episodes_deleted']}")
    print(f"Tumours moved: {stats['tumours_moved']}")
    print(f"Treatments moved: {stats['treatments_moved']}")
    print("=" * 80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    if dry_run:
        print("\n⚠️  This was a DRY RUN - no changes were made")
        print("Run with --live to apply changes to the database\n")
    else:
        print("\n✅ Consolidation complete!\n")

    client.close()
    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Consolidate synchronous episodes')
    parser.add_argument('--database', default='impact_test', help='Database name (default: impact_test)')
    parser.add_argument('--live', action='store_true', help='Apply changes (default: dry run)')
    args = parser.parse_args()

    try:
        stats = consolidate_synchronous_episodes(
            db_name=args.database,
            dry_run=not args.live
        )
    except Exception as e:
        print(f"\n❌ Consolidation failed: {e}")
        raise
