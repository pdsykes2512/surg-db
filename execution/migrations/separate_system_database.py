#!/usr/bin/env python3
"""
Separate System and Clinical Audit Databases

Creates impact_system database for persistent application data (users, clinicians)
and keeps impact database for clinical audit data that can be refreshed.

This architectural separation allows clinical data refreshes without affecting logins.
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

# Load environment
load_dotenv('/etc/impact/secrets.env')
load_dotenv('.env')


def separate_databases(source_db='impact', system_db='impact_system'):
    """
    Create impact_system database and copy users/clinicians from source
    """
    # Connect to MongoDB
    mongo_uri = os.getenv('MONGODB_URI')
    if not mongo_uri:
        raise ValueError("MONGODB_URI not found in environment")

    client = MongoClient(mongo_uri)

    print("\n" + "=" * 80)
    print("DATABASE SEPARATION: System vs Clinical Audit Data")
    print("=" * 80)
    print(f"Source database: {source_db}")
    print(f"System database: {system_db} (NEW)")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")

    source = client[source_db]
    system = client[system_db]

    stats = {
        'users_copied': 0,
        'clinicians_copied': 0
    }

    # ========================================================================
    # COPY USERS
    # ========================================================================
    print("[1/2] Copying users...")

    # Check if system database already has users
    existing_users = system.users.count_documents({})
    if existing_users > 0:
        print(f"  ⚠️  Warning: {system_db}.users already has {existing_users} users")
        print(f"  Skipping users copy to avoid duplicates")
    else:
        users = list(source.users.find({}))
        if users:
            system.users.insert_many(users)
            stats['users_copied'] = len(users)
            print(f"  ✅ Copied {len(users)} users to {system_db}.users")
        else:
            print(f"  ⚠️  No users found in {source_db}.users")

    # ========================================================================
    # COPY CLINICIANS
    # ========================================================================
    print("\n[2/2] Copying clinicians...")

    # Check if system database already has clinicians
    existing_clinicians = system.clinicians.count_documents({})
    if existing_clinicians > 0:
        print(f"  ⚠️  Warning: {system_db}.clinicians already has {existing_clinicians} clinicians")
        print(f"  Skipping clinicians copy to avoid duplicates")
    else:
        clinicians = list(source.clinicians.find({}))
        if clinicians:
            system.clinicians.insert_many(clinicians)
            stats['clinicians_copied'] = len(clinicians)
            print(f"  ✅ Copied {len(clinicians)} clinicians to {system_db}.clinicians")
        else:
            print(f"  ⚠️  No clinicians found in {source_db}.clinicians")

    # ========================================================================
    # CREATE INDEXES
    # ========================================================================
    print("\n[3/2] Creating indexes in system database...")

    # Users indexes
    system.users.create_index("username", unique=True)
    print(f"  ✅ Created unique index on users.username")

    # Clinicians indexes (if needed)
    # system.clinicians.create_index("email", unique=True)

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Users copied: {stats['users_copied']}")
    print(f"Clinicians copied: {stats['clinicians_copied']}")
    print("\nDatabase Structure:")
    print(f"  {system_db} (System):")
    print(f"    - users: {system.users.count_documents({})} documents")
    print(f"    - clinicians: {system.clinicians.count_documents({})} documents")
    print(f"\n  {source_db} (Clinical Audit):")
    print(f"    - patients: {source.patients.count_documents({})} documents")
    print(f"    - episodes: {source.episodes.count_documents({})} documents")
    print(f"    - tumours: {source.tumours.count_documents({})} documents")
    print(f"    - treatments: {source.treatments.count_documents({})} documents")
    print("=" * 80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Separate system and clinical databases')
    parser.add_argument('--source', default='impact', help='Source database (default: impact)')
    parser.add_argument('--system', default='impact_system', help='System database (default: impact_system)')
    args = parser.parse_args()

    try:
        stats = separate_databases(source_db=args.source, system_db=args.system)
        print("\n✅ Database separation completed successfully!\n")
        print("Next steps:")
        print("  1. Update backend configuration to use both databases")
        print("  2. Run fresh import to impact database")
        print("  3. Test authentication")
    except Exception as e:
        print(f"\n❌ Database separation failed: {e}")
        raise
