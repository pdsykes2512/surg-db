#!/usr/bin/env python3
"""
Debug script to understand data relationships between collections.
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient('mongodb://admin:admin123@surg-db.vps:27017/surgdb?authSource=admin')
    db = client['surgdb']
    
    print("=" * 80)
    print("DATABASE STRUCTURE ANALYSIS")
    print("=" * 80)
    
    # Check patients collection
    print("\n1. PATIENTS COLLECTION")
    print("-" * 80)
    patient = await db.patients.find_one()
    if patient:
        print("Sample patient keys:", list(patient.keys()))
        print(f"  _id: {patient.get('_id')}")
        print(f"  record_number: {patient.get('record_number')}")
        print(f"  nhs_number: {patient.get('nhs_number')}")
        print(f"  patient_id: {patient.get('patient_id')}")
    print(f"Total patients: {await db.patients.count_documents({})}")
    
    # Check episodes collection
    print("\n2. EPISODES COLLECTION")
    print("-" * 80)
    episode = await db.episodes.find_one({"condition_type": "cancer"})
    if episode:
        print("Sample cancer episode keys:", list(episode.keys()))
        print(f"  _id: {episode.get('_id')}")
        print(f"  episode_id: {episode.get('episode_id')}")
        print(f"  patient_id: {episode.get('patient_id')}")
        print(f"  patient_record_number: {episode.get('patient_record_number')}")
        print(f"  condition_type: {episode.get('condition_type')}")
        print(f"  cancer_type: {episode.get('cancer_type')}")
    cancer_count = await db.episodes.count_documents({"condition_type": "cancer"})
    print(f"Total cancer episodes: {cancer_count}")
    
    # Check tumours collection
    print("\n3. TUMOURS COLLECTION")
    print("-" * 80)
    tumour = await db.tumours.find_one()
    if tumour:
        print("Sample tumour keys:", list(tumour.keys()))
        print(f"  _id: {tumour.get('_id')}")
        print(f"  episode_id: {tumour.get('episode_id')}")
        print(f"  tumour_id: {tumour.get('tumour_id')}")
    tumour_count = await db.tumours.count_documents({})
    print(f"Total tumours: {tumour_count}")
    
    # Check treatments collection
    print("\n4. TREATMENTS COLLECTION")
    print("-" * 80)
    treatment = await db.treatments.find_one()
    if treatment:
        print("Sample treatment keys:", list(treatment.keys()))
        print(f"  _id: {treatment.get('_id')}")
        print(f"  episode_id: {treatment.get('episode_id')}")
        print(f"  treatment_id: {treatment.get('treatment_id')}")
        print(f"  treatment_type: {treatment.get('treatment_type')}")
    treatment_count = await db.treatments.count_documents({})
    print(f"Total treatments: {treatment_count}")
    
    # Test relationship queries
    print("\n5. RELATIONSHIP TESTING")
    print("-" * 80)
    
    if episode:
        episode_id = episode.get('episode_id') or str(episode['_id'])
        patient_id = episode.get('patient_id')
        
        print(f"\nTesting episode: {episode_id}")
        print(f"Episode's patient_id: {patient_id}")
        
        # Try different patient lookup methods
        patient_by_record = await db.patients.find_one({"record_number": patient_id})
        patient_by_id = await db.patients.find_one({"patient_id": patient_id})
        patient_by_objectid = None
        try:
            from bson import ObjectId
            if patient_id and len(str(patient_id)) == 24:
                patient_by_objectid = await db.patients.find_one({"_id": ObjectId(patient_id)})
        except:
            pass
        
        print(f"  Patient found by record_number: {'✅' if patient_by_record else '❌'}")
        print(f"  Patient found by patient_id: {'✅' if patient_by_id else '❌'}")
        print(f"  Patient found by _id (ObjectId): {'✅' if patient_by_objectid else '❌'}")
        
        # Check tumours
        tumours = await db.tumours.find({"episode_id": episode_id}).to_list(length=None)
        print(f"  Tumours for this episode: {len(tumours)}")
        
        # Check treatments
        treatments = await db.treatments.find({"episode_id": episode_id}).to_list(length=None)
        print(f"  Treatments for this episode: {len(treatments)}")
        
        # Show what patients actually have
        print("\n6. SAMPLE PATIENT IDS IN DATABASE")
        print("-" * 80)
        async for p in db.patients.find().limit(5):
            print(f"  record_number: {p.get('record_number')}, patient_id: {p.get('patient_id')}, _id: {p.get('_id')}")
    
    print("\n" + "=" * 80)
    print("DIAGNOSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
