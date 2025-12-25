#!/usr/bin/env python3
"""Test script to verify audit logging is working."""

import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient

async def test_audit_logging():
    """Test audit logging collection access."""
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://admin:admin123@surg-db.vps:27017/surgdb?authSource=admin")
    db = client.surgdb
    audit_collection = db.audit_logs
    
    try:
        # Count documents
        count = await audit_collection.count_documents({})
        print(f"✓ Audit logs collection accessible: {count} entries")
        
        # Show sample entries
        if count > 0:
            print("\nRecent audit log entries:")
            async for entry in audit_collection.find().sort("timestamp", -1).limit(5):
                timestamp = entry.get("timestamp", "?")
                username = entry.get("username", "?")
                action = entry.get("action", "?")
                entity_type = entry.get("entity_type", "?")
                entity_id = entry.get("entity_id", "?")
                print(f"  - {timestamp} | {username:12s} | {action:8s} | {entity_type:12s} | {entity_id}")
        else:
            print("\n⚠ No audit log entries found yet. Create/update/delete some entities to test.")
        
        return 0
    except Exception as e:
        print(f"✗ Error accessing audit logs: {e}")
        return 1
    finally:
        client.close()

if __name__ == "__main__":
    sys.exit(asyncio.run(test_audit_logging()))
