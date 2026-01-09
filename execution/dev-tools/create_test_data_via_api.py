#!/usr/bin/env python3
"""
Create test dataset by calling the API (simulates real user input)
This ensures data passes through validation and uses proper OPCS-4 codes
"""
import asyncio
import sys
import argparse
import random
from pathlib import Path
from datetime import datetime, timedelta, date
from typing import Dict, Any, List
import aiohttp
import json

# Add backend to path for OPCS-4 codes
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))
from app.services.opcs4_validator import OPCS4Validator

# Configuration
NUM_PATIENTS = 100  # Default smaller for API-based generation
API_BASE_URL = "http://localhost:8000/api"

# Data templates (same as before)
FIRST_NAMES_MALE = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph",
    "Thomas", "Charles", "Christopher", "Daniel", "Matthew", "Anthony"
]
FIRST_NAMES_FEMALE = [
    "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan",
    "Jessica", "Sarah", "Karen", "Nancy", "Lisa", "Betty", "Margaret"
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore"
]

CITIES = ["Manchester", "Liverpool", "Birmingham", "Leeds", "Sheffield"]
ETHNICITIES = ["white_british", "white_irish", "asian_indian", "asian_pakistani", "black_african"]

# Colorectal specific
COLORECTAL_SITES = ["caecum", "ascending_colon", "transverse_colon", "descending_colon",
                    "sigmoid_colon", "rectosigmoid_junction", "rectum"]
METASTATIC_SITES = ["liver", "lung", "peritoneum", "lymph_node"]

T_STAGES = ["1", "2", "3", "4a", "4b"]
N_STAGES = ["0", "1", "1a", "1b", "2"]
M_STAGES = ["0", "1a", "1b"]
TUMOUR_GRADES = ["well", "moderate", "poor"]

REFERRAL_SOURCES = ["gp", "2ww", "emergency", "screening"]
URGENCY_TYPES = ["elective", "urgent", "emergency"]
SURGERY_APPROACHES = ["laparoscopic", "open", "robotic"]

# OPCS-4 codes for colorectal surgery (from validator)
COLORECTAL_OPCS4_CODES = {
    # Right sided
    "H04.4": "Excision of right hemicolon",
    "H46.1": "Laparoscopic excision of right hemicolon",

    # Left sided
    "H04.7": "Excision of left hemicolon",
    "H46.2": "Laparoscopic excision of left hemicolon",

    # Sigmoid
    "H05.3": "Excision of sigmoid colon",
    "H46.3": "Laparoscopic excision of sigmoid colon",

    # Rectal
    "H08.1": "Anterior resection of rectum",
    "H08.3": "Ultra-low anterior resection of rectum",
    "H46.5": "Laparoscopic anterior resection of rectum",

    # APE
    "H09.1": "Abdominoperineal excision of rectum",

    # Hartmann
    "H10.1": "Hartmann operation",

    # Total/subtotal
    "H05.1": "Total excision of colon",
    "H07.1": "Subtotal excision of colon with anastomosis of ileum to rectum",
}


def generate_nhs_number(index: int) -> str:
    """Generate realistic NHS number"""
    base = 9000000000 + index
    nhs = str(base).zfill(10)
    return f"{nhs[0:3]} {nhs[3:6]} {nhs[6:10]}"


def generate_patient_id(index: int) -> str:
    """Generate unique 6-char hex patient ID"""
    offset = 0x200000  # Different range than direct DB script
    hex_id = hex(offset + index)[2:]
    return hex_id.upper().zfill(6)


def generate_episode_id(patient_id: str, count: int) -> str:
    """Generate episode ID in format EPI-PATIENTID-COUNT"""
    return f"EPI-{patient_id}-{str(count + 1).zfill(2)}"


def generate_mrn(index: int) -> str:
    """Generate MRN"""
    if index % 3 == 0:
        return f"IW{str(100000 + index).zfill(6)}"
    else:
        return f"{91000000 + index}"


def generate_postcode() -> str:
    """Generate UK postcode"""
    letters = "ABCDEFGHJKLMNPQRSTUVWXY"
    area = random.choice(["M", "L", "B", "LS", "S"])
    district = random.randint(1, 30)
    sector = random.randint(1, 9)
    unit = f"{random.choice(letters)}{random.choice(letters)}"
    return f"{area}{district} {sector}{unit}"


