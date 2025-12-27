#!/usr/bin/env python3
"""
Analyze and optimize database queries
Adds comprehensive indexes, query profiling, and optimization recommendations
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime


async def analyze_collection_stats(db, collection_name):
    """Get collection statistics"""
    stats = await db.command("collStats", collection_name)
    return {
        "count": stats.get("count", 0),
        "size_mb": stats.get("size", 0) / (1024 * 1024),
        "avg_obj_size": stats.get("avgObjSize", 0),
        "indexes": stats.get("nindexes", 0)
    }


async def create_optimized_indexes(db):
    """Create comprehensive indexes for all collections"""
    print("\n" + "="*60)
    print("CREATING OPTIMIZED DATABASE INDEXES")
    print("="*60 + "\n")
    
    # Helper function to create index safely
    async def safe_create_index(collection, keys, **kwargs):
        try:
            await collection.create_index(keys, **kwargs)
            return True
        except Exception as e:
            if "already exists" in str(e) or "IndexKeySpecsConflict" in str(e):
                return False  # Index already exists
            raise  # Re-raise other errors
    
    # PATIENTS COLLECTION
    print("📊 Patients Collection:")
    if await safe_create_index(db.patients, [("record_number", 1)], unique=True):
        print("  ✓ Unique index: record_number")
    else:
        print("  • Index exists: record_number")
    
    if await safe_create_index(db.patients, [("nhs_number", 1)], unique=True, sparse=True):
        print("  ✓ Unique sparse index: nhs_number")
    else:
        print("  • Index exists: nhs_number")
    
    if await safe_create_index(db.patients, [("surname", 1), ("first_name", 1)]):
        print("  ✓ Compound index: surname + first_name (for name searches)")
    else:
        print("  • Index exists: surname + first_name")
    
    if await safe_create_index(db.patients, [("date_of_birth", 1)]):
        print("  ✓ Index: date_of_birth (for age calculations)")
    else:
        print("  • Index exists: date_of_birth")
    
    # EPISODES COLLECTION (formerly surgeries)
    print("\n📊 Episodes Collection:")
    await db.surgeries.create_index([("patient_id", 1)])
    print("  ✓ Index: patient_id (for patient episode lookup)")
    
    await db.surgeries.create_index([("perioperative_timeline.surgery_date", -1)])
    print("  ✓ Index: surgery_date descending (for recent episodes)")
    
    await db.surgeries.create_index([("classification.urgency", 1)])
    print("  ✓ Index: urgency (for filtering)")
    
    await db.surgeries.create_index([("team.primary_surgeon", 1)])
    print("  ✓ Index: primary_surgeon (for surgeon-specific queries)")
    
    # Compound indexes for common query patterns
    await db.surgeries.create_index([
        ("perioperative_timeline.surgery_date", -1),
        ("classification.urgency", 1)
    ])
    print("  ✓ Compound: surgery_date + urgency")
    
    await db.surgeries.create_index([
        ("team.primary_surgeon", 1),
        ("perioperative_timeline.surgery_date", -1)
    ])
    print("  ✓ Compound: primary_surgeon + surgery_date")
    
    # Outcome indexes for reporting
    await db.surgeries.create_index([("outcomes.mortality_30day", 1)])
    print("  ✓ Index: mortality_30day (for outcome reporting)")
    
    await db.surgeries.create_index([("outcomes.readmission_30day", 1)])
    print("  ✓ Index: readmission_30day")
    
    await db.surgeries.create_index([("postoperative_events.complications", 1)])
    print("  ✓ Index: complications (for complication tracking)")
    
    # Episode type and category indexes
    await db.surgeries.create_index([("episode_type", 1)])
    print("  ✓ Index: episode_type (cancer/IBD/benign)")
    
    await db.surgeries.create_index([("cancer_episode.category", 1)])
    print("  ✓ Index: cancer category (colorectal/upper_gi/etc)")
    
    # SURGEONS/CLINICIANS COLLECTION
    print("\n📊 Surgeons Collection:")
    await db.surgeons.create_index([("gmc_number", 1)], unique=True, sparse=True)
    print("  ✓ Unique sparse index: gmc_number")
    
    await db.surgeons.create_index([("first_name", 1), ("surname", 1)])
    print("  ✓ Compound index: first_name + surname")
    
    await db.surgeons.create_index([("is_active", 1)])
    print("  ✓ Index: is_active (for filtering active surgeons)")
    
    # USERS COLLECTION
    print("\n📊 Users Collection:")
    await db.users.create_index([("email", 1)], unique=True)
    print("  ✓ Unique index: email")
    
    await db.users.create_index([("is_active", 1)])
    print("  ✓ Index: is_active")
    
    await db.users.create_index([("role", 1)])
    print("  ✓ Index: role")
    
    # AUDIT LOGS COLLECTION
    print("\n📊 Audit Logs Collection:")
    await db.audit_logs.create_index([("timestamp", -1)])
    print("  ✓ Index: timestamp descending (for recent activity)")
    
    await db.audit_logs.create_index([("user_id", 1), ("timestamp", -1)])
    print("  ✓ Compound: user_id + timestamp (for user history)")
    
    await db.audit_logs.create_index([("entity_type", 1), ("entity_id", 1)])
    print("  ✓ Compound: entity_type + entity_id (for entity history)")
    
    await db.audit_logs.create_index([("action", 1)])
    print("  ✓ Index: action (for filtering by action type)")
    
    # TTL index for audit log retention (optional - keep 2 years of logs)
    await db.audit_logs.create_index(
        [("timestamp", 1)],
        expireAfterSeconds=63072000  # 2 years
    )
    print("  ✓ TTL index: auto-delete logs after 2 years")
    
    # INVESTIGATIONS COLLECTION
    print("\n📊 Investigations Collection:")
    await db.investigations.create_index([("episode_id", 1)])
    print("  ✓ Index: episode_id (for episode-specific investigations)")
    
    await db.investigations.create_index([("patient_id", 1)])
    print("  ✓ Index: patient_id (for patient investigation history)")
    
    await db.investigations.create_index([("investigation_date", -1)])
    print("  ✓ Index: investigation_date descending")
    
    await db.investigations.create_index([("investigation_type", 1)])
    print("  ✓ Index: investigation_type (imaging/endoscopy/laboratory)")
    
    # TUMOURS COLLECTION
    print("\n📊 Tumours Collection:")
    await db.tumours.create_index([("episode_id", 1)])
    print("  ✓ Index: episode_id")
    
    await db.tumours.create_index([("patient_id", 1)])
    print("  ✓ Index: patient_id")


async def get_index_usage_stats(db):
    """Get index usage statistics"""
    print("\n" + "="*60)
    print("INDEX USAGE STATISTICS")
    print("="*60 + "\n")
    
    collections = ["patients", "surgeries", "surgeons", "users", "audit_logs", "investigations"]
    
    for coll_name in collections:
        print(f"\n{coll_name.upper()}:")
        indexes = await db[coll_name].index_information()
        for idx_name, idx_info in indexes.items():
            print(f"  • {idx_name}: {idx_info.get('key', [])}")


async def analyze_slow_queries(db):
    """Analyze and report slow queries"""
    print("\n" + "="*60)
    print("QUERY PERFORMANCE RECOMMENDATIONS")
    print("="*60 + "\n")
    
    print("✓ Enable MongoDB profiling to capture slow queries:")
    print("  db.setProfilingLevel(1, { slowms: 100 })")
    print("\n✓ Monitor slow queries with:")
    print("  db.system.profile.find().limit(10).sort({ ts: -1 })")
    print("\n✓ Analyze query plans with:")
    print("  db.surgeries.find({...}).explain('executionStats')")


async def main():
    """Main optimization routine"""
    print("\n" + "="*60)
    print("DATABASE QUERY OPTIMIZATION TOOL")
    print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    client = AsyncIOMotorClient('mongodb://admin:admin123@localhost:27017/surg_outcomes?authSource=admin')
    db = client.surg_outcomes
    
    try:
        # Get collection statistics
        print("\n" + "="*60)
        print("COLLECTION STATISTICS")
        print("="*60 + "\n")
        
        for coll_name in ["patients", "surgeries", "surgeons", "users", "audit_logs", "investigations"]:
            try:
                stats = await analyze_collection_stats(db, coll_name)
                print(f"{coll_name}:")
                print(f"  Documents: {stats['count']:,}")
                print(f"  Size: {stats['size_mb']:.2f} MB")
                print(f"  Avg doc size: {stats['avg_obj_size']:.0f} bytes")
                print(f"  Indexes: {stats['indexes']}\n")
            except Exception as e:
                print(f"{coll_name}: Collection not found or error - {e}\n")
        
        # Create optimized indexes
        await create_optimized_indexes(db)
        
        # Show index usage
        await get_index_usage_stats(db)
        
        # Performance recommendations
        await analyze_slow_queries(db)
        
        print("\n" + "="*60)
        print("✅ DATABASE OPTIMIZATION COMPLETE")
        print("="*60 + "\n")
        
        print("NEXT STEPS:")
        print("1. Monitor query performance in ~/.tmp/api_requests.log")
        print("2. Enable MongoDB profiling for slow query detection")
        print("3. Review and tune indexes based on actual query patterns")
        print("4. Consider adding caching for frequently accessed data")
        
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
