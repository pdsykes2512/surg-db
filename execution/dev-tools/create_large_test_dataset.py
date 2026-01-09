#!/usr/bin/env python3
"""
Create large test dataset with 5000 patients
Generates patients with episodes, tumours, investigations, and treatments
Execution script for performance testing and demonstrations
"""
import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta, date
import random
from typing import List, Dict, Any

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# Load environment variables (loads .env and secrets)
load_dotenv()
load_dotenv("/etc/impact/secrets.env", override=True)

# Configuration
NUM_PATIENTS = 5000
MIN_EPISODES_PER_PATIENT = 1
MAX_EPISODES_PER_PATIENT = 3
MIN_TUMOURS_PER_EPISODE = 1
MAX_TUMOURS_PER_EPISODE = 2
MIN_INVESTIGATIONS_PER_EPISODE = 1
MAX_INVESTIGATIONS_PER_EPISODE = 4
MIN_TREATMENTS_PER_EPISODE = 1
MAX_TREATMENTS_PER_EPISODE = 3

# Database configuration (default to test database)
# Get MONGODB_URI from environment (loaded from secrets.env)
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    print("ERROR: MONGODB_URI not found in environment variables")
    print("Please ensure /etc/impact/secrets.env contains MONGODB_URI")
    sys.exit(1)

DB_NAME = os.getenv("TEST_DB_NAME", "impact_test")

# Data templates
TITLES = ["Mr", "Mrs", "Ms", "Miss", "Dr"]
FIRST_NAMES_MALE = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph",
    "Thomas", "Charles", "Christopher", "Daniel", "Matthew", "Anthony", "Donald",
    "Mark", "Paul", "Steven", "Andrew", "Kenneth", "Joshua", "Kevin", "Brian",
    "George", "Edward", "Ronald", "Timothy", "Jason", "Jeffrey", "Ryan"
]
FIRST_NAMES_FEMALE = [
    "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan",
    "Jessica", "Sarah", "Karen", "Nancy", "Lisa", "Betty", "Margaret", "Sandra",
    "Ashley", "Dorothy", "Kimberly", "Emily", "Donna", "Michelle", "Carol",
    "Amanda", "Melissa", "Deborah", "Stephanie", "Rebecca", "Laura", "Sharon"
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White", "Harris",
    "Clark", "Lewis", "Robinson", "Walker", "Young", "Allen", "King", "Wright",
    "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green", "Adams", "Nelson",
    "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter", "Roberts", "Patel",
    "Khan", "Ahmed", "Ali", "Hussein", "Chen", "Wang", "Zhang", "Liu"
]

CITIES = [
    "Manchester", "Liverpool", "Birmingham", "Leeds", "Sheffield", "Bristol",
    "Newcastle", "Nottingham", "Leicester", "Coventry", "Bradford", "Cardiff",
    "Stoke", "Wolverhampton", "Plymouth", "Derby", "Southampton", "Portsmouth",
    "York", "Preston", "Cambridge", "Oxford", "Norwich", "Exeter", "Bath"
]

ETHNICITIES = [
    "white_british", "white_irish", "white_other", "asian_indian", "asian_pakistani",
    "asian_bangladeshi", "asian_chinese", "asian_other", "black_caribbean",
    "black_african", "black_other", "mixed_white_black_caribbean",
    "mixed_white_black_african", "mixed_white_asian", "other"
]

# Only colorectal cancer for this dataset
CANCER_TYPE = "bowel"
COLORECTAL_SITES = ["caecum", "ascending_colon", "transverse_colon", "descending_colon",
                    "sigmoid_colon", "rectosigmoid_junction", "rectum"]
METASTATIC_SITES = ["liver", "lung", "peritoneum", "lymph_node"]  # For metastases

