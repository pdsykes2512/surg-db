#!/usr/bin/env python3
"""
Verify test database contains expected data
Quick validation script to check record counts and data quality
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
load_dotenv("/etc/impact/secrets.env", override=True)

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = "impact_test"


async def verify_test_data():
    """Verify test database has been populated"""
    print(f"\n{'='*70}")
    print("TEST DATABASE VERIFICATION")
    print(f"{'='*70}\n")
    print(f"Database: {DB_NAME}")
    print(f"Connecting to MongoDB...\n")

    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]

    # Get collections
    collections = {
        "patients": db["patients"],
        "episodes": db["episodes"],
        "treatments": db["treatments"],
        "tumours": db["tumours"],
        "investigations": db["investigations"],
        "clinicians": db["clinicians"]
    }

    # Count records
    print(f"{'='*70}")
    print("RECORD COUNTS")
    print(f"{'='*70}")

    total_records = 0
    for name, collection in collections.items():
        count = await collection.count_documents({})
        print(f"  {name.capitalize():20} {count:>10,}")
        total_records += count

    print(f"  {'-'*32}")
    print(f"  {'Total':20} {total_records:>10,}")

    # Sample data quality checks
    print(f"\n{'='*70}")
    print("DATA QUALITY CHECKS")
    print(f"{'='*70}\n")

    # Check patients have required fields
    patient = await collections["patients"].find_one({})
    if patient:
        has_patient_id = "patient_id" in patient
        has_nhs_number = "nhs_number" in patient
        has_demographics = "demographics" in patient
        print(f"✓ Patients have required fields:")
        print(f"  - patient_id: {has_patient_id}")
        print(f"  - nhs_number: {has_nhs_number}")
        print(f"  - demographics: {has_demographics}")

    # Check episodes have required relationships
    episode = await collections["episodes"].find_one({})
    if episode:
        has_patient_id = "patient_id" in episode
        has_cancer_type = "cancer_type" in episode
        has_lead_clinician = "lead_clinician" in episode
        print(f"\n✓ Episodes have required fields:")
        print(f"  - patient_id: {has_patient_id}")
        print(f"  - cancer_type: {has_cancer_type}")
        print(f"  - lead_clinician: {has_lead_clinician}")

    # Check tumours have TNM staging
    tumour = await collections["tumours"].find_one({})
    if tumour:
        has_t_stage = "clinical_t" in tumour
        has_n_stage = "clinical_n" in tumour
        has_m_stage = "clinical_m" in tumour
        print(f"\n✓ Tumours have TNM staging:")
        print(f"  - clinical_t: {has_t_stage}")
        print(f"  - clinical_n: {has_n_stage}")
        print(f"  - clinical_m: {has_m_stage}")

    # Check treatments
    treatment = await collections["treatments"].find_one({})
    if treatment:
        has_treatment_type = "treatment_type" in treatment
        has_treatment_date = "treatment_date" in treatment
        print(f"\n✓ Treatments have required fields:")
        print(f"  - treatment_type: {has_treatment_type}")
        print(f"  - treatment_date: {has_treatment_date}")

    # Sample a few records
    print(f"\n{'='*70}")
    print("SAMPLE RECORDS")
    print(f"{'='*70}\n")

    # Sample patient
    sample_patient = await collections["patients"].find_one({})
    if sample_patient:
        print(f"Sample Patient:")
        print(f"  ID: {sample_patient.get('patient_id')}")
        print(f"  NHS: {sample_patient.get('nhs_number')}")
        print(f"  Gender: {sample_patient.get('demographics', {}).get('gender')}")
        print(f"  Age: {sample_patient.get('demographics', {}).get('age')}")

    # Sample episode
    sample_episode = await collections["episodes"].find_one({})
    if sample_episode:
        print(f"\nSample Episode:")
        print(f"  ID: {sample_episode.get('episode_id')}")
        print(f"  Patient: {sample_episode.get('patient_id')}")
        print(f"  Cancer Type: {sample_episode.get('cancer_type')}")
        print(f"  Status: {sample_episode.get('episode_status')}")

    # Calculate averages
    patient_count = await collections["patients"].count_documents({})
    episode_count = await collections["episodes"].count_documents({})
    tumour_count = await collections["tumours"].count_documents({})
    investigation_count = await collections["investigations"].count_documents({})
    treatment_count = await collections["treatments"].count_documents({})

    print(f"\n{'='*70}")
    print("AVERAGES")
    print(f"{'='*70}")
    if patient_count > 0:
        print(f"  Episodes per patient:       {episode_count / patient_count:.2f}")
    if episode_count > 0:
        print(f"  Tumours per episode:        {tumour_count / episode_count:.2f}")
        print(f"  Investigations per episode: {investigation_count / episode_count:.2f}")
        print(f"  Treatments per episode:     {treatment_count / episode_count:.2f}")

    print(f"\n{'='*70}")
    print("✅ VERIFICATION COMPLETE")
    print(f"{'='*70}\n")

    client.close()


if __name__ == "__main__":
    asyncio.run(verify_test_data())