def generate_date_of_birth() -> str:
    """Generate DOB (age 40-90)"""
    today = date.today()
    age = random.randint(40, 90)
    year = today.year - age
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{year}-{month:02d}-{day:02d}"


def select_opcs4_for_site(site: str, approach: str) -> tuple[str, str]:
    """Select appropriate OPCS-4 code based on tumour site and approach"""

    # Map sites to procedures
    if site in ["caecum", "ascending_colon", "hepatic_flexure"]:
        if approach == "laparoscopic":
            return ("H46.1", "Laparoscopic excision of right hemicolon")
        else:
            return ("H04.4", "Excision of right hemicolon")

    elif site in ["descending_colon", "splenic_flexure"]:
        if approach == "laparoscopic":
            return ("H46.2", "Laparoscopic excision of left hemicolon")
        else:
            return ("H04.7", "Excision of left hemicolon")

    elif site == "sigmoid_colon":
        if approach == "laparoscopic":
            return ("H46.3", "Laparoscopic excision of sigmoid colon")
        else:
            return ("H05.3", "Excision of sigmoid colon")

    elif site in ["rectum", "rectosigmoid_junction"]:
        low_tumour = random.choice([True, False])
        if low_tumour:
            return ("H09.1", "Abdominoperineal excision of rectum")
        elif approach == "laparoscopic":
            return ("H46.5", "Laparoscopic anterior resection of rectum")
        else:
            return ("H08.1", "Anterior resection of rectum")

    elif site == "transverse_colon":
        return ("H04.5", "Excision of transverse colon")

    else:
        # Default to subtotal colectomy
        return ("H07.1", "Subtotal excision of colon with anastomosis of ileum to rectum")


async def get_auth_token(session: aiohttp.ClientSession, username: str = "admin@example.com", password: str = "admin123") -> str:
    """Get JWT auth token"""
    # OAuth2 expects form data, not JSON
    form_data = aiohttp.FormData()
    form_data.add_field('username', username)
    form_data.add_field('password', password)

    async with session.post(
        f"{API_BASE_URL}/auth/login",
        data=form_data
    ) as response:
        if response.status == 200:
            data = await response.json()
            return data["access_token"]
        else:
            text = await response.text()
            raise Exception(f"Authentication failed: {response.status} - {text}")


async def create_patient_via_api(session: aiohttp.ClientSession, headers: Dict, index: int) -> Dict:
    """Create a patient via API"""
    gender = random.choice(["male", "female"])
    first_name = random.choice(FIRST_NAMES_MALE if gender == "male" else FIRST_NAMES_FEMALE)
    last_name = random.choice(LAST_NAMES)

    patient_data = {
        "patient_id": generate_patient_id(index),
        "mrn": generate_mrn(index),  # Medical Record Number
        "nhs_number": generate_nhs_number(index),
        "demographics": {
            "date_of_birth": generate_date_of_birth(),
            "gender": gender,
            "ethnicity": random.choice(ETHNICITIES),
            "postcode": generate_postcode(),
            "bmi": round(random.uniform(18.5, 35.0), 1),
            "weight_kg": round(random.uniform(50, 120), 1),
            "height_cm": round(random.uniform(150, 190), 1)
        },
        "medical_history": {
            "conditions": random.sample(["hypertension", "diabetes", "none"], k=random.randint(0, 2)),
            "smoking_status": random.choice(["never", "former", "current"])
        }
    }

    async with session.post(
        f"{API_BASE_URL}/patients",
        headers=headers,
        json=patient_data
    ) as response:
        if response.status in [200, 201]:
            return await response.json()
        else:
            text = await response.text()
            raise Exception(f"Failed to create patient: {response.status} - {text}")