T_STAGES = ["T1", "T2", "T3", "T4a", "T4b"]
N_STAGES = ["N0", "N1", "N1a", "N1b", "N2", "N2a"]
M_STAGES = ["M0", "M1a", "M1b"]
TUMOUR_GRADES = ["well", "moderate", "poor", "undifferentiated"]

INVESTIGATION_TYPES = {
    "imaging": ["ct_abdomen", "ct_chest", "ct_staging", "mri_primary", "mri_liver", "pet_ct", "ultrasound"],
    "endoscopy": ["colonoscopy", "sigmoidoscopy", "gastroscopy", "bronchoscopy"],
    "laboratory": ["cea", "ca125", "psa", "fbc", "lft", "u_e"]
}

TREATMENT_TYPES = ["surgery_primary", "chemotherapy", "radiotherapy"]
# Only colorectal surgery procedures
SURGERY_PROCEDURES = [
    "Right hemicolectomy", "Left hemicolectomy", "Sigmoid colectomy",
    "Anterior resection", "Abdominoperineal excision", "Total colectomy",
    "Hartmann's procedure", "Subtotal colectomy", "Panproctocolectomy"
]

SURGERY_APPROACHES = ["laparoscopic", "open", "robotic", "converted"]
URGENCY_TYPES = ["elective", "urgent", "emergency"]
REFERRAL_SOURCES = ["gp", "2ww", "emergency", "screening", "consultant"]

# Will be loaded from impact_system database
CLINICIANS = []


def generate_nhs_number(index: int) -> str:
    """Generate realistic NHS number format (XXX XXX XXXX)"""
    # Use a range starting from 900 to avoid real NHS numbers
    base = 9000000000 + index
    nhs = str(base).zfill(10)
    return f"{nhs[0:3]} {nhs[3:6]} {nhs[6:10]}"


def generate_patient_id(index: int) -> str:
    """Generate unique patient_id as 6-character hexadecimal"""
    # Use index as base for hex (guarantees uniqueness)
    # Add offset to make IDs look more random
    offset = 0x100000  # Start from 1 million in hex
    hex_id = hex(offset + index)[2:]  # Remove '0x' prefix
    return hex_id.upper().zfill(6)  # Pad to 6 chars, uppercase


def generate_mrn(index: int) -> str:
    """Generate Medical Record Number (8 digits or IW+6 digits)"""
    if index % 3 == 0:
        # IW format
        return f"IW{str(index).zfill(6)}"
    else:
        # 8 digits
        return f"{90000000 + index}"


def generate_postcode() -> str:
    """Generate realistic UK postcode"""
    letters = "ABCDEFGHJKLMNPQRSTUVWXY"
    area = random.choice(["M", "L", "B", "LS", "S", "BS", "NE", "NG", "LE", "CV"])
    district = random.randint(1, 99)
    sector = random.randint(1, 9)
    unit = f"{random.choice(letters)}{random.choice(letters)}"
    return f"{area}{district} {sector}{unit}"


def generate_date_of_birth() -> str:
    """Generate realistic date of birth (age 40-90)"""
    today = date.today()
    age = random.randint(40, 90)
    year = today.year - age
    month = random.randint(1, 12)
    day = random.randint(1, 28)  # Safe for all months
    return f"{year}-{month:02d}-{day:02d}"


