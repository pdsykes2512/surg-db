#!/usr/bin/env python3
"""
IMPACT Database Import Script - Based on Mapping Files

This script imports data from Access database (acpdata_v3_db.mdb) to MongoDB
following the field-by-field mappings documented in execution/mappings/*.yaml

Each function corresponds to a mapping file and implements the exact transformations
documented there. This ensures data quality and maintains compatibility with the
working surgdb structure.

Mapping Files Reference:
- patients_mapping.yaml    → import_patients()
- episodes_mapping.yaml    → import_episodes()
- tumours_mapping.yaml     → import_tumours()
- treatments_mapping.yaml  → import_treatments_surgery()
- investigations_mapping.yaml → import_investigations()
- pathology_mapping.yaml   → import_pathology()
- oncology_mapping.yaml    → import_oncology()
- followup_mapping.yaml    → import_followup()

Import Sequence:
1. Patients       → creates patient_id mapping
2. Episodes       → creates episode_id mapping
3. Tumours        → creates tumour_id mapping
4. Treatments     → updates episodes
5. Investigations → creates investigation records
6. Pathology      → updates tumours
7. Oncology       → creates RT/chemo treatments
8. Follow-up      → updates episodes
9. Mortality      → updates treatments

Mode: INSERT-ONLY (skip if record exists) - Safe for production
"""

import os
import sys
import hashlib
import pandas as pd
from pymongo import MongoClient
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import re

# Add parent directory to path to import from backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))
from app.utils.encryption import encrypt_field, ENCRYPTED_FIELDS

# Load environment
load_dotenv('/etc/impact/secrets.env')
load_dotenv('.env')

# Access database path
ACCESS_DB_PATH = '/root/impact/data/acpdata_v3_db.mdb'

# CSV export directory (we'll export from Access to CSV first)
CSV_DIR = os.path.expanduser('~/.tmp/access_export_mapped')


# ============================================================================
# HELPER FUNCTIONS - ID GENERATION
# ============================================================================

def generate_random_patient_id() -> str:
    """
    Generate random 6-character alphanumeric patient ID
    Mapping: patients_mapping.yaml - patient_id

    CRITICAL: Randomly generated to avoid any link to identifiable data.
    NOT derived from hospital number, NHS number, or any patient data.
    Example: "A3K7M2", "P9X4Q1", etc.
    """
    import random
    import string
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(6))


def generate_episode_id(patient_id: str, sequence: int) -> str:
    """
    Generate episode ID: E-{patient_id}-{sequence:02d}
    Mapping: episodes_mapping.yaml - episode_id
    """
    return f"E-{patient_id}-{sequence:02d}"


def generate_treatment_id(patient_id: str, sequence: int) -> str:
    """
    Generate treatment ID: T-{patient_id}-{sequence:02d}
    Mapping: treatments_mapping.yaml - treatment_id
    Note: Oncology treatments use 1000+ sequence to avoid collisions
    """
    return f"T-{patient_id}-{sequence:02d}"


def generate_tumour_id(patient_id: str, sequence: int) -> str:
    """
    Generate tumour ID: TUM-{patient_id}-{sequence:02d}
    Mapping: tumours_mapping.yaml - tumour_id
    """
    return f"TUM-{patient_id}-{sequence:02d}"


# ============================================================================
# HELPER FUNCTIONS - DATE PARSING
# ============================================================================