async def create_episode_via_api(session: aiohttp.ClientSession, headers: Dict,
                                 patient_id: str, clinicians: List[str], episode_count: int = 0) -> Dict:
    """Create a colorectal cancer episode via API"""
    referral_date = datetime.now() - timedelta(days=random.randint(30, 730))
    first_seen = referral_date + timedelta(days=random.randint(3, 14))
    mdt_date = first_seen + timedelta(days=random.randint(3, 10))

    episode_data = {
        "episode_id": generate_episode_id(patient_id, episode_count),
        "patient_id": patient_id,
        "condition_type": "cancer",
        "cancer_type": "bowel",
        "referral_date": referral_date.strftime("%Y-%m-%d"),
        "first_seen_date": first_seen.strftime("%Y-%m-%d"),
        "mdt_discussion_date": mdt_date.strftime("%Y-%m-%d"),
        "lead_clinician": random.choice(clinicians),
        "referral_source": random.choice(REFERRAL_SOURCES),
        "cns_involved": random.choice(["yes", "no"]),
        "performance_status": str(random.randint(0, 2)),
        "episode_status": "active",
        "created_by": "admin@example.com",
        "last_modified_by": "admin@example.com"
    }

    async with session.post(
        f"{API_BASE_URL}/episodes",
        headers=headers,
        json=episode_data
    ) as response:
        if response.status in [200, 201]:
            return await response.json()
        else:
            text = await response.text()
            raise Exception(f"Failed to create episode: {response.status} - {text}")


async def create_tumour_via_api(session: aiohttp.ClientSession, headers: Dict,
                                episode_id: str, is_primary: bool = True) -> Dict:
    """Create a tumour via API"""
    site = random.choice(COLORECTAL_SITES if is_primary else METASTATIC_SITES)

    tumour_data = {
        "tumour_type": "primary" if is_primary else "metastasis",
        "site": site,
        "diagnosis_date": (datetime.now() - timedelta(days=random.randint(30, 180))).strftime("%Y-%m-%d"),
        "tnm_version": "8",
        "clinical_t": random.choice(T_STAGES),
        "clinical_n": random.choice(N_STAGES),
        "clinical_m": random.choice(M_STAGES) if is_primary else random.choice(["M1a", "M1b"]),
        "histology_grade": random.choice(TUMOUR_GRADES),
        "histology_type": "Adenocarcinoma",
        "tumour_size_mm": random.randint(10, 80),
        "nodes_examined": random.randint(8, 20),
        "nodes_positive": random.randint(0, 5)
    }

    async with session.post(
        f"{API_BASE_URL}/episodes/{episode_id}/tumours",
        headers=headers,
        json=tumour_data
    ) as response:
        if response.status in [200, 201]:
            return await response.json()
        else:
            text = await response.text()
            raise Exception(f"Failed to create tumour: {response.status} - {text}")


async def create_surgery_via_api(session: aiohttp.ClientSession, headers: Dict,
                                 episode_id: str, tumour_site: str, clinicians: List[str]) -> Dict:
    """Create surgery treatment with proper OPCS-4 code via API"""
    approach = random.choice(SURGERY_APPROACHES)
    opcs4_code, opcs4_name = select_opcs4_for_site(tumour_site, approach)

    surgery_date = datetime.now() - timedelta(days=random.randint(10, 180))

    surgeon = random.choice(clinicians)

    surgery_data = {
        "treatment_type": "surgery_primary",
        "treatment_date": surgery_date.strftime("%Y-%m-%d"),
        "treating_clinician": surgeon,
        "treatment_intent": random.choice(["curative", "palliative"]),
        "provider_organisation": "RYR",
        "classification": {
            "urgency": random.choice(URGENCY_TYPES),
            "primary_diagnosis": f"Colorectal cancer - {tumour_site.replace('_', ' ')}",
            "indication": "cancer"
        },
        "procedure": {
            "primary_procedure": opcs4_name,
            "opcs_codes": [opcs4_code],
            "approach": approach,
            "additional_procedures": []
        },
        "perioperative_timeline": {
            "admission_date": surgery_date.strftime("%Y-%m-%d"),
            "surgery_date": surgery_date.strftime("%Y-%m-%d"),
            "discharge_date": (surgery_date + timedelta(days=random.randint(3, 14))).strftime("%Y-%m-%d")
        },
        "team": {
            "primary_surgeon": surgeon,
            "assistants": [],
            "anaesthetist": surgeon,
            "scrub_nurse": "Staff Nurse"
        },
        "outcomes": {
            "length_of_stay": random.randint(3, 14),
            "complications": random.choice([True, False]),
            "readmission_30d": random.choice([True, False]),
            "mortality_30d": False
        }
    }

    async with session.post(
        f"{API_BASE_URL}/episodes/{episode_id}/treatments",
        headers=headers,
        json=surgery_data
    ) as response:
        if response.status in [200, 201]:
            return await response.json()
        else:
            text = await response.text()
            raise Exception(f"Failed to create surgery: {response.status} - {text}")


