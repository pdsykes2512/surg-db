#!/usr/bin/env python3
"""
Migration Script: Move Treatments and Tumours to Separate Collections

This script migrates embedded treatments and tumours arrays from episodes 
to separate collections for better data management and NBOCA reporting.

Before running:
- Backup your database
- Ensure no active writes to episodes collection

After running:
- Verify migration report
- Update application code to use new collections
"""
import asyncio
import sys
import json
import os
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
from bson import ObjectId
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Get MongoDB URI from environment or use default with auth
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://admin:admin123@localhost:27017/surg_outcomes?authSource=admin")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "surg_outcomes")


class MigrationReport:
    """Track migration statistics"""
    def __init__(self):
        self.start_time = datetime.now()
        self.before = {}
        self.after = {}
        self.errors = []
        self.warnings = []
        
    def add_before(self, collection, count):
        self.before[collection] = count
        
    def add_after(self, collection, count):
        self.after[collection] = count
        
    def add_error(self, error):
        self.errors.append(error)
        
    def add_warning(self, warning):
        self.warnings.append(warning)
        
    def print_report(self):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        print("\n" + "="*80)
        print("MIGRATION REPORT: Treatments & Tumours to Separate Collections")
        print("="*80)
        print(f"\nStart Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {duration:.2f} seconds")
        
        print("\n--- BEFORE MIGRATION ---")
        for collection, count in self.before.items():
            print(f"  {collection}: {count} documents")
        
        print("\n--- AFTER MIGRATION ---")
        for collection, count in self.after.items():
            print(f"  {collection}: {count} documents")
        
        print("\n--- CHANGES ---")
        for collection in set(self.before.keys()) | set(self.after.keys()):
            before = self.before.get(collection, 0)
            after = self.after.get(collection, 0)
            change = after - before
            if change != 0:
                print(f"  {collection}: {before} → {after} ({change:+d})")
        
        if self.warnings:
            print(f"\n--- WARNINGS ({len(self.warnings)}) ---")
            for warning in self.warnings:
                print(f"  ⚠️  {warning}")
        
        if self.errors:
            print(f"\n--- ERRORS ({len(self.errors)}) ---")
            for error in self.errors:
                print(f"  ❌ {error}")
            print("\n⚠️  MIGRATION COMPLETED WITH ERRORS - PLEASE REVIEW")
        else:
            print("\n✅ MIGRATION COMPLETED SUCCESSFULLY")
        
        print("="*80 + "\n")
        
        # Save report to file
        report_file = Path.home() / ".tmp" / f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.parent.mkdir(exist_ok=True)
        
        report_data = {
            "start_time": self.start_time.isoformat(),
            "duration_seconds": duration,
            "before": self.before,
            "after": self.after,
            "changes": {
                collection: self.after.get(collection, 0) - self.before.get(collection, 0)
                for collection in set(self.before.keys()) | set(self.after.keys())
            },
            "warnings": self.warnings,
            "errors": self.errors
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"Report saved to: {report_file}")


async def validate_before_migration(db):
    """Capture state before migration"""
    report = MigrationReport()
    
    print("📊 Capturing pre-migration state...")
    
    # Count episodes
    episodes_count = await db.episodes.count_documents({})
    report.add_before("episodes", episodes_count)
    
    # Count existing treatments/tumours collections (should be 0 or minimal)
    treatments_count = await db.treatments.count_documents({})
    tumours_count = await db.tumours.count_documents({})
    report.add_before("treatments", treatments_count)
    report.add_before("tumours", tumours_count)
    
    # Count embedded treatments and tumours
    episodes_with_treatments = 0
    episodes_with_tumours = 0
    total_embedded_treatments = 0
    total_embedded_tumours = 0
    
    async for episode in db.episodes.find({}):
        treatments = episode.get("treatments", [])
        tumours = episode.get("tumours", [])
        
        if treatments:
            episodes_with_treatments += 1
            total_embedded_treatments += len(treatments)
        
        if tumours:
            episodes_with_tumours += 1
            total_embedded_tumours += len(tumours)
    
    print(f"  - Episodes: {episodes_count}")
    print(f"  - Episodes with embedded treatments: {episodes_with_treatments}")
    print(f"  - Total embedded treatments: {total_embedded_treatments}")
    print(f"  - Episodes with embedded tumours: {episodes_with_tumours}")
    print(f"  - Total embedded tumours: {total_embedded_tumours}")
    print(f"  - Existing treatments collection: {treatments_count} (will be preserved)")
    print(f"  - Existing tumours collection: {tumours_count} (will be preserved)")
    
    if treatments_count > 0 or tumours_count > 0:
        report.add_warning(f"Collections already have data: treatments={treatments_count}, tumours={tumours_count}")
    
    report.before["embedded_treatments"] = total_embedded_treatments
    report.before["embedded_tumours"] = total_embedded_tumours
    report.before["episodes_with_treatments"] = episodes_with_treatments
    report.before["episodes_with_tumours"] = episodes_with_tumours
    
    return report


