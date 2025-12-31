"""
Database Index Definitions

This module defines all MongoDB indexes for optimal query performance.
Indexes are created on startup to ensure efficient querying across all collections.

Index Strategy:
- Unique indexes on ID fields for data integrity
- Compound indexes for common filter combinations
- Sparse indexes for optional encrypted fields
- Temporal indexes for date-based queries and sorting
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)


async def ensure_all_indexes(db: AsyncIOMotorDatabase) -> dict:
    """
    Create all required indexes for optimal performance.

    This function is idempotent - it can be called multiple times safely.
    Existing indexes will not be recreated.

    Args:
        db: Motor database instance

    Returns:
        Dict with index creation summary
    """
    logger.info("Creating database indexes...")
    results = {
        'created': [],
        'existing': [],
        'failed': []
    }

    try:
        # ======================
        # PATIENTS COLLECTION
        # ======================
        logger.info("Ensuring indexes on 'patients' collection...")

        # Unique index on patient_id
        await db.patients.create_index("patient_id", unique=True, name="idx_patient_id")
        results['created'].append("patients.patient_id")

        # Unique sparse indexes on encrypted fields (allow null)
        await db.patients.create_index("nhs_number", unique=True, sparse=True, name="idx_nhs_number")
        results['created'].append("patients.nhs_number")

        await db.patients.create_index("mrn", unique=True, sparse=True, name="idx_mrn")
        results['created'].append("patients.mrn")

        # Index for geographic queries
        await db.patients.create_index("demographics.postcode", name="idx_postcode")
        results['created'].append("patients.demographics.postcode")

        # Temporal index for audit/timeline queries
        await db.patients.create_index("created_at", name="idx_patients_created_at")
        results['created'].append("patients.created_at")

        # ======================
        # EPISODES COLLECTION
        # ======================
        logger.info("Ensuring indexes on 'episodes' collection...")

        # Unique index on episode_id
        await db.episodes.create_index("episode_id", unique=True, name="idx_episode_id")
        results['created'].append("episodes.episode_id")

        # Index for frequent patient lookups
        await db.episodes.create_index("patient_id", name="idx_episode_patient_id")
        results['created'].append("episodes.patient_id")

        # Index for sorting/filtering by referral date
        await db.episodes.create_index("referral_date", name="idx_referral_date")
        results['created'].append("episodes.referral_date")

        # Compound index for combined filtering
        await db.episodes.create_index([
            ("condition_type", 1),
            ("cancer_type", 1)
        ], name="idx_condition_cancer_type")
        results['created'].append("episodes.condition_type+cancer_type")

        # Index for surgeon performance queries
        await db.episodes.create_index("lead_clinician", name="idx_lead_clinician")
        results['created'].append("episodes.lead_clinician")

        # Temporal index
        await db.episodes.create_index("created_at", name="idx_episodes_created_at")
        results['created'].append("episodes.created_at")

        # ======================
        # TREATMENTS COLLECTION
        # ======================
        logger.info("Ensuring indexes on 'treatments' collection...")

        # Unique index on treatment_id
        await db.treatments.create_index("treatment_id", unique=True, name="idx_treatment_id")
        results['created'].append("treatments.treatment_id")

        # Index for lookups by episode
        await db.treatments.create_index("episode_id", name="idx_treatment_episode_id")
        results['created'].append("treatments.episode_id")

        # Index for patient treatment history
        await db.treatments.create_index("patient_id", name="idx_treatment_patient_id")
        results['created'].append("treatments.patient_id")

        # Index for temporal queries
        await db.treatments.create_index("admission_date", name="idx_admission_date")
        results['created'].append("treatments.admission_date")

        # Index for surgeon performance analytics
        await db.treatments.create_index("surgeon", name="idx_surgeon")
        results['created'].append("treatments.surgeon")

        # Temporal index
        await db.treatments.create_index("created_at", name="idx_treatments_created_at")
        results['created'].append("treatments.created_at")

        # ======================
        # TUMOURS COLLECTION
        # ======================
        logger.info("Ensuring indexes on 'tumours' collection...")

        # Unique index on tumour_id
        await db.tumours.create_index("tumour_id", unique=True, name="idx_tumour_id")
        results['created'].append("tumours.tumour_id")

        # Index for episode detail lookups
        await db.tumours.create_index("episode_id", name="idx_tumour_episode_id")
        results['created'].append("tumours.episode_id")

        # Index for temporal queries
        await db.tumours.create_index("diagnosis_date", name="idx_diagnosis_date")
        results['created'].append("tumours.diagnosis_date")

        # ======================
        # INVESTIGATIONS COLLECTION
        # ======================
        logger.info("Ensuring indexes on 'investigations' collection...")

        # Unique index on investigation_id
        await db.investigations.create_index("investigation_id", unique=True, name="idx_investigation_id")
        results['created'].append("investigations.investigation_id")

        # Index for episode lookups
        await db.investigations.create_index("episode_id", name="idx_investigation_episode_id")
        results['created'].append("investigations.episode_id")

        # Index for filtering by type
        await db.investigations.create_index("investigation_type", name="idx_investigation_type")
        results['created'].append("investigations.investigation_type")

        # ======================
        # CLINICIANS COLLECTION
        # ======================
        logger.info("Ensuring indexes on 'clinicians' collection...")

        # Compound index for name searches
        await db.clinicians.create_index([
            ("surname", 1),
            ("first_name", 1)
        ], name="idx_clinician_name")
        results['created'].append("clinicians.surname+first_name")

        # ======================
        # AUDIT_LOGS COLLECTION
        # ======================
        logger.info("Ensuring indexes on 'audit_logs' collection...")

        # Compound index for entity history
        await db.audit_logs.create_index([
            ("entity_type", 1),
            ("entity_id", 1)
        ], name="idx_audit_entity")
        results['created'].append("audit_logs.entity_type+entity_id")

        # Index for user activity
        await db.audit_logs.create_index("user_id", name="idx_audit_user_id")
        results['created'].append("audit_logs.user_id")

        # Index for recent activity queries (most important for audit logs)
        await db.audit_logs.create_index("timestamp", name="idx_audit_timestamp")
        results['created'].append("audit_logs.timestamp")

        logger.info(f"✅ Successfully created {len(results['created'])} indexes")
        return results

    except Exception as e:
        logger.error(f"❌ Error creating indexes: {e}")
        results['failed'].append(str(e))
        raise


async def get_index_info(db: AsyncIOMotorDatabase) -> dict:
    """
    Get information about all indexes across collections.
    Useful for verification and debugging.

    Returns:
        Dict mapping collection names to their index information
    """
    collections = [
        'patients', 'episodes', 'treatments', 'tumours',
        'investigations', 'clinicians', 'audit_logs'
    ]

    index_info = {}
    for coll_name in collections:
        indexes = await db[coll_name].list_indexes().to_list(length=None)
        index_info[coll_name] = [
            {
                'name': idx['name'],
                'keys': idx['key'],
                'unique': idx.get('unique', False),
                'sparse': idx.get('sparse', False)
            }
            for idx in indexes
        ]

    return index_info


async def drop_all_indexes(db: AsyncIOMotorDatabase, confirm: bool = False):
    """
    Drop all non-_id indexes across all collections.

    WARNING: This is a destructive operation. Use with caution.
    Requires confirm=True to execute.

    Args:
        db: Motor database instance
        confirm: Must be True to execute (safety check)
    """
    if not confirm:
        logger.warning("drop_all_indexes called without confirm=True. Aborting.")
        return

    collections = [
        'patients', 'episodes', 'treatments', 'tumours',
        'investigations', 'clinicians', 'audit_logs'
    ]

    logger.warning("🚨 Dropping all indexes (except _id)...")
    for coll_name in collections:
        try:
            await db[coll_name].drop_indexes()
            logger.info(f"✓ Dropped indexes on {coll_name}")
        except Exception as e:
            logger.error(f"❌ Failed to drop indexes on {coll_name}: {e}")

    logger.warning("⚠️  All indexes dropped. Remember to recreate them with ensure_all_indexes()")