async def get_clinicians(session: aiohttp.ClientSession, headers: Dict) -> List[str]:
    """Get list of clinicians from API"""
    async with session.get(
        f"{API_BASE_URL}/clinicians",
        headers=headers
    ) as response:
        if response.status == 200:
            data = await response.json()
            # Extract names from clinicians
            names = []
            for clinician in data:
                first = clinician.get('first_name', '')
                last = clinician.get('surname', '')
                if first and last:
                    role = clinician.get('clinical_role', 'surgeon')
                    title = "Mr" if role == 'surgeon' else "Dr"
                    names.append(f"{title} {first} {last}")

            return names if names else ["Mr John Smith", "Ms Jane Doe"]
        else:
            return ["Mr John Smith", "Ms Jane Doe"]


async def create_test_data_via_api(num_patients: int = NUM_PATIENTS):
    """Create test dataset via API calls"""
    print(f"\n{'='*70}")
    print(f"API-BASED TEST DATA GENERATION")
    print(f"{'='*70}")
    print(f"Target patients: {num_patients:,}")
    print(f"API endpoint: {API_BASE_URL}")
    print(f"{'='*70}\n")

    stats = {
        'patients': 0,
        'episodes': 0,
        'tumours': 0,
        'surgeries': 0,
        'errors': 0
    }

    async with aiohttp.ClientSession() as session:
        # 1. Authenticate
        print("🔐 Authenticating...")
        try:
            token = await get_auth_token(session)
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            print("   ✓ Authenticated\n")
        except Exception as e:
            print(f"   ❌ Authentication failed: {e}")
            return

        # 2. Get clinicians
        print("👨‍⚕️ Loading clinicians...")
        clinicians = await get_clinicians(session, headers)
        print(f"   ✓ Loaded {len(clinicians)} clinicians\n")

        # 3. Create patients with episodes
        print(f"👤 Creating {num_patients:,} patients with episodes...")
        print("-" * 70)

        for i in range(num_patients):
            try:
                # Create patient
                patient = await create_patient_via_api(session, headers, i)
                stats['patients'] += 1
                patient_id = patient['patient_id']

                # Create episode
                episode = await create_episode_via_api(session, headers, patient_id, clinicians)
                stats['episodes'] += 1
                episode_id = episode['episode_id']

                # Create primary tumour
                tumour = await create_tumour_via_api(session, headers, episode_id, is_primary=True)
                stats['tumours'] += 1
                tumour_site = tumour.get('site', 'sigmoid_colon')

                # Create surgery with OPCS-4 code
                surgery = await create_surgery_via_api(session, headers, episode_id, tumour_site, clinicians)
                stats['surgeries'] += 1

                # Progress
                if (i + 1) % 10 == 0:
                    progress = ((i + 1) / num_patients) * 100
                    print(f"  Progress: {i + 1:,}/{num_patients:,} ({progress:.0f}%) - "
                          f"{stats['episodes']} episodes, {stats['tumours']} tumours, "
                          f"{stats['surgeries']} surgeries")

            except Exception as e:
                stats['errors'] += 1
                if stats['errors'] <= 5:  # Only print first 5 errors
                    print(f"  ⚠️  Error creating patient {i}: {str(e)[:100]}")

    # Final summary
    print("\n" + "=" * 70)
    print("✅ API-BASED TEST DATA GENERATION COMPLETE!")
    print("=" * 70)
    print(f"\nRecords Created:")
    print(f"  Patients:    {stats['patients']:>6,}")
    print(f"  Episodes:    {stats['episodes']:>6,}")
    print(f"  Tumours:     {stats['tumours']:>6,}")
    print(f"  Surgeries:   {stats['surgeries']:>6,}")
    print(f"  Errors:      {stats['errors']:>6,}")
    print("=" * 70)
    print("\n✅ All data created through API with:")
    print("   • Proper validation")
    print("   • Correct OPCS-4 codes")
    print("   • Site-appropriate procedures")
    print("   • Realistic data structure")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate test data via API")
    parser.add_argument('--count', '-c', type=int, default=NUM_PATIENTS,
                       help=f'Number of patients (default: {NUM_PATIENTS})')
    args = parser.parse_args()

    print(f"\n{'='*70}")
    print("IMPACT - API-Based Test Data Generator")
    print(f"{'='*70}\n")

    asyncio.run(create_test_data_via_api(args.count))
