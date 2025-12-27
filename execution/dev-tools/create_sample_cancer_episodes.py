#!/usr/bin/env python3
"""
Test script to create sample cancer episodes for demonstration and testing.
Creates one episode for each cancer type with realistic data.
"""
import asyncio
import sys
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.config import settings


async def create_sample_episodes():
    """Create sample cancer episodes"""
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]
    
    episodes_collection = db["episodes"]
    patients_collection = db["patients"]
    
    # Check if we have any patients
    patient_count = await patients_collection.count_documents({})
    if patient_count == 0:
        print("⚠️  No patients found in database.")
        print("   Please create patients first using the admin interface.")
        client.close()
        return
    
    # Get first few patients
    patients = await patients_collection.find({}).limit(7).to_list(length=7)
    if len(patients) < 7:
        print(f"⚠️  Only {len(patients)} patients found. Creating episodes for available patients.")
    
    sample_episodes = []
    today = datetime.now()
    
    # Bowel Cancer Episode
    if len(patients) > 0:
        sample_episodes.append({
            "episode_id": "EPI-SAMPLE-BOWEL-001",
            "patient_id": patients[0]["record_number"],
            "condition_type": "cancer",
            "cancer_type": "bowel",
            "referral_date": (today - timedelta(days=60)).isoformat(),
            "first_seen_date": (today - timedelta(days=55)).isoformat(),
            "mdt_discussion_date": (today - timedelta(days=50)).isoformat(),
            "lead_clinician": "Dr. Sarah Johnson",
            "mdt_team": ["Dr. Michael Chen", "Dr. Emily Roberts"],
            "episode_status": "active",
            "created_at": datetime.utcnow(),
            "created_by": "sample_data_script",
            "last_modified_at": datetime.utcnow(),
            "last_modified_by": "sample_data_script",
            "cancer_data": {
                "cancer_site": "rectum",
                "presentation_type": "symptomatic",
                "symptoms": ["bleeding", "pain"],
                "histological_type": "adenocarcinoma",
                "differentiation": "moderate",
                "tumor_size_mm": 35.0,
                "lymph_nodes_examined": 15,
                "lymph_nodes_positive": 2,
                "lymphovascular_invasion": True,
                "kras_status": "wild_type",
                "mdt_treatment_plan": "Neoadjuvant chemoradiotherapy followed by total mesorectal excision"
            },
            "treatments": []
        })
    
    # Breast Cancer (Primary)
    if len(patients) > 1:
        sample_episodes.append({
            "episode_id": "EPI-SAMPLE-BREAST-001",
            "patient_id": patients[1]["record_number"],
            "condition_type": "cancer",
            "cancer_type": "breast_primary",
            "referral_date": (today - timedelta(days=45)).isoformat(),
            "first_seen_date": (today - timedelta(days=40)).isoformat(),
            "mdt_discussion_date": (today - timedelta(days=35)).isoformat(),
            "lead_clinician": "Dr. Lisa Anderson",
            "mdt_team": ["Dr. James Wilson"],
            "episode_status": "active",
            "created_at": datetime.utcnow(),
            "created_by": "sample_data_script",
            "last_modified_at": datetime.utcnow(),
            "last_modified_by": "sample_data_script",
            "cancer_data": {
                "is_metastatic": False,
                "cancer_site": "left_breast",
                "laterality": "left",
                "quadrant": "upper_outer",
                "detection_method": "screening",
                "histological_type": "ductal",
                "histological_grade": 2,
                "er_status": "positive",
                "er_percentage": 95.0,
                "pr_status": "positive",
                "pr_percentage": 85.0,
                "her2_status": "negative",
                "ki67_percentage": 20.0,
                "tumor_size_mm": 18.0,
                "lymph_nodes_examined": 2,
                "lymph_nodes_positive": 0,
                "surgery_plan": "lumpectomy",
                "mdt_treatment_plan": "Wide local excision + sentinel node biopsy, followed by adjuvant endocrine therapy"
            },
            "treatments": []
        })
    
    # Prostate Cancer
    if len(patients) > 2:
        sample_episodes.append({
            "episode_id": "EPI-SAMPLE-PROSTATE-001",
            "patient_id": patients[2]["record_number"],
            "condition_type": "cancer",
            "cancer_type": "prostate",
            "referral_date": (today - timedelta(days=30)).isoformat(),
            "first_seen_date": (today - timedelta(days=25)).isoformat(),
            "mdt_discussion_date": (today - timedelta(days=20)).isoformat(),
            "lead_clinician": "Dr. Robert Martinez",
            "mdt_team": ["Dr. Helen Thompson"],
            "episode_status": "active",
            "created_at": datetime.utcnow(),
            "created_by": "sample_data_script",
            "last_modified_at": datetime.utcnow(),
            "last_modified_by": "sample_data_script",
            "cancer_data": {
                "detection_method": "psa_screening",
                "psa_at_diagnosis": 8.5,
                "gleason_primary": 3,
                "gleason_secondary": 4,
                "gleason_score": 7,
                "isup_grade_group": 2,
                "pirads_score": 4,
                "risk_group": "intermediate",
                "metastatic": False,
                "mdt_treatment_plan": "Radical prostatectomy with nerve-sparing technique recommended"
            },
            "treatments": []
        })
    
    # Kidney Cancer
    if len(patients) > 3:
        sample_episodes.append({
            "episode_id": "EPI-SAMPLE-KIDNEY-001",
            "patient_id": patients[3]["record_number"],
            "condition_type": "cancer",
            "cancer_type": "kidney",
            "referral_date": (today - timedelta(days=40)).isoformat(),
            "first_seen_date": (today - timedelta(days=35)).isoformat(),
            "mdt_discussion_date": (today - timedelta(days=28)).isoformat(),
            "lead_clinician": "Dr. Patricia Lee",
            "mdt_team": [],
            "episode_status": "active",
            "created_at": datetime.utcnow(),
            "created_by": "sample_data_script",
            "last_modified_at": datetime.utcnow(),
            "last_modified_by": "sample_data_script",
            "cancer_data": {
                "cancer_site": "right_kidney",
                "histological_type": "clear_cell",
                "fuhrman_grade": 2,
                "presentation_type": "incidental",
                "tumor_size_mm": 42.0,
                "tumor_location": "lower_pole",
                "imdc_risk_score": "favorable",
                "mdt_treatment_plan": "Partial nephrectomy (nephron-sparing surgery)"
            },
            "treatments": []
        })
    
    # Oesophageal Cancer
    if len(patients) > 4:
        sample_episodes.append({
            "episode_id": "EPI-SAMPLE-OESOPH-001",
            "patient_id": patients[4]["record_number"],
            "condition_type": "cancer",
            "cancer_type": "oesophageal",
            "referral_date": (today - timedelta(days=50)).isoformat(),
            "first_seen_date": (today - timedelta(days=45)).isoformat(),
            "mdt_discussion_date": (today - timedelta(days=40)).isoformat(),
            "lead_clinician": "Dr. David Brown",
            "mdt_team": ["Dr. Susan Clark"],
            "episode_status": "active",
            "created_at": datetime.utcnow(),
            "created_by": "sample_data_script",
            "last_modified_at": datetime.utcnow(),
            "last_modified_by": "sample_data_script",
            "cancer_data": {
                "cancer_site": "lower_third",
                "distance_from_incisors_cm": 38.0,
                "histological_type": "adenocarcinoma",
                "differentiation": "moderate",
                "symptoms": ["dysphagia", "weight_loss"],
                "dysphagia_score": 2,
                "weight_loss_kg": 8.5,
                "neoadjuvant_therapy": "chemoradiotherapy",
                "mdt_treatment_plan": "Neoadjuvant CROSS protocol (carboplatin + paclitaxel + radiotherapy) followed by Ivor Lewis oesophagectomy"
            },
            "treatments": []
        })
    
    # Ovarian Cancer
    if len(patients) > 5:
        sample_episodes.append({
            "episode_id": "EPI-SAMPLE-OVARIAN-001",
            "patient_id": patients[5]["record_number"],
            "condition_type": "cancer",
            "cancer_type": "ovarian",
            "referral_date": (today - timedelta(days=35)).isoformat(),
            "first_seen_date": (today - timedelta(days=30)).isoformat(),
            "mdt_discussion_date": (today - timedelta(days=25)).isoformat(),
            "lead_clinician": "Dr. Rachel Green",
            "mdt_team": ["Dr. Mark Davis"],
            "episode_status": "active",
            "created_at": datetime.utcnow(),
            "created_by": "sample_data_script",
            "last_modified_at": datetime.utcnow(),
            "last_modified_by": "sample_data_script",
            "cancer_data": {
                "cancer_site": "bilateral",
                "histological_type": "serous",
                "histological_grade": 3,
                "figo_stage": "IIIC",
                "presentation_type": "symptomatic",
                "symptoms": ["abdominal_pain", "bloating", "ascites"],
                "ascites_present": True,
                "ca125_at_diagnosis": 450.0,
                "peritoneal_disease": True,
                "brca1_status": "negative",
                "brca2_status": "positive",
                "resectability_assessment": "optimal",
                "neoadjuvant_chemotherapy": False,
                "mdt_treatment_plan": "Primary debulking surgery (total hysterectomy + BSO + omentectomy) followed by platinum-based chemotherapy"
            },
            "treatments": []
        })
    
    # Breast Cancer (Metastatic)
    if len(patients) > 6:
        sample_episodes.append({
            "episode_id": "EPI-SAMPLE-BREAST-MET-001",
            "patient_id": patients[6]["record_number"],
            "condition_type": "cancer",
            "cancer_type": "breast_metastatic",
            "referral_date": (today - timedelta(days=20)).isoformat(),
            "first_seen_date": (today - timedelta(days=18)).isoformat(),
            "mdt_discussion_date": (today - timedelta(days=15)).isoformat(),
            "lead_clinician": "Dr. Jennifer White",
            "mdt_team": ["Dr. Thomas Moore"],
            "episode_status": "active",
            "created_at": datetime.utcnow(),
            "created_by": "sample_data_script",
            "last_modified_at": datetime.utcnow(),
            "last_modified_by": "sample_data_script",
            "cancer_data": {
                "is_metastatic": True,
                "cancer_site": "right_breast",
                "laterality": "right",
                "detection_method": "symptomatic",
                "histological_type": "lobular",
                "histological_grade": 3,
                "er_status": "positive",
                "er_percentage": 70.0,
                "pr_status": "negative",
                "her2_status": "negative",
                "metastatic_sites": ["bone", "liver"],
                "line_of_therapy": 1,
                "mdt_treatment_plan": "First-line CDK4/6 inhibitor (palbociclib) + aromatase inhibitor (letrozole)"
            },
            "treatments": []
        })
    
    # Insert episodes
    created_count = 0
    skipped_count = 0
    
    for episode in sample_episodes:
        # Check if already exists
        existing = await episodes_collection.find_one({"episode_id": episode["episode_id"]})
        if existing:
            print(f"⊘ Skipped {episode['episode_id']} (already exists)")
            skipped_count += 1
            continue
        
        await episodes_collection.insert_one(episode)
        cancer_type = episode['cancer_type'].replace('_', ' ').title()
        print(f"✓ Created {cancer_type} episode: {episode['episode_id']}")
        created_count += 1
    
    print(f"\n{'='*60}")
    print(f"Sample Data Summary:")
    print(f"  Created: {created_count}")
    print(f"  Skipped (already exists): {skipped_count}")
    print(f"  Total: {len(sample_episodes)}")
    print(f"{'='*60}\n")
    
    if created_count > 0:
        print("✓ Sample cancer episodes created successfully!")
        print("\nYou can now:")
        print("  1. View them via: GET /api/v2/episodes")
        print("  2. Get statistics: GET /api/v2/episodes/stats/overview")
        print("  3. Test the frontend forms with real data")
    
    client.close()


async def main():
    """Main function"""
    print("Creating sample cancer episodes...\n")
    try:
        await create_sample_episodes()
    except Exception as e:
        print(f"\n✗ Error creating sample episodes: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