async def migrate_treatments_and_tumours(db, report):
    """Migrate treatments and tumours to separate collections"""
    
    print("\n🔄 Starting migration...")
    
    episodes_processed = 0
    treatments_migrated = 0
    tumours_migrated = 0
    episodes_updated = 0
    
    async for episode in db.episodes.find({}):
        episode_id = str(episode["_id"])
        episodes_processed += 1
        
        treatments = episode.get("treatments", [])
        tumours = episode.get("tumours", [])
        
        try:
            # Migrate treatments
            if treatments:
                for idx, treatment in enumerate(treatments):
                    # Add episode reference
                    treatment["episode_id"] = episode_id
                    treatment["patient_id"] = episode.get("patient_id")
                    
                    # Add metadata if missing
                    if "created_at" not in treatment:
                        treatment["created_at"] = episode.get("created_at", datetime.utcnow())
                    if "created_by" not in treatment:
                        treatment["created_by"] = episode.get("created_by", "migration_script")
                    
                    # Generate _id if treatment doesn't have one
                    if "_id" not in treatment:
                        treatment["_id"] = ObjectId()
                    
                    # Insert into treatments collection
                    await db.treatments.update_one(
                        {"_id": treatment["_id"]},
                        {"$set": treatment},
                        upsert=True
                    )
                    treatments_migrated += 1
            
            # Migrate tumours
            if tumours:
                for idx, tumour in enumerate(tumours):
                    # Add episode reference
                    tumour["episode_id"] = episode_id
                    tumour["patient_id"] = episode.get("patient_id")
                    
                    # Add metadata if missing
                    if "created_at" not in tumour:
                        tumour["created_at"] = episode.get("created_at", datetime.utcnow())
                    if "created_by" not in tumour:
                        tumour["created_by"] = episode.get("created_by", "migration_script")
                    
                    # Generate _id if tumour doesn't have one
                    if "_id" not in tumour:
                        tumour["_id"] = ObjectId()
                    
                    # Insert into tumours collection
                    await db.tumours.update_one(
                        {"_id": tumour["_id"]},
                        {"$set": tumour},
                        upsert=True
                    )
                    tumours_migrated += 1
            
            # Remove embedded arrays from episode
            if treatments or tumours:
                update_fields = {}
                if treatments:
                    update_fields["treatments"] = []
                if tumours:
                    update_fields["tumours"] = []
                
                await db.episodes.update_one(
                    {"_id": episode["_id"]},
                    {"$set": update_fields}
                )
                episodes_updated += 1
        
        except Exception as e:
            error_msg = f"Error processing episode {episode_id}: {str(e)}"
            report.add_error(error_msg)
            print(f"  ❌ {error_msg}")
    
    print(f"\n  ✓ Processed {episodes_processed} episodes")
    print(f"  ✓ Migrated {treatments_migrated} treatments")
    print(f"  ✓ Migrated {tumours_migrated} tumours")
    print(f"  ✓ Updated {episodes_updated} episodes (cleared embedded arrays)")
    
    return treatments_migrated, tumours_migrated


