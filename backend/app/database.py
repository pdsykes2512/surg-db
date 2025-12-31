"""
MongoDB database connection and utilities
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from .config import settings
import logging

logger = logging.getLogger(__name__)


class Database:
    client: Optional[AsyncIOMotorClient] = None
    
    @classmethod
    async def connect_db(cls):
        """Establish database connection"""
        cls.client = AsyncIOMotorClient(settings.mongodb_uri)
        print(f"Connected to MongoDB at {settings.mongodb_uri}")

    @classmethod
    async def initialize_indexes(cls):
        """Initialize database indexes for optimal performance"""
        if not cls.client:
            raise Exception("Database not connected. Call connect_db first.")

        logger.info("Initializing database indexes...")
        created_indexes = []
        failed_indexes = []

        # Get database instances
        clinical_db = cls.client[settings.mongodb_db_name]
        system_db = cls.client[settings.mongodb_system_db_name]

        # Helper function to create index with error handling
        async def create_index_safe(collection, *args, **kwargs):
            index_name = kwargs.get('name', 'unnamed')
            try:
                await collection.create_index(*args, **kwargs)
                created_indexes.append(index_name)
                return True
            except Exception as e:
                error_msg = str(e)
                if "E11000" in error_msg or "DuplicateKey" in error_msg:
                    logger.warning(f"⚠️  Skipping {index_name}: Data quality issue (duplicates found)")
                    failed_indexes.append(f"{index_name} (duplicates)")
                elif "IndexOptionsConflict" in error_msg or "already exists" in error_msg:
                    logger.info(f"✓ Index {index_name} already exists")
                    created_indexes.append(f"{index_name} (existing)")
                else:
                    logger.error(f"❌ Failed to create {index_name}: {error_msg[:100]}")
                    failed_indexes.append(f"{index_name} ({error_msg[:50]})")
                return False

        try:
            # PATIENTS COLLECTION
            logger.info("Creating indexes on patients collection...")

            # Drop problematic old indexes
            for idx in ["idx_nhs_number", "idx_mrn"]:
                try:
                    await clinical_db.patients.drop_index(idx)
                    logger.info(f"✓ Dropped old {idx}")
                except:
                    pass

            await create_index_safe(clinical_db.patients, "patient_id", unique=True, name="idx_patient_id")
            await create_index_safe(clinical_db.patients, "nhs_number", unique=True, name="idx_nhs_number",
                                    partialFilterExpression={"nhs_number": {"$exists": True, "$type": "string"}})
            await create_index_safe(clinical_db.patients, "mrn", unique=True, name="idx_mrn",
                                    partialFilterExpression={"mrn": {"$exists": True, "$type": "string"}})
            await create_index_safe(clinical_db.patients, "demographics.postcode", name="idx_postcode")
            await create_index_safe(clinical_db.patients, "created_at", name="idx_patients_created_at")

            # EPISODES COLLECTION
            logger.info("Creating indexes on episodes collection...")
            await create_index_safe(clinical_db.episodes, "episode_id", unique=True, name="idx_episode_id")
            await create_index_safe(clinical_db.episodes, "patient_id", name="idx_episode_patient_id")
            await create_index_safe(clinical_db.episodes, "referral_date", name="idx_referral_date")
            await create_index_safe(clinical_db.episodes, [("condition_type", 1), ("cancer_type", 1)], name="idx_condition_cancer_type")
            await create_index_safe(clinical_db.episodes, "lead_clinician", name="idx_lead_clinician")
            await create_index_safe(clinical_db.episodes, "created_at", name="idx_episodes_created_at")

            # TREATMENTS COLLECTION
            logger.info("Creating indexes on treatments collection...")
            await create_index_safe(clinical_db.treatments, "treatment_id", unique=True, name="idx_treatment_id")
            await create_index_safe(clinical_db.treatments, "episode_id", name="idx_treatment_episode_id")
            await create_index_safe(clinical_db.treatments, "patient_id", name="idx_treatment_patient_id")
            await create_index_safe(clinical_db.treatments, "admission_date", name="idx_admission_date")
            await create_index_safe(clinical_db.treatments, "surgeon", name="idx_surgeon")
            await create_index_safe(clinical_db.treatments, "created_at", name="idx_treatments_created_at")

            # TUMOURS COLLECTION
            logger.info("Creating indexes on tumours collection...")
            await create_index_safe(clinical_db.tumours, "tumour_id", unique=True, name="idx_tumour_id")
            await create_index_safe(clinical_db.tumours, "episode_id", name="idx_tumour_episode_id")
            await create_index_safe(clinical_db.tumours, "diagnosis_date", name="idx_diagnosis_date")

            # INVESTIGATIONS COLLECTION
            logger.info("Creating indexes on investigations collection...")
            # Skip unique index on investigation_id due to known duplicates
            await create_index_safe(clinical_db.investigations, "investigation_id", name="idx_investigation_id_non_unique")
            await create_index_safe(clinical_db.investigations, "episode_id", name="idx_investigation_episode_id")
            await create_index_safe(clinical_db.investigations, "investigation_type", name="idx_investigation_type")

            # CLINICIANS COLLECTION (system DB)
            logger.info("Creating indexes on clinicians collection...")
            await create_index_safe(system_db.clinicians, [("surname", 1), ("first_name", 1)], name="idx_clinician_name")

            # AUDIT_LOGS COLLECTION (system DB)
            logger.info("Creating indexes on audit_logs collection...")
            await create_index_safe(system_db.audit_logs, [("entity_type", 1), ("entity_id", 1)], name="idx_audit_entity")
            await create_index_safe(system_db.audit_logs, "user_id", name="idx_audit_user_id")
            await create_index_safe(system_db.audit_logs, "timestamp", name="idx_audit_timestamp")

            # Summary
            logger.info(f"✅ Index initialization complete: {len(created_indexes)} created/verified, {len(failed_indexes)} skipped")
            if failed_indexes:
                logger.warning(f"⚠️  Skipped indexes (data quality issues): {', '.join(failed_indexes)}")

            return {'success': True, 'created': len(created_indexes), 'failed': len(failed_indexes)}

        except Exception as e:
            logger.error(f"❌ Unexpected error during index initialization: {e}")
            logger.warning("⚠️  Application will continue with partially created indexes")
            return {'success': False, 'error': str(e), 'created': len(created_indexes), 'failed': len(failed_indexes)}
        
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