def parse_date(date_val) -> Optional[str]:
    """
    Parse date from various formats to YYYY-MM-DD
    Used throughout all mapping files
    """
    if pd.isna(date_val) or date_val == '' or date_val is None:
        return None

    if isinstance(date_val, datetime):
        return date_val.strftime('%Y-%m-%d')

    date_str = str(date_val).strip()

    # Try various formats
    formats = [
        '%Y-%m-%d',
        '%m/%d/%y %H:%M:%S',
        '%m/%d/%Y %H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%m/%d/%y',
        '%m/%d/%Y',
        '%d/%m/%Y'
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except:
            continue

    return None


def parse_dob(dob_val) -> Optional[str]:
    """
    Parse date of birth specifically
    Mapping: patients_mapping.yaml - demographics.date_of_birth
    """
    return parse_date(dob_val)


def calculate_age(dob: Optional[str]) -> Optional[int]:
    """
    Calculate age from date of birth
    Mapping: patients_mapping.yaml - demographics.age
    """
    if not dob:
        return None

    try:
        dob_date = datetime.strptime(dob, '%Y-%m-%d')
        today = datetime.utcnow()
        age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
        return age if age >= 0 else None
    except:
        return None


# ============================================================================
# HELPER FUNCTIONS - GENDER/DEMOGRAPHICS
# ============================================================================

def parse_gender(gender_val) -> str:
    """
    Map gender to COSD-compliant values
    Mapping: patients_mapping.yaml - demographics.gender
    """
    if pd.isna(gender_val):
        return 'unknown'

    gender_str = str(gender_val).strip().upper()

    if gender_str in ['M', 'MALE']:
        return 'male'
    elif gender_str in ['F', 'FEMALE']:
        return 'female'
    else:
        return 'unknown'


# ============================================================================
# HELPER FUNCTIONS - YES/NO STANDARDIZATION
# ============================================================================

def map_yes_no(value) -> Optional[str]:
    """
    Convert boolean/numeric to yes/no string
    Used throughout all mapping files
    """
    if pd.isna(value):
        return None

    # Handle boolean
    if isinstance(value, bool):
        return 'yes' if value else 'no'

    # Handle numeric (0/1 or -1/0)
    if isinstance(value, (int, float)):
        return 'yes' if value else 'no'

    # Handle string
    value_str = str(value).strip().lower()

    if value_str in ['yes', 'y', 'true', '1', '-1']:
        return 'yes'
    elif value_str in ['no', 'n', 'false', '0', '']:
        return 'no'

    return None


# ============================================================================
# HELPER FUNCTIONS - COSD STANDARDIZATION
# ============================================================================

def map_referral_source(value) -> Optional[str]:
    """
    Map to COSD-compliant referral source values
    Mapping: episodes_mapping.yaml - referral_source
    Values: gp/consultant/screening/emergency/other
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip().lower()

    if 'gp' in value_str or 'general practitioner' in value_str:
        return 'gp'
    elif 'consultant' in value_str or 'specialist' in value_str:
        return 'consultant'
    elif 'screen' in value_str or 'bcsp' in value_str:
        return 'screening'
    elif 'emerg' in value_str or 'a&e' in value_str or 'a+e' in value_str:
        return 'emergency'
    else:
        return 'other'


def map_referral_priority(value) -> Optional[str]:
    """
    Map to COSD-compliant referral priority
    Mapping: episodes_mapping.yaml - referral_priority
    Values: routine/urgent/two_week_wait
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip().upper()

    if value_str in ['R', 'ROUTINE']:
        return 'routine'
    elif value_str in ['U', 'URGENT']:
        return 'urgent'
    elif value_str in ['TW', 'TWC', '2WW', 'TWO_WEEK_WAIT']:
        return 'two_week_wait'

    return None


def map_tumour_site(value) -> Optional[str]:
    """
    Map tumour site to standardized values
    Mapping: tumours_mapping.yaml - site
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip().lower()

    site_mapping = {
        'sigmoid': 'sigmoid_colon',
        'rectum': 'rectum',
        'caecum': 'caecum',
        'ascending': 'ascending_colon',
        'descending': 'descending_colon',
        'transverse': 'transverse_colon',
        'rectosigmoid': 'rectosigmoid_junction',
        'hepatic': 'hepatic_flexure',
        'splenic': 'splenic_flexure'
    }

    for key, mapped_value in site_mapping.items():
        if key in value_str:
            return mapped_value

    return value_str


def map_tnm_stage(value) -> Optional[str]:
    """
    Map TNM stage to simple format
    Mapping: tumours_mapping.yaml, pathology_mapping.yaml
    Examples: "T3" → "3", "N1a" → "1a", "M0" → "0"
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip().upper()

    # Remove T/N/M prefix if present
    value_str = value_str.replace('T', '').replace('N', '').replace('M', '')
    value_str = value_str.strip()

    return value_str if value_str else None


def map_grade(value) -> Optional[str]:
    """
    Map histological grade to COSD format
    Mapping: pathology_mapping.yaml - grade
    Values: g1/g2/g3/g4
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip().lower()

    if 'well' in value_str or '1' in value_str or 'g1' in value_str:
        return 'g1'
    elif 'moderate' in value_str or '2' in value_str or 'g2' in value_str:
        return 'g2'
    elif 'poor' in value_str or '3' in value_str or 'g3' in value_str:
        return 'g3'
    elif 'undifferent' in value_str or '4' in value_str or 'g4' in value_str:
        return 'g4'

    return None


def map_histology_type(value) -> Optional[str]:
    """
    Map histology type to standardized values
    Mapping: pathology_mapping.yaml - histology_type
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip().lower()

    if 'mucinous' in value_str:
        return 'mucinous_adenocarcinoma'
    elif 'signet' in value_str:
        return 'signet_ring_carcinoma'
    elif 'adenocarcinoma' in value_str or 'adeno' in value_str:
        return 'adenocarcinoma'

    return value_str


# ============================================================================
# HELPER FUNCTIONS - INVASION STATUS
# ============================================================================

def map_invasion_status(value) -> Optional[str]:
    """
    Map invasion status to standard values
    Mapping: pathology_mapping.yaml
    Values: present/absent/uncertain
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip().lower()

    if 'yes' in value_str or 'present' in value_str or 'positive' in value_str:
        return 'present'
    elif 'no' in value_str or 'absent' in value_str or 'negative' in value_str:
        return 'absent'
    elif 'uncertain' in value_str or 'unclear' in value_str or 'indeterminate' in value_str:
        return 'uncertain'

    return None


def map_crm_status(value) -> Optional[str]:
    """
    Map CRM status to standard values
    Mapping: tumours_mapping.yaml, pathology_mapping.yaml
    Values: yes/no/uncertain
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip().lower()

    if 'involved' in value_str or 'positive' in value_str or 'yes' in value_str:
        return 'yes'
    elif 'clear' in value_str or 'negative' in value_str or 'no' in value_str:
        return 'no'
    elif 'uncertain' in value_str or 'unclear' in value_str:
        return 'uncertain'

    return None


def map_resection_grade(value) -> Optional[str]:
    """
    Map resection grade to COSD format
    Mapping: pathology_mapping.yaml - resection_grade
    Values: r0/r1/r2
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip().upper()

    if 'R0' in value_str:
        return 'r0'
    elif 'R1' in value_str:
        return 'r1'
    elif 'R2' in value_str:
        return 'r2'

    return None


# ============================================================================
# HELPER FUNCTIONS - TREATMENT MAPPINGS
# ============================================================================

def map_treatment_intent(value) -> Optional[str]:
    """
    Map treatment intent to standard values
    Mapping: treatments_mapping.yaml - treatment_intent
    Values: curative/palliative
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip().lower()

    if 'curative' in value_str or 'cure' in value_str:
        return 'curative'
    elif 'palliative' in value_str or 'palliat' in value_str:
        return 'palliative'

    return None


def map_asa(value) -> Optional[int]:
    """
    Map ASA score to integer 1-5
    Mapping: treatments_mapping.yaml - asa_score
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip().upper()

    # Extract number from string
    for i in range(1, 6):
        if str(i) in value_str:
            return i

    return None


def map_urgency(value) -> Optional[str]:
    """
    Map surgery urgency to standard values
    Mapping: treatments_mapping.yaml - classification.urgency
    Values: elective/urgent/emergency
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip().lower()

    if 'elective' in value_str or 'planned' in value_str:
        return 'elective'
    elif 'urgent' in value_str:
        return 'urgent'
    elif 'emergency' in value_str or 'emerg' in value_str:
        return 'emergency'

    return None


def determine_surgical_approach(row) -> Optional[str]:
    """
    Determine surgical approach with PRIORITY LOGIC
    Mapping: treatments_mapping.yaml - classification.approach

    CRITICAL: Priority order matters!
    1. Check Robotic field first (overrides all)
    2. Check for "converted to open" in LapType
    3. Otherwise use LapProc mapping

    Values: open/laparoscopic/robotic/converted_to_open
    """
    # Priority 1: Check robotic field
    robotic = row.get('Robotic')
    if pd.notna(robotic) and robotic:
        return 'robotic'

    # Priority 2: Check for conversion in LapType
    lap_type = row.get('LapType', '')
    if pd.notna(lap_type):
        lap_type_str = str(lap_type).strip().lower()
        if 'convert' in lap_type_str and 'open' in lap_type_str:
            return 'converted_to_open'

    # Priority 3: Use LapProc mapping
    lap_proc = row.get('LapProc', '')
    if pd.notna(lap_proc):
        lap_proc_str = str(lap_proc).strip().lower()

        if 'laparoscopic' in lap_proc_str or 'lap' in lap_proc_str:
            return 'laparoscopic'
        elif 'open' in lap_proc_str:
            return 'open'

    # Default to open if unclear
    return 'open'


def map_procedure_type(value) -> Optional[str]:
    """
    Map procedure type to standard values
    Mapping: treatments_mapping.yaml - procedure.procedure_type
    Values: resection/stoma_only/other
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip().lower()

    if 'resection' in value_str or 'resect' in value_str:
        return 'resection'
    elif 'stoma' in value_str and 'only' in value_str:
        return 'stoma_only'
    else:
        return 'other'


def map_surgeon_grade(value) -> Optional[str]:
    """
    Map surgeon grade to standard values
    Mapping: treatments_mapping.yaml - team.surgeon_grade
    Values: consultant/specialist_registrar/other
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip().lower()

    if 'consultant' in value_str:
        return 'consultant'
    elif 'spr' in value_str or 'registrar' in value_str or 'reg' in value_str:
        return 'specialist_registrar'
    else:
        return 'other'


def map_stoma_type(value) -> Optional[str]:
    """
    Map stoma type to standard values
    Mapping: treatments_mapping.yaml - intraoperative.stoma_type

    CRITICAL: Use StomDone (what was done) NOT StomType (what was planned)

    Values: ileostomy/colostomy/other
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip().lower()

    if 'ileostomy' in value_str or 'ileos' in value_str:
        return 'ileostomy'
    elif 'colostomy' in value_str or 'colos' in value_str:
        return 'colostomy'
    else:
        return 'other'


def is_defunctioning_stoma(row) -> Optional[str]:
    """
    Determine if defunctioning stoma created
    Mapping: treatments_mapping.yaml - intraoperative.defunctioning_stoma

    CRITICAL: Return 'yes' ONLY if BOTH anastomosis AND stoma performed

    Values: yes/no
    """
    anastomosis = row.get('Anastom')
    stoma = row.get('Stoma')

    # Both must be true for defunctioning stoma
    if pd.notna(anastomosis) and pd.notna(stoma):
        if anastomosis and stoma:
            return 'yes'

    return 'no'


def map_bowel_prep(value) -> Optional[str]:
    """
    Map bowel preparation to standard values
    Mapping: treatments_mapping.yaml - intraoperative.bowel_prep
    Values: full/enema_only/none
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip().lower()

    if 'full' in value_str or 'complete' in value_str:
        return 'full'
    elif 'enema' in value_str:
        return 'enema_only'
    elif 'none' in value_str or 'no' in value_str:
        return 'none'

    return None


def map_extraction_site(value) -> Optional[str]:
    """
    Map specimen extraction site to standard values
    Mapping: treatments_mapping.yaml - intraoperative.extraction_site
    Values: pfannenstiel/midline/extended_port/other
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip().lower()

    if 'pfannenstiel' in value_str:
        return 'pfannenstiel'
    elif 'midline' in value_str or 'mid-line' in value_str:
        return 'midline'
    elif 'port' in value_str and ('extend' in value_str or 'enlarge' in value_str):
        return 'extended_port'
    else:
        return 'other'


def parse_complications(row) -> List[str]:
    """
    Parse complications from multiple boolean fields
    Mapping: treatments_mapping.yaml - postoperative_events.complications

    Returns array of complication types that occurred
    """
    complications = []

    complication_fields = {
        'MJ_Leak': 'major_anastomotic_leak',
        'MJ_Abs': 'major_abscess',
        'MJ_Bleed': 'major_bleeding',
        'MJ_Obst': 'major_obstruction',
        'MI_Leak': 'minor_anastomotic_leak',
        'MI_Abs': 'minor_abscess',
        'MI_Bleed': 'minor_bleeding',
        'MI_Obst': 'minor_obstruction',
        'WI': 'wound_infection',
        'CI': 'chest_infection',
        'MI': 'myocardial_infarction',
        'UTI': 'urinary_tract_infection',
        'Cardio': 'cardiovascular'
    }

    for field, complication_name in complication_fields.items():
        value = row.get(field)
        if pd.notna(value) and value:
            complications.append(complication_name)

    return complications


def safe_to_int(value) -> Optional[int]:
    """Helper to safely convert to int"""
    if pd.isna(value):
        return None
    try:
        return int(float(value))
    except:
        return None


def safe_to_float(value) -> Optional[float]:
    """Helper to safely convert to float"""
    if pd.isna(value):
        return None
    try:
        return float(value)
    except:
        return None


# ============================================================================
# HELPER FUNCTIONS - ONCOLOGY MAPPINGS
# ============================================================================

def map_treatment_timing(value) -> Optional[str]:
    """
    Map treatment timing to standard values
    Mapping: oncology_mapping.yaml - timing
    Values: neoadjuvant/adjuvant/palliative
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip().lower()

    if 'pre' in value_str or 'neo' in value_str or 'before' in value_str:
        return 'neoadjuvant'
    elif 'post' in value_str or 'adj' in value_str or 'after' in value_str:
        return 'adjuvant'
    elif 'palliat' in value_str:
        return 'palliative'

    return None


def map_rt_technique(value) -> Optional[str]:
    """
    Map radiotherapy technique to standard values
    Mapping: oncology_mapping.yaml - technique
    Values: long_course/short_course/contact
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip().lower()

    if 'long' in value_str:
        return 'long_course'
    elif 'short' in value_str:
        return 'short_course'
    elif 'contact' in value_str or 'brachy' in value_str:
        return 'contact'

    return None


# ============================================================================
# HELPER FUNCTIONS - FOLLOW-UP MAPPINGS
# ============================================================================

def map_followup_modality(value) -> Optional[str]:
    """
    Map follow-up modality to standard values
    Mapping: followup_mapping.yaml - modality
    Values: clinic/telephone/other
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip().lower()

    if 'clinic' in value_str or 'face' in value_str:
        return 'clinic'
    elif 'telephone' in value_str or 'phone' in value_str or 'virtual' in value_str:
        return 'telephone'
    else:
        return 'other'


def map_performance_status(value) -> Optional[int]:
    """
    Map performance status to integer 0-4
    Mapping: episodes_mapping.yaml - performance_status
    """
    if pd.isna(value):
        return None

    value_str = str(value).strip()

    # Extract number
    for i in range(5):  # 0-4
        if str(i) in value_str:
            return i

    return None


def map_lead_clinician(value) -> Optional[str]:
    """
    Clean lead clinician name for storage
    Used when clinician doesn't match active clinicians table
    """
    if pd.isna(value):
        return None

    return str(value).strip() or None


# ============================================================================
# HELPER FUNCTIONS - ENCRYPTION (UK GDPR + CALDICOTT COMPLIANCE)
# ============================================================================

def encrypt_patient_document(patient_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Encrypt sensitive fields in patient document for UK GDPR and Caldicott compliance

    Encrypts:
    - nhs_number: NHS patient identifier
    - mrn: Medical record number
    - hospital_number: Legacy hospital identifier
    - demographics.first_name: Patient given name
    - demographics.last_name: Patient surname
    - demographics.date_of_birth: Patient DOB (quasi-identifier)
    - demographics.deceased_date: Date of death
    - contact.postcode: Geographic identifier

    Args:
        patient_doc: Patient document dictionary

    Returns:
        Patient document with encrypted sensitive fields
    """
    # Encrypt top-level fields
    for field in ['nhs_number', 'mrn', 'hospital_number']:
        if field in patient_doc and patient_doc[field]:
            patient_doc[field] = encrypt_field(field, patient_doc[field])

    # Encrypt nested demographics fields
    if 'demographics' in patient_doc:
        demo = patient_doc['demographics']
        for field in ['first_name', 'last_name', 'date_of_birth', 'deceased_date']:
            if field in demo and demo[field]:
                demo[field] = encrypt_field(field, demo[field])

    # Encrypt contact fields
    if 'contact' in patient_doc and 'postcode' in patient_doc['contact']:
        if patient_doc['contact']['postcode']:
            patient_doc['contact']['postcode'] = encrypt_field(
                'postcode',
                patient_doc['contact']['postcode']
            )

    return patient_doc


# ============================================================================
# HELPER FUNCTIONS - CLINICIAN MATCHING
# ============================================================================

def load_clinicians_mapping(client) -> Dict[str, str]:
    """
    Load clinicians from impact_system database and create name→ID mapping
    Mapping: treatments_mapping.yaml - team.primary_surgeon

    Returns:
        Dict mapping surgeon name variations to clinician_id
    """
    system_db = client['impact_system']
    clinicians = list(system_db.clinicians.find({'status': 'active'}))

    clinician_mapping = {}

    for clinician in clinicians:
        clinician_id = str(clinician.get('_id'))
        first_name = str(clinician.get('first_name', '')).strip()
        surname = str(clinician.get('surname', '')).strip()

        if not surname:
            continue

        # Create various name formats for matching (case-insensitive)
        full_name = f"{first_name} {surname}".strip()
        surname_first = f"{surname} {first_name}".strip()
        surname_only = surname

        # Map all variations to the clinician_id
        clinician_mapping[full_name.lower()] = clinician_id
        clinician_mapping[surname_first.lower()] = clinician_id
        clinician_mapping[surname_only.lower()] = clinician_id

        # Also try with initials
        if first_name:
            initial_name = f"{first_name[0]} {surname}".strip()
            clinician_mapping[initial_name.lower()] = clinician_id

            surname_initial = f"{surname} {first_name[0]}".strip()
            clinician_mapping[surname_initial.lower()] = clinician_id

    print(f"✅ Loaded {len(clinicians)} active clinicians from impact_system")
    return clinician_mapping


def match_surgeon_to_clinician(surgeon_name: str, clinician_mapping: Dict[str, str]) -> tuple[Optional[str], Optional[str]]:
    """
    Match surgeon name to clinician ID (case-insensitive)
    Mapping: treatments_mapping.yaml - team.primary_surgeon

    Args:
        surgeon_name: Name from CSV
        clinician_mapping: Dict of name→clinician_id

    Returns:
        Tuple of (clinician_id or None, display_name)
    """
    if not surgeon_name:
        return None, None

    surgeon_clean = surgeon_name.strip()
    surgeon_lower = surgeon_clean.lower()

    # Try exact match (case-insensitive)
    clinician_id = clinician_mapping.get(surgeon_lower)

    if clinician_id:
        return clinician_id, surgeon_clean

    # No match - return None for clinician_id but keep the text name
    return None, surgeon_clean


# ============================================================================
# IMPORT FUNCTIONS
# ============================================================================

def import_patients(db, csv_path_primary: str, csv_path_fallback: str, stats: Dict) -> tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    """
    Import patients from tblPatient CSV (primary) with Table1 CSV (fallback)
    Mapping: patients_mapping.yaml

    CRITICAL CHANGES:
    - Random patient_id generation (not derived from any field)
    - NHS number as PRIMARY linking field
    - PAS number as FALLBACK linking field
    - tblPatient as primary source, Table1 as fallback for missing data
    - ALL SENSITIVE FIELDS ENCRYPTED (UK GDPR + Caldicott compliance)

    Returns:
        Tuple of (nhs_to_patient_id, pas_to_patient_id, hosp_no_to_patient_id, deceased_patients)
    """
    print("\n" + "=" * 80)
    print("IMPORTING PATIENTS (WITH ENCRYPTION)")
    print("=" * 80)
    print(f"Mapping reference: execution/mappings/patients_mapping.yaml")
    print(f"Primary source: tblPatient (7,973 patients)")
    print(f"Fallback source: Table1 (7,250 patients)")

    # Load both CSVs
    df_primary = pd.read_csv(csv_path_primary, low_memory=False)
    df_fallback = pd.read_csv(csv_path_fallback, low_memory=False)
    print(f"Loaded {len(df_primary)} patients from tblPatient (primary)")
    print(f"Loaded {len(df_fallback)} patients from Table1 (fallback)")

    # Create fallback lookup by hospital number
    fallback_dict = {}
    for _, row in df_fallback.iterrows():
        hosp_no = str(row.get('Hosp_No', '')).strip()
        if hosp_no and hosp_no != 'nan':
            fallback_dict[hosp_no] = row

    patients_collection = db.patients
    nhs_to_patient_id = {}  # PRIMARY linking field
    pas_to_patient_id = {}  # FALLBACK linking field
    hosp_no_to_patient_id = {}  # SECONDARY linking field (for tblTumour/tblSurgery)
    deceased_patients = {}
    used_patient_ids = set()  # Track to avoid collisions

    for idx, row in df_primary.iterrows():
        hosp_no = str(row.get('Hosp_No', '')).strip()

        if not hosp_no or hosp_no == 'nan':
            stats['patients_skipped_no_hosp_no'] += 1
            continue

        # Generate RANDOM patient_id (patients_mapping.yaml - patient_id)
        # Ensure uniqueness by checking against used IDs
        patient_id = generate_random_patient_id()
        while patient_id in used_patient_ids:
            patient_id = generate_random_patient_id()
        used_patient_ids.add(patient_id)

        # Check if patient already exists (INSERT-ONLY mode)
        existing = patients_collection.find_one({'patient_id': patient_id})
        if existing:
            stats['patients_skipped_existing'] += 1
            continue

        # Get fallback row if exists
        fallback_row = fallback_dict.get(hosp_no)

        # Helper to get value with fallback
        def get_with_fallback(field):
            val = row.get(field)
            if pd.isna(val) or val == '' or val == 'nan':
                if fallback_row is not None:
                    return fallback_row.get(field)
            return val

        # Clean NHS number - CRITICAL FIX (patients_mapping.yaml - nhs_number)
        # Access stores as Double which adds .0 - must strip decimal
        nhs_number = get_with_fallback('NHS_No')
        if pd.notna(nhs_number):
            nhs_str = str(int(float(nhs_number)))  # Convert to int first to remove decimal
            nhs_number = nhs_str if nhs_str else None
        else:
            nhs_number = None

        # Get PAS number (MRN)
        pas_no = get_with_fallback('PAS_No')
        mrn = str(pas_no).strip() if pd.notna(pas_no) and str(pas_no) != 'nan' else None

        # Create linking mappings (patients_mapping.yaml - linking strategy)
        # PRIMARY: NHS number
        if nhs_number:
            nhs_to_patient_id[nhs_number] = patient_id
        # FALLBACK: PAS number
        if mrn:
            pas_to_patient_id[mrn] = patient_id
        # SECONDARY: Hospital number (for tblTumour/tblSurgery which don't have NHS/PAS)
        if hosp_no and hosp_no != 'nan':
            hosp_no_to_patient_id[hosp_no] = patient_id

        # Parse demographics with fallback
        dob = parse_dob(get_with_fallback('P_DOB'))
        deceased_date = parse_date(get_with_fallback('DeathDat'))

        if deceased_date:
            deceased_patients[patient_id] = deceased_date

        # Build patient document (BEFORE encryption)
        patient_doc = {
            'patient_id': patient_id,
            'mrn': mrn,
            'nhs_number': nhs_number,
            'hospital_number': hosp_no,
            'demographics': {
                'first_name': str(get_with_fallback('Forename')).strip() or None,
                'last_name': str(get_with_fallback('Surname')).strip() or None,
                'date_of_birth': dob,
                'age': calculate_age(dob),
                'gender': parse_gender(get_with_fallback('Sex')),
                'ethnicity': 'Z',  # Not in Access DB - default to "Z" (Not stated)
                'deceased_date': deceased_date,
                'bmi': float(get_with_fallback('BMI')) if pd.notna(get_with_fallback('BMI')) else None,
                'weight_kg': float(get_with_fallback('Weight')) if pd.notna(get_with_fallback('Weight')) else None,
                'height_cm': float(get_with_fallback('Height')) if pd.notna(get_with_fallback('Height')) else None
            },
            'contact': {
                'postcode': str(get_with_fallback('Postcode')).strip() or None
            },
            'medical_history': {
                'family_history': bool(get_with_fallback('Fam_Hist')),
                'family_history_positive': str(get_with_fallback('Fam_Hist_positive')).strip() or None
            },
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        # ENCRYPT SENSITIVE FIELDS (UK GDPR + Caldicott compliance)
        patient_doc = encrypt_patient_document(patient_doc)

        patients_collection.insert_one(patient_doc)
        stats['patients_inserted'] += 1

        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{len(df_primary)} patients...")

    print(f"✅ Patients imported: {stats['patients_inserted']} inserted, {stats['patients_skipped_existing']} skipped (existing)")
    print(f"   NHS number mappings: {len(nhs_to_patient_id)}")
    print(f"   PAS number mappings: {len(pas_to_patient_id)}")
    print(f"   Hospital number mappings: {len(hosp_no_to_patient_id)}")
    print(f"   Deceased patients tracked: {len(deceased_patients)}")
    print(f"   🔒 Sensitive fields ENCRYPTED per UK GDPR + Caldicott")

    return nhs_to_patient_id, pas_to_patient_id, hosp_no_to_patient_id, deceased_patients


def import_episodes(db, csv_path: str, nhs_to_patient_id: Dict, pas_to_patient_id: Dict, hosp_no_to_patient_id: Dict, stats: Dict) -> Dict:
    """
    Import episodes from tblTumour CSV export (referral/MDT data portion)
    Mapping: episodes_mapping.yaml

    Uses Hospital number (primary) or NHS/PAS number (fallback) to link to patients.

    Returns:
        episode_mapping dict: (patient_id, TumSeqno) → episode_id
    """
    print("\n" + "=" * 80)
    print("IMPORTING EPISODES (Referral/MDT Data)")
    print("=" * 80)
    print(f"Mapping reference: execution/mappings/episodes_mapping.yaml")

    df = pd.read_csv(csv_path, low_memory=False)
    print(f"Loaded {len(df)} tumour records from CSV (will create episodes)")

    episodes_collection = db.episodes
    episode_mapping = {}  # (patient_id, TumSeqno) → episode_id
    episode_counter = {}  # patient_id → count (for sequential numbering)

    for idx, row in df.iterrows():
        # Use Hospital number (PRIMARY) to find patient
        # tblTumour only has Hosp_No, not NHS_No or PAS_No
        hosp_no = row.get('Hosp_No')
        patient_id = None

        # PRIMARY: Try Hospital number
        if pd.notna(hosp_no):
            hosp_str = str(hosp_no).strip()
            patient_id = hosp_no_to_patient_id.get(hosp_str)

        if not patient_id:
            stats['episodes_skipped_no_patient'] += 1
            continue

        tum_seqno = row.get('TumSeqno', 0)

        # Generate sequential episode_id per patient (episodes_mapping.yaml - episode_id)
        episode_counter[patient_id] = episode_counter.get(patient_id, 0) + 1
        episode_id = generate_episode_id(patient_id, episode_counter[patient_id])

        # Check if episode already exists
        existing = episodes_collection.find_one({'episode_id': episode_id})
        if existing:
            stats['episodes_skipped_existing'] += 1
            episode_mapping[(patient_id, tum_seqno)] = episode_id
            continue

        # Parse dates - use Dt_Diag as fallback for missing dates
        referral_date = parse_date(row.get('DtRef'))
        first_seen_date = parse_date(row.get('Dt_Visit'))
        diagnosis_date = parse_date(row.get('Dt_Diag'))

        # Fallback logic (episodes_mapping.yaml - referral_date, first_seen_date)
        if not referral_date and diagnosis_date:
            referral_date = diagnosis_date
        if not first_seen_date and diagnosis_date:
            first_seen_date = diagnosis_date

        # Treatment intent from careplan (episodes_mapping.yaml - treatment_intent)
        treatment_intent_val = str(row.get('careplan', '')).strip().lower()
        treatment_intent = None
        if 'curative' in treatment_intent_val:
            treatment_intent = 'curative'
        elif 'palliative' in treatment_intent_val:
            treatment_intent = 'palliative'

        # Treatment plan from plan_treat (episodes_mapping.yaml - treatment_plan)
        treatment_plan = str(row.get('plan_treat', '')).strip() or None

        episode_doc = {
            'episode_id': episode_id,
            'patient_id': patient_id,
            'condition_type': 'cancer',  # Fixed value
            'cancer_type': 'bowel',  # Fixed value
            'referral_date': referral_date,
            'referral_source': map_referral_source(row.get('RefType')),
            'referral_priority': map_referral_priority(row.get('Priority')),
            'first_seen_date': first_seen_date,
            'provider_first_seen': 'RHU',  # Portsmouth Hospitals University NHS Trust
            'mdt_discussion_date': None,  # Populated from surgery table later
            'mdt_team': str(row.get('Mdt_org', '')).strip() or None,
            'mdt_meeting_type': 'Colorectal MDT',  # Fixed value for colorectal database
            'treatment_intent': treatment_intent,
            'treatment_plan': treatment_plan,
            'cns_involved': map_yes_no(row.get('CNS')),
            'performance_status': map_performance_status(row.get('performance')),
            'episode_status': 'active',
            'lead_clinician': None,  # Will be populated from surgery table with proper matching
            'treatment_ids': [],
            'tumour_ids': [],
            'follow_up': [],  # Will be populated from follow-up table
            'no_treatment': None,  # Will be populated from surgery table (NoSurg field)
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        episodes_collection.insert_one(episode_doc)
        stats['episodes_inserted'] += 1
        episode_mapping[(patient_id, tum_seqno)] = episode_id

        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{len(df)} episodes...")

    print(f"✅ Episodes imported: {stats['episodes_inserted']} inserted, {stats['episodes_skipped_existing']} skipped")

    return episode_mapping


def import_tumours(db, csv_path: str, nhs_to_patient_id: Dict, pas_to_patient_id: Dict, hosp_no_to_patient_id: Dict, episode_mapping: Dict, stats: Dict) -> Dict:
    """
    Import tumours from tblTumour CSV export (diagnosis/staging data portion)
    Mapping: tumours_mapping.yaml

    Uses NHS number (primary) or PAS number (fallback) to link to patients.

    Returns:
        tumour_mapping dict: (patient_id, TumSeqno) → tumour_id
    """
    print("\n" + "=" * 80)
    print("IMPORTING TUMOURS (Diagnosis/Staging Data)")
    print("=" * 80)
    print(f"Mapping reference: execution/mappings/tumours_mapping.yaml")

    df = pd.read_csv(csv_path, low_memory=False)
    print(f"Loaded {len(df)} tumour records from CSV")

    tumours_collection = db.tumours
    tumour_counter = {}  # patient_id → count (for sequential numbering)
    tumour_mapping = {}  # (patient_id, TumSeqno) → tumour_id (for pathology matching)

    for idx, row in df.iterrows():
        # Use Hospital number (PRIMARY) to find patient
        # tblTumour only has Hosp_No, not NHS_No or PAS_No
        hosp_no = row.get('Hosp_No')
        patient_id = None

        # PRIMARY: Try Hospital number
        if pd.notna(hosp_no):
            hosp_str = str(hosp_no).strip()
            patient_id = hosp_no_to_patient_id.get(hosp_str)

        if not patient_id:
            stats['tumours_skipped_no_patient'] += 1
            continue

        tum_seqno = row.get('TumSeqno', 0)
        episode_id = episode_mapping.get((patient_id, tum_seqno))

        if not episode_id:
            stats['tumours_skipped_no_episode'] += 1
            continue

        # Generate sequential tumour_id per patient (tumours_mapping.yaml - tumour_id)
        tumour_counter[patient_id] = tumour_counter.get(patient_id, 0) + 1
        tumour_id = generate_tumour_id(patient_id, tumour_counter[patient_id])

        # Check if tumour already exists
        existing = tumours_collection.find_one({'tumour_id': tumour_id})
        if existing:
            stats['tumours_skipped_existing'] += 1
            tumour_mapping[(patient_id, tum_seqno)] = tumour_id
            continue

        tumour_doc = {
            'tumour_id': tumour_id,
            'patient_id': patient_id,
            'episode_id': episode_id,
            'tumour_type': 'primary',  # All tumours are primary colorectal cancers
            'diagnosis_date': parse_date(row.get('Dt_Diag')),
            'icd10_code': str(row.get('TumICD10', '')).strip() or None,
            'site': map_tumour_site(row.get('TumSite')),
            'tnm_version': '8',  # TNM 8th edition

            # Clinical TNM staging (tumours_mapping.yaml - clinical_t/n/m)
            'clinical_t': map_tnm_stage(row.get('preTNM_T')),
            'clinical_n': map_tnm_stage(row.get('preTNM_N')),
            'clinical_m': map_tnm_stage(row.get('preTNM_M')),

            # Pathological staging (populated from pathology table later)
            'pathological_t': None,
            'pathological_n': None,
            'pathological_m': None,

            # Rectal cancer specific
            'distance_from_anal_verge_cm': float(row.get('Height')) if pd.notna(row.get('Height')) else None,

            # Imaging results (tumours_mapping.yaml - imaging_results)
            'imaging_results': {
                'ct_chest': {
                    'result': map_yes_no(row.get('CT_pneumo')),
                    'date': parse_date(row.get('Dt_CT_pneumo'))
                },
                'ct_abdomen': {
                    'result': map_yes_no(row.get('CT_Abdo')),
                    'date': parse_date(row.get('Dt_CT_Abdo'))
                },
                'mri_primary': {
                    'date': parse_date(row.get('Dt_MRI1')),
                    't_stage': map_tnm_stage(row.get('MRI1_T')),
                    'n_stage': map_tnm_stage(row.get('MRI1_N')),
                    'crm_status': map_crm_status(row.get('MRI1_CRM')),
                    'crm_distance_mm': float(row.get('MRI1_dist')) if pd.notna(row.get('MRI1_dist')) else None,
                    'emvi': map_yes_no(row.get('EMVI'))
                }
            },

            # Metastases (tumours_mapping.yaml - distant_metastases)
            'distant_metastases': {
                'liver': map_yes_no(row.get('DM_Liver')),
                'lung': map_yes_no(row.get('DM_Lung')),
                'bone': map_yes_no(row.get('DM_Bone')),
                'other': map_yes_no(row.get('DM_Other'))
            },

            # Screening (tumours_mapping.yaml - screening)
            'screening': {
                'screening_programme': map_yes_no(row.get('BCSP')),
                'screened': map_yes_no(row.get('Screened'))
            },

            # Synchronous tumors
            'synchronous': map_yes_no(row.get('Sync')),
            'synchronous_description': str(row.get('TumSync', '')).strip() or None,

            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        tumours_collection.insert_one(tumour_doc)
        stats['tumours_inserted'] += 1

        # Store mapping for pathology import
        tumour_mapping[(patient_id, tum_seqno)] = tumour_id

        # Update episode with tumour_id (tumours_mapping.yaml - notes #4)
        db.episodes.update_one(
            {'episode_id': episode_id},
            {'$push': {'tumour_ids': tumour_id}}
        )

        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{len(df)} tumours...")

    print(f"✅ Tumours imported: {stats['tumours_inserted']} inserted, {stats['tumours_skipped_existing']} skipped")

    return tumour_mapping


# Due to file length, I'll create a second part of the script...
# To be continued in import_from_access_mapped_part2.py


def import_treatments_surgery(db, csv_path: str, nhs_to_patient_id: Dict, pas_to_patient_id: Dict, hosp_no_to_patient_id: Dict,
                              episode_mapping: Dict, clinician_mapping: Dict, stats: Dict) -> int:
    """
    Import surgical treatments from tblSurgery CSV export
    Mapping: treatments_mapping.yaml

    Uses NHS number (primary) or PAS number (fallback) to link to patients.

    Returns:
        Count of treatments inserted
    """
    print("\n" + "=" * 80)
    print("IMPORTING SURGICAL TREATMENTS")
    print("=" * 80)
    print(f"Mapping reference: execution/mappings/treatments_mapping.yaml")

    df = pd.read_csv(csv_path, low_memory=False)
    print(f"Loaded {len(df)} surgical treatment records from CSV")

    treatments_collection = db.treatments
    episodes_collection = db.episodes
    treatment_counter = {}  # patient_id → count (for sequential numbering)

    for idx, row in df.iterrows():
        # Use Hospital number (PRIMARY) to find patient
        # tblSurgery/tblTumour only has Hosp_No, not NHS_No or PAS_No
        hosp_no = row.get('Hosp_No')
        patient_id = None

        # PRIMARY: Try Hospital number
        if pd.notna(hosp_no):
            hosp_str = str(hosp_no).strip()
            patient_id = hosp_no_to_patient_id.get(hosp_str)

        if not patient_id:
            stats['treatments_skipped_no_patient'] += 1
            continue

        tum_seqno = row.get('TumSeqNo', 0)  # tblSurgery uses 'TumSeqNo' (uppercase)
        episode_id = episode_mapping.get((patient_id, tum_seqno))

        if not episode_id:
            stats['treatments_skipped_no_episode'] += 1
            continue

        # Generate sequential treatment_id per patient (treatments_mapping.yaml - treatment_id)
        treatment_counter[patient_id] = treatment_counter.get(patient_id, 0) + 1
        treatment_id = generate_treatment_id(patient_id, treatment_counter[patient_id])

        # Check if treatment already exists
        surgery_date = parse_date(row.get('Surgery'))
        if not surgery_date:
            stats['treatments_skipped_no_date'] += 1
            continue

        # Check for duplicate by patient + date (safer than treatment_id for re-runs)
        existing = treatments_collection.find_one({
            'patient_id': patient_id,
            'treatment_date': surgery_date,
            'treatment_type': 'surgery'
        })
        if existing:
            stats['treatments_skipped_existing'] += 1
            continue

        discharge_date = parse_date(row.get('Date_Dis'))

        # Calculate length of stay
        length_of_stay = None
        if surgery_date and discharge_date:
            try:
                surg_dt = datetime.strptime(surgery_date, '%Y-%m-%d')
                disc_dt = datetime.strptime(discharge_date, '%Y-%m-%d')
                length_of_stay = (disc_dt - surg_dt).days
            except:
                pass

        # Match primary surgeon to clinician (treatments_mapping.yaml - team.primary_surgeon)
        surgeon_name = str(row.get('Surgeon', '')).strip()
        primary_surgeon_id, primary_surgeon_text = match_surgeon_to_clinician(surgeon_name, clinician_mapping)

        # Match assistant surgeons
        assistant_surgeons = []
        assistant_surgeons_text = []
        for asst_field in ['Assistnt', 'Assistn2']:
            asst_name = str(row.get(asst_field, '')).strip()
            if asst_name:
                asst_id, asst_text = match_surgeon_to_clinician(asst_name, clinician_mapping)
                if asst_id:
                    assistant_surgeons.append(asst_id)
                if asst_text:
                    assistant_surgeons_text.append(asst_text)

        treatment_doc = {
            'treatment_id': treatment_id,
            'patient_id': patient_id,
            'episode_id': episode_id,
            'treatment_type': 'surgery',  # All records in tblSurgery are surgical
            'treatment_date': surgery_date,
            'treatment_intent': map_treatment_intent(row.get('Curative')),

            # COSD mandatory fields
            'opcs4_code': str(row.get('OPCS4', '')).strip() or None,
            'asa_score': map_asa(row.get('ASA')),
            'provider_organisation': str(row.get('Unit_ID', '')).strip() or None,

            # Classification (treatments_mapping.yaml - classification)
            'classification': {
                'urgency': map_urgency(row.get('ModeOp')),
                'approach': determine_surgical_approach(row)  # CRITICAL: Priority logic
            },

            # Procedure (treatments_mapping.yaml - procedure)
            'procedure': {
                'primary_procedure': str(row.get('ProcName', '')).strip() or None,
                'procedure_type': map_procedure_type(row.get('ProcType')),
                'resection_performed': map_yes_no(row.get('ProcResect')),
                'robotic_surgery': map_yes_no(row.get('Robotic')),
                'conversion_to_open': map_yes_no(row.get('Convert')),
                'anterior_resection_type': str(row.get('AR_high_low', '')).strip() or None
            },

            # Perioperative timeline
            'perioperative_timeline': {
                'admission_date': surgery_date,  # Default to surgery date (not separately recorded)
                'surgery_date': surgery_date,
                'operation_duration_minutes': safe_to_int(row.get('Total_op_time')),
                'discharge_date': discharge_date,
                'length_of_stay_days': length_of_stay
            },

            # Team (treatments_mapping.yaml - team)
            'team': {
                'primary_surgeon': primary_surgeon_id,
                'primary_surgeon_text': primary_surgeon_text,
                'surgeon_grade': map_surgeon_grade(row.get('SurGrad')),
                'assistant_surgeons': assistant_surgeons,
                'assistant_surgeons_text': assistant_surgeons_text,
                'anesthetist_grade': map_surgeon_grade(row.get('AneGrad')),
                'surgical_fellow': str(row.get('SurgFellow', '')).strip() or None
            },

            # Intraoperative (treatments_mapping.yaml - intraoperative)
            'intraoperative': {
                'stoma_created': map_yes_no(row.get('Stoma')),
                'stoma_type': map_stoma_type(row.get('StomDone')),  # CRITICAL: StomDone NOT StomType
                'stoma_closure_date': parse_date(row.get('DatClose')),
                'defunctioning_stoma': is_defunctioning_stoma(row),  # CRITICAL: Both anastomosis AND stoma
                'anastomosis_performed': map_yes_no(row.get('Anastom')),
                'anastomosis_height_cm': safe_to_float(row.get('Hgt_anast')),
                'laparoscopic_duration_minutes': safe_to_int(row.get('Lap_op_time')),
                'docking_time_minutes': safe_to_int(row.get('Dock_time')),
                'blood_loss_ml': safe_to_int(row.get('bl_loss_ mm')),
                'bowel_prep': map_bowel_prep(row.get('Bowel_prep')),
                'thromboprophylaxis': str(row.get('ThromboP', '')).strip() or None,
                'antibiotic_prophylaxis': str(row.get('AntiProp', '')).strip() or None,
                'extraction_site': map_extraction_site(row.get('extraction_site')),
                'extraction_size_cm': safe_to_float(row.get('extraction_meas_cm')),
                'previous_abdominal_surgery': map_yes_no(row.get('prev_ab_surg_YN'))
            },

            # Postoperative events (treatments_mapping.yaml - postoperative_events)
            'postoperative_events': {
                'return_to_theatre': {
                    'occurred': map_yes_no(row.get('re_op'))
                },
                'complications': parse_complications(row),
                'post_op_complications': str(row.get('Post_Op', '')).strip() or None,
                'post_op_ileus': map_yes_no(row.get('PO_ileus')),
                'post_op_ct_collection': map_yes_no(row.get('PO_CT_coll'))
            },

            # Outcomes (treatments_mapping.yaml - outcomes)
            'outcomes': {
                'readmission_30day': map_yes_no(row.get('Post_IP')),  # CRITICAL: Post_IP NOT Major_C
                'mortality_30day': None,  # Calculated later from deceased_date
                'mortality_90day': None   # Calculated later from deceased_date
            },

            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        treatments_collection.insert_one(treatment_doc)
        stats['treatments_inserted'] += 1

        # Update episode with treatment_id
        episodes_collection.update_one(
            {'episode_id': episode_id},
            {'$push': {'treatment_ids': treatment_id}}
        )

        # Update episode with lead_clinician if this is the first treatment
        if primary_surgeon_id or primary_surgeon_text:
            episodes_collection.update_one(
                {'episode_id': episode_id, 'lead_clinician': None},
                {'$set': {'lead_clinician': primary_surgeon_id or primary_surgeon_text}}
            )

        # Update episode with no_treatment flag based on NoSurg field
        no_surg = row.get('NoSurg')
        if pd.notna(no_surg):
            episodes_collection.update_one(
                {'episode_id': episode_id},
                {'$set': {'no_treatment': bool(no_surg)}}
            )

        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{len(df)} treatments...")

    print(f"✅ Treatments imported: {stats['treatments_inserted']} inserted, {stats['treatments_skipped_existing']} skipped")

    return stats['treatments_inserted']


# ==============================================================================
# MAIN ORCHESTRATION FUNCTION
# ==============================================================================
# HELPER FUNCTION - RESULT TEXT CLEANING
# ==============================================================================

def clean_result_text(value) -> Optional[str]:
    """
    Clean investigation result text by removing leading numbers
    Mapping: investigations_mapping.yaml - result
    
    Access DB stores results like "1 Normal", "2 Abnormal"
    This removes the leading number and returns just the text
    
    Examples:
        "1 Normal" → "normal"
        "2 Abnormal" → "abnormal"
        "Normal" → "normal"
    """
    if pd.isna(value) or not value:
        return None
    
    value_str = str(value).strip()
    
    # Remove leading number and space (e.g., "1 Normal" → "Normal")
    import re
    cleaned = re.sub(r'^\d+\s+', '', value_str)
    
    # Convert to lowercase
    return cleaned.lower() if cleaned else None


# ==============================================================================
# IMPORT FUNCTION - INVESTIGATIONS
# ==============================================================================

def import_investigations(db, csv_path: str, nhs_to_patient_id: Dict, pas_to_patient_id: Dict, hosp_no_to_patient_id: Dict,
                         episode_mapping: Dict, tumour_mapping: Dict, stats: Dict) -> int:
    """
    Import investigations from tblTumour CSV export (imaging portion)
    Mapping: investigations_mapping.yaml
    
    Creates 4 investigation types per tumour (if date present):
    1. CT Abdomen (ct_abdomen)
    2. CT Colonography (ct_colonography)  
    3. Colonoscopy (colonoscopy)
    4. MRI Primary (mri_primary) with TNM findings
    
    Uses NHS number (primary) or PAS number (fallback) to link to patients.
    
    Returns:
        Count of investigations inserted
    """
    print("\n" + "=" * 80)
    print("IMPORTING INVESTIGATIONS")
    print("=" * 80)
    print(f"Mapping reference: execution/mappings/investigations_mapping.yaml")
    
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"Loaded {len(df)} tumour records from CSV (will extract investigations)")
    
    investigations_collection = db.investigations
    investigation_counters = {}  # (patient_id, type) → count
    investigations_inserted = 0
    
    for idx, row in df.iterrows():
        # Use Hospital number (PRIMARY) to find patient
        hosp_no = row.get('Hosp_No')
        patient_id = None

        # PRIMARY: Try Hospital number
        if pd.notna(hosp_no):
            hosp_str = str(hosp_no).strip()
            patient_id = hosp_no_to_patient_id.get(hosp_str)

        if not patient_id:
            continue
        
        tum_seqno = row.get('TumSeqno', 0)
        episode_id = episode_mapping.get((patient_id, tum_seqno))
        tumour_id = tumour_mapping.get((patient_id, tum_seqno))
        
        if not episode_id or not tumour_id:
            continue
        
        # Investigation 1: CT Abdomen
        ct_abdo_date = parse_date(row.get('Dt_CT_Abdo'))
        if ct_abdo_date:
            key = (patient_id, 'CTA')
            investigation_counters[key] = investigation_counters.get(key, 0) + 1
            inv_id = f"INV-{patient_id}-CTA-{investigation_counters[key]:02d}"
            
            inv_doc = {
                'investigation_id': inv_id,
                'patient_id': patient_id,
                'episode_id': episode_id,
                'tumour_id': tumour_id,
                'type': 'imaging',
                'subtype': 'ct_abdomen',
                'date': ct_abdo_date,
                'result': clean_result_text(row.get('CT_Abdo_result')),
                'findings': {},
                'report_url': None,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            investigations_collection.insert_one(inv_doc)
            investigations_inserted += 1
        
        # Investigation 2: CT Colonography (CT Pneumocolon)
        ct_pneumo_date = parse_date(row.get('Dt_CT_pneumo'))
        if ct_pneumo_date:
            key = (patient_id, 'CTC')
            investigation_counters[key] = investigation_counters.get(key, 0) + 1
            inv_id = f"INV-{patient_id}-CTC-{investigation_counters[key]:02d}"
            
            inv_doc = {
                'investigation_id': inv_id,
                'patient_id': patient_id,
                'episode_id': episode_id,
                'tumour_id': tumour_id,
                'type': 'imaging',
                'subtype': 'ct_colonography',
                'date': ct_pneumo_date,
                'result': clean_result_text(row.get('CT_pneumo_result')),
                'findings': {},
                'report_url': None,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            investigations_collection.insert_one(inv_doc)
            investigations_inserted += 1
        
        # Investigation 3: Colonoscopy
        col_date = parse_date(row.get('Date_Col'))
        if col_date:
            key = (patient_id, 'COL')
            investigation_counters[key] = investigation_counters.get(key, 0) + 1
            inv_id = f"INV-{patient_id}-COL-{investigation_counters[key]:02d}"
            
            inv_doc = {
                'investigation_id': inv_id,
                'patient_id': patient_id,
                'episode_id': episode_id,
                'tumour_id': tumour_id,
                'type': 'endoscopy',
                'subtype': 'colonoscopy',
                'date': col_date,
                'result': clean_result_text(row.get('Col_result')),
                'findings': {},
                'report_url': None,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            investigations_collection.insert_one(inv_doc)
            investigations_inserted += 1
        
        # Investigation 4: MRI Primary (with structured findings)
        mri_date = parse_date(row.get('Dt_MRI1'))
        if mri_date:
            key = (patient_id, 'MRI')
            investigation_counters[key] = investigation_counters.get(key, 0) + 1
            inv_id = f"INV-{patient_id}-MRI-{investigation_counters[key]:02d}"
            
            # Structured MRI findings (investigations_mapping.yaml - mri_primary.findings)
            mri_findings = {
                't_stage': map_tnm_stage(row.get('MRI1_T')),
                'n_stage': map_tnm_stage(row.get('MRI1_N')),
                'crm_status': map_crm_status(row.get('MRI1_CRM')),
                'crm_distance_mm': safe_to_float(row.get('MRI1_dist')),
                'emvi': map_yes_no(row.get('EMVI'))
            }
            
            inv_doc = {
                'investigation_id': inv_id,
                'patient_id': patient_id,
                'episode_id': episode_id,
                'tumour_id': tumour_id,
                'type': 'imaging',
                'subtype': 'mri_primary',
                'date': mri_date,
                'result': clean_result_text(row.get('MRI1_result')),
                'findings': mri_findings,
                'report_url': None,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            investigations_collection.insert_one(inv_doc)
            investigations_inserted += 1
        
        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{len(df)} tumour records...")
    
    print(f"✅ Investigations imported: {investigations_inserted} created")
    stats['investigations_inserted'] = investigations_inserted
    
    return investigations_inserted


# ==============================================================================
# IMPORT FUNCTION - PATHOLOGY (UPDATES TUMOURS)
# ==============================================================================

def import_pathology(db, csv_path: str, nhs_to_patient_id: Dict, pas_to_patient_id: Dict, hosp_no_to_patient_id: Dict,
                    tumour_mapping: Dict, stats: Dict) -> int:
    """
    Import pathology data from tblPathology CSV export
    Mapping: pathology_mapping.yaml
    
    OPERATION: UPDATE (not INSERT)
    Updates existing tumour records with pathological staging and histology
    
    Uses NHS number (primary) or PAS number (fallback) to link to patients.
    
    Returns:
        Count of tumours updated
    """
    print("\n" + "=" * 80)
    print("IMPORTING PATHOLOGY (Updating Tumours)")
    print("=" * 80)
    print(f"Mapping reference: execution/mappings/pathology_mapping.yaml")
    
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"Loaded {len(df)} pathology records from CSV")
    
    tumours_collection = db.tumours
    tumours_updated = 0
    
    for idx, row in df.iterrows():
        # Use Hospital number (PRIMARY) to find patient
        hosp_no = row.get('Hosp_No')
        patient_id = None

        # PRIMARY: Try Hospital number
        if pd.notna(hosp_no):
            hosp_str = str(hosp_no).strip()
            patient_id = hosp_no_to_patient_id.get(hosp_str)

        if not patient_id:
            continue
        
        tum_seqno = row.get('TumSeqNo', 0)  # Note: TumSeqNo in pathology table
        tumour_id = tumour_mapping.get((patient_id, tum_seqno))
        
        if not tumour_id:
            continue
        
        # Build pathology update (pathology_mapping.yaml)
        pathology_update = {
            # Pathological TNM staging (post-surgery)
            'pathological_t': map_tnm_stage(row.get('TNM_Tumr')),
            'pathological_n': map_tnm_stage(row.get('TNM_Nods')),
            'pathological_m': map_tnm_stage(row.get('TNM_Mets')),
            
            # Histology
            'grade': map_grade(row.get('HistGrad')),
            'histology_type': map_histology_type(row.get('HistType')),
            
            # Lymph nodes (COSD quality metrics)
            'lymph_nodes_examined': safe_to_int(row.get('NoLyNoF')),
            'lymph_nodes_positive': safe_to_int(row.get('NoLyNoP')),
            
            # Invasion markers
            'lymphovascular_invasion': map_invasion_status(row.get('VasInv')),
            'perineural_invasion': map_invasion_status(row.get('PerInv')),
            'peritoneal_invasion': map_invasion_status(row.get('PeriInv')),
            
            # Margins (critical for rectal cancer)
            'crm_status': map_crm_status(row.get('Mar_Cir')),
            'crm_distance_mm': safe_to_float(row.get('Mar_Cir_dist')),
            'proximal_margin_mm': safe_to_float(row.get('Mar_Prox')),
            'distal_margin_mm': safe_to_float(row.get('Mar_Dist')),
            
            # Resection grade
            'resection_grade': map_resection_grade(row.get('resect_grade')),
            
            # Additional pathology
            'tumour_deposits': map_yes_no(row.get('Tum_dep')),
            'number_of_tumour_deposits': safe_to_int(row.get('Tum_dep_no')),
            
            'updated_at': datetime.utcnow()
        }
        
        # Update tumour record
        result = tumours_collection.update_one(
            {'tumour_id': tumour_id},
            {'$set': pathology_update}
        )
        
        if result.modified_count > 0:
            tumours_updated += 1
        
        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{len(df)} pathology records...")
    
    print(f"✅ Pathology imported: {tumours_updated} tumours updated")
    stats['pathology_updated'] = tumours_updated
    
    return tumours_updated


# ==============================================================================
# IMPORT FUNCTION - FOLLOW-UP (APPENDS TO EPISODES)
# ==============================================================================

def import_followup(db, csv_path: str, nhs_to_patient_id: Dict, pas_to_patient_id: Dict, hosp_no_to_patient_id: Dict,
                   episode_mapping: Dict, stats: Dict) -> int:
    """
    Import follow-up data from tblFollowUp CSV export
    Mapping: followup_mapping.yaml
    
    OPERATION: UPDATE (appends to episode.follow_up array)
    Each follow-up record is appended to the episode's follow_up array
    
    Uses NHS number (primary) or PAS number (fallback) to link to patients.
    
    Returns:
        Count of follow-up records added
    """
    print("\n" + "=" * 80)
    print("IMPORTING FOLLOW-UP DATA (Appending to Episodes)")
    print("=" * 80)
    print(f"Mapping reference: execution/mappings/followup_mapping.yaml")
    
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"Loaded {len(df)} follow-up records from CSV")
    
    episodes_collection = db.episodes
    followups_added = 0
    
    for idx, row in df.iterrows():
        # Use Hospital number (PRIMARY) to find patient
        hosp_no = row.get('Hosp_No')
        patient_id = None

        # PRIMARY: Try Hospital number
        if pd.notna(hosp_no):
            hosp_str = str(hosp_no).strip()
            patient_id = hosp_no_to_patient_id.get(hosp_str)

        if not patient_id:
            continue
        
        tum_seqno = row.get('TumSeqNo', 0)
        episode_id = episode_mapping.get((patient_id, tum_seqno))
        
        if not episode_id:
            continue
        
        # Parse follow-up date
        followup_date = parse_date(row.get('Date_FU'))
        if not followup_date:
            continue  # Skip if no date
        
        # Build follow-up record (followup_mapping.yaml)
        followup_record = {
            'follow_up_date': followup_date,
            'modality': map_followup_modality(row.get('ModeFol')),
            
            # Local recurrence
            'local_recurrence': {
                'occurred': map_yes_no(row.get('Local')),
                'date': parse_date(row.get('LocalDat')),
                'diagnosis': str(row.get('LocalDia', '')).strip() or None
            },
            
            # Distant recurrence (metastases)
            'distant_recurrence': {
                'occurred': map_yes_no(row.get('Distant')),
                'date': parse_date(row.get('DistDate')),
                'sites': {
                    'liver': map_yes_no(row.get('DS_Liver')),
                    'lung': map_yes_no(row.get('DS_Lung')),
                    'bone': map_yes_no(row.get('DS_Bone')),
                    'other': map_yes_no(row.get('DS_Other'))
                }
            },
            
            # Follow-up investigations
            'investigations': {
                'ct': {
                    'performed': map_yes_no(row.get('CT_FU')),
                    'date': parse_date(row.get('CT_date'))
                },
                'colonoscopy': {
                    'performed': map_yes_no(row.get('Col_FU')),
                    'date': parse_date(row.get('Col_Date'))
                }
            },
            
            # Palliative referral (indicates transition from curative to palliative care)
            'palliative_referral': {
                'referred': map_yes_no(row.get('Ref_Pall')),
                'date': parse_date(row.get('Dat_Pall'))
            }
        }
        
        # Append to episode's follow_up array
        result = episodes_collection.update_one(
            {'episode_id': episode_id},
            {'$push': {'follow_up': followup_record}}
        )
        
        if result.modified_count > 0:
            followups_added += 1
        
        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{len(df)} follow-up records...")
    
    print(f"✅ Follow-up data imported: {followups_added} records added to episodes")
    stats['followup_added'] = followups_added
    
    return followups_added


# ==============================================================================
# UTILITY FUNCTION - POPULATE MORTALITY FLAGS
# ==============================================================================

def populate_mortality_flags(db, deceased_patients: Dict, stats: Dict) -> int:
    """
    Populate 30-day and 90-day mortality flags in treatment records
    
    Calculates mortality flags by comparing surgery date to deceased date:
    - mortality_30day: 'yes' if died within 30 days of surgery
    - mortality_90day: 'yes' if died within 90 days of surgery
    
    Args:
        db: MongoDB database
        deceased_patients: Dict of {patient_id: deceased_date}
        stats: Statistics dictionary
    
    Returns:
        Count of treatments updated
    """
    print("\n" + "=" * 80)
    print("POPULATING MORTALITY FLAGS")
    print("=" * 80)
    
    treatments_collection = db.treatments
    treatments_updated = 0
    
    # Process each deceased patient
    for patient_id, deceased_date_str in deceased_patients.items():
        # Find all surgical treatments for this patient
        treatments = list(treatments_collection.find({
            'patient_id': patient_id,
            'treatment_type': 'surgery'
        }))
        
        if not treatments:
            continue
        
        deceased_date = datetime.strptime(deceased_date_str, '%Y-%m-%d')
        
        for treatment in treatments:
            surgery_date_str = treatment.get('treatment_date')
            if not surgery_date_str:
                continue
            
            surgery_date = datetime.strptime(surgery_date_str, '%Y-%m-%d')
            
            # Calculate days between surgery and death
            days_to_death = (deceased_date - surgery_date).days
            
            # Determine mortality flags
            mortality_30day = 'yes' if 0 <= days_to_death <= 30 else 'no'
            mortality_90day = 'yes' if 0 <= days_to_death <= 90 else 'no'
            
            # Update treatment record
            result = treatments_collection.update_one(
                {'treatment_id': treatment['treatment_id']},
                {'$set': {
                    'outcomes.mortality_30day': mortality_30day,
                    'outcomes.mortality_90day': mortality_90day
                }}
            )
            
            if result.modified_count > 0:
                treatments_updated += 1
    
    print(f"✅ Mortality flags populated: {treatments_updated} treatments updated")
    stats['mortality_flags_updated'] = treatments_updated
    
    return treatments_updated
# ==============================================================================

def run_import(mongodb_uri: str, db_name: str = 'impact'):
    """
    Main function to orchestrate the complete import process
    
    Import sequence:
    1. Patients → creates patient_id mappings (NHS/PAS)
    2. Episodes → creates episode_id mapping
    3. Tumours → creates tumour_id mapping
    4. Treatments → creates surgical treatment records
    5. Investigations → creates imaging/endoscopy records
    6. Pathology → updates tumours with pathological staging
    7. Follow-up → appends follow-up records to episodes
    8. Mortality → populates 30/90-day mortality flags
    
    Args:
        mongodb_uri: MongoDB connection string
        db_name: Database name (default: 'impact')
    """
    print("=" * 80)
    print("IMPACT DATABASE IMPORT - Based on Field Mappings")
    print("=" * 80)
    print(f"MongoDB URI: {mongodb_uri}")
    print(f"Database: {db_name}")
    print(f"CSV Directory: {CSV_DIR}")
    print()
    
    # Initialize statistics
    stats = {
        'patients_inserted': 0,
        'patients_skipped_no_hosp_no': 0,
        'patients_skipped_existing': 0,
        'episodes_inserted': 0,
        'episodes_skipped_no_patient': 0,
        'episodes_skipped_existing': 0,
        'tumours_inserted': 0,
        'tumours_skipped_no_patient': 0,
        'tumours_skipped_no_episode': 0,
        'tumours_skipped_existing': 0,
        'treatments_inserted': 0,
        'treatments_skipped_no_patient': 0,
        'treatments_skipped_no_episode': 0,
        'treatments_skipped_no_date': 0,
        'treatments_skipped_existing': 0,
        'investigations_inserted': 0,
        'pathology_updated': 0,
        'followup_added': 0,
        'mortality_flags_updated': 0
    }
    
    # Connect to MongoDB
    print("Connecting to MongoDB...")
    client = MongoClient(mongodb_uri)
    db = client[db_name]
    
    # Load clinicians mapping
    clinician_mapping = load_clinicians_mapping(client)
    
    # IMPORT SEQUENCE
    start_time = datetime.utcnow()
    
    # 1. Import Patients (PRIMARY + FALLBACK sources with ENCRYPTION)
    nhs_to_patient_id, pas_to_patient_id, hosp_no_to_patient_id, deceased_patients = import_patients(
        db,
        csv_path_primary=f"{CSV_DIR}/tblPatient.csv",
        csv_path_fallback=f"{CSV_DIR}/Table1.csv",
        stats=stats
    )
    
    # 2. Import Episodes
    episode_mapping = import_episodes(
        db,
        csv_path=f"{CSV_DIR}/tblTumour.csv",
        nhs_to_patient_id=nhs_to_patient_id,
        pas_to_patient_id=pas_to_patient_id,
        hosp_no_to_patient_id=hosp_no_to_patient_id,
        stats=stats
    )
    
    # 3. Import Tumours
    tumour_mapping = import_tumours(
        db,
        csv_path=f"{CSV_DIR}/tblTumour.csv",
        nhs_to_patient_id=nhs_to_patient_id,
        pas_to_patient_id=pas_to_patient_id,
        hosp_no_to_patient_id=hosp_no_to_patient_id,
        episode_mapping=episode_mapping,
        stats=stats
    )
    
    # 4. Import Surgical Treatments
    import_treatments_surgery(
        db,
        csv_path=f"{CSV_DIR}/tblSurgery.csv",
        nhs_to_patient_id=nhs_to_patient_id,
        pas_to_patient_id=pas_to_patient_id,
        hosp_no_to_patient_id=hosp_no_to_patient_id,
        episode_mapping=episode_mapping,
        clinician_mapping=clinician_mapping,
        stats=stats
    )
    
    # 5. Import Investigations
    import_investigations(
        db,
        csv_path=f"{CSV_DIR}/tblTumour.csv",
        nhs_to_patient_id=nhs_to_patient_id,
        pas_to_patient_id=pas_to_patient_id,
        hosp_no_to_patient_id=hosp_no_to_patient_id,
        episode_mapping=episode_mapping,
        tumour_mapping=tumour_mapping,
        stats=stats
    )
    
    # 6. Import Pathology (updates tumours)
    import_pathology(
        db,
        csv_path=f"{CSV_DIR}/tblPathology.csv",
        nhs_to_patient_id=nhs_to_patient_id,
        pas_to_patient_id=pas_to_patient_id,
        hosp_no_to_patient_id=hosp_no_to_patient_id,
        tumour_mapping=tumour_mapping,
        stats=stats
    )
    
    # 7. Import Follow-up Data (appends to episodes)
    import_followup(
        db,
        csv_path=f"{CSV_DIR}/tblFollowUp.csv",
        nhs_to_patient_id=nhs_to_patient_id,
        pas_to_patient_id=pas_to_patient_id,
        hosp_no_to_patient_id=hosp_no_to_patient_id,
        episode_mapping=episode_mapping,
        stats=stats
    )
    
    # 8. Populate Mortality Flags
    populate_mortality_flags(db, deceased_patients, stats)
    
    # Calculate total time
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    # Print final statistics
    print("\n" + "=" * 80)
    print("IMPORT COMPLETE")
    print("=" * 80)
    print(f"Duration: {duration:.1f} seconds")
    print()
    print("Summary:")
    print(f"  Patients:      {stats['patients_inserted']} inserted")
    print(f"  Episodes:      {stats['episodes_inserted']} inserted")
    print(f"  Tumours:       {stats['tumours_inserted']} inserted")
    print(f"  Treatments:    {stats['treatments_inserted']} inserted")
    print(f"  Investigations: {stats['investigations_inserted']} inserted")
    print(f"  Pathology:     {stats['pathology_updated']} tumours updated")
    print(f"  Follow-up:     {stats['followup_added']} records added")
    print(f"  Mortality:     {stats['mortality_flags_updated']} flags set")
    print()
    print("Mappings created:")
    print(f"  NHS → Patient ID: {len(nhs_to_patient_id)}")
    print(f"  PAS → Patient ID: {len(pas_to_patient_id)}")
    print(f"  Hospital → Patient ID: {len(hosp_no_to_patient_id)}")
    print(f"  Episode mapping: {len(episode_mapping)}")
    print(f"  Tumour mapping: {len(tumour_mapping)}")
    print()
    print("🔒 All sensitive fields encrypted per UK GDPR + Caldicott")
    print("=" * 80)
    
    client.close()
    return stats


if __name__ == '__main__':
    """
    Run the import script
    
    Usage:
        python import_from_access_mapped.py
    
    Prerequisites:
        1. Export Access DB to CSV using: bash execution/migrations/export_access_to_csv.sh
        2. Ensure MongoDB is running
        3. Ensure environment variables are set in /etc/impact/secrets.env or .env
    """
    import sys
    
    # Get MongoDB URI from environment
    mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
    db_name = os.getenv('MONGODB_DB_NAME', 'impact')
    
    print("IMPACT Database Import Script")
    print("Based on field-by-field mappings in execution/mappings/")
    print()
    print(f"MongoDB URI: {mongodb_uri}")
    print(f"Database: {db_name}")
    print(f"CSV Directory: {CSV_DIR}")
    print()
    
    # Check if CSV directory exists
    if not os.path.exists(CSV_DIR):
        print(f"❌ ERROR: CSV directory not found: {CSV_DIR}")
        print()
        print("Please run the CSV export script first:")
        print("  bash execution/migrations/export_access_to_csv.sh")
        sys.exit(1)
    
    # Check for required CSV files
    required_files = [
        'tblPatient.csv',
        'Table1.csv',
        'tblTumour.csv',
        'tblSurgery.csv',
        'tblPathology.csv',
        'tblFollowUp.csv'
    ]
    
    missing_files = []
    for filename in required_files:
        filepath = os.path.join(CSV_DIR, filename)
        if not os.path.exists(filepath):
            missing_files.append(filename)
    
    if missing_files:
        print(f"❌ ERROR: Missing required CSV files:")
        for filename in missing_files:
            print(f"  - {filename}")
        print()
        print("Please run the CSV export script first:")
        print("  bash execution/migrations/export_access_to_csv.sh")
        sys.exit(1)
    
    # Confirm before proceeding
    print("This will import data into the MongoDB database.")
    print("Existing records will be skipped (INSERT-ONLY mode).")
    print()
    
    response = input("Proceed with import? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Import cancelled.")
        sys.exit(0)
    
    # Run import
    try:
        run_import(mongodb_uri, db_name)
        print("\n✅ Import completed successfully!")
    except Exception as e:
        print(f"\n❌ Import failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


