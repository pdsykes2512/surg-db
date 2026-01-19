import os
#!/usr/bin/env python3
"""Fix investigation dates - convert datetime objects to strings."""

import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

async def fix_investigation_dates():
    client = AsyncIOMotorClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    db = client.surgdb
    collection = db.investigations
    
    try:
        print("Finding investigations with datetime date fields...")
        
        # Find all investigations where date is a datetime object
        cursor = collection.find({"date": {"$type": "date"}})
        
        count = 0
        async for inv in cursor:
            date_obj = inv.get('date')
            if isinstance(date_obj, datetime):
                # Convert to YYYY-MM-DD string format
                date_str = date_obj.strftime('%Y-%m-%d')
                
                # Update the document
                await collection.update_one(
                    {"_id": inv["_id"]},
                    {"$set": {"date": date_str}}
                )
                count += 1
                
                if count % 1000 == 0:
                    print(f"  Processed {count} investigations...")
        
        print(f"\n✓ Converted {count} datetime dates to string format")
        
        # Verify
        datetime_remaining = await collection.count_documents({"date": {"$type": "date"}})
        string_count = await collection.count_documents({"date": {"$type": "string"}})
        
        print(f"\nVerification:")
        print(f"  Date as datetime: {datetime_remaining}")
        print(f"  Date as string: {string_count}")
        
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(fix_investigation_dates())
