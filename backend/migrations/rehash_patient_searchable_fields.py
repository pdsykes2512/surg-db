#!/usr/bin/env python3
"""
Migration: Rehash Patient Searchable Fields
============================================

This migration updates the hash values for NHS numbers and MRNs to use the new
normalization that removes spaces. This is required after fixing the hash
generation to be consistent with search queries.

Old normalization: .strip().lower()
New normalization: .replace(" ", "").strip().lower()

Usage:
    python backend/migrations/rehash_patient_searchable_fields.py

Safety:
    - Reads encrypted data, decrypts it, rehashes with new normalization
    - Only updates _hash fields, does not modify encrypted values
    - Can be run multiple times safely (idempotent)
"""

import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables (secrets first, then .env)
secrets_path = Path('/etc/impact/secrets.env')
if secrets_path.exists():
    load_dotenv(secrets_path)

env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.app.database import Database, get_patients_collection
from backend.app.utils.encryption import decrypt_field, generate_search_hash

async def rehash_patients():
    """Rehash all patient NHS numbers and MRNs with new normalization."""
    # Connect to database
    await Database.connect_db()

    collection = await get_patients_collection()

    # Find all patients
    cursor = collection.find({})
    patients = await cursor.to_list(length=None)

    print(f"Found {len(patients)} patients to process")

    updated_count = 0
    error_count = 0

    for patient in patients:
        try:
            patient_id = patient.get('patient_id', 'UNKNOWN')
            updates = {}

            # Rehash NHS number if present
            if 'nhs_number' in patient:
                encrypted_nhs = patient['nhs_number']
                if encrypted_nhs and encrypted_nhs.startswith('ENC:'):
                    try:
                        # Decrypt to get plaintext
                        plaintext_nhs = decrypt_field('nhs_number', encrypted_nhs)
                        # Generate new hash with updated normalization
                        new_hash = generate_search_hash('nhs_number', plaintext_nhs)
                        if new_hash:
                            updates['nhs_number_hash'] = new_hash
                    except Exception as e:
                        print(f"  Warning: Could not rehash NHS number for patient {patient_id}: {e}")

            # Rehash MRN if present
            if 'mrn' in patient:
                encrypted_mrn = patient['mrn']
                if encrypted_mrn and encrypted_mrn.startswith('ENC:'):
                    try:
                        # Decrypt to get plaintext
                        plaintext_mrn = decrypt_field('mrn', encrypted_mrn)
                        # Generate new hash with updated normalization
                        new_hash = generate_search_hash('mrn', plaintext_mrn)
                        if new_hash:
                            updates['mrn_hash'] = new_hash
                    except Exception as e:
                        print(f"  Warning: Could not rehash MRN for patient {patient_id}: {e}")

            # Update document if we have new hashes
            if updates:
                await collection.update_one(
                    {'_id': patient['_id']},
                    {'$set': updates}
                )
                updated_count += 1
                if updated_count % 100 == 0:
                    print(f"  Processed {updated_count} patients...")

        except Exception as e:
            error_count += 1
            print(f"  Error processing patient: {e}")

    print(f"\nMigration complete!")
    print(f"  Updated: {updated_count} patients")
    print(f"  Errors: {error_count}")

if __name__ == '__main__':
    print("Starting patient searchable field rehash migration...")
    print("This will update NHS number and MRN hashes with new normalization.\n")

    asyncio.run(rehash_patients())
