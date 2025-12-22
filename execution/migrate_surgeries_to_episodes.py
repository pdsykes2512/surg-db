#!/usr/bin/env python3
"""
Migrate existing surgery records to the new episode-based system.
Each surgery becomes an episode with a surgery treatment.
This preserves all existing data while transitioning to the new architecture.
"""
import asyncio
import sys
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.config import settings


def generate_episode_id(surgery_id: str) -> str:
    """Generate episode ID from surgery ID"""
    # Convert SUR-xxx to EPI-xxx
    if surgery_id.startswith("SUR-"):
        return surgery_id.replace("SUR-", "EPI-", 1)
    return f"EPI-{surgery_id}"


def generate_treatment_id(surgery_id: str) -> str:
    """Generate treatment ID from surgery ID"""
    # Keep the surgery ID as treatment ID with TRT prefix
    if surgery_id.startswith("SUR-"):
        return surgery_id.replace("SUR-", "TRT-", 1)
    return f"TRT-{surgery_id}"


async def migrate_surgeries_to_episodes():
    """Migrate surgery records to episode format"""
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]
    
    surgeries_collection = db["surgeries"]
    episodes_collection = db["episodes"]
    
    # Get all surgeries
    surgeries = await surgeries_collection.find({}).to_list(length=None)
    
    if not surgeries:
        print("No surgeries found to migrate.")
        client.close()
        return
    
    print(f"Found {len(surgeries)} surgeries to migrate\n")
    
    migrated_count = 0
    skipped_count = 0
    error_count = 0
    
    for surgery in surgeries:
        try:
            surgery_id = surgery.get("surgery_id")
            episode_id = generate_episode_id(surgery_id)
            
            # Check if episode already exists
            existing = await episodes_collection.find_one({"episode_id": episode_id})
            if existing:
                print(f"⊘ Skipping {surgery_id} - episode {episode_id} already exists")
                skipped_count += 1
                continue
            
            # Extract condition info from surgery classification
            classification = surgery.get("classification", {})
            indication = classification.get("indication", "benign")
            
            # Map indication to condition_type
            condition_type_map = {
                "cancer": "cancer",
                "ibd": "ibd",
                "diverticular": "benign",
                "benign": "benign",
                "other": "benign"
            }
            condition_type = condition_type_map.get(indication, "benign")
            
            # Determine cancer type if applicable
            cancer_type = None
            cancer_data = {}
            if condition_type == "cancer":
                cancer_specific = surgery.get("cancer_specific", {})
                if cancer_specific.get("applicable"):
                    raw_cancer_type = cancer_specific.get("cancer_type", "").lower()
                    
                    # Map surgery cancer types to new episode cancer types
                    cancer_type_map = {
                        "colorectal": "bowel",
                        "colon": "bowel",
                        "rectal": "bowel",
                        "bowel": "bowel",
                        "renal": "kidney",
                        "kidney": "kidney",
                        "breast": "breast_primary",
                        "oesophageal": "oesophageal",
                        "ovarian": "ovarian",
                        "prostate": "prostate"
                    }
                    
                    for key, value in cancer_type_map.items():
                        if key in raw_cancer_type:
                            cancer_type = value
                            break
                    
                    # Build basic cancer_data from available surgery data
                    if cancer_type:
                        tnm_staging = cancer_specific.get("tnm_staging")
                        pathology = cancer_specific.get("pathology")
                        
                        cancer_data = {
                            "presentation_type": "symptomatic",  # Default
                            "mdt_treatment_plan": cancer_specific.get("adjuvant_therapy_planned") and "Adjuvant therapy planned" or None
                        }
                        
                        if tnm_staging:
                            cancer_data["tnm_staging"] = tnm_staging
                        
                        if pathology:
                            if cancer_type == "bowel":
                                cancer_data.update({
                                    "cancer_site": "colon",  # Default
                                    "histological_type": pathology.get("histology"),
                                    "tumor_size_mm": pathology.get("tumor_size_mm"),
                                    "lymph_nodes_examined": pathology.get("lymph_nodes_examined"),
                                    "lymph_nodes_positive": pathology.get("lymph_nodes_positive"),
                                    "lymphovascular_invasion": pathology.get("lymphovascular_invasion"),
                                    "perineural_invasion": pathology.get("perineural_invasion"),
                                })
            
            # Build episode document
            timeline = surgery.get("perioperative_timeline", {})
            team = surgery.get("team", {})
            audit = surgery.get("audit_trail", {})
            
            episode = {
                "episode_id": episode_id,
                "patient_id": surgery.get("patient_id"),
                "condition_type": condition_type,
                "cancer_type": cancer_type,
                "cancer_data": cancer_data if cancer_data else None,
                
                # Dates
                "referral_date": timeline.get("admission_date") or datetime.utcnow(),
                "first_seen_date": timeline.get("admission_date"),
                "mdt_discussion_date": None,
                
                # Team
                "lead_clinician": team.get("primary_surgeon", "Unknown"),
                "mdt_team": team.get("assistant_surgeons", []),
                
                # Status
                "episode_status": "completed" if surgery.get("outcomes", {}).get("discharge_date") else "active",
                
                # Audit
                "created_at": audit.get("created_at", datetime.utcnow()),
                "created_by": audit.get("created_by", "migration_script"),
                "last_modified_at": audit.get("updated_at", datetime.utcnow()),
                "last_modified_by": audit.get("updated_by", "migration_script"),
                
                # Treatments - surgery as first treatment
                "treatments": [
                    {
                        "treatment_id": generate_treatment_id(surgery_id),
                        "treatment_type": "surgery",
                        "treatment_date": timeline.get("surgery_date", datetime.utcnow()),
                        "treating_clinician": team.get("primary_surgeon", "Unknown"),
                        "treatment_intent": "curative" if condition_type == "cancer" else "curative",
                        "notes": None,
                        
                        # Preserve all surgery data
                        "classification": classification,
                        "procedure": surgery.get("procedure", {}),
                        "perioperative_timeline": timeline,
                        "team": team,
                        "intraoperative": surgery.get("intraoperative", {}),
                        "pathology": surgery.get("cancer_specific", {}).get("pathology") if surgery.get("cancer_specific", {}).get("applicable") else None,
                        "postoperative_events": surgery.get("postoperative_events", {}),
                        "outcomes": surgery.get("outcomes", {}),
                        "follow_up": surgery.get("follow_up", {}),
                        "documents": surgery.get("documents", []),
                    }
                ],
                
                # Migration metadata
                "_migration": {
                    "migrated_from": "surgeries",
                    "original_surgery_id": surgery_id,
                    "migration_date": datetime.utcnow(),
                    "migration_script": "migrate_surgeries_to_episodes.py"
                }
            }
            
            # Insert episode
            await episodes_collection.insert_one(episode)
            print(f"✓ Migrated {surgery_id} → {episode_id} (condition: {condition_type}, cancer: {cancer_type or 'N/A'})")
            migrated_count += 1
            
        except Exception as e:
            print(f"✗ Error migrating surgery {surgery.get('surgery_id', 'unknown')}: {str(e)}")
            error_count += 1
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"Migration Summary:")
    print(f"  Migrated: {migrated_count}")
    print(f"  Skipped (already exists): {skipped_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total processed: {len(surgeries)}")
    print(f"{'='*60}\n")
    
    if migrated_count > 0:
        print("Note: Original surgery records are preserved in the 'surgeries' collection.")
        print("You can safely keep both collections during the transition period.")
    
    client.close()


async def main():
    """Main function"""
    print("Starting surgery to episode migration...\n")
    print("This will convert existing surgery records to the new episode format.")
    print("Original surgery records will be preserved.\n")
    
    try:
        await migrate_surgeries_to_episodes()
        print("\n✓ Migration completed!")
    except Exception as e:
        print(f"\n✗ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
