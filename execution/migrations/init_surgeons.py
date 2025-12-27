"""
Initialize surgeons in the database
"""
import asyncio
import sys
import os
from datetime import datetime, UTC
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Get MongoDB connection from environment
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'surg_outcomes')


async def init_surgeons():
    """Initialize surgeons with default data"""
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    
    surgeons = [
        {"first_name": "Jim", "surname": "Khan", "gmc_number": None},
        {"first_name": "John", "surname": "Conti", "gmc_number": None},
        {"first_name": "Gerald", "surname": "David", "gmc_number": None},
        {"first_name": "Filippos", "surname": "Sagias", "gmc_number": None},
        {"first_name": "Paul", "surname": "Sykes", "gmc_number": None},
        {"first_name": "John", "surname": "Richardson", "gmc_number": None},
        {"first_name": "Ania", "surname": "Przedlack", "gmc_number": None},
        {"first_name": "Dan", "surname": "O'Leary", "gmc_number": None},
    ]
    
    now = datetime.now(UTC)
    
    for surgeon in surgeons:
        # Check if surgeon already exists
        existing = await db.surgeons.find_one({
            "first_name": surgeon["first_name"],
            "surname": surgeon["surname"]
        })
        
        if not existing:
            surgeon["created_at"] = now
            surgeon["updated_at"] = now
            await db.surgeons.insert_one(surgeon)
            print(f"Created surgeon: {surgeon['first_name']} {surgeon['surname']}")
        else:
            print(f"Surgeon already exists: {surgeon['first_name']} {surgeon['surname']}")
    
    client.close()
    print("\nSurgeon initialization complete!")


if __name__ == "__main__":
    asyncio.run(init_surgeons())
