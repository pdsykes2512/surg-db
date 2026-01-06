#!/usr/bin/env python3
"""
Migration: Convert treatment_type from 'surgery' to 'surgery_primary'
Also migrates any existing reverses_stoma_from_treatment_id to new relationship model

Run in production: python3 migrate_surgery_types.py --database impact
Run in test: python3 migrate_surgery_types.py --database impact_test
"""
import os
import argparse
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment
load_dotenv('/etc/impact/secrets.env')
MONGODB_URI = os.getenv('MONGODB_URI')


def migrate_surgery_types(db_name='impact', dry_run=False):
    """
    Migrate treatment types and stoma reversal relationships

    Changes:
    1. treatment_type: 'surgery' → 'surgery_primary'
    2. reverses_stoma_from_treatment_id → parent_surgery_id + relationship model
    """
    client = MongoClient(MONGODB_URI)
    db = client[db_name]

    print("=" * 80)
    print(f"MIGRATING SURGERY TYPES - Database: {db_name}")
    if dry_run:
        print("DRY RUN MODE - No changes will be made")
    print("=" * 80)
    print()

    stats = {
        'total_surgeries': 0,
        'surgeries_migrated': 0,
        'reversals_migrated': 0,
        'errors': []
    }

    # STEP 1: Migrate 'surgery' → 'surgery_primary'
    print("STEP 1: Migrating treatment_type 'surgery' → 'surgery_primary'")
    print("-" * 80)

    surgeries = db.treatments.count_documents({'treatment_type': 'surgery'})
    stats['total_surgeries'] = surgeries

    print(f"Found {surgeries} treatments with treatment_type='surgery'")

    if surgeries > 0 and not dry_run:
        result = db.treatments.update_many(
            {'treatment_type': 'surgery'},
            {'$set': {'treatment_type': 'surgery_primary'}}
        )
        stats['surgeries_migrated'] = result.modified_count
        print(f"✓ Updated {result.modified_count} surgeries to 'surgery_primary'")
    elif dry_run:
        print(f"[DRY RUN] Would update {surgeries} surgeries")
    else:
        print("✓ No surgeries to migrate")

    print()

    # STEP 2: Migrate stoma reversals with old field
    print("STEP 2: Migrating stoma reversals (reverses_stoma_from_treatment_id)")
    print("-" * 80)

    reversals = list(db.treatments.find({
        'reverses_stoma_from_treatment_id': {'$exists': True, '$ne': None}
    }))

    print(f"Found {len(reversals)} treatments with old reversal field")

    for reversal in reversals:
        parent_id = reversal.get('reverses_stoma_from_treatment_id')
        reversal_id = reversal.get('treatment_id')

        print(f"\nMigrating reversal: {reversal_id}")
        print(f"  Parent surgery: {parent_id}")

        # Find parent surgery
        parent = db.treatments.find_one({'treatment_id': parent_id})
        if not parent:
            error_msg = f"  ❌ Parent surgery {parent_id} not found"
            print(error_msg)
            stats['errors'].append(error_msg)
            continue

        if not dry_run:
            # Update reversal surgery (child)
            db.treatments.update_one(
                {'_id': reversal['_id']},
                {
                    '$set': {
                        'treatment_type': 'surgery_reversal',
                        'parent_surgery_id': parent_id,
                        'parent_episode_id': reversal.get('episode_id'),
                        'reversal_notes': f"Migrated from old reversal field"
                    },
                    '$unset': {
                        'reverses_stoma_from_treatment_id': ''
                    }
                }
            )
            print(f"  ✓ Updated reversal surgery to surgery_reversal")

            # Update parent surgery (add to related_surgery_ids)
            db.treatments.update_one(
                {'_id': parent['_id']},
                {
                    '$push': {
                        'related_surgery_ids': {
                            'treatment_id': reversal_id,
                            'treatment_type': 'surgery_reversal',
                            'date_created': datetime.now(timezone.utc)
                        }
                    },
                    '$set': {
                        'intraoperative.stoma_closure_date': reversal.get('treatment_date'),
                        'intraoperative.reversal_treatment_id': reversal_id
                    }
                }
            )
            print(f"  ✓ Updated parent surgery with reversal link")
            stats['reversals_migrated'] += 1
        else:
            print(f"  [DRY RUN] Would migrate this reversal")

    print()

    # STEP 3: Verify
    print("=" * 80)
    print("VERIFICATION")
    print("=" * 80)

    if not dry_run:
        primary_count = db.treatments.count_documents({'treatment_type': 'surgery_primary'})
        rtt_count = db.treatments.count_documents({'treatment_type': 'surgery_rtt'})
        reversal_count = db.treatments.count_documents({'treatment_type': 'surgery_reversal'})
        old_surgery_count = db.treatments.count_documents({'treatment_type': 'surgery'})

        print(f"Treatment types after migration:")
        print(f"  surgery_primary: {primary_count}")
        print(f"  surgery_rtt: {rtt_count}")
        print(f"  surgery_reversal: {reversal_count}")
        print(f"  surgery (old): {old_surgery_count}")

        if old_surgery_count > 0:
            print(f"\n⚠️  WARNING: {old_surgery_count} treatments still have treatment_type='surgery'")
        else:
            print(f"\n✓ All surgeries migrated successfully")

    print()

    # STEP 4: Summary
    print("=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)
    print(f"Database: {db_name}")
    print(f"Dry run: {dry_run}")
    print(f"\nStatistics:")
    print(f"  Total surgeries found: {stats['total_surgeries']}")
    print(f"  Surgeries migrated: {stats['surgeries_migrated']}")
    print(f"  Reversals migrated: {stats['reversals_migrated']}")
    print(f"  Errors: {len(stats['errors'])}")

    if stats['errors']:
        print(f"\nErrors encountered:")
        for error in stats['errors']:
            print(f"  {error}")

    print()

    if dry_run:
        print("⚠️  DRY RUN - No changes were made to the database")
    else:
        print("✅ Migration completed successfully")

    print("=" * 80)

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Migrate surgery treatment types')
    parser.add_argument('--database', default='impact_test',
                       help='Database name (default: impact_test)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run without making changes')
    parser.add_argument('--production', action='store_true',
                       help='Run on production database (impact)')

    args = parser.parse_args()

    # Safety check for production
    if args.production:
        db_name = 'impact'
        print("\n⚠️  WARNING: Running on PRODUCTION database!")
        confirm = input("Type 'migrate production' to continue: ")
        if confirm != 'migrate production':
            print("Migration cancelled")
            exit(0)
    else:
        db_name = args.database

    migrate_surgery_types(db_name=db_name, dry_run=args.dry_run)
