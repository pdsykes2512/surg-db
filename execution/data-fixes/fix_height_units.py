#!/usr/bin/env python3
"""
Fix height units in treatment records - convert meters to centimeters

Issue: During data migration, patient heights were stored in meters (e.g., 1.65)
instead of centimeters (165) in the height_cm field.

This script:
1. Identifies treatments with height < 10 (likely in meters)
2. Converts them to centimeters by multiplying by 100
3. Recalculates BMI where needed
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/etc/impact/secrets.env')

# Connect to MongoDB
client = MongoClient(os.getenv('MONGODB_URI'))
db = client['impact']
treatments = db.treatments

def fix_height_units():
    """Convert heights from meters to centimeters"""

    print("=== Fixing Height Units in Treatment Records ===\n")

    # Find treatments with height < 10 (likely in meters)
    problematic_treatments = list(treatments.find(
        {'height_cm': {'$lt': 10, '$gt': 0}},
        {'treatment_id': 1, 'height_cm': 1, 'weight_kg': 1, 'bmi': 1}
    ))

    print(f"Found {len(problematic_treatments)} treatments with height < 10 (likely in meters)")

    if not problematic_treatments:
        print("No problematic heights found!")
        return

    # Show sample before fixing
    print("\nSample BEFORE fixing:")
    for t in problematic_treatments[:5]:
        print(f"  {t['treatment_id']}: {t.get('height_cm')}m → {t.get('height_cm', 0) * 100}cm")

    # Ask for confirmation
    response = input(f"\nConvert {len(problematic_treatments)} heights from meters to centimeters? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted.")
        return

    # Fix each treatment
    fixed_count = 0
    recalculated_bmi_count = 0

    for treatment in problematic_treatments:
        treatment_id = treatment['treatment_id']
        height_m = treatment.get('height_cm')
        weight_kg = treatment.get('weight_kg')
        old_bmi = treatment.get('bmi')

        if not height_m:
            continue

        # Convert height from meters to centimeters
        height_cm = round(height_m * 100, 1)

        update_fields = {'height_cm': height_cm}

        # Recalculate BMI if we have weight
        if weight_kg and weight_kg > 0:
            calculated_bmi = round(weight_kg / (height_m ** 2), 1)
            # Only update BMI if it's missing or significantly different (accounting for rounding)
            if old_bmi is None or abs(old_bmi - calculated_bmi) > 0.2:
                update_fields['bmi'] = calculated_bmi
                recalculated_bmi_count += 1

        # Update the treatment
        treatments.update_one(
            {'treatment_id': treatment_id},
            {'$set': update_fields}
        )

        fixed_count += 1

        if fixed_count % 500 == 0:
            print(f"  Processed {fixed_count}/{len(problematic_treatments)}...")

    print(f"\n✅ Fixed {fixed_count} height values")
    print(f"✅ Recalculated {recalculated_bmi_count} BMI values")

    # Verify the fix
    print("\nVerifying fixes...")
    still_problematic = treatments.count_documents({'height_cm': {'$lt': 10, '$gt': 0}})
    correct_heights = treatments.count_documents({'height_cm': {'$gte': 100, '$lte': 250}})

    print(f"  Heights still < 10: {still_problematic}")
    print(f"  Heights 100-250cm (correct): {correct_heights}")

    # Show sample after fixing
    print("\nSample AFTER fixing:")
    fixed_samples = list(treatments.find(
        {'treatment_id': {'$in': [t['treatment_id'] for t in problematic_treatments[:5]]}},
        {'treatment_id': 1, 'height_cm': 1, 'weight_kg': 1, 'bmi': 1}
    ))
    for t in fixed_samples:
        print(f"  {t['treatment_id']}: {t.get('height_cm')}cm, BMI={t.get('bmi')}")

if __name__ == '__main__':
    fix_height_units()
