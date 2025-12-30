"""
MongoDB database connection and utilities
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from .config import settings


class Database:
    client: Optional[AsyncIOMotorClient] = None
    
    @classmethod
    async def connect_db(cls):
        """Establish database connection"""
        cls.client = AsyncIOMotorClient(settings.mongodb_uri)
        print(f"Connected to MongoDB at {settings.mongodb_uri}")
        
    @classmethod
    async def close_db(cls):
        """Close database connection"""
        if cls.client:
            cls.client.close()
            print("Closed MongoDB connection")
    
    @classmethod
    def get_database(cls):
        """Get clinical audit database instance"""
        if not cls.client:
            raise Exception("Database not connected. Call connect_db first.")
        return cls.client[settings.mongodb_db_name]

    @classmethod
    def get_system_database(cls):
        """Get system database instance (users, clinicians, audit logs)"""
        if not cls.client:
            raise Exception("Database not connected. Call connect_db first.")
        return cls.client[settings.mongodb_system_db_name]

    @classmethod
    def get_collection(cls, collection_name: str):
        """Get collection from clinical audit database"""
        db = cls.get_database()
        return db[collection_name]

    @classmethod
    def get_system_collection(cls, collection_name: str):
        """Get collection from system database"""
        db = cls.get_system_database()
        return db[collection_name]


# Convenience functions
def get_database():
    """Get database instance for dependency injection"""
    return Database.get_database()


async def get_patients_collection():
    """Get patients collection"""
    return Database.get_collection("patients")


async def get_surgeries_collection():
    """Get surgeries collection"""
    return Database.get_collection("surgeries")


async def get_episodes_collection():
    """Get episodes collection"""
    return Database.get_collection("episodes")


async def get_treatments_collection():
    """Get treatments collection"""
    return Database.get_collection("treatments")


async def get_tumours_collection():
    """Get tumours collection"""
    return Database.get_collection("tumours")


async def get_clinicians_collection():
    """Get clinicians collection from system database"""
    return Database.get_system_collection("clinicians")

async def get_investigations_collection():
    """Get investigations collection"""
    return Database.get_collection("investigations")

async def get_audit_logs_collection():
    """Get audit logs collection from system database"""
    return Database.get_system_collection("audit_logs")
