#!/usr/bin/env python3
"""
Migration script to add is_consultant field to existing surgeons
Sets is_consultant=False by default for existing surgeons
"""
import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("MONGODB_DB_NAME", "surgical_outcomes")


async def migrate_surgeons():
    """Add is_consultant field to all existing surgeons"""
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    
    print("🔄 Starting migration: Adding is_consultant field to surgeons...")
    
    # Update all surgeons that don't have is_consultant field
    result = await db.surgeons.update_many(
        {"is_consultant": {"$exists": False}},
        {"$set": {"is_consultant": False}}
    )
    
    print(f"✅ Updated {result.modified_count} surgeon(s)")
    print(f"📊 Matched {result.matched_count} surgeon(s) without is_consultant field")
    
    # Show current state
    total_surgeons = await db.surgeons.count_documents({})
    consultants = await db.surgeons.count_documents({"is_consultant": True})
    
    print(f"\n📈 Current state:")
    print(f"   Total surgeons: {total_surgeons}")
    print(f"   Consultants: {consultants}")
    print(f"   Non-consultants: {total_surgeons - consultants}")
    
    client.close()


if __name__ == "__main__":
    try:
        asyncio.run(migrate_surgeons())
        print("\n✅ Migration completed successfully!")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
