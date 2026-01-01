"""
Fix treatments that have surgeon ObjectId strings instead of names
Replace ObjectId values with actual clinician full names
"""
from pymongo import MongoClient
from bson import ObjectId
import re

client = MongoClient('mongodb://admin:admin123@localhost:27017')
db = client.surgdb

# Pattern to match ObjectId strings (24 hex characters)
objectid_pattern = re.compile(r'^[a-f0-9]{24}$', re.IGNORECASE)

print("="*80)
print("FIXING SURGEON IDs TO NAMES")
print("="*80)

# Find all treatments with ObjectId-like surgeon values
treatments_with_ids = []
all_treatments = db.treatments.find({"surgeon": {"$exists": True, "$ne": ""}})

for treatment in all_treatments:
    surgeon_value = treatment.get('surgeon', '')
    if surgeon_value and objectid_pattern.match(surgeon_value):
        treatments_with_ids.append(treatment)

print(f"\nFound {len(treatments_with_ids)} treatments with ObjectId strings as surgeon")

# Build a mapping of ObjectId to full name
clinician_map = {}
for clinician in db.clinicians.find():
    oid_str = str(clinician['_id'])
    full_name = f"{clinician.get('first_name', '')} {clinician.get('surname', '')}".strip()
    clinician_map[oid_str] = full_name
    print(f"  {oid_str} -> {full_name}")

print(f"\nBuilt mapping for {len(clinician_map)} clinicians")

# Update treatments
updated_count = 0
not_found_count = 0
not_found_ids = set()

for treatment in treatments_with_ids:
    surgeon_id = treatment.get('surgeon')
    
    if surgeon_id in clinician_map:
        full_name = clinician_map[surgeon_id]
        
        # Update the treatment
        result = db.treatments.update_one(
            {"_id": treatment['_id']},
            {
                "$set": {
                    "surgeon": full_name,
                    "surgeon_source": "clinician_id_lookup"
                }
            }
        )
        
        if result.modified_count > 0:
            updated_count += 1
            if updated_count <= 5:  # Show first 5 examples
                print(f"\n  Updated {treatment.get('treatment_id')}: '{surgeon_id}' -> '{full_name}'")
    else:
        not_found_count += 1
        not_found_ids.add(surgeon_id)

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Total treatments with ObjectId strings: {len(treatments_with_ids)}")
print(f"Successfully updated: {updated_count}")
print(f"Not found in clinicians table: {not_found_count}")

if not_found_ids:
    print(f"\nObjectId strings not found in clinicians table:")
    for oid in sorted(not_found_ids):
        count = sum(1 for t in treatments_with_ids if t.get('surgeon') == oid)
        print(f"  {oid} - {count} treatments")

# Verify the changes
print("\n" + "="*80)
print("VERIFICATION")
print("="*80)

remaining_with_ids = db.treatments.count_documents({
    "surgeon": {"$regex": r'^[a-f0-9]{24}$', "$options": "i"}
})
print(f"Treatments still with ObjectId strings: {remaining_with_ids}")

# Show sample of updated treatments
print("\nSample of updated treatments:")
updated_treatments = db.treatments.find({
    "surgeon_source": "clinician_id_lookup"
}).limit(5)

for t in updated_treatments:
    print(f"  {t.get('treatment_id')}: surgeon='{t.get('surgeon')}'")

print("\n" + "="*80)
print("COMPLETE")
print("="*80)
