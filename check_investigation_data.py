#!/usr/bin/env python3
"""Check investigation data structure."""

import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient

async def check_investigation():
    client = AsyncIOMotorClient("mongodb://admin:admin123@surg-db.vps:27017/surgdb?authSource=admin")
    db = client.surgdb
    collection = db.investigations
    
    try:
        # Get a sample of investigations
        print("Checking date formats in investigations...\n")
        count = 0
        async for inv in collection.find({}, {'_id': 0, 'investigation_id': 1, 'date': 1, 'type': 1, 'subtype': 1}).limit(20):
            count += 1
            date_val = inv.get('date')
            date_type = type(date_val).__name__
            print(f"{count}. {inv.get('investigation_id')} | Type: {date_type:15s} | Value: {date_val}")
        
        # Check if any dates are datetime objects
        print("\n\nChecking for datetime objects...")
        datetime_count = await collection.count_documents({"date": {"$type": "date"}})
        string_count = await collection.count_documents({"date": {"$type": "string"}})
        null_count = await collection.count_documents({"date": None})
        total = await collection.count_documents({})
        
        print(f"Total investigations: {total}")
        print(f"Date as datetime object: {datetime_count}")
        print(f"Date as string: {string_count}")
        print(f"Date as null: {null_count}")
        
        if datetime_count > 0:
            print("\n⚠ Found datetime objects! These need to be converted to strings.")
            # Show example
            example = await collection.find_one({"date": {"$type": "date"}}, {'_id': 0, 'investigation_id': 1, 'date': 1})
            if example:
                print(f"Example: {example}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(check_investigation())
