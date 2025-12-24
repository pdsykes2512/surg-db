#!/usr/bin/env python3
"""Find patients without any episodes"""

import requests
import json

API_URL = "http://localhost:8000/api"

# Get token (using admin credentials)
login_response = requests.post(f"{API_URL}/auth/login", data={
    "username": "admin@example.com",
    "password": "admin123"
})

if login_response.status_code != 200:
    print(f"Login failed: {login_response.text}")
    exit(1)

token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Get all patients
patients_response = requests.get(f"{API_URL}/patients?limit=10000", headers=headers)
if patients_response.status_code != 200:
    print(f"Failed to get patients: {patients_response.status_code} - {patients_response.text}")
    exit(1)
all_patients = patients_response.json()
print(f"Total patients: {len(all_patients)}")

# Get all episodes
episodes_response = requests.get(f"{API_URL}/episodes?limit=10000", headers=headers)
all_episodes = episodes_response.json()
print(f"Total episodes: {len(all_episodes)}")

# Build set of patient_ids that have episodes
episode_patient_ids = set(ep["patient_id"] for ep in all_episodes if "patient_id" in ep)
print(f"Patients with episodes: {len(episode_patient_ids)}")

# Find patients without episodes
patients_without_episodes = []
for patient in all_patients:
    patient_id = patient.get("patient_id")
    if patient_id not in episode_patient_ids:
        patients_without_episodes.append(patient)

print(f"\nPatients without episodes: {len(patients_without_episodes)}\n")

if patients_without_episodes:
    print("Patient details:")
    print("-" * 90)
    for i, p in enumerate(patients_without_episodes, 1):
        mrn = p.get("mrn", "N/A")
        first = p.get("first_name", "")
        surname = p.get("surname", "")
        pid = p.get("patient_id", "N/A")
        dob = p.get("date_of_birth", "N/A")
        print(f"{i:2}. MRN: {mrn:>10} | Name: {first:15} {surname:15} | DOB: {dob:12} | ID: {pid}")
