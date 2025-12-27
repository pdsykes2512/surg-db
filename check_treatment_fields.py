#!/usr/bin/env python3
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient('mongodb://localhost:27017/')
    db = client.surgdb
    
    # Get one treatment
    treatment = await db.treatments.find_one({'treatment_type': 'surgery'})
    
    if treatment:
        print("Treatment keys:")
        for key in sorted(treatment.keys()):
            if key != '_id':
                print(f"  {key}: {type(treatment[key]).__name__}")
    else:
        print("No treatment found")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