def generate_patient(index: int) -> Dict[str, Any]:
    """Generate a complete patient record"""
    nhs_number = generate_nhs_number(index)
    patient_id = generate_patient_id(index)  # Pass index directly for unique ID
    gender = random.choice(["male", "female"])

    if gender == "male":
        title = random.choice(["Mr", "Dr"])
        first_name = random.choice(FIRST_NAMES_MALE)
    else:
        title = random.choice(["Mrs", "Ms", "Miss", "Dr"])
        first_name = random.choice(FIRST_NAMES_FEMALE)

    last_name = random.choice(LAST_NAMES)
    dob = generate_date_of_birth()

    patient = {
        "patient_id": patient_id,
        "mrn": generate_mrn(index),
        "nhs_number": nhs_number,
        "demographics": {
            "date_of_birth": dob,
            "age": (date.today() - datetime.strptime(dob, "%Y-%m-%d").date()).days // 365,
            "gender": gender,
            "ethnicity": random.choice(ETHNICITIES),
            "postcode": generate_postcode(),
            "bmi": round(random.uniform(18.5, 35.0), 1),
            "weight_kg": round(random.uniform(50, 120), 1),
            "height_cm": round(random.uniform(150, 190), 1)
        },
        "medical_history": {
            "conditions": random.sample(
                ["hypertension", "diabetes", "copd", "asthma", "ckd", "ihd", "none"],
                k=random.randint(0, 3)
            ),
            "smoking_status": random.choice(["never", "former", "current"]),
            "alcohol_use": random.choice(["none", "social", "moderate", "heavy"])
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    return patient


def generate_episode_id(patient_id: str, count: int) -> str:
    """Generate episode ID in format EPI-PATIENTID-COUNT"""
    return f"EPI-{patient_id}-{str(count + 1).zfill(2)}"


def generate_tumour_id(patient_id: str, count: int) -> str:
    """Generate tumour ID in format TUM-PATIENTID-COUNT"""
    return f"TUM-{patient_id}-{str(count + 1).zfill(2)}"


def generate_investigation_id(patient_id: str, inv_type: str, count: int) -> str:
    """Generate investigation ID"""
    type_prefix = inv_type[:3].upper()
    return f"INV-{patient_id}-{type_prefix}-{str(count + 1).zfill(2)}"


def generate_treatment_id(treatment_type: str, patient_id: str, count: int) -> str:
    """Generate treatment ID with type-specific prefix"""
    prefix_map = {
        'surgery_primary': 'SUR',
        'surgery_rtt': 'RTT',
        'surgery_reversal': 'REV',
        'chemotherapy': 'ONC',
        'radiotherapy': 'DXT',
        'immunotherapy': 'IMM',
        'hormone_therapy': 'HOR',
        'targeted_therapy': 'TAR'
    }

    prefix = prefix_map.get(treatment_type, 'TRE')
    return f"{prefix}-{patient_id}-{str(count + 1).zfill(2)}"


async def load_clinicians_from_system_db(client: AsyncIOMotorClient) -> List[str]:
    """Load clinicians from impact_system database"""
    global CLINICIANS

    system_db = client["impact_system"]
    clinicians_col = system_db["clinicians"]

    clinician_names = []
    async for clinician in clinicians_col.find({}):
        first_name = clinician.get('first_name', '')
        surname = clinician.get('surname', '')

        if first_name and surname:
            # Add title based on role
            title = "Mr" if clinician.get('clinical_role') == 'surgeon' else "Dr"
            full_name = f"{title} {first_name} {surname}"
            clinician_names.append(full_name)

    if not clinician_names:
        # Fallback to default names if no clinicians found
        clinician_names = [
            "Mr John Smith", "Ms Jane Doe", "Mr David Williams"
        ]

    CLINICIANS = clinician_names
    return clinician_names


async def create_large_test_dataset(skip_confirmation: bool = False):
    """Create comprehensive test dataset with 5000 patients"""
    print(f"\n{'='*70}")
    print(f"LARGE TEST DATASET GENERATION - COLORECTAL CANCER ONLY")
    print(f"{'='*70}")
    print(f"Target patients: {NUM_PATIENTS:,}")
    print(f"Database: {DB_NAME}")
    print(f"MongoDB URI: {MONGODB_URI}")
    print(f"{'='*70}\n")

    # Confirm before proceeding
    if not skip_confirmation:
        response = input(f"This will create ~{NUM_PATIENTS:,} patients with colorectal cancer episodes.\nProceed? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Cancelled.")
            return
    else:
        print(f"Auto-proceeding (--yes flag provided)...")

    print(f"\nConnecting to MongoDB...")
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]

    # Load clinicians from impact_system database
    print(f"\n👨‍⚕️ Loading Clinicians from impact_system...")
    print("-" * 70)
    clinicians = await load_clinicians_from_system_db(client)
    for clinician in clinicians:
        print(f"  ✓ {clinician}")
    print(f"\n  Total: {len(clinicians)} clinicians loaded")

    # Get collections
    patients_col = db["patients"]
    episodes_col = db["episodes"]
    treatments_col = db["treatments"]
    tumours_col = db["tumours"]
    investigations_col = db["investigations"]

    # Track statistics
    stats = {
        'patients': 0,
        'episodes': 0,
        'treatments': 0,
        'tumours': 0,
        'investigations': 0
    }

    # Create patients with colorectal cancer episodes
    print(f"\n👤 Creating {NUM_PATIENTS:,} Colorectal Cancer Patients...")
    print("-" * 70)

    batch_size = 100
    for batch_start in range(0, NUM_PATIENTS, batch_size):
        batch_end = min(batch_start + batch_size, NUM_PATIENTS)

        patients_batch = []
        episodes_batch = []
        tumours_batch = []
        investigations_batch = []
        treatments_batch = []

        for i in range(batch_start, batch_end):
            # Generate patient
            patient = generate_patient(i)
            patient_id = patient["patient_id"]
            patients_batch.append(patient)

            # Generate episodes for this patient
            num_episodes = random.randint(MIN_EPISODES_PER_PATIENT, MAX_EPISODES_PER_PATIENT)

            for ep_idx in range(num_episodes):
                episode_id = generate_episode_id(patient_id, ep_idx)

                # Only colorectal cancer
                cancer_type = CANCER_TYPE  # "bowel"

                # Generate dates
                referral_date = datetime.now() - timedelta(days=random.randint(30, 730))
                first_seen_date = referral_date + timedelta(days=random.randint(3, 14))
                mdt_date = first_seen_date + timedelta(days=random.randint(3, 10))

                # Initialize arrays to track IDs for this episode
                episode_tumour_ids = []
                episode_treatment_ids = []

                episode = {
                    "episode_id": episode_id,
                    "patient_id": patient["mrn"],  # Use MRN for patient_id in episode
                    "condition_type": "cancer",
                    "cancer_type": cancer_type,
                    "referral_date": referral_date.strftime("%Y-%m-%d"),
                    "first_seen_date": first_seen_date.strftime("%Y-%m-%d"),
                    "mdt_discussion_date": mdt_date.strftime("%Y-%m-%d"),
                    "lead_clinician": random.choice(CLINICIANS),
                    "referral_source": random.choice(REFERRAL_SOURCES),
                    "cns_involved": random.choice(["yes", "no"]),
                    "performance_status": str(random.randint(0, 2)),
                    "episode_status": random.choice(["active", "active", "active", "completed"]),
                    "treatment_ids": [],  # Will be populated below
                    "tumour_ids": [],     # Will be populated below
                    "created_at": datetime.utcnow(),
                    "created_by": "test_data_script",
                    "last_modified_at": datetime.utcnow(),
                    "last_modified_by": "test_data_script"
                }

                # Generate tumours for this episode
                num_tumours = random.randint(MIN_TUMOURS_PER_EPISODE, MAX_TUMOURS_PER_EPISODE)

                for tum_idx in range(num_tumours):
                    tumour_id = generate_tumour_id(patient_id, len(tumours_batch))
                    episode_tumour_ids.append(tumour_id)  # Track for episode

                    # Select site - primary tumour in colorectum, metastases elsewhere
                    if tum_idx == 0:
                        site = random.choice(COLORECTAL_SITES)
                    else:
                        site = random.choice(METASTATIC_SITES)

                    t_stage = random.choice(T_STAGES)
                    n_stage = random.choice(N_STAGES)
                    m_stage = random.choice(M_STAGES) if tum_idx == 0 else random.choice(["M1a", "M1b"])

                    tumour = {
                        "tumour_id": tumour_id,
                        "tumour_type": "primary" if tum_idx == 0 else "metastasis",
                        "site": site,
                        "diagnosis_date": referral_date.strftime("%Y-%m-%d"),  # Convert to string
                        "tnm_version": "8",
                        "clinical_t": t_stage,
                        "clinical_n": n_stage,
                        "clinical_m": m_stage,
                        "pathological_t": t_stage,
                        "pathological_n": n_stage,
                        "pathological_m": m_stage,
                        "histology_grade": random.choice(TUMOUR_GRADES),
                        "histology_type": "Adenocarcinoma",
                        "tumour_size_mm": random.randint(10, 80),
                        "nodes_examined": random.randint(8, 20),
                        "nodes_positive": random.randint(0, 5) if n_stage != "N0" else 0,
                        "created_at": datetime.utcnow(),
                        "created_by": "test_data_script",
                        "updated_at": datetime.utcnow()
                    }

                    tumours_batch.append(tumour)

                # Generate investigations for this episode
                num_investigations = random.randint(MIN_INVESTIGATIONS_PER_EPISODE, MAX_INVESTIGATIONS_PER_EPISODE)

                for inv_idx in range(num_investigations):
                    inv_category = random.choice(list(INVESTIGATION_TYPES.keys()))
                    inv_subtype = random.choice(INVESTIGATION_TYPES[inv_category])
                    investigation_id = generate_investigation_id(patient_id, inv_subtype, len(investigations_batch))

                    inv_date = referral_date + timedelta(days=random.randint(-30, 30))

                    investigation = {
                        "investigation_id": investigation_id,
                        "patient_id": patient_id,
                        "episode_id": episode_id,
                        "type": inv_category,
                        "subtype": inv_subtype,
                        "date": inv_date.strftime("%Y-%m-%d"),
                        "result": random.choice(["Normal", "Abnormal", "Suspicious", "Confirmed malignancy"]),
                        "findings": {
                            "quality": random.choice(["good", "adequate", "poor"]),
                            "reporter": random.choice(CLINICIANS)
                        },
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }

                    investigations_batch.append(investigation)

                # Generate treatments for this episode
                num_treatments = random.randint(MIN_TREATMENTS_PER_EPISODE, MAX_TREATMENTS_PER_EPISODE)
                treatment_types_selected = random.sample(TREATMENT_TYPES, min(num_treatments, len(TREATMENT_TYPES)))

                for treat_idx, treatment_type in enumerate(treatment_types_selected):
                    treatment_id = generate_treatment_id(treatment_type, patient_id, len(treatments_batch))
                    episode_treatment_ids.append(treatment_id)  # Track for episode

                    treatment_date = mdt_date + timedelta(days=random.randint(14, 90))

                    treatment = {
                        "treatment_id": treatment_id,
                        "treatment_type": treatment_type,
                        "treatment_date": treatment_date.strftime("%Y-%m-%d"),
                        "treating_clinician": random.choice(CLINICIANS),
                        "treatment_intent": random.choice(["curative", "palliative", "adjuvant", "neoadjuvant"]),
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }

                    # Add surgery-specific fields
                    if treatment_type == "surgery_primary":
                        treatment.update({
                            "provider_organisation": "RYR",
                            "classification": {
                                "procedure_name": random.choice(SURGERY_PROCEDURES),
                                "urgency": random.choice(URGENCY_TYPES),
                                "approach": random.choice(SURGERY_APPROACHES),
                                "asa_score": random.randint(1, 4)
                            },
                            "perioperative_timeline": {
                                "admission_date": treatment_date.strftime("%Y-%m-%d"),
                                "surgery_date": treatment_date.strftime("%Y-%m-%d"),
                                "discharge_date": (treatment_date + timedelta(days=random.randint(3, 14))).strftime("%Y-%m-%d")
                            },
                            "outcomes": {
                                "length_of_stay": random.randint(3, 14),
                                "complications": random.choice([True, False]),
                                "readmission_30d": random.choice([True, False]),
                                "mortality_30d": random.choice([True, False]) if random.random() < 0.05 else False
                            }
                        })

                    treatments_batch.append(treatment)

                # Now update episode with collected IDs
                episode["tumour_ids"] = episode_tumour_ids
                episode["treatment_ids"] = episode_treatment_ids

                # Add episode to batch
                episodes_batch.append(episode)

        # Insert batch
        if patients_batch:
            await patients_col.insert_many(patients_batch)
            stats['patients'] += len(patients_batch)

        if episodes_batch:
            await episodes_col.insert_many(episodes_batch)
            stats['episodes'] += len(episodes_batch)

        if tumours_batch:
            await tumours_col.insert_many(tumours_batch)
            stats['tumours'] += len(tumours_batch)

        if investigations_batch:
            await investigations_col.insert_many(investigations_batch)
            stats['investigations'] += len(investigations_batch)

        if treatments_batch:
            await treatments_col.insert_many(treatments_batch)
            stats['treatments'] += len(treatments_batch)

        # Progress update
        progress = (batch_end / NUM_PATIENTS) * 100
        print(f"  Progress: {batch_end:,}/{NUM_PATIENTS:,} patients ({progress:.1f}%) - "
              f"{len(episodes_batch)} episodes, {len(tumours_batch)} tumours, "
              f"{len(investigations_batch)} investigations, {len(treatments_batch)} treatments")

    # Print final summary
    print("\n" + "=" * 70)
    print("✅ COLORECTAL CANCER TEST DATASET CREATION COMPLETE!")
    print("=" * 70)
    print(f"Database: {DB_NAME}")
    print(f"Cancer Type: {CANCER_TYPE} (Colorectal only)")
    print(f"Clinicians: Linked to {len(CLINICIANS)} clinicians from impact_system")
    print(f"\nRecords Created:")
    print(f"  Patients:        {stats['patients']:>6,}")
    print(f"  Episodes:        {stats['episodes']:>6,}")
    print(f"  Tumours:         {stats['tumours']:>6,}")
    print(f"  Investigations:  {stats['investigations']:>6,}")
    print(f"  Treatments:      {stats['treatments']:>6,}")
    print(f"\nTotal Records:   {sum(stats.values()):>6,}")
    print("=" * 70)

    print("\n💡 ID Format Examples:")
    print("   Patients:    6-char hex (e.g., 100000, 100001)")
    print("   Episodes:    EPI-PATIENTID-##")
    print("   Tumours:     TUM-PATIENTID-##")
    print("   Treatments:  SUR/ONC/DXT-PATIENTID-##")
    print("   Investigations: INV-PATIENTID-TYPE-##")

    print("\n📊 Database Statistics:")
    print(f"   Avg episodes per patient:   {stats['episodes'] / stats['patients']:.2f}")
    print(f"   Avg tumours per episode:    {stats['tumours'] / stats['episodes']:.2f}")
    print(f"   Avg investigations per episode: {stats['investigations'] / stats['episodes']:.2f}")
    print(f"   Avg treatments per episode: {stats['treatments'] / stats['episodes']:.2f}")

    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate large test dataset for IMPACT")
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')
    parser.add_argument('--count', '-c', type=int, default=NUM_PATIENTS, help=f'Number of patients to create (default: {NUM_PATIENTS})')
    args = parser.parse_args()

    # Update global count if specified
    if args.count != NUM_PATIENTS:
        NUM_PATIENTS = args.count

    print(f"\n{'='*70}")
    print("IMPACT - Large Test Dataset Generator")
    print(f"{'='*70}\n")

    asyncio.run(create_large_test_dataset(skip_confirmation=args.yes))
