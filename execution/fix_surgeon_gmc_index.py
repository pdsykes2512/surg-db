#!/usr/bin/env python3
"""
Fix surgeon GMC number unique index issue
- Drop the unique index on gmc_number (it should allow multiple empty values)
- Convert empty string GMC numbers to None
- Create a sparse unique index (allows multiple nulls)
"""
import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "surg_outcomes")


async def fix_gmc_index():
    """Fix GMC number index and data"""
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    
    print("🔧 Fixing surgeon GMC number unique index issue...")
    
    # Step 1: Drop the problematic unique index if it exists
    try:
        await db.surgeons.drop_index("gmc_number_1")
        print("✅ Dropped unique index on gmc_number")
    except Exception as e:
        print(f"ℹ️  No index to drop (or already dropped): {e}")
    
    # Step 2: Convert empty strings to None
    result = await db.surgeons.update_many(
        {"gmc_number": ""},
        {"$set": {"gmc_number": None}}
    )
    print(f"✅ Converted {result.modified_count} empty GMC numbers to null")
    
    # Step 3: Create a partial unique index (unique only when gmc_number exists and is not null)
    try:
        await db.surgeons.create_index(
            "gmc_number",
            unique=True,
            partialFilterExpression={"gmc_number": {"$exists": True, "$type": "string"}},
            name="gmc_number_unique_when_present"
        )
        print("✅ Created partial unique index on gmc_number (unique when present, allows nulls)")
    except Exception as e:
        print(f"⚠️  Could not create partial index: {e}")
    
    # Show current state
    total = await db.surgeons.count_documents({})
    with_gmc = await db.surgeons.count_documents({"gmc_number": {"$ne": None}})
    without_gmc = total - with_gmc
    
    print(f"\n📊 Current state:")
    print(f"   Total surgeons: {total}")
    print(f"   With GMC number: {with_gmc}")
    print(f"   Without GMC number: {without_gmc}")
    
    client.close()


if __name__ == "__main__":
    try:
        asyncio.run(fix_gmc_index())
        print("\n✅ Fix completed successfully!")
    except Exception as e:
        print(f"\n❌ Fix failed: {e}")
        sys.exit(1)
