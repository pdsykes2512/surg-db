"""
Create sample data with new NHS Number-based ID format
Execution script to populate database with realistic test data
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB_NAME", "surg_outcomes")


def generate_episode_id(nhs_number: str, count: int) -> str:
    """Generate episode ID in format EPI-NHSNUMBER-COUNT"""
    clean_nhs = nhs_number.replace(' ', '')
    incremental_num = str(count + 1).zfill(2)
    return f"EPI-{clean_nhs}-{incremental_num}"


def generate_treatment_id(treatment_type: str, nhs_number: str, count: int) -> str:
    """Generate treatment ID with type-specific prefix"""
    clean_nhs = nhs_number.replace(' ', '')
    incremental_num = str(count + 1).zfill(2)
    
    prefix_map = {
        'surgery': 'SUR',
        'chemotherapy': 'ONC',
        'radiotherapy': 'DXT',
        'immunotherapy': 'IMM'
    }
    
    prefix = prefix_map.get(treatment_type, 'TRE')
    return f"{prefix}-{clean_nhs}-{incremental_num}"


def generate_tumour_id(nhs_number: str, count: int) -> str:
    """Generate tumour ID in format TUM-NHSNUMBER-COUNT"""
    clean_nhs = nhs_number.replace(' ', '')
    incremental_num = str(count + 1).zfill(2)
    return f"TUM-{clean_nhs}-{incremental_num}"


# Sample data templates
SAMPLE_PATIENTS = [
    {
        "record_number": "MRN001234",
        "nhs_number": "1234567890",
        "demographics": {
            "title": "Mr",
            "first_name": "John",
            "last_name": "Smith",
            "date_of_birth": "1965-03-15",
            "gender": "male",
            "ethnicity": "white_british"
        },
        "contact": {
            "address_line_1": "123 High Street",
            "city": "Manchester",
            "postcode": "M1 1AA",
            "phone": "07700900123"
        }
    },
    {
        "record_number": "MRN005678",
        "nhs_number": "2345678901",
        "demographics": {
            "title": "Mrs",
            "first_name": "Sarah",
            "last_name": "Johnson",
            "date_of_birth": "1972-08-22",
            "gender": "female",
            "ethnicity": "white_british"
        },
        "contact": {
            "address_line_1": "45 Park Lane",
            "city": "Liverpool",
            "postcode": "L1 2BB",
            "phone": "07700900456"
        }
    },
    {
        "record_number": "MRN009012",
        "nhs_number": "3456789012",
        "demographics": {
            "title": "Ms",
            "first_name": "Priya",
            "last_name": "Patel",
            "date_of_birth": "1980-11-30",
            "gender": "female",
            "ethnicity": "asian_indian"
        },
        "contact": {
            "address_line_1": "78 Oak Avenue",
            "city": "Birmingham",
            "postcode": "B1 3CC",
            "phone": "07700900789"
        }
    }
]

CANCER_TYPES = ['colorectal', 'gastric', 'pancreatic', 'hepatobiliary']
COLORECTAL_SITES = ['caecum', 'ascending_colon', 'transverse_colon', 'sigmoid_colon', 'rectum']
URGENCY_TYPES = ['elective', 'urgent', 'emergency']
APPROACH_TYPES = ['laparoscopic', 'open', 'robotic', 'converted']
PROCEDURES = [
    'Right hemicolectomy',
    'Left hemicolectomy',
    'Sigmoid colectomy',
    'Anterior resection',
    'Abdominoperineal excision'
]
OPCS4_CODES = ['H04', 'H05', 'H06', 'H33', 'H34']


async def create_sample_data():
    """Create comprehensive sample data"""
    print(f"Connecting to MongoDB at {MONGODB_URI}...")
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    
    print(f"\n📊 Creating sample data for database: {DB_NAME}")
    print("=" * 60)
    
    # Get collections
    patients_col = db["patients"]
    episodes_col = db["episodes"]
    treatments_col = db["treatments"]
    tumours_col = db["tumours"]
    clinicians_col = db["clinicians"]
    
    # Track created items
    stats = {
        'patients': 0,
        'episodes': 0,
        'treatments': 0,
        'tumours': 0,
        'clinicians': 0
    }
    
    # 1. Create sample clinicians
    print("\n👨‍⚕️ Creating Clinicians...")
    print("-" * 60)
    
    clinicians = [
        {
            "gmc_number": "1234567",
            "name": "Mr James Wilson",
            "specialty": "Colorectal Surgery",
            "grade": "Consultant",
            "department": "General Surgery",
            "trust": "RYR",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "gmc_number": "2345678",
            "name": "Ms Rachel Green",
            "specialty": "Upper GI Surgery",
            "grade": "Consultant",
            "department": "General Surgery",
            "trust": "RYR",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "gmc_number": "3456789",
            "name": "Mr David Brown",
            "specialty": "General Surgery",
            "grade": "ST7",
            "department": "General Surgery",
            "trust": "RYR",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    for clinician in clinicians:
        existing = await clinicians_col.find_one({"gmc_number": clinician["gmc_number"]})
        if not existing:
            await clinicians_col.insert_one(clinician)
            print(f"  ✓ {clinician['name']} (GMC: {clinician['gmc_number']})")
            stats['clinicians'] += 1
        else:
            print(f"  - {clinician['name']} already exists")
    
    # 2. Create sample patients
    print("\n👤 Creating Patients...")
    print("-" * 60)
    
    for patient_data in SAMPLE_PATIENTS:
        existing = await patients_col.find_one({"record_number": patient_data["record_number"]})
        if not existing:
            patient_data["created_at"] = datetime.utcnow()
            patient_data["created_by"] = "system"
            patient_data["updated_at"] = datetime.utcnow()
            await patients_col.insert_one(patient_data)
            print(f"  ✓ {patient_data['demographics']['first_name']} {patient_data['demographics']['last_name']} "
                  f"(NHS: {patient_data['nhs_number']})")
            stats['patients'] += 1
        else:
            print(f"  - Patient {patient_data['record_number']} already exists")
    
    # 3. Create episodes with treatments and tumours
    print("\n📋 Creating Episodes with Treatments and Tumours...")
    print("-" * 60)
    
    for patient_data in SAMPLE_PATIENTS:
        patient_id = patient_data["record_number"]
        nhs_number = patient_data["nhs_number"]
        
        # Get existing episode count for this patient
        existing_episodes = await episodes_col.count_documents({"patient_id": patient_id})
        
        # Create 1-2 episodes per patient
        num_episodes = random.randint(1, 2)
        
        for ep_idx in range(num_episodes):
            episode_id = generate_episode_id(nhs_number, existing_episodes + ep_idx)
            
            # Check if episode already exists
            if await episodes_col.find_one({"episode_id": episode_id}):
                print(f"  - Episode {episode_id} already exists")
                continue
            
            cancer_type = random.choice(CANCER_TYPES)
            diagnosis_date = datetime.now() - timedelta(days=random.randint(30, 365))
            
            episode = {
                "episode_id": episode_id,
                "patient_id": patient_id,
                "cancer_type": cancer_type,
                "diagnosis_date": diagnosis_date.strftime("%Y-%m-%d"),
                "mdt_date": (diagnosis_date + timedelta(days=7)).strftime("%Y-%m-%d"),
                "mdt_outcome": "surgery",
                "intent": "curative",
                "status": "active",
                "created_at": datetime.utcnow(),
                "created_by": "system",
                "updated_at": datetime.utcnow()
            }
            
            await episodes_col.insert_one(episode)
            print(f"  ✓ Episode {episode_id} ({cancer_type})")
            stats['episodes'] += 1
            
            # Create 1-2 tumours for this episode
            num_tumours = random.randint(1, 2)
            
            for tum_idx in range(num_tumours):
                tumour_id = generate_tumour_id(nhs_number, tum_idx)
                
                if await tumours_col.find_one({"tumour_id": tumour_id, "episode_id": episode_id}):
                    continue
                
                t_stage = random.choice(['T1', 'T2', 'T3', 'T4a'])
                n_stage = random.choice(['N0', 'N1', 'N2'])
                m_stage = random.choice(['M0', 'M1a'])
                
                tumour = {
                    "tumour_id": tumour_id,
                    "episode_id": episode_id,
                    "tumour_type": "primary" if tum_idx == 0 else "metastasis",
                    "site": random.choice(COLORECTAL_SITES) if cancer_type == 'colorectal' else 'liver',
                    "diagnosis_date": diagnosis_date.strftime("%Y-%m-%d"),
                    "tnm_version": "8",
                    "clinical_t": t_stage,
                    "clinical_n": n_stage,
                    "clinical_m": m_stage,
                    "pathological_t": t_stage,
                    "pathological_n": n_stage,
                    "pathological_m": m_stage,
                    "grade": random.choice(['well', 'moderate', 'poor']),
                    "histology_type": "Adenocarcinoma",
                    "treated_by_treatment_ids": [],
                    "created_at": datetime.utcnow(),
                    "created_by": "system",
                    "updated_at": datetime.utcnow()
                }
                
                await tumours_col.insert_one(tumour)
                print(f"    ✓ Tumour {tumour_id} ({tumour['tumour_type']}, {t_stage}{n_stage}{m_stage})")
                stats['tumours'] += 1
            
            # Create treatments for this episode
            # Get existing treatment counts by type for this patient
            all_patient_episodes = await episodes_col.find({"patient_id": patient_id}).to_list(length=None)
            all_episode_ids = [ep['episode_id'] for ep in all_patient_episodes]
            existing_treatments = await treatments_col.find(
                {"episode_id": {"$in": all_episode_ids}}
            ).to_list(length=None)
            
            treatment_counts = {}
            for t in existing_treatments:
                t_type = t.get('treatment_type', 'surgery')
                treatment_counts[t_type] = treatment_counts.get(t_type, 0) + 1
            
            # Create 1-3 treatments
            num_treatments = random.randint(1, 3)
            treatment_types = random.sample(['surgery', 'chemotherapy', 'radiotherapy'], 
                                           min(num_treatments, 3))
            
            for treatment_type in treatment_types:
                count = treatment_counts.get(treatment_type, 0)
                treatment_id = generate_treatment_id(treatment_type, nhs_number, count)
                treatment_counts[treatment_type] = count + 1
                
                if await treatments_col.find_one({"treatment_id": treatment_id}):
                    continue
                
                treatment_date = diagnosis_date + timedelta(days=random.randint(14, 60))
                
                treatment = {
                    "treatment_id": treatment_id,
                    "episode_id": episode_id,
                    "treatment_type": treatment_type,
                    "treatment_date": treatment_date.strftime("%Y-%m-%d"),
                    "provider_organisation": "RYR",
                    "created_at": datetime.utcnow(),
                    "created_by": "system",
                    "updated_at": datetime.utcnow()
                }
                
                # Add type-specific fields
                if treatment_type == 'surgery':
                    procedure_idx = random.randint(0, len(PROCEDURES) - 1)
                    treatment.update({
                        "procedure_name": PROCEDURES[procedure_idx],
                        "opcs4_code": OPCS4_CODES[procedure_idx],
                        "approach": random.choice(APPROACH_TYPES),
                        "urgency": random.choice(URGENCY_TYPES),
                        "surgeon": random.choice(clinicians)["gmc_number"],
                        "admission_date": treatment_date.strftime("%Y-%m-%d"),
                        "discharge_date": (treatment_date + timedelta(days=random.randint(3, 10))).strftime("%Y-%m-%d"),
                        "length_of_stay": random.randint(3, 10),
                        "asa_score": random.randint(2, 4),
                        "complications": random.choice([True, False]),
                        "readmission_30d": random.choice([True, False]),
                        "return_to_theatre": random.choice([True, False]),
                        "mortality_30d": False
                    })
                elif treatment_type == 'chemotherapy':
                    treatment.update({
                        "regimen": "FOLFOX",
                        "cycle_number": random.randint(1, 12),
                        "dose": "Standard dose"
                    })
                elif treatment_type == 'radiotherapy':
                    treatment.update({
                        "site": random.choice(COLORECTAL_SITES),
                        "total_dose": "50.4 Gy",
                        "fractions": 28
                    })
                
                await treatments_col.insert_one(treatment)
                print(f"    ✓ Treatment {treatment_id} ({treatment_type})")
                stats['treatments'] += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("✅ Sample Data Creation Complete!")
    print("=" * 60)
    print(f"Clinicians: {stats['clinicians']}")
    print(f"Patients:   {stats['patients']}")
    print(f"Episodes:   {stats['episodes']}")
    print(f"Tumours:    {stats['tumours']}")
    print(f"Treatments: {stats['treatments']}")
    print("\n💡 All IDs use new NHS Number-based format:")
    print("   Episodes:   EPI-NHSNUMBER-##")
    print("   Tumours:    TUM-NHSNUMBER-##")
    print("   Surgery:    SUR-NHSNUMBER-##")
    print("   Chemo:      ONC-NHSNUMBER-##")
    print("   Radio:      DXT-NHSNUMBER-##")
    print("   Immuno:     IMM-NHSNUMBER-##")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(create_sample_data())
