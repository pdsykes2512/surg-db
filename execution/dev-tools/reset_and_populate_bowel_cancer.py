#!/usr/bin/env python3
"""
Reset database and populate with bowel cancer episodes only
Keeps users intact but wipes all clinical data
"""
from pymongo import MongoClient
from datetime import datetime, date, timedelta
import random
from bson import ObjectId

# MongoDB connection
uri = "mongodb://admin:admin123@localhost:27017/surg_outcomes?authSource=admin"
client = MongoClient(uri)
db = client['surg_outcomes']

print("=== Resetting Database ===\n")

# Drop all clinical data collections (keep users)
collections_to_clear = ['patients', 'episodes', 'treatments', 'tumours', 'clinicians']
for collection in collections_to_clear:
    count = db[collection].count_documents({})
    db[collection].delete_many({})
    print(f"Cleared {count} documents from {collection}")

print("\n=== Creating Clinicians ===\n")

# Create clinicians
clinicians_data = [
    {"first_name": "Jim", "surname": "Khan", "specialty": "Colorectal Surgery", "is_consultant": True, "clinical_role": "surgeon"},
    {"first_name": "Paul", "surname": "Sykes", "specialty": "Colorectal Surgery", "is_consultant": True, "clinical_role": "surgeon"},
    {"first_name": "Sarah", "surname": "Williams", "specialty": "Colorectal Surgery", "is_consultant": True, "clinical_role": "surgeon"},
    {"first_name": "Michael", "surname": "Chen", "specialty": "Colorectal Surgery", "is_consultant": False, "clinical_role": "surgeon"},
    {"first_name": "Emma", "surname": "Thompson", "specialty": "Upper GI Surgery", "is_consultant": True, "clinical_role": "surgeon"},
]