async def validate_after_migration(db, report):
    """Validate migration success"""
    
    print("\n📊 Validating migration...")
    
    # Count after migration
    episodes_count = await db.episodes.count_documents({})
    treatments_count = await db.treatments.count_documents({})
    tumours_count = await db.tumours.count_documents({})
    
    report.add_after("episodes", episodes_count)
    report.add_after("treatments", treatments_count)
    report.add_after("tumours", tumours_count)
    
    # Check for remaining embedded data
    episodes_with_treatments = await db.episodes.count_documents({"treatments.0": {"$exists": True}})
    episodes_with_tumours = await db.episodes.count_documents({"tumours.0": {"$exists": True}})
    
    print(f"  - Episodes: {episodes_count}")
    print(f"  - Treatments collection: {treatments_count}")
    print(f"  - Tumours collection: {tumours_count}")
    print(f"  - Episodes still with embedded treatments: {episodes_with_treatments}")
    print(f"  - Episodes still with embedded tumours: {episodes_with_tumours}")
    
    # Validation checks
    if episodes_with_treatments > 0:
        report.add_warning(f"{episodes_with_treatments} episodes still have embedded treatments")
    
    if episodes_with_tumours > 0:
        report.add_warning(f"{episodes_with_tumours} episodes still have embedded tumours")
    
    # Compare counts
    expected_treatments = report.before.get("embedded_treatments", 0)
    actual_treatments = treatments_count - report.before.get("treatments", 0)
    
    expected_tumours = report.before.get("embedded_tumours", 0)
    actual_tumours = tumours_count - report.before.get("tumours", 0)
    
    if actual_treatments != expected_treatments:
        report.add_warning(
            f"Treatment count mismatch: expected {expected_treatments}, migrated {actual_treatments}"
        )
    
    if actual_tumours != expected_tumours:
        report.add_warning(
            f"Tumour count mismatch: expected {expected_tumours}, migrated {actual_tumours}"
        )
    
    # Sample validation - check a few episodes have their data in separate collections
    sample_episodes = await db.episodes.find({"cancer_type": {"$exists": True}}).limit(5).to_list(5)
    
    for episode in sample_episodes:
        episode_id = str(episode["_id"])
        treatments = await db.treatments.count_documents({"episode_id": episode_id})
        tumours = await db.tumours.count_documents({"episode_id": episode_id})
        
        print(f"  - Episode {episode_id}: {treatments} treatments, {tumours} tumours in separate collections")


async def create_indexes(db):
    """Create indexes for new collections"""
    
    print("\n📑 Creating indexes...")
    
    # Treatments indexes
    await db.treatments.create_index("episode_id")
    await db.treatments.create_index("patient_id")
    await db.treatments.create_index("treatment_type")
    await db.treatments.create_index("treatment_date")
    await db.treatments.create_index([("episode_id", 1), ("treatment_date", -1)])
    
    # Tumours indexes
    await db.tumours.create_index("episode_id")
    await db.tumours.create_index("patient_id")
    await db.tumours.create_index([("episode_id", 1), ("created_at", -1)])
    
    print("  ✓ Indexes created successfully")


async def main():
    """Main migration process"""
    
    print("\n" + "="*80)
    print("MIGRATION: Move Treatments & Tumours to Separate Collections")
    print("="*80 + "\n")
    
    # Connect to database with proper auth
    print(f"Connecting to MongoDB...")
    print(f"Database: {MONGODB_DB_NAME}")
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    
    # Test connection
    try:
        await db.command("ping")
        print(f"✓ Connected successfully")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        client.close()
        return
    
    try:
        # Step 1: Validate before migration
        report = await validate_before_migration(db)
        
        # Confirm with user
        if report.before.get("embedded_treatments", 0) == 0 and report.before.get("embedded_tumours", 0) == 0:
            print("\n⚠️  No embedded treatments or tumours found. Nothing to migrate.")
            client.close()
            return
        
        print(f"\n⚠️  About to migrate:")
        print(f"   - {report.before.get('embedded_treatments', 0)} treatments")
        print(f"   - {report.before.get('embedded_tumours', 0)} tumours")
        print(f"   from {report.before.get('episodes_with_treatments', 0)} episodes")
        
        response = input("\nProceed with migration? (yes/no): ")
        if response.lower() != "yes":
            print("Migration cancelled.")
            client.close()
            return
        
        # Step 2: Perform migration
        treatments_count, tumours_count = await migrate_treatments_and_tumours(db, report)
        
        # Step 3: Create indexes
        await create_indexes(db)
        
        # Step 4: Validate after migration
        await validate_after_migration(db, report)
        
        # Step 5: Print report
        report.print_report()
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
