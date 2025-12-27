"""
Create a default admin user for initial system access
"""
import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB_NAME", "surg_outcomes")

async def create_admin_user():
    """Create default admin user"""
    print(f"Connecting to MongoDB at {MONGODB_URI}...")
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    
    # Check if admin already exists
    existing_admin = await db.users.find_one({"email": "admin@example.com"})
    if existing_admin:
        print("✓ Admin user already exists (admin@example.com)")
        return
    
    # Create admin user
    password = b"admin123"
    hashed = bcrypt.hashpw(password, bcrypt.gensalt())
    
    admin_user = {
        "email": "admin@example.com",
        "full_name": "System Administrator",
        "hashed_password": hashed.decode('utf-8'),
        "role": "admin",
        "is_active": True,
        "department": "Administration",
        "job_title": "System Administrator",
        "created_at": datetime.utcnow(),
        "created_by": None,
        "updated_at": datetime.utcnow(),
        "updated_by": None,
        "last_login": None
    }
    
    result = await db.users.insert_one(admin_user)
    print(f"✅ Admin user created!")
    print(f"   Email: admin@example.com")
    print(f"   Password: admin123")
    print(f"   ⚠️  IMPORTANT: Change this password after first login!")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(create_admin_user())