for surgeon_data in clinicians_data:
    clinician = {
        "first_name": surgeon_data["first_name"],
        "surname": surgeon_data["surname"],
        "specialty": surgeon_data["specialty"],
        "is_consultant": surgeon_data["is_consultant"],
        "clinical_role": surgeon_data["clinical_role"],
        "subspecialty_leads": [],
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    db.clinicians.insert_one(clinician)
    print(f"Created clinician: {surgeon_data['first_name']} {surgeon_data['surname']}")

print("\n=== Creating Patients and Episodes ===\n")

# Sample patient data
patient_templates = [
    {"record_number": "12345678", "nhs_number": "123 456 7890", "first_name": "John", "last_name": "Smith", "dob": "1965-05-15", "gender": "male", "postcode": "E1 6AN"},
    {"record_number": "23456789", "nhs_number": "234 567 8901", "first_name": "Mary", "last_name": "Johnson", "dob": "1958-08-22", "gender": "female", "postcode": "SW1A 1AA"},
    {"record_number": "34567890", "nhs_number": "345 678 9012", "first_name": "Robert", "last_name": "Williams", "dob": "1972-03-10", "gender": "male", "postcode": "M1 1AE"},
    {"record_number": "45678901", "nhs_number": "456 789 0123", "first_name": "Patricia", "last_name": "Brown", "dob": "1960-11-30", "gender": "female", "postcode": "B2 4QA"},
    {"record_number": "56789012", "nhs_number": "567 890 1234", "first_name": "James", "last_name": "Jones", "dob": "1968-07-18", "gender": "male", "postcode": "LS1 4AP"},
    {"record_number": "67890123", "nhs_number": "678 901 2345", "first_name": "Linda", "last_name": "Davis", "dob": "1975-02-25", "gender": "female", "postcode": "NE1 1EE"},
    {"record_number": "78901234", "nhs_number": "789 012 3456", "first_name": "Michael", "last_name": "Miller", "dob": "1963-09-12", "gender": "male", "postcode": "G2 1DY"},
    {"record_number": "89012345", "nhs_number": "890 123 4567", "first_name": "Barbara", "last_name": "Wilson", "dob": "1970-12-05", "gender": "female", "postcode": "CF10 1EP"},
]

# Bowel cancer specific data
cancer_sites = ["caecum", "ascending_colon", "hepatic_flexure", "transverse_colon", "splenic_flexure", "descending_colon", "sigmoid", "rectum"]
procedures = [
    {"name": "Right hemicolectomy", "opcs": "H06", "sites": ["caecum", "ascending_colon", "hepatic_flexure"]},
    {"name": "Extended right hemicolectomy", "opcs": "H06", "sites": ["transverse_colon"]},
    {"name": "Left hemicolectomy", "opcs": "H07", "sites": ["splenic_flexure", "descending_colon"]},
    {"name": "Sigmoid colectomy", "opcs": "H08", "sites": ["sigmoid"]},
    {"name": "Anterior resection of rectum", "opcs": "H33", "sites": ["rectum"]},
    {"name": "Abdominoperineal resection", "opcs": "H33", "sites": ["rectum"]},
]

tnm_combinations = [
    {"clinical_t": "T1", "clinical_n": "N0", "clinical_m": "M0", "pathological_t": "T1", "pathological_n": "N0", "pathological_m": "M0", "nodes_pos": 0},
    {"clinical_t": "T2", "clinical_n": "N0", "clinical_m": "M0", "pathological_t": "T2", "pathological_n": "N0", "pathological_m": "M0", "nodes_pos": 0},
    {"clinical_t": "T3", "clinical_n": "N1", "clinical_m": "M0", "pathological_t": "T3", "pathological_n": "N1", "pathological_m": "M0", "nodes_pos": 2},
    {"clinical_t": "T3", "clinical_n": "N2", "clinical_m": "M0", "pathological_t": "T3", "pathological_n": "N2", "pathological_m": "M0", "nodes_pos": 5},
    {"clinical_t": "T4", "clinical_n": "N1", "clinical_m": "M0", "pathological_t": "T4a", "pathological_n": "N1", "pathological_m": "M0", "nodes_pos": 3},
]

approaches = ["open", "laparoscopic", "laparoscopic_converted", "robotic"]
urgencies = ["elective", "urgent", "emergency"]
grades = ["well", "moderate", "poor"]

base_date = datetime.now() - timedelta(days=180)

for i, patient_data in enumerate(patient_templates):
    # Create patient
    patient = {
        "record_number": patient_data["record_number"],
        "nhs_number": patient_data["nhs_number"],
        "demographics": {
            "first_name": patient_data["first_name"],
            "last_name": patient_data["last_name"],
            "date_of_birth": patient_data["dob"],
            "gender": patient_data["gender"],
            "ethnicity": random.choice(["English, Welsh, Scottish, Northern Irish or British", "Irish", "White - Any other White background", "Asian or Asian British - Indian"])
        },
        "contact_details": {
            "phone": f"07{random.randint(100000000, 999999999)}",
            "address": {
                "postcode": patient_data["postcode"]
            }
        },
        "created_at": datetime.now(),
        "created_by": "reset_script",
        "updated_at": datetime.now()
    }
    patient_result = db.patients.insert_one(patient)
    
    # Create episode for this patient
    site = random.choice(cancer_sites)
    tnm = random.choice(tnm_combinations)
    referral_date = base_date + timedelta(days=random.randint(0, 150))
    first_seen_date = referral_date + timedelta(days=random.randint(7, 21))
    diagnosis_date = first_seen_date + timedelta(days=random.randint(3, 14))
    mdt_date = diagnosis_date + timedelta(days=random.randint(5, 14))
    surgery_date = mdt_date + timedelta(days=random.randint(14, 42))
    
    episode_id = str(ObjectId())
    
    episode = {
        "_id": ObjectId(episode_id),
        "episode_id": episode_id,
        "patient_id": patient_data["record_number"],
        "condition_type": "cancer",
        "cancer_type": "bowel",
        "referral_date": referral_date.strftime("%Y-%m-%d"),
        "first_seen_date": first_seen_date.strftime("%Y-%m-%d"),
        "mdt_discussion_date": mdt_date.strftime("%Y-%m-%d"),
        "lead_clinician": random.choice(["Jim Khan", "Paul Sykes", "Sarah Williams"]),
        "mdt_team": ["colorectal"],
        "episode_status": "completed",
        "provider_first_seen": "RYR",
        "referral_source": random.choice(["2ww", "routine", "emergency"]),
        "cns_indication": "01",
        "mdt_type": "colorectal",
        "performance_status": str(random.choice([0, 1, 1, 2])),
        "cancer_data": {
            "cancer_site": site,
            "presentation_type": random.choice(["symptomatic", "screening"]),
            "symptoms": random.sample(["bleeding", "pain", "change_in_bowel_habit", "weight_loss"], k=random.randint(1, 3)),
            "histological_type": "adenocarcinoma",
            "differentiation": random.choice(grades),
        },
        "created_at": datetime.now(),
        "created_by": "reset_script",
        "last_modified_at": datetime.now(),
        "last_modified_by": "reset_script"
    }
    
    db.episodes.insert_one(episode)
    
    # Create tumour
    icd_codes = {
        "caecum": "C18.0",
        "ascending_colon": "C18.2",
        "hepatic_flexure": "C18.3",
        "transverse_colon": "C18.4",
        "splenic_flexure": "C18.5",
        "descending_colon": "C18.6",
        "sigmoid": "C18.7",
        "rectum": "C20"
    }
    
    nodes_examined = random.randint(12, 25)
    
    tumour = {
        "tumour_id": f"TUM-{random.randint(10000000, 99999999)}",
        "episode_id": episode_id,
        "patient_id": patient_data["record_number"],
        "tumour_type": "primary",
        "site": site,
        "diagnosis_date": diagnosis_date.strftime("%Y-%m-%d"),
        "icd10_code": icd_codes[site],
        "histology_type": "Adenocarcinoma",
        "grade": random.choice(grades),
        "tnm_version": "8",
        "clinical_stage_date": diagnosis_date.strftime("%Y-%m-%d"),
        "clinical_t": tnm["clinical_t"],
        "clinical_n": tnm["clinical_n"],
        "clinical_m": tnm["clinical_m"],
        "pathological_stage_date": (surgery_date + timedelta(days=7)).strftime("%Y-%m-%d"),
        "pathological_t": tnm["pathological_t"],
        "pathological_n": tnm["pathological_n"],
        "pathological_m": tnm["pathological_m"],
        "lymph_nodes_examined": nodes_examined,
        "lymph_nodes_positive": tnm["nodes_pos"],
        "lymphovascular_invasion": tnm["nodes_pos"] > 0,
        "perineural_invasion": random.choice([True, False]) if tnm["nodes_pos"] > 0 else False,
        "crm_status": "clear" if site == "rectum" else "not_applicable",
        "crm_distance_mm": random.randint(3, 15) if site == "rectum" else None,
        "proximal_margin_mm": random.randint(30, 100),
        "distal_margin_mm": random.randint(20, 80),
        "kras_status": random.choice(["Wild-type", "Mutant"]),
        "braf_status": random.choice(["Wild-type", "Mutant"]),
        "mismatch_repair_status": random.choice(["MSS", "MSI-H"]),
        "created_at": datetime.now(),
        "created_by": "reset_script",
        "last_modified_at": datetime.now(),
        "treated_by_treatment_ids": []
    }
    
    db.tumours.insert_one(tumour)
    
    # Create treatment (surgery)
    # Find appropriate procedure for this site
    procedure = next((p for p in procedures if site in p["sites"]), procedures[0])
    
    urgency = random.choices(urgencies, weights=[0.7, 0.2, 0.1])[0]
    approach = random.choices(approaches, weights=[0.15, 0.35, 0.05, 0.45])[0]
    
    treatment = {
        "treatment_id": f"SUR-{random.randint(10000000, 99999999)}",
        "episode_id": episode_id,
        "patient_id": patient_data["record_number"],
        "treatment_type": "surgery",
        "treatment_date": surgery_date.strftime("%Y-%m-%d"),
        "admission_date": (surgery_date - timedelta(days=1 if urgency == "elective" else 0)).strftime("%Y-%m-%d"),
        "discharge_date": (surgery_date + timedelta(days=random.randint(4, 8))).strftime("%Y-%m-%d"),
        "procedure_name": procedure["name"],
        "opcs4_code": procedure["opcs"],
        "surgeon": random.choice(["Jim Khan", "Paul Sykes", "Sarah Williams"]),
        "urgency": urgency,
        "approach": approach,
        "anesthesia_type": "general",
        "operation_duration_minutes": random.randint(120, 300),
        "blood_loss_ml": random.randint(50, 400),
        "transfusion_required": random.choice([False, False, False, True]),
        "drains_placed": random.choice([True, False]),
        "complexity": random.choice(["routine", "routine", "complex"]),
        "asa_score": random.choice([1, 2, 2, 3]),
        "notes": "",
        "created_at": datetime.now(),
        "created_by": "reset_script"
    }
    
    db.treatments.insert_one(treatment)
    
    print(f"Created episode for {patient_data['first_name']} {patient_data['last_name']}: {site} cancer, {procedure['name']}")

print(f"\n=== Summary ===")
print(f"Patients: {db.patients.count_documents({})}")
print(f"Episodes: {db.episodes.count_documents({})}")
print(f"Tumours: {db.tumours.count_documents({})}")
print(f"Treatments: {db.treatments.count_documents({})}")
print(f"Clinicians: {db.clinicians.count_documents({})}")
print(f"Users: {db.users.count_documents({})} (preserved)")

client.close()
print("\n✅ Database reset and populated with bowel cancer episodes")
