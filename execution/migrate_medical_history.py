#!/usr/bin/env python3
"""
Migrate legacy medical_history structure to new format.

Old structure (legacy from COSD import):
{
  "family_history": false,
  "family_history_positive": "0"
}

New structure (matches Pydantic model):
{
  "conditions": [],
  "previous_surgeries": [],
  "medications": [],
  "allergies": [],
  "smoking_status": null,
  "alcohol_use": null
}

This migration removes the legacy fields that are not used in the UI.
"""

from pymongo import MongoClient
from datetime import datetime
import sys

# Load MongoDB URI from secrets
secrets = {}
with open('/etc/impact/secrets.env', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            secrets[key] = value

uri = secrets.get('MONGODB_URI')
if not uri:
    print("❌ MONGODB_URI not found in /etc/impact/secrets.env")
    sys.exit(1)

# Connect to MongoDB
print("Connecting to MongoDB...")
client = MongoClient(uri)
db = client['impact']
patients_coll = db['patients']

# Count patients with old structure
old_structure_count = patients_coll.count_documents({
    'medical_history.family_history': {'$exists': True}
})

print(f"\n{'='*80}")
print(f"Medical History Migration")
print(f"{'='*80}")
print(f"Found {old_structure_count} patients with old medical_history structure")

if old_structure_count == 0:
    print("✅ No migration needed - all patients already have new structure")
    client.close()
    sys.exit(0)

# Ask for confirmation
print(f"\nThis will:")
print(f"  1. Remove 'family_history' and 'family_history_positive' fields")
print(f"  2. Replace with empty arrays for conditions, medications, etc.")
print(f"  3. Update {old_structure_count} patient records")
print()
response = input("Proceed with migration? (yes/no): ")

if response.lower() != 'yes':
    print("❌ Migration cancelled")
    client.close()
    sys.exit(0)

# Perform migration
print("\n" + "="*80)
print("Starting migration...")
print("="*80)

# New medical_history structure
new_medical_history = {
    "conditions": [],
    "previous_surgeries": [],
    "medications": [],
    "allergies": [],
    "smoking_status": None,
    "alcohol_use": None
}

# Update all patients with old structure
result = patients_coll.update_many(
    {'medical_history.family_history': {'$exists': True}},
    {
        '$set': {
            'medical_history': new_medical_history,
            'updated_at': datetime.utcnow()
        }
    }
)

print(f"\n✅ Migration complete!")
print(f"   Updated {result.modified_count} patient records")

# Verify
remaining_old = patients_coll.count_documents({
    'medical_history.family_history': {'$exists': True}
})

if remaining_old > 0:
    print(f"\n⚠️  Warning: {remaining_old} patients still have old structure")
else:
    print(f"\n✅ Verification passed: All patients now have new structure")

# Show sample of migrated data
print("\nSample migrated record:")
sample = patients_coll.find_one({'medical_history': new_medical_history})
if sample:
    print(f"  Patient ID: {sample.get('patient_id')}")
    print(f"  medical_history: {sample.get('medical_history')}")

client.close()
print("\n" + "="*80)
print("Migration complete!")
print("="*80)
