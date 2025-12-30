#!/usr/bin/env python3
"""
Fix Procedure Names and OPCS4 Codes

Maps procedure names to canonical names and ensures correct OPCS4 codes are assigned.

Author: IMPACT Data Migration
Date: 2025-12-30
"""

import os
import sys
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional

# Load environment
load_dotenv('/etc/impact/secrets.env')
load_dotenv('.env')


def map_procedure_name_and_opcs4(proc_name: str, existing_opcs4: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
    """
    Map procedure name to canonical name and OPCS4 code

    Returns:
        Tuple of (canonical_procedure_name, opcs4_code)
    """
    if not proc_name or proc_name == 'nan':
        return None, existing_opcs4

    proc_clean = proc_name.strip().lower()

    # Comprehensive mapping from source data variations to canonical names and OPCS4 codes
    # Format: source_name_pattern → (canonical_name, default_opcs4_code)
    procedure_mapping = {
        # Colorectal procedures
        'anterior resection': ('Anterior resection of rectum', 'H33.4'),
        'right hemicolectomy': ('Right hemicolectomy', 'H07.9'),
        'extended right hemicolectomy': ('Extended right hemicolectomy', 'H06.9'),
        'left hemicolectomy': ('Left hemicolectomy', 'H09.9'),
        'sigmoid colectomy': ('Sigmoid colectomy', 'H10.9'),
        'transverse colectomy': ('Transverse colectomy', 'H07.9'),
        'hartmann': ('Hartmann procedure', 'H33.5'),
        'aper': ('Abdominoperineal excision of rectum', 'H33.1'),
        'abdominoperineal': ('Abdominoperineal excision of rectum', 'H33.1'),
        'subtotal colectomy': ('Subtotal colectomy', 'H08.9'),
        'total colectomy': ('Total colectomy', 'H09.9'),
        'proctocolectomy': ('Proctocolectomy', 'H10.9'),
        'panproctocolectomy': ('Panproctocolectomy', 'H11.9'),

        # Stoma procedures
        'stoma only': ('Stoma formation', 'H15.9'),
        'stoma': ('Stoma formation', 'H15.9'),
        'ileostomy': ('Ileostomy', 'H46.9'),
        'colostomy': ('Colostomy', 'H47.9'),
        'closure of stoma': ('Closure of stoma', 'H48.9'),

        # Endoscopic/minimal access
        'polypectomy': ('Polypectomy', 'H23.9'),
        'tems': ('Transanal endoscopic microsurgery', 'H41.2'),
        'trans anal resection': ('Transanal excision of lesion', 'H41.1'),
        'transanal resection': ('Transanal excision of lesion', 'H41.1'),

        # Other/palliative
        'stent': ('Colorectal stent insertion', 'H24.3'),
        'bypass': ('Intestinal bypass', 'H05.1'),
        'laparotomy only': ('Laparotomy and exploration', 'T30.1'),
        'laparoscopy only': ('Diagnostic laparoscopy', 'T42.1'),
        'other': ('Other colorectal procedure', 'H99.9'),
    }

    # Try to find a match - sort by pattern length (longest first) to check specific patterns before generic ones
    for pattern in sorted(procedure_mapping.keys(), key=len, reverse=True):
        if pattern in proc_clean:
            canonical_name, default_opcs4 = procedure_mapping[pattern]
            # Use existing OPCS4 if available and valid, otherwise use default
            opcs4 = existing_opcs4 if (existing_opcs4 and existing_opcs4 != 'nan' and existing_opcs4 != '') else default_opcs4
            return canonical_name, opcs4

    # If no match found, return cleaned version of original name
    return proc_name.strip(), existing_opcs4


def fix_procedure_names_and_opcs4(db_name='impact_test', dry_run=True):
    """
    Fix procedure names and OPCS4 codes in treatments collection

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
    print(f"FIX PROCEDURE NAMES AND OPCS4 CODES - Database: {db_name}")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will modify database)'}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    stats = {
        'treatments_checked': 0,
        'procedures_updated': 0,
        'opcs4_updated': 0,
        'no_changes_needed': 0
    }

    treatments_collection = db.treatments

    # Get all surgery treatments
    all_treatments = treatments_collection.find({'treatment_type': 'surgery'})

    for treatment in all_treatments:
        stats['treatments_checked'] += 1

        # Get current values
        current_proc = treatment.get('procedure', {}).get('primary_procedure')
        current_opcs4 = treatment.get('opcs4_code')

        # Map to canonical values
        canonical_proc, mapped_opcs4 = map_procedure_name_and_opcs4(current_proc, current_opcs4)

        # Check if updates are needed
        proc_needs_update = current_proc != canonical_proc
        opcs4_needs_update = current_opcs4 != mapped_opcs4

        if proc_needs_update or opcs4_needs_update:
            if dry_run:
                if stats['procedures_updated'] < 20:  # Show first 20
                    print(f"\n  Treatment {treatment.get('treatment_id')}:")
                    if proc_needs_update:
                        print(f"    Procedure: \"{current_proc}\" → \"{canonical_proc}\"")
                    if opcs4_needs_update:
                        print(f"    OPCS4: \"{current_opcs4}\" → \"{mapped_opcs4}\"")
            else:
                # Build update document
                update_doc = {'updated_at': datetime.utcnow()}
                if proc_needs_update:
                    update_doc['procedure.primary_procedure'] = canonical_proc
                if opcs4_needs_update:
                    update_doc['opcs4_code'] = mapped_opcs4

                treatments_collection.update_one(
                    {'_id': treatment['_id']},
                    {'$set': update_doc}
                )

            if proc_needs_update:
                stats['procedures_updated'] += 1
            if opcs4_needs_update:
                stats['opcs4_updated'] += 1
        else:
            stats['no_changes_needed'] += 1

        if stats['treatments_checked'] % 1000 == 0:
            print(f"  Processed {stats['treatments_checked']} treatments...")

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Treatments checked: {stats['treatments_checked']}")
    print(f"Procedure names updated: {stats['procedures_updated']}")
    print(f"OPCS4 codes updated: {stats['opcs4_updated']}")
    print(f"No changes needed: {stats['no_changes_needed']}")
    print("=" * 80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    if dry_run:
        print("\n⚠️  This was a DRY RUN - no changes were made")
        print("Run with --live to apply changes to the database\n")
    else:
        print("\n✅ Procedure names and OPCS4 codes fixed!\n")

    client.close()
    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Fix procedure names and OPCS4 codes')
    parser.add_argument('--database', default='impact_test', help='Database name (default: impact_test)')
    parser.add_argument('--live', action='store_true', help='Apply changes (default: dry run)')
    args = parser.parse_args()

    try:
        stats = fix_procedure_names_and_opcs4(
            db_name=args.database,
            dry_run=not args.live
        )
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        raise
