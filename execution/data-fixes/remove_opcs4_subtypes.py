#!/usr/bin/env python3
"""
Remove OPCS-4 sub-types from treatment codes.

Converts codes like "H33.4" to "H33", "H07.9" to "H07", etc.
Keeps just the base procedure code without the decimal point variant.
"""

import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

def remove_subtype(opcs_code):
    """Remove decimal point and sub-type digit from OPCS code."""
    if not opcs_code:
        return opcs_code

    code_str = str(opcs_code)

    # Remove everything after and including the decimal point
    if '.' in code_str:
        return code_str.split('.')[0]

    return code_str

def main():
    # Check for --live flag
    live_mode = '--live' in sys.argv

    # Load environment
    load_dotenv('/etc/impact/secrets.env')
    load_dotenv('.env')

    # Connect to MongoDB
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client['impact']

    print("=" * 70)
    print("Remove OPCS-4 Sub-types")
    print("=" * 70)
    print(f"Mode: {'LIVE - Will modify database' if live_mode else 'DRY RUN - No changes will be made'}")
    print()

    # Find all treatments with OPCS codes
    treatments = list(db.treatments.find(
        {'opcs4_code': {'$exists': True, '$ne': None}},
        {'treatment_id': 1, 'opcs4_code': 1, 'procedure.primary_procedure': 1}
    ))

    print(f"Found {len(treatments)} treatments with OPCS codes")
    print()

    # Analyze changes
    updates_needed = []
    no_change_needed = []

    for treatment in treatments:
        old_code = treatment.get('opcs4_code')
        new_code = remove_subtype(old_code)

        if old_code != new_code:
            updates_needed.append({
                'treatment_id': treatment['treatment_id'],
                'old_code': old_code,
                'new_code': new_code,
                'procedure': treatment.get('procedure', {}).get('primary_procedure', 'N/A')
            })
        else:
            no_change_needed.append(treatment['treatment_id'])

    print(f"Treatments requiring updates: {len(updates_needed)}")
    print(f"Treatments already correct: {len(no_change_needed)}")
    print()

    if updates_needed:
        print("Sample changes (first 10):")
        for update in updates_needed[:10]:
            print(f"  {update['treatment_id']}: {update['old_code']} → {update['new_code']} ({update['procedure']})")

        if len(updates_needed) > 10:
            print(f"  ... and {len(updates_needed) - 10} more")
        print()

    # Apply updates if in live mode
    if live_mode and updates_needed:
        print("Applying updates...")

        updated_count = 0
        for update in updates_needed:
            result = db.treatments.update_one(
                {'treatment_id': update['treatment_id']},
                {
                    '$set': {
                        'opcs4_code': update['new_code'],
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            if result.modified_count > 0:
                updated_count += 1

        print(f"✅ Updated {updated_count} treatments")

        # Verify
        print("\nVerification:")
        with_decimal = db.treatments.count_documents({'opcs4_code': {'$regex': r'\.'}})
        without_decimal = db.treatments.count_documents({'opcs4_code': {'$exists': True, '$ne': None, '$not': {'$regex': r'\.'}}})
        print(f"  Codes with decimal point: {with_decimal}")
        print(f"  Codes without decimal: {without_decimal}")

    elif not live_mode:
        print("⚠️  DRY RUN MODE - No changes made")
        print("Run with --live flag to apply changes")

    client.close()

if __name__ == '__main__':
    main()
