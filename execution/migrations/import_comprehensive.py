#!/usr/bin/env python3
"""
Comprehensive Data Import for COSD-Compliant IMPACT Database

This script imports all data from Access database CSV exports to MongoDB
with complete field mappings for COSD compliance.

Imports in order:
1. Patients (creates patient_id mapping)
2. Episodes (from tumours.csv - referral/MDT data)
3. Tumours (from tumours.csv - diagnosis/staging)
4. Treatments - Surgery (from treatments_surgery.csv)
5. Pathology (from pathology.csv - updates tumours)
6. Oncology (from oncology.csv - creates treatments)
7. Follow-up (from followup.csv - updates episodes)
8. Mortality flags (calculates from deceased dates)

Mode: INSERT-ONLY (skip if record exists) - Safe for production
"""

import os
import hashlib
import pandas as pd
from pymongo import MongoClient
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv


# Load environment
load_dotenv('/etc/impact/secrets.env')
load_dotenv('.env')

# CSV input directory
CSV_DIR = os.path.expanduser('~/.tmp/access_export_comprehensive')


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_clinicians_mapping(client) -> Dict[str, str]:
    """
    Load COLORECTAL LEAD clinicians from impact_system database and create name→ID mapping

    Only includes clinicians where 'colorectal' is in subspecialty_leads array.
    These are the lead clinicians who should be matched for lead_clinician field.

    Returns:
        Dict mapping surgeon name variations to clinician_id
    """
    system_db = client['impact_system']
    # ONLY load colorectal clinical leads (subspecialty_leads contains 'colorectal')
    clinicians = list(system_db.clinicians.find({'subspecialty_leads': 'colorectal'}))

    clinician_mapping = {}

    for clinician in clinicians:
        clinician_id = str(clinician.get('_id'))
        first_name = str(clinician.get('first_name', '')).strip()
        surname = str(clinician.get('surname', '')).strip()

        if not surname:
            continue

        # Create various name formats for matching
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

    print(f"✅ Loaded {len(clinicians)} COLORECTAL LEAD clinicians from impact_system with {len(clinician_mapping)} name variations")
    return clinician_mapping


def match_surgeon_to_clinician(surgeon_name: str, clinician_mapping: Dict[str, str]) -> tuple[Optional[str], Optional[str]]:
    """
    Match surgeon name to clinician ID

    Args:
        surgeon_name: Name from CSV
        clinician_mapping: Dict of name→clinician_id

    Returns:
        Tuple of (clinician_id or None, display_name in Title Case)
    """
    if not surgeon_name:
        return None, None

    surgeon_clean = surgeon_name.strip()
    surgeon_lower = surgeon_clean.lower()
    surgeon_title = surgeon_clean.title()  # Normalize to Title Case

    # Try exact match first
    clinician_id = clinician_mapping.get(surgeon_lower)

    if clinician_id:
        return clinician_id, surgeon_title

    # No match - return None for clinician_id but keep the text name in Title Case
    return None, surgeon_title


def generate_patient_id(hosp_no: str) -> str:
    """Generate 6-character patient ID from hospital number"""
    hash_obj = hashlib.md5(str(hosp_no).encode())
    return hash_obj.hexdigest()[:6].upper()


def generate_episode_id(patient_id: str, sequence: int) -> str:
    """Generate episode ID"""
    return f"E-{patient_id}-{sequence:02d}"


def generate_treatment_id(patient_id: str, sequence: int) -> str:
    """Generate treatment ID"""
    return f"T-{patient_id}-{sequence:02d}"


def generate_tumour_id(patient_id: str, sequence: int) -> str:
    """Generate tumour ID"""
    return f"TUM-{patient_id}-{sequence:02d}"


def strip_numeric_prefix(value: str) -> str:
    """
    Strip numeric prefix from field values

    Removes patterns like "1 ", "17 " from start of string
    Examples:
        "6 Anterior resection" -> "Anterior resection"
        "01 surgery" -> "surgery"
        "Laparoscopic" -> "Laparoscopic" (unchanged)

    Args:
        value: String value that may have numeric prefix

    Returns:
        String with numeric prefix removed
    """
    import re
    if not value or pd.isna(value):
        return value

    value_str = str(value).strip()

    # Pattern: one or more digits followed by space at start of string
    # ^(\d+)\s+ means: start of string, one or more digits, whitespace
    cleaned = re.sub(r'^\d+\s+', '', value_str)

    return cleaned


def parse_date(date_val) -> Optional[str]:
    """Parse date from various formats to YYYY-MM-DD"""
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
            # Fix 2-digit year issues
            if dt.year > 2050:
                dt = dt.replace(year=dt.year - 100)
            return dt.strftime('%Y-%m-%d')
        except:
            continue

    return None


def parse_dob(dob_val) -> Optional[str]:
    """Parse date of birth with special handling for medical records"""
    parsed = parse_date(dob_val)
    if not parsed:
        return None

    # Additional validation for DOB
    dt = datetime.strptime(parsed, '%Y-%m-%d')

    # For medical records, assume any 20XX year should be 19XX
    # Colorectal surgery patients are typically older adults
    # If year >= 2000, assume it should be 19XX
    if dt.year >= 2000:
        # Convert to 19XX (e.g., 2050 -> 1950, 2025 -> 1925)
        dt = dt.replace(year=dt.year - 100)
        return dt.strftime('%Y-%m-%d')

    # Also catch future dates (shouldn't happen but safety check)
    current_year = datetime.now().year
    if dt.year > current_year:
        dt = dt.replace(year=dt.year - 100)
        return dt.strftime('%Y-%m-%d')

    return parsed


def calculate_age(dob_str: Optional[str]) -> Optional[int]:
    """Calculate age from date of birth"""
    if not dob_str:
        return None

    try:
        dob = datetime.strptime(dob_str, '%Y-%m-%d')
        today = datetime.now()
        age = today.year - dob.year
        if today.month < dob.month or (today.month == dob.month and today.day < dob.day):
            age -= 1
        return age if 0 <= age <= 150 else None
    except:
        return None


def safe_to_int(value) -> Optional[int]:
    """Safely convert value to int, returning None if not possible"""
    if pd.isna(value) or value == '' or value is None:
        return None
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return None


def safe_to_float(value) -> Optional[float]:
    """Safely convert value to float, returning None if not possible"""
    if pd.isna(value) or value == '' or value is None:
        return None
    try:
        return float(str(value))
    except (ValueError, TypeError):
        return None


def convert_height_to_cm(value) -> Optional[float]:
    """
    Convert height to centimeters, handling both meters and centimeters

    If value < 10, assumes it's in meters and converts to cm (e.g., 1.65 → 165)
    If value >= 10, assumes it's already in cm (e.g., 165 → 165)

    Returns:
        Height in centimeters, or None if invalid
    """
    height = safe_to_float(value)
    if height is None:
        return None

    # If height is unrealistically small (< 10), it's likely in meters
    if height < 10:
        return round(height * 100, 1)

    # Otherwise assume it's already in cm
    return round(height, 1)


def parse_gender(sex_val) -> Optional[str]:
    """Parse gender field"""
    if pd.isna(sex_val):
        return None

    sex_str = str(sex_val).strip().lower()

    # IMPORTANT: Check 'female' FIRST to avoid substring match ('female' contains 'male')
    if sex_str.startswith('2') or 'female' in sex_str:
        return 'female'
    elif sex_str.startswith('1') or sex_str == 'male':
        return 'male'

    return None


def map_urgency(mode_op) -> Optional[str]:
    """Map ModeOp to urgency (elective/urgent/emergency)"""
    if pd.isna(mode_op):
        return None

    mode_str = str(mode_op).strip().lower()

    if mode_str.startswith('1') or 'elective' in mode_str or 'scheduled' in mode_str:
        return 'elective'
    elif mode_str.startswith('3') or 'urgent' in mode_str:
        return 'urgent'
    elif mode_str.startswith('4') or 'emergency' in mode_str or 'emerg' in mode_str:
        return 'emergency'

    return None


def map_asa(asa_val) -> Optional[int]:
    """Map ASA grade to integer (1-5)"""
    if pd.isna(asa_val):
        return None

    asa_str = str(asa_val).strip().upper()

    # Map Roman numerals and numbers
    asa_map = {
        '1': 1, 'I': 1,
        '2': 2, 'II': 2,
        '3': 3, 'III': 3,
        '4': 4, 'IV': 4,
        '5': 5, 'V': 5
    }

    return asa_map.get(asa_str)


def remove_opcs4_subtype(opcs_code: Optional[str]) -> Optional[str]:
    """
    Remove decimal point and sub-type from OPCS-4 code.
    Examples: H33.4 → H33, H07.9 → H07
    """
    if not opcs_code or opcs_code == 'nan' or opcs_code == '':
        return opcs_code

    code_str = str(opcs_code).strip()

    # Remove everything after and including the decimal point
    if '.' in code_str:
        return code_str.split('.')[0]

    return code_str


def map_procedure_name_and_opcs4(proc_name: str, existing_opcs4: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
    """
    Map procedure name to canonical name and OPCS4 code

    Returns:
        Tuple of (canonical_procedure_name, opcs4_code)
    """
    if not proc_name or pd.isna(proc_name) or proc_name == 'nan':
        return None, remove_opcs4_subtype(existing_opcs4)

    proc_clean = proc_name.strip().lower()

    # Comprehensive mapping from source data variations to canonical names and OPCS4 codes
    # Format: source_name_pattern → (canonical_name, default_opcs4_code)
    # IMPORTANT: Order matters - check more specific patterns first
    # NOTE: OPCS codes are base codes only (no decimal sub-types)
    procedure_mapping = {
        # Colorectal procedures (most specific first)
        'extended right hemicolectomy': ('Extended right hemicolectomy', 'H06'),
        'anterior resection': ('Anterior resection of rectum', 'H33'),
        'right hemicolectomy': ('Right hemicolectomy', 'H07'),
        'left hemicolectomy': ('Left hemicolectomy', 'H09'),
        'sigmoid colectomy': ('Sigmoid colectomy', 'H10'),
        'transverse colectomy': ('Transverse colectomy', 'H07'),
        'hartmann': ('Hartmann procedure', 'H33'),
        'aper': ('Abdominoperineal excision of rectum', 'H33'),
        'abdominoperineal': ('Abdominoperineal excision of rectum', 'H33'),
        'subtotal colectomy': ('Subtotal colectomy', 'H08'),
        'total colectomy': ('Total colectomy', 'H09'),
        'proctocolectomy': ('Proctocolectomy', 'H10'),
        'panproctocolectomy': ('Panproctocolectomy', 'H11'),

        # Stoma procedures
        'stoma only': ('Stoma formation', 'H15'),
        'stoma': ('Stoma formation', 'H15'),
        'ileostomy': ('Ileostomy', 'H46'),
        'colostomy': ('Colostomy', 'H47'),
        'closure of stoma': ('Closure of stoma', 'H48'),

        # Endoscopic/minimal access
        'polypectomy': ('Polypectomy', 'H23'),
        'tems': ('Transanal endoscopic microsurgery', 'H41'),
        'trans anal resection': ('Transanal excision of lesion', 'H41'),
        'transanal resection': ('Transanal excision of lesion', 'H41'),

        # Other/palliative
        'stent': ('Colorectal stent insertion', 'H24'),
        'bypass': ('Intestinal bypass', 'H05'),
        'laparotomy only': ('Laparotomy and exploration', 'T30'),
        'laparoscopy only': ('Diagnostic laparoscopy', 'T42'),
        'other': ('Other colorectal procedure', 'H99'),
    }

    # Try to find a match - sort by pattern length (longest first) to check specific patterns before generic ones
    for pattern in sorted(procedure_mapping.keys(), key=len, reverse=True):
        if pattern in proc_clean:
            canonical_name, default_opcs4 = procedure_mapping[pattern]
            # Use existing OPCS4 if available and valid, otherwise use default
            opcs4 = existing_opcs4 if (existing_opcs4 and existing_opcs4 != 'nan' and existing_opcs4 != '') else default_opcs4
            # Remove sub-type from final OPCS code
            return canonical_name, remove_opcs4_subtype(opcs4)

    # If no match found, return cleaned version of original name
    return proc_name.strip(), remove_opcs4_subtype(existing_opcs4)


def map_approach(lap_proc) -> Optional[str]:
    """Map laparoscopic procedure field to approach"""
    if pd.isna(lap_proc):
        return None

    lap_str = str(lap_proc).strip().lower()

    if 'open' in lap_str or lap_str.startswith('1'):
        return 'open'
    elif 'laparoscopic' in lap_str or 'lap' in lap_str or lap_str.startswith('2'):
        return 'laparoscopic'
    elif 'robotic' in lap_str or 'robot' in lap_str or lap_str.startswith('3'):
        return 'robotic'
    elif 'convert' in lap_str or lap_str.startswith('4'):
        return 'converted'

    return None


def map_intent(curative_val) -> Optional[str]:
    """Map curative field to treatment intent"""
    if pd.isna(curative_val):
        return None

    cur_str = str(curative_val).strip().lower()

    if 'curative' in cur_str or cur_str.startswith('1'):
        return 'curative'
    elif 'palliative' in cur_str or cur_str.startswith('2'):
        return 'palliative'

    return None


def map_tnm_stage(stage_val) -> Optional[str]:
    """
    Map TNM stage value to simple number format (matching surgdb)

    Examples: "3", "1", "4a", "0", "x" (lowercase, no prefix)
    Frontend will add the "pT", "pN", "pM" prefix for display

    Args:
        stage_val: The stage value from CSV (can be numeric 0,1,2,3,4)

    Returns:
        Simple stage value: "0", "1", "2", "3", "4", "4a", "4b", "x", "is", etc.
    """
    if pd.isna(stage_val):
        return None

    stage_str = str(stage_val).strip().lower()

    # If already in correct format (just numbers/letters), return as-is
    if stage_str in ['0', '1', '2', '3', '4', '4a', '4b', 'x', 'is']:
        return stage_str

    # Handle uppercase versions
    stage_upper = stage_str.upper()

    # Strip T/N/M prefix if present
    if stage_upper.startswith('T'):
        stage_str = stage_upper[1:].lower()
    elif stage_upper.startswith('N'):
        stage_str = stage_upper[1:].lower()
    elif stage_upper.startswith('M'):
        stage_str = stage_upper[1:].lower()

    # Normalize special cases
    if stage_str == 'tis':
        return 'is'

    # Return cleaned value
    if stage_str in ['0', '1', '2', '3', '4', '4a', '4b', 'x', 'is', '1a', '1b', '2a', '2b']:
        return stage_str

    return None


def map_tumour_site(site_val) -> Optional[str]:
    """
    Map tumour site to clean format matching surgdb

    surgdb uses: sigmoid_colon, ascending_colon, rectum, etc.
    CSV has: "8 Sigmoid Colon", "3 Ascending Colon", "10 Rectum"
    """
    if pd.isna(site_val):
        return None

    site_str = str(site_val).strip().lower()

    # Map from CSV format to surgdb format
    site_map = {
        'caecum': 'caecum',
        '1 caecum': 'caecum',
        'appendix': 'appendix',
        '2 appendix': 'appendix',
        'ascending colon': 'ascending_colon',
        '3 ascending colon': 'ascending_colon',
        'hepatic flexure': 'hepatic_flexure',
        '4 hepatic flexure': 'hepatic_flexure',
        'transverse colon': 'transverse_colon',
        '5 transverse colon': 'transverse_colon',
        'splenic flexure': 'splenic_flexure',
        '6 splenic flexure': 'splenic_flexure',
        'descending colon': 'descending_colon',
        '7 descending colon': 'descending_colon',
        'sigmoid colon': 'sigmoid_colon',
        '8 sigmoid colon': 'sigmoid_colon',
        'recto/sigmoid': 'rectosigmoid_junction',
        '9 recto/sigmoid': 'rectosigmoid_junction',
        'rectum': 'rectum',
        '10 rectum': 'rectum'
    }

    return site_map.get(site_str)


def map_grade(grade_val) -> Optional[str]:
    """
    Map histological grade to clean format matching surgdb

    surgdb uses: g1, g2, g3, g4
    CSV has: "G1", "G2", "2 Other", etc.
    """
    if pd.isna(grade_val):
        return None

    grade_str = str(grade_val).strip().lower()

    # Handle various formats
    if grade_str in ['g1', '1', '1 well', 'well']:
        return 'g1'
    elif grade_str in ['g2', '2', '2 other', 'moderate', 'moderately']:
        return 'g2'
    elif grade_str in ['g3', '3', '3 poor', 'poor', 'poorly']:
        return 'g3'
    elif grade_str in ['g4', '4', 'undifferentiated']:
        return 'g4'

    return None


def map_histology_type(histology_val) -> Optional[str]:
    """
    Map histology type to clean format matching surgdb

    surgdb uses: adenocarcinoma, mucinous_adenocarcinoma, etc.
    CSV has: "1 Adenocarcinoma", "2 Mucinous", etc.
    """
    if pd.isna(histology_val):
        return None

    hist_str = str(histology_val).strip().lower()

    # Map from CSV format to surgdb format
    hist_map = {
        'adenocarcinoma': 'adenocarcinoma',
        '1 adenocarcinoma': 'adenocarcinoma',
        'mucinous': 'mucinous_adenocarcinoma',
        '2 mucinous': 'mucinous_adenocarcinoma',
        'mucinous adenocarcinoma': 'mucinous_adenocarcinoma',
        'signet ring': 'signet_ring_carcinoma',
        'signet ring cell': 'signet_ring_carcinoma',
        'squamous cell': 'squamous_cell_carcinoma',
        'adenosquamous': 'adenosquamous_carcinoma',
        'small cell': 'small_cell_carcinoma',
        'large cell': 'large_cell_carcinoma',
        'undifferentiated': 'undifferentiated_carcinoma',
        'neuroendocrine': 'neuroendocrine_tumour',
        'carcinoid': 'carcinoid_tumour'
    }

    return hist_map.get(hist_str, 'adenocarcinoma')  # Default to adenocarcinoma


# ============================================================================
# COMPREHENSIVE DATA CLEANING MAPPING FUNCTIONS
# Added for complete data quality matching surgdb structure
# ============================================================================

def map_yes_no(value) -> Optional[str]:
    """
    Map various yes/no formats to simple 'yes'/'no'
    Handles: "1 Yes", "2 No", "1", "2", True, False, "Yes", "No"
    """
    if pd.isna(value):
        return None

    val_str = str(value).strip().lower()

    # Handle coded values
    if val_str in ['1', '1 yes', 'yes', 'true', 't', 'y']:
        return 'yes'
    elif val_str in ['2', '2 no', 'no', 'false', 'f', 'n']:
        return 'no'

    return None


def strip_leading_number(value) -> Optional[str]:
    """
    Remove leading category numbers from values
    Examples: "5 Other" → "other", "2 Mucinous" → "mucinous"
    """
    if pd.isna(value):
        return None

    val_str = str(value).strip()

    # Check if starts with digit followed by space
    import re
    match = re.match(r'^\d+\s+(.+)$', val_str)
    if match:
        return match.group(1).lower()

    return val_str.lower()


def map_positive_negative(value) -> Optional[str]:
    """
    Map various positive/negative/uncertain formats
    Handles: "1 Positive", "2 Negative", "3 Uncertain"
    """
    if pd.isna(value):
        return None

    val_str = str(value).strip().lower()

    if val_str in ['1', '1 positive', 'positive', 'pos', '+']:
        return 'positive'
    elif val_str in ['2', '2 negative', 'negative', 'neg', '-']:
        return 'negative'
    elif val_str in ['3', '3 uncertain', 'uncertain', 'unknown']:
        return 'uncertain'

    return None


def map_referral_source(value) -> Optional[str]:
    """
    surgdb uses: 'gp', 'consultant', 'screening', 'emergency', 'other'
    CSV has: "1 GP", "2 Consultant", "3 Screening", "4 Emergency", "5 Other"
    """
    if pd.isna(value):
        return None

    val_str = str(value).strip().lower()

    source_map = {
        '1': 'gp',
        '1 gp': 'gp',
        'gp': 'gp',
        '2': 'consultant',
        '2 consultant': 'consultant',
        'consultant': 'consultant',
        '3': 'screening',
        '3 screening': 'screening',
        'screening': 'screening',
        'bcsp': 'screening',
        '4': 'emergency',
        '4 emergency': 'emergency',
        'emergency': 'emergency',
        'a&e': 'emergency',
        '5': 'other',
        '5 other': 'other',
        'other': 'other'
    }

    return source_map.get(val_str, 'other')


def map_referral_priority(value) -> Optional[str]:
    """
    surgdb uses: 'routine', 'urgent', 'two_week_wait'
    CSV has: "1 Routine", "2 Urgent", "3 Two Week Wait"
    """
    if pd.isna(value):
        return None

    val_str = str(value).strip().lower()

    priority_map = {
        '1': 'routine',
        '1 routine': 'routine',
        'routine': 'routine',
        '2': 'urgent',
        '2 urgent': 'urgent',
        'urgent': 'urgent',
        '3': 'two_week_wait',
        '3 two week wait': 'two_week_wait',
        'two week wait': 'two_week_wait',
        '2ww': 'two_week_wait'
    }

    return priority_map.get(val_str, 'routine')


def map_performance_status(value) -> Optional[int]:
    """
    surgdb uses: integer 0-4 (WHO/ECOG performance status)
    CSV may have: "0", "1", "2", "3", "4" or with descriptions
    """
    if pd.isna(value):
        return None

    val_str = str(value).strip().lower()

    # Extract just the number if present
    import re
    match = re.match(r'^(\d)', val_str)
    if match:
        ps = int(match.group(1))
        if 0 <= ps <= 4:
            return ps

    return None


def map_surgeon_grade(value) -> Optional[str]:
    """
    surgdb uses: 'consultant', 'specialist_registrar', 'other'
    CSV has: "1 Consultant", "2 Specialist Registrar", "3 Other"
    """
    if pd.isna(value):
        return None

    val_str = str(value).strip().lower()

    grade_map = {
        '1': 'consultant',
        '1 consultant': 'consultant',
        'consultant': 'consultant',
        '2': 'specialist_registrar',
        '2 specialist registrar': 'specialist_registrar',
        'specialist registrar': 'specialist_registrar',
        'registrar': 'specialist_registrar',
        'spr': 'specialist_registrar',
        '3': 'other',
        '3 other': 'other',
        'other': 'other'
    }

    return grade_map.get(val_str, 'other')


def map_stoma_type(value) -> Optional[str]:
    """
    surgdb uses: 'ileostomy', 'colostomy', 'none'
    CSV has: "1 Ileostomy", "2 Colostomy", "3 None"
    """
    if pd.isna(value):
        return None

    val_str = str(value).strip().lower()

    stoma_map = {
        '1': 'ileostomy',
        '1 ileostomy': 'ileostomy',
        'ileostomy': 'ileostomy',
        '2': 'colostomy',
        '2 colostomy': 'colostomy',
        'colostomy': 'colostomy',
        '3': 'none',
        '3 none': 'none',
        'none': 'none',
        'no': 'none'
    }

    return stoma_map.get(val_str, 'none')


def map_procedure_type(value) -> Optional[str]:
    """
    surgdb uses: 'resection', 'stoma_only', 'other'
    CSV has: "1 Resection", "2 Stoma Only", "3 Other"
    """
    if pd.isna(value):
        return None

    val_str = str(value).strip().lower()

    proc_map = {
        '1': 'resection',
        '1 resection': 'resection',
        'resection': 'resection',
        '2': 'stoma_only',
        '2 stoma only': 'stoma_only',
        'stoma only': 'stoma_only',
        'stoma': 'stoma_only',
        '3': 'other',
        '3 other': 'other',
        'other': 'other'
    }

    return proc_map.get(val_str, 'other')


def map_bowel_prep(value) -> Optional[str]:
    """
    surgdb uses: 'full', 'enema_only', 'none'
    CSV has: "1 Full", "2 Enema Only", "3 None"
    """
    if pd.isna(value):
        return None

    val_str = str(value).strip().lower()

    prep_map = {
        '1': 'full',
        '1 full': 'full',
        'full': 'full',
        '2': 'enema_only',
        '2 enema only': 'enema_only',
        'enema only': 'enema_only',
        'enema': 'enema_only',
        '3': 'none',
        '3 none': 'none',
        'none': 'none'
    }

    return prep_map.get(val_str, 'none')


def map_extraction_site(value) -> Optional[str]:
    """
    surgdb uses: 'pfannenstiel', 'midline', 'extended_port', 'other'
    CSV has: "1 Pfannenstiel", "2 Midline", "3 Extended Port", "4 Other"
    """
    if pd.isna(value):
        return None

    val_str = str(value).strip().lower()

    extraction_map = {
        '1': 'pfannenstiel',
        '1 pfannenstiel': 'pfannenstiel',
        'pfannenstiel': 'pfannenstiel',
        '2': 'midline',
        '2 midline': 'midline',
        'midline': 'midline',
        '3': 'extended_port',
        '3 extended port': 'extended_port',
        'extended port': 'extended_port',
        '4': 'other',
        '4 other': 'other',
        'other': 'other'
    }

    return extraction_map.get(val_str, 'other')


def map_treatment_intent(value) -> Optional[str]:
    """
    surgdb uses: 'curative', 'palliative'
    CSV has: "1 Curative", "2 Palliative" or boolean
    """
    if pd.isna(value):
        return None

    val_str = str(value).strip().lower()

    if val_str in ['1', '1 curative', 'curative', 'true', 't']:
        return 'curative'
    elif val_str in ['2', '2 palliative', 'palliative', 'false', 'f']:
        return 'palliative'

    return None


def map_crm_status(value) -> Optional[str]:
    """
    surgdb uses: 'positive', 'negative', 'uncertain'
    CSV has: "1 Positive", "2 Negative", "3 Uncertain"
    User requested: yes/no format
    """
    if pd.isna(value):
        return None

    val_str = str(value).strip().lower()

    # Map to yes/no as user requested
    if val_str in ['1', '1 positive', 'positive', 'pos', '+']:
        return 'yes'
    elif val_str in ['2', '2 negative', 'negative', 'neg', '-']:
        return 'no'
    elif val_str in ['3', '3 uncertain', 'uncertain', 'unknown']:
        return 'uncertain'

    return None


def map_invasion_status(value) -> Optional[str]:
    """
    For vascular, lymphatic, perineural invasion fields
    surgdb uses: 'present', 'absent', 'uncertain'
    CSV has: "1 Present", "2 Absent", "3 Uncertain"
    """
    if pd.isna(value):
        return None

    val_str = str(value).strip().lower()

    if val_str in ['1', '1 present', 'present', 'yes', 'positive']:
        return 'present'
    elif val_str in ['2', '2 absent', 'absent', 'no', 'negative']:
        return 'absent'
    elif val_str in ['3', '3 uncertain', 'uncertain', 'unknown']:
        return 'uncertain'

    return None


def map_resection_grade(value) -> Optional[str]:
    """
    surgdb uses: 'r0', 'r1', 'r2'
    CSV has: "1 R0", "2 R1", "3 R2" or just "R0", "R1", "R2"
    """
    if pd.isna(value):
        return None

    val_str = str(value).strip().lower()

    if val_str in ['1', '1 r0', 'r0', '0']:
        return 'r0'
    elif val_str in ['2', '2 r1', 'r1', '1']:
        return 'r1'
    elif val_str in ['3', '3 r2', 'r2', '2']:
        return 'r2'

    return None


def map_treatment_timing(value) -> Optional[str]:
    """
    surgdb uses: 'neoadjuvant', 'adjuvant', 'palliative'
    CSV has: "1 Neoadjuvant", "2 Adjuvant", "3 Palliative"
    """
    if pd.isna(value):
        return None

    val_str = str(value).strip().lower()

    timing_map = {
        '1': 'neoadjuvant',
        '1 neoadjuvant': 'neoadjuvant',
        'neoadjuvant': 'neoadjuvant',
        'neo': 'neoadjuvant',
        'pre': 'neoadjuvant',
        '2': 'adjuvant',
        '2 adjuvant': 'adjuvant',
        'adjuvant': 'adjuvant',
        'post': 'adjuvant',
        '3': 'palliative',
        '3 palliative': 'palliative',
        'palliative': 'palliative'
    }

    return timing_map.get(val_str)


def map_rt_technique(value) -> Optional[str]:
    """
    surgdb uses: 'long_course', 'short_course', 'contact'
    CSV has: "1 Long Course", "2 Short Course", "3 Contact"
    """
    if pd.isna(value):
        return None

    val_str = str(value).strip().lower()

    technique_map = {
        '1': 'long_course',
        '1 long course': 'long_course',
        'long course': 'long_course',
        'long': 'long_course',
        '2': 'short_course',
        '2 short course': 'short_course',
        'short course': 'short_course',
        'short': 'short_course',
        '3': 'contact',
        '3 contact': 'contact',
        'contact': 'contact'
    }

    return technique_map.get(val_str)


def map_followup_modality(value) -> Optional[str]:
    """
    surgdb uses: 'clinic', 'telephone', 'other'
    CSV has: "1 Clinic", "2 Telephone", "3 Other"
    """
    if pd.isna(value):
        return None

    val_str = str(value).strip().lower()

    modality_map = {
        '1': 'clinic',
        '1 clinic': 'clinic',
        'clinic': 'clinic',
        'face to face': 'clinic',
        '2': 'telephone',
        '2 telephone': 'telephone',
        'telephone': 'telephone',
        'phone': 'telephone',
        '3': 'other',
        '3 other': 'other',
        'other': 'other'
    }

    return modality_map.get(val_str, 'other')


def map_lead_clinician(value) -> Optional[str]:
    """
    surgdb stores as string: "First_Name Surname"
    Ensure we never store ObjectId, always store name as string
    """
    if pd.isna(value):
        return None

    val_str = str(value).strip()

    # If it looks like an ObjectId (24 hex chars), reject it
    if len(val_str) == 24 and all(c in '0123456789abcdef' for c in val_str.lower()):
        return None  # Don't store ObjectId

    # Return clean name string
    return val_str if val_str else None


def determine_surgical_approach(row) -> Optional[str]:
    """
    Determine surgical approach from multiple fields
    User requirements:
    - Use LapProc with cleaned text
    - Set "converted" if LapType contains "converted to open"
    - Set "robotic" if Robotic field is true
    """
    # Check if robotic first
    if map_yes_no(row.get('Robotic')) == 'yes':
        return 'robotic'

    # Check if converted to open
    lap_type = str(row.get('LapType', '')).lower()
    if 'converted' in lap_type and 'open' in lap_type:
        return 'converted'

    # Otherwise use LapProc mapping
    return map_approach(row.get('LapProc'))


def is_defunctioning_stoma(row) -> Optional[str]:
    """
    User requirement: Defunctioning/Protective stoma if anastomosis true AND stoma performed
    """
    anastomosis = map_yes_no(row.get('Anastom'))
    stoma = map_yes_no(row.get('Stoma'))

    if anastomosis == 'yes' and stoma == 'yes':
        return 'yes'
    elif stoma == 'yes':
        return 'no'  # Stoma but no anastomosis = not defunctioning
    else:
        return None  # No stoma


def parse_complications(row: pd.Series) -> List[Dict[str, Any]]:
    """Parse complication fields into structured list"""
    complications = []

    # Anastomotic leak
    if row.get('MJ_Leak') or row.get('MI_Leak'):
        complications.append({
            'type': 'anastomotic_leak',
            'severity': 'major' if row.get('MJ_Leak') else 'minor',
            'clavien_dindo_grade': 'IIIb' if row.get('MJ_Leak') else 'II'
        })

    # Bleeding
    if row.get('MJ_Bleed') or row.get('MI_Bleed'):
        complications.append({
            'type': 'bleeding',
            'severity': 'major' if row.get('MJ_Bleed') else 'minor',
            'clavien_dindo_grade': 'IIIb' if row.get('MJ_Bleed') else 'II'
        })

    # Abscess
    if row.get('MI_Abs'):
        complications.append({
            'type': 'abscess',
            'severity': 'minor',
            'clavien_dindo_grade': 'II'
        })

    # Obstruction
    if row.get('MI_Obst'):
        complications.append({
            'type': 'obstruction',
            'severity': 'minor',
            'clavien_dindo_grade': 'II'
        })

    # Wound infection
    if row.get('WI'):
        complications.append({
            'type': 'wound_infection',
            'severity': 'minor',
            'clavien_dindo_grade': 'I'
        })

    # Chest infection
    if row.get('CI'):
        complications.append({
            'type': 'chest_infection',
            'severity': 'minor',
            'clavien_dindo_grade': 'II'
        })

    # Cardiac
    if row.get('Cardio'):
        complications.append({
            'type': 'cardiac',
            'severity': 'major',
            'clavien_dindo_grade': 'IV'
        })

    # UTI
    if row.get('UTI'):
        complications.append({
            'type': 'uti',
            'severity': 'minor',
            'clavien_dindo_grade': 'I'
        })

    return complications


# ============================================================================
# IMPORT FUNCTIONS
# ============================================================================

def import_patients(db, csv_path: str, stats: Dict) -> Dict[str, str]:
    """
    Import patients from patients.csv
    Returns mapping: hosp_no → patient_id
    """
    print("\n" + "=" * 80)
    print("IMPORTING PATIENTS")
    print("=" * 80)

    df = pd.read_csv(csv_path, low_memory=False)
    print(f"Loaded {len(df)} patient records from CSV")

    patients_collection = db.patients
    hosp_no_to_patient_id = {}
    deceased_patients = {}

    for idx, row in df.iterrows():
        hosp_no = str(row.get('Hosp_No', '')).strip()
        pas_no = str(row.get('PAS_No', '')).strip()

        if not hosp_no or hosp_no == 'nan':
            stats['patients_skipped_no_hosp_no'] += 1
            continue

        # Generate patient_id
        patient_id = generate_patient_id(hosp_no)
        hosp_no_to_patient_id[hosp_no] = patient_id

        # Check if patient already exists (INSERT-ONLY mode)
        existing = patients_collection.find_one({'patient_id': patient_id})
        if existing:
            stats['patients_skipped_existing'] += 1
            # Still track deceased dates for mortality calculation
            deceased_date = parse_date(row.get('DeathDat'))
            if deceased_date:
                deceased_patients[patient_id] = deceased_date
            continue

        # Parse demographics
        dob = parse_dob(row.get('P_DOB'))
        deceased_date = parse_date(row.get('DeathDat'))

        if deceased_date:
            deceased_patients[patient_id] = deceased_date

        # Clean NHS number - remove decimal if present
        nhs_number = row.get('NHS_No')
        if pd.notna(nhs_number):
            nhs_str = str(int(float(nhs_number)))  # Convert to int first to remove decimal
            nhs_number = nhs_str if nhs_str else None
        else:
            nhs_number = None

        patient_doc = {
            'patient_id': patient_id,
            'mrn': pas_no if pas_no and pas_no != 'nan' else None,
            'nhs_number': nhs_number,
            'hospital_number': hosp_no,
            'demographics': {
                'first_name': str(row.get('Forename', '')).strip() or None,
                'last_name': str(row.get('Surname', '')).strip() or None,
                'date_of_birth': dob,
                'age': calculate_age(dob),
                'gender': parse_gender(row.get('Sex')),
                'ethnicity': 'Z',  # Not stated - as per user decision
                'deceased_date': deceased_date,
                'bmi': float(row.get('BMI')) if pd.notna(row.get('BMI')) else None,
                'weight_kg': float(row.get('Weight')) if pd.notna(row.get('Weight')) else None,
                'height_cm': convert_height_to_cm(row.get('Height'))  # Converts meters to cm if < 10
            },
            'contact': {
                'postcode': str(row.get('Postcode', '')).strip() or None
            },
            'medical_history': {
                'family_history': bool(row.get('Fam_Hist')),
                'family_history_positive': str(row.get('Fam_Hist_positive', '')).strip() or None
            },
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        patients_collection.insert_one(patient_doc)
        stats['patients_inserted'] += 1

        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{len(df)} patients...")

    print(f"✅ Patients imported: {stats['patients_inserted']} inserted, {stats['patients_skipped_existing']} skipped (existing)")
    print(f"   Deceased patients tracked: {len(deceased_patients)}")

    return hosp_no_to_patient_id, deceased_patients


def import_episodes(db, csv_path: str, hosp_no_to_patient_id: Dict, stats: Dict, clinician_mapping: Dict = None) -> Dict:
    """
    Import episodes from tumours.csv (referral/MDT data)
    Returns mapping structures for linking

    Args:
        clinician_mapping: Dict mapping surgeon names to clinician IDs (optional)
    """
    print("\n" + "=" * 80)
    print("IMPORTING EPISODES (Referral/MDT Data)")
    print("=" * 80)

    df_tumours = pd.read_csv(csv_path, low_memory=False)
    print(f"Loaded {len(df_tumours)} tumour records from CSV (will create episodes)")

    # Read patient CSV to get SurgFirm for lead_clinician
    patient_csv_path = csv_path.replace('tumours.csv', 'tblPatient.csv')
    df_patient = pd.read_csv(patient_csv_path, encoding='latin1', low_memory=False)

    # Join tumours with patient data on Hosp_No to get SurgFirm
    df = df_tumours.merge(df_patient[['Hosp_No', 'SurgFirm']], on='Hosp_No', how='left')
    print(f"Joined with patient data - {df['SurgFirm'].notna().sum()} episodes have SurgFirm")

    episodes_collection = db.episodes
    episode_mapping = {}  # (patient_id, TumSeqno) → episode_id
    episode_counter = {}  # patient_id → count (for sequential numbering)

    for idx, row in df.iterrows():
        hosp_no = str(row.get('Hosp_No', '')).strip()
        if not hosp_no or hosp_no == 'nan':
            stats['episodes_skipped_no_patient'] += 1
            continue

        patient_id = hosp_no_to_patient_id.get(hosp_no)
        if not patient_id:
            stats['episodes_skipped_no_patient'] += 1
            continue

        tum_seqno = row.get('TumSeqno', 0)

        # Generate sequential episode_id per patient
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

        # If referral_date is missing, use diagnosis_date as fallback
        if not referral_date and diagnosis_date:
            referral_date = diagnosis_date

        # If first_seen_date is missing, use diagnosis_date as fallback
        if not first_seen_date and diagnosis_date:
            first_seen_date = diagnosis_date

        # Treatment intent from careplan
        treatment_intent_val = str(row.get('careplan', '')).strip().lower()
        treatment_intent = None
        if 'curative' in treatment_intent_val:
            treatment_intent = 'curative'
        elif 'palliative' in treatment_intent_val:
            treatment_intent = 'palliative'

        # Treatment plan from plan_treat - strip numeric prefix (e.g., "01 surgery" -> "surgery")
        treatment_plan_raw = str(row.get('plan_treat', '')).strip()
        treatment_plan = strip_numeric_prefix(treatment_plan_raw) if treatment_plan_raw and treatment_plan_raw != 'nan' else None

        # Lead clinician from SurgFirm (patient's surgeon firm)
        # Match against clinicians if mapping available, otherwise store as text
        lead_clinician = None
        surgfirm = str(row.get('SurgFirm', '')).strip()
        if surgfirm and surgfirm != 'nan':
            if clinician_mapping:
                # Try to match to clinician ID
                clinician_id, display_name = match_surgeon_to_clinician(surgfirm, clinician_mapping)
                if clinician_id:
                    lead_clinician = clinician_id
                else:
                    # Store as free text if no match
                    lead_clinician = display_name or surgfirm.title()
            else:
                # No clinician mapping available, store as text
                lead_clinician = surgfirm.title()

        episode_doc = {
            'episode_id': episode_id,
            'patient_id': patient_id,
            'condition_type': 'cancer',
            'cancer_type': 'bowel',
            'referral_date': referral_date,
            'referral_source': map_referral_source(row.get('RefType')),  # CLEANED: gp/consultant/screening/emergency/other
            'referral_priority': map_referral_priority(row.get('Priority')),  # CLEANED: routine/urgent/two_week_wait
            'first_seen_date': first_seen_date,
            'provider_first_seen': 'RHU',  # Royal Hospital for Neurodisability (user specified)
            'mdt_discussion_date': None,  # Populated from surgery table later
            'mdt_team': str(row.get('Mdt_org', '')).strip() or None,
            'mdt_meeting_type': 'Colorectal MDT',  # User specified
            'treatment_intent': treatment_intent,  # From careplan field
            'treatment_plan': treatment_plan,  # From plan_treat field
            'cns_involved': map_yes_no(row.get('CNS')),  # CLEANED: yes/no
            'performance_status': map_performance_status(row.get('performance')),  # CLEANED: integer 0-4
            'episode_status': 'active',
            'lead_clinician': lead_clinician,  # From SurgFirm (patient's consultant/firm)
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


def import_tumours(db, csv_path: str, hosp_no_to_patient_id: Dict, episode_mapping: Dict, stats: Dict) -> Dict:
    """
    Import tumours from tumours.csv (diagnosis/staging data)
    Returns mapping of (patient_id, TumSeqno) → tumour_id for pathology matching
    """
    print("\n" + "=" * 80)
    print("IMPORTING TUMOURS (Diagnosis/Staging Data)")
    print("=" * 80)

    df = pd.read_csv(csv_path, low_memory=False)
    print(f"Loaded {len(df)} tumour records from CSV")

    tumours_collection = db.tumours
    tumour_counter = {}  # patient_id → count (for sequential numbering)
    tumour_mapping = {}  # (patient_id, TumSeqno) → tumour_id (for pathology matching)

    for idx, row in df.iterrows():
        hosp_no = str(row.get('Hosp_No', '')).strip()
        if not hosp_no or hosp_no == 'nan':
            stats['tumours_skipped_no_patient'] += 1
            continue

        patient_id = hosp_no_to_patient_id.get(hosp_no)
        if not patient_id:
            stats['tumours_skipped_no_patient'] += 1
            continue

        tum_seqno = row.get('TumSeqno', 0)
        episode_id = episode_mapping.get((patient_id, tum_seqno))

        if not episode_id:
            stats['tumours_skipped_no_episode'] += 1
            continue

        # Generate sequential tumour_id per patient
        tumour_counter[patient_id] = tumour_counter.get(patient_id, 0) + 1
        tumour_id = generate_tumour_id(patient_id, tumour_counter[patient_id])

        # Check if tumour already exists
        existing = tumours_collection.find_one({'tumour_id': tumour_id})
        if existing:
            stats['tumours_skipped_existing'] += 1
            continue

        tumour_doc = {
            'tumour_id': tumour_id,
            'patient_id': patient_id,
            'episode_id': episode_id,
            'tumour_type': 'primary',
            'diagnosis_date': parse_date(row.get('Dt_Diag')),  # COSD CR2030
            'icd10_code': str(row.get('TumICD10', '')).strip() or None,  # COSD CR0370
            'site': map_tumour_site(row.get('TumSite')),  # Clean format: sigmoid_colon, etc.
            'tnm_version': '8',

            # Clinical TNM staging (COSD CR0520/0540/0560) - stored as simple numbers
            'clinical_t': map_tnm_stage(row.get('preTNM_T')),  # "3", "1", "4a", etc.
            'clinical_n': map_tnm_stage(row.get('preTNM_N')),
            'clinical_m': map_tnm_stage(row.get('preTNM_M')),

            # Pathological staging (populated from pathology table later)
            'pathological_t': None,
            'pathological_n': None,
            'pathological_m': None,

            # Rectal cancer specific (CO5160)
            # TODO: This should map to a rectal-specific field, not 'Height' - appears to be a data mapping error
            'distance_from_anal_verge_cm': safe_to_float(row.get('Height')),

            # Imaging results
            'imaging_results': {
                'ct_chest': {
                    'result': map_yes_no(row.get('CT_pneumo')),  # CLEANED: yes/no
                    'date': parse_date(row.get('Dt_CT_pneumo'))
                },
                'ct_abdomen': {
                    'result': map_yes_no(row.get('CT_Abdo')),  # CLEANED: yes/no
                    'date': parse_date(row.get('Dt_CT_Abdo'))
                },
                'mri_primary': {
                    'date': parse_date(row.get('Dt_MRI1')),
                    't_stage': map_tnm_stage(row.get('MRI1_T')),  # CLEANED: simple numbers
                    'n_stage': map_tnm_stage(row.get('MRI1_N')),  # CLEANED: simple numbers
                    'crm_status': map_crm_status(row.get('MRI1_CRM')),  # CLEANED: yes/no/uncertain
                    'crm_distance_mm': float(row.get('MRI1_dist')) if pd.notna(row.get('MRI1_dist')) else None,
                    'emvi': map_yes_no(row.get('EMVI'))  # CLEANED: yes/no
                }
            },

            # Metastases
            'distant_metastases': {
                'liver': map_yes_no(row.get('DM_Liver')),  # CLEANED: yes/no
                'lung': map_yes_no(row.get('DM_Lung')),  # CLEANED: yes/no
                'bone': map_yes_no(row.get('DM_Bone')),  # CLEANED: yes/no
                'other': map_yes_no(row.get('DM_Other'))  # CLEANED: yes/no
            },

            # Screening
            'screening': {
                'screening_programme': map_yes_no(row.get('BCSP')),  # CLEANED: yes/no
                'screened': map_yes_no(row.get('Screened'))  # CLEANED: yes/no
            },

            # Synchronous tumors
            'synchronous': map_yes_no(row.get('Sync')),  # CLEANED: yes/no
            'synchronous_description': str(row.get('TumSync', '')).strip() or None,

            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        tumours_collection.insert_one(tumour_doc)
        stats['tumours_inserted'] += 1

        # Store mapping for pathology import
        tumour_mapping[(patient_id, tum_seqno)] = tumour_id

        # Update episode with tumour_id
        db.episodes.update_one(
            {'episode_id': episode_id},
            {'$push': {'tumour_ids': tumour_id}}
        )

        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{len(df)} tumours...")

    print(f"✅ Tumours imported: {stats['tumours_inserted']} inserted, {stats['tumours_skipped_existing']} skipped")

    return tumour_mapping


def import_treatments_surgery(db, csv_path: str, hosp_no_to_patient_id: Dict, episode_mapping: Dict, clinician_mapping: Dict, stats: Dict):
    """
    Import surgical treatments from treatments_surgery.csv

    Args:
        db: Database connection
        csv_path: Path to treatments_surgery.csv
        hosp_no_to_patient_id: Hospital number to patient_id mapping
        episode_mapping: Episode mapping
        clinician_mapping: Surgeon name to clinician_id mapping
        stats: Statistics dictionary
    """
    print("\n" + "=" * 80)
    print("IMPORTING SURGICAL TREATMENTS")
    print("=" * 80)

    df = pd.read_csv(csv_path, low_memory=False)
    print(f"Loaded {len(df)} surgery records from CSV")

    treatments_collection = db.treatments
    treatment_counter = {}  # patient_id → count

    for idx, row in df.iterrows():
        hosp_no = str(row.get('Hosp_No', '')).strip()
        if not hosp_no or hosp_no == 'nan':
            stats['treatments_skipped_no_patient'] += 1
            continue

        patient_id = hosp_no_to_patient_id.get(hosp_no)
        if not patient_id:
            stats['treatments_skipped_no_patient'] += 1
            continue

        # Get tumour sequence to find episode
        tum_seqno = row.get('TumSeqNo', 0)
        episode_id = episode_mapping.get((patient_id, tum_seqno))

        # Generate treatment_id
        treatment_counter[patient_id] = treatment_counter.get(patient_id, 0) + 1
        treatment_id = generate_treatment_id(patient_id, treatment_counter[patient_id])

        # Check if treatment already exists by surgery date
        surgery_date = parse_date(row.get('Surgery'))
        if surgery_date:
            existing = treatments_collection.find_one({
                'patient_id': patient_id,
                'treatment_date': surgery_date,
                'treatment_type': 'surgery'
            })
            if existing:
                stats['treatments_skipped_existing'] += 1
                continue

        # Calculate length of stay
        discharge_date = parse_date(row.get('Date_Dis'))
        los = None
        if surgery_date and discharge_date:
            try:
                surg_dt = datetime.strptime(surgery_date, '%Y-%m-%d')
                disc_dt = datetime.strptime(discharge_date, '%Y-%m-%d')
                los = (disc_dt - surg_dt).days
            except:
                pass

        # Parse complications
        complications = parse_complications(row)

        # Map procedure name to canonical name and OPCS4 code
        proc_name_raw = str(row.get('ProcName', '')).strip()
        proc_name_cleaned = strip_numeric_prefix(proc_name_raw) if proc_name_raw and proc_name_raw != 'nan' else None
        existing_opcs4 = str(row.get('OPCS4', '')).strip() if pd.notna(row.get('OPCS4')) else None
        canonical_procedure, mapped_opcs4 = map_procedure_name_and_opcs4(proc_name_cleaned, existing_opcs4)

        treatment_doc = {
            'treatment_id': treatment_id,
            'patient_id': patient_id,
            'episode_id': episode_id,
            'treatment_type': 'surgery',
            'treatment_date': surgery_date,  # COSD CR0710
            'treatment_intent': map_treatment_intent(row.get('Curative')),  # CLEANED: curative/palliative

            # COSD mandatory fields
            'opcs4_code': mapped_opcs4,  # CR0720 - Mapped from procedure or existing code
            'asa_score': map_asa(row.get('ASA')),  # CR6010
            'provider_organisation': 'Portsmouth Hospitals University NHS Trust',  # CR1450 - COSD Provider Organisation

            # Patient vitals at time of treatment
            'height_cm': convert_height_to_cm(row.get('Height')),  # Converts meters to cm if < 10
            'weight_kg': float(row.get('Weight')) if pd.notna(row.get('Weight')) else None,
            'bmi': float(row.get('BMI')) if pd.notna(row.get('BMI')) else None,

            'classification': {
                'urgency': map_urgency(row.get('ModeOp')),  # CLEANED: elective/urgent/emergency
                'approach': determine_surgical_approach(row),  # Improved logic for approach
            },

            'procedure': {
                # Canonical procedure name with numeric prefix stripped and mapped to standard
                'primary_procedure': canonical_procedure,
                'procedure_type': map_procedure_type(row.get('ProcType')),  # CLEANED: resection/stoma_only/other
                'resection_performed': map_yes_no(row.get('ProcResect')),  # CLEANED: yes/no
                'robotic_surgery': map_yes_no(row.get('Robotic')),  # CLEANED: yes/no
                'conversion_to_open': map_yes_no(row.get('Convert')),  # CLEANED: yes/no
                'anterior_resection_type': str(row.get('AR_high_low', '')).strip() or None  # User requested
            },

            'perioperative_timeline': {
                'admission_date': surgery_date,  # Default to surgery date
                'surgery_date': surgery_date,
                'operation_duration_minutes': int(row.get('Total_op_time')) if pd.notna(row.get('Total_op_time')) else None,
                'discharge_date': discharge_date,
                'length_of_stay_days': los
            },

            'team': {
                'primary_surgeon': None,  # Will be set below with clinician matching
                'primary_surgeon_text': None,  # Text name from CSV
                'surgeon_grade': map_surgeon_grade(row.get('SurGrad')),  # CLEANED: consultant/specialist_registrar/other
                'assistant_surgeons': [],  # Will be populated below
                'assistant_surgeons_text': [],  # Text names from CSV
                'anesthetist_grade': map_surgeon_grade(row.get('AneGrad')),  # CLEANED: consultant/specialist_registrar/other
                'surgical_fellow': str(row.get('SurgFellow', '')).strip() or None
            },

            'intraoperative': {
                'stoma_created': map_yes_no(row.get('Stoma')),  # CLEANED: yes/no
                'stoma_type': map_stoma_type(row.get('StomDone')),  # USER FIX: Use StomDone not StomType
                'stoma_closure_date': parse_date(row.get('DatClose')),
                'defunctioning_stoma': is_defunctioning_stoma(row),  # User requested: if anastomosis AND stoma
                'anastomosis_performed': map_yes_no(row.get('Anastom')),  # CLEANED: yes/no
                'anastomosis_height_cm': float(row.get('Hgt_anast')) if pd.notna(row.get('Hgt_anast')) else None,
                'laparoscopic_duration_minutes': int(row.get('Lap_op_time')) if pd.notna(row.get('Lap_op_time')) else None,
                'docking_time_minutes': int(row.get('Dock_time')) if pd.notna(row.get('Dock_time')) else None,
                'blood_loss_ml': safe_to_int(row.get('bl_loss_ mm')),
                'bowel_prep': map_bowel_prep(row.get('Bowel_prep')),  # CLEANED: full/enema_only/none
                'thromboprophylaxis': str(row.get('ThromboP', '')).strip() or None,
                'antibiotic_prophylaxis': str(row.get('AntiProp', '')).strip() or None,
                'extraction_site': map_extraction_site(row.get('extraction_site')),  # CLEANED: pfannenstiel/midline/extended_port/other
                'extraction_size_cm': safe_to_float(row.get('extraction_meas_cm')),
                'previous_abdominal_surgery': map_yes_no(row.get('prev_ab_surg_YN'))  # CLEANED: yes/no
            },

            'postoperative_events': {
                'return_to_theatre': {
                    'occurred': map_yes_no(row.get('re_op'))  # CLEANED: yes/no - User requested
                },
                'complications': complications,
                'post_op_complications': str(row.get('Post_Op', '')).strip() or None,  # User requested: Post_Op field
                'post_op_ileus': map_yes_no(row.get('PO_ileus')),  # CLEANED: yes/no
                'post_op_ct_collection': map_yes_no(row.get('PO_CT_coll'))  # CLEANED: yes/no
            },

            'outcomes': {
                'readmission_30day': map_yes_no(row.get('Post_IP')),  # User requested: Use Post_IP field
                'return_to_theatre': map_yes_no(row.get('re_op')),  # Return to theatre flag
                'mortality_30day': False,  # Calculated later
                'mortality_90day': False   # Calculated later
            },

            # Clinical trials
            'clinical_trial': {
                'enrolled': map_yes_no(row.get('Clin_Trial')),  # CLEANED: yes/no
                'trial_name': str(row.get('ClinTrial_name', '')).strip() or None
            },

            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        # Match primary surgeon to clinician
        surgeon_name = str(row.get('Surgeon', '')).strip()
        if surgeon_name and surgeon_name != 'nan':
            clinician_id, surgeon_text = match_surgeon_to_clinician(surgeon_name, clinician_mapping)
            treatment_doc['team']['primary_surgeon'] = clinician_id
            treatment_doc['team']['primary_surgeon_text'] = surgeon_text

        # Match assistant surgeons to clinicians
        assistant_surgeons = []
        assistant_surgeons_text = []

        for assistant_field in ['Assistnt', 'Assistn2']:
            assistant_name = str(row.get(assistant_field, '')).strip()
            if assistant_name and assistant_name != 'nan':
                clinician_id, assistant_text = match_surgeon_to_clinician(assistant_name, clinician_mapping)
                if clinician_id:
                    assistant_surgeons.append(clinician_id)
                assistant_surgeons_text.append(assistant_text)

        treatment_doc['team']['assistant_surgeons'] = assistant_surgeons
        treatment_doc['team']['assistant_surgeons_text'] = assistant_surgeons_text

        treatments_collection.insert_one(treatment_doc)
        stats['treatments_inserted'] += 1

        # Update episode with treatment_id, lead_clinician, and no_treatment
        if episode_id:
            update_fields = {'$push': {'treatment_ids': treatment_id}}

            # Set lead_clinician from primary surgeon (FALLBACK ONLY)
            # Primary source is SurgFirm from patient record (set during episode import)
            # This only sets lead_clinician if SurgFirm was not available
            primary_surgeon_text = treatment_doc['team'].get('primary_surgeon_text')
            clinician_id = treatment_doc['team'].get('primary_surgeon')

            if primary_surgeon_text:
                # Only set if episode doesn't already have a lead_clinician (from SurgFirm)
                episode = db.episodes.find_one({'episode_id': episode_id})
                if episode and not episode.get('lead_clinician'):
                    # If we matched to a clinician in the admin table, use that
                    if clinician_id:
                        # Store the clinician ID (it's already matched)
                        update_fields.setdefault('$set', {})['lead_clinician'] = clinician_id
                    else:
                        # Fallback to free text from original database
                        cleaned_text = map_lead_clinician(primary_surgeon_text)
                        if cleaned_text:
                            update_fields.setdefault('$set', {})['lead_clinician'] = cleaned_text

            # Set no_treatment from NoSurg field
            no_surg = row.get('NoSurg')
            if pd.notna(no_surg):
                no_treatment = map_yes_no(no_surg)
                update_fields.setdefault('$set', {})['no_treatment'] = no_treatment

            db.episodes.update_one(
                {'episode_id': episode_id},
                update_fields
            )

        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{len(df)} treatments...")

    print(f"✅ Treatments imported: {stats['treatments_inserted']} inserted, {stats['treatments_skipped_existing']} skipped")


def import_pathology(db, csv_path: str, hosp_no_to_patient_id: Dict, tumour_mapping: Dict, stats: Dict):
    """
    Import pathology data from pathology.csv
    Updates existing tumour records with pathological staging

    Args:
        db: Database connection
        csv_path: Path to pathology.csv
        hosp_no_to_patient_id: Hospital number to patient_id mapping
        tumour_mapping: (patient_id, TumSeqno) → tumour_id mapping
        stats: Statistics dictionary
    """
    print("\n" + "=" * 80)
    print("IMPORTING PATHOLOGY DATA")
    print("=" * 80)

    df = pd.read_csv(csv_path, low_memory=False)
    print(f"Loaded {len(df)} pathology records from CSV")

    tumours_collection = db.tumours

    for idx, row in df.iterrows():
        hosp_no = str(row.get('Hosp_No', '')).strip()
        if not hosp_no or hosp_no == 'nan':
            stats['pathology_skipped_no_patient'] += 1
            continue

        patient_id = hosp_no_to_patient_id.get(hosp_no)
        if not patient_id:
            stats['pathology_skipped_no_patient'] += 1
            continue

        # Find matching tumour using the mapping
        tum_seqno = row.get('TumSeqNo', 0)
        tumour_id = tumour_mapping.get((patient_id, tum_seqno))

        if not tumour_id:
            stats['pathology_skipped_no_tumour'] += 1
            continue

        # Update tumour with pathology data (matching surgdb format)
        pathology_update = {
            # Pathological TNM staging - stored as simple numbers ("3", "1", "4a", etc.)
            'pathological_t': map_tnm_stage(row.get('TNM_Tumr')),  # pCR0910
            'pathological_n': map_tnm_stage(row.get('TNM_Nods')),  # pCR0920
            'pathological_m': map_tnm_stage(row.get('TNM_Mets')),  # pCR0930

            # Grade - clean format (g1, g2, g3, g4)
            'grade': map_grade(row.get('HistGrad')),

            # Histology type - clean format (adenocarcinoma, mucinous_adenocarcinoma, etc.)
            'histology_type': map_histology_type(row.get('HistType')),

            'size_mm': float(row.get('MaxDiam')) if pd.notna(row.get('MaxDiam')) else None,

            'lymph_nodes_examined': int(row.get('NoLyNoF')) if pd.notna(row.get('NoLyNoF')) else None,  # pCR0890
            'lymph_nodes_positive': int(row.get('NoLyNoP')) if pd.notna(row.get('NoLyNoP')) else None,  # pCR0900

            'lymphovascular_invasion': map_invasion_status(row.get('VasInv')),  # CLEANED: present/absent/uncertain
            'perineural_invasion': map_invasion_status(row.get('Perineural')),  # CLEANED: present/absent/uncertain

            'crm_status': map_crm_status(row.get('Mar_Cir')),  # CLEANED: yes/no/uncertain (pCR1150)
            'crm_distance_mm': float(row.get('Dist_Cir')) if pd.notna(row.get('Dist_Cir')) else None,
            'proximal_margin_mm': float(row.get('Dist_Cut')) if pd.notna(row.get('Dist_Cut')) else None,
            'distal_margin_mm': None,  # Not in current data

            'resection_grade': map_resection_grade(row.get('resect_grade')),  # CLEANED: r0/r1/r2

            'vascular_invasion': map_invasion_status(row.get('Venous')),  # CLEANED: present/absent/uncertain
            'extranodal_extension': map_yes_no(row.get('Nod_Extr')),  # CLEANED: yes/no
            'apical_node_involvement': map_yes_no(row.get('Nod_Apic')),  # CLEANED: yes/no
            'mesorectal_involvement': False,  # Not in current data

            'tnm_version': '8',  # CR2070
            'pathological_stage_date': parse_date(row.get('Spec_Dat')),  # Specimen date

            'updated_at': datetime.utcnow()
        }

        tumours_collection.update_one(
            {'tumour_id': tumour_id},
            {'$set': pathology_update}
        )
        stats['pathology_updated'] += 1

        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{len(df)} pathology records...")

    print(f"✅ Pathology data imported: {stats['pathology_updated']} tumours updated")


def import_oncology(db, csv_path: str, hosp_no_to_patient_id: Dict, episode_mapping: Dict, stats: Dict):
    """
    Import oncology treatments from oncology.csv
    Creates radiotherapy and chemotherapy treatment records
    """
    print("\n" + "=" * 80)
    print("IMPORTING ONCOLOGY TREATMENTS")
    print("=" * 80)

    df = pd.read_csv(csv_path, low_memory=False)
    print(f"Loaded {len(df)} oncology records from CSV")

    treatments_collection = db.treatments
    oncology_treatment_counter = {}

    for idx, row in df.iterrows():
        hosp_no = str(row.get('Hosp_No', '')).strip()
        if not hosp_no or hosp_no == 'nan':
            stats['oncology_skipped_no_patient'] += 1
            continue

        patient_id = hosp_no_to_patient_id.get(hosp_no)
        if not patient_id:
            stats['oncology_skipped_no_patient'] += 1
            continue

        tum_seqno = row.get('TumSeqNo', 0)
        episode_id = episode_mapping.get((patient_id, tum_seqno))

        oncology_treatment_counter[patient_id] = oncology_treatment_counter.get(patient_id, 0)

        # Radiotherapy
        if row.get('RadioTh'):
            rt_start = parse_date(row.get('RT_Start'))
            if rt_start:
                # Check if RT treatment already exists
                existing_rt = treatments_collection.find_one({
                    'patient_id': patient_id,
                    'treatment_type': 'radiotherapy',
                    'treatment_date': rt_start
                })

                if not existing_rt:
                    oncology_treatment_counter[patient_id] += 1
                    rt_treatment_id = generate_treatment_id(patient_id, 1000 + oncology_treatment_counter[patient_id])

                    rt_doc = {
                        'treatment_id': rt_treatment_id,
                        'patient_id': patient_id,
                        'episode_id': episode_id,
                        'treatment_type': 'radiotherapy',
                        'treatment_date': rt_start,
                        'timing': map_treatment_timing(row.get('RT_when')),  # CLEANED: neoadjuvant/adjuvant/palliative
                        'technique': map_rt_technique(row.get('RT_Type')),  # CLEANED: long_course/short_course/contact
                        'start_date': rt_start,
                        'end_date': parse_date(row.get('RT_Finish')),
                        'trial_enrollment': map_yes_no(row.get('RT_Trial')),  # CLEANED: yes/no
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    }

                    treatments_collection.insert_one(rt_doc)
                    stats['oncology_rt_inserted'] += 1

                    if episode_id:
                        db.episodes.update_one(
                            {'episode_id': episode_id},
                            {'$push': {'treatment_ids': rt_treatment_id}}
                        )

        # Chemotherapy
        if row.get('ChemoTh'):
            ch_start = parse_date(row.get('Ch_Start'))
            if ch_start:
                # Check if chemo treatment already exists
                existing_ch = treatments_collection.find_one({
                    'patient_id': patient_id,
                    'treatment_type': 'chemotherapy',
                    'treatment_date': ch_start
                })

                if not existing_ch:
                    oncology_treatment_counter[patient_id] += 1
                    ch_treatment_id = generate_treatment_id(patient_id, 1000 + oncology_treatment_counter[patient_id])

                    ch_doc = {
                        'treatment_id': ch_treatment_id,
                        'patient_id': patient_id,
                        'episode_id': episode_id,
                        'treatment_type': 'chemotherapy',
                        'treatment_date': ch_start,
                        'timing': map_treatment_timing(row.get('Ch_When')),  # CLEANED: neoadjuvant/adjuvant/palliative
                        'regimen': {
                            'regimen_name': str(row.get('Ch_Type', '')).strip() or None
                        },
                        'start_date': ch_start,
                        'trial_enrollment': map_yes_no(row.get('Ch_Trial')),  # CLEANED: yes/no
                        'trial_name': str(row.get('Ch_Trial_name', '')).strip() or None,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    }

                    treatments_collection.insert_one(ch_doc)
                    stats['oncology_chemo_inserted'] += 1

                    if episode_id:
                        db.episodes.update_one(
                            {'episode_id': episode_id},
                            {'$push': {'treatment_ids': ch_treatment_id}}
                        )

        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{len(df)} oncology records...")

    print(f"✅ Oncology treatments imported: {stats['oncology_rt_inserted']} RT, {stats['oncology_chemo_inserted']} chemo")


def import_investigations(db, csv_path: str, hosp_no_to_patient_id: Dict, episode_mapping: Dict, tumour_mapping: Dict, stats: Dict):
    """
    Import investigations from tumours.csv (imaging data)
    User requirement: Create investigations from tblTumour imaging fields
    - Dt_CT_Abdo = CT Abdomen/Pelvis Date
    - Dt_CT_pneumo = CT Colonography Date
    - Date_Col = Colonoscopy Date
    - Clean result text by removing leading numbers
    """
    print("\n" + "=" * 80)
    print("IMPORTING INVESTIGATIONS (Imaging Data)")
    print("=" * 80)

    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} tumour records from CSV (will extract imaging data)")

    investigations_collection = db.investigations
    investigations_created = 0

    def clean_result_text(value) -> Optional[str]:
        """Remove leading numbers from result text"""
        if pd.isna(value):
            return None
        val_str = str(value).strip()

        # Remove leading number and space (e.g., "1 Normal" -> "Normal")
        import re
        match = re.match(r'^\d+\s+(.+)$', val_str)
        if match:
            return match.group(1).lower()

        return val_str.lower() if val_str and val_str != 'nan' else None

    for idx, row in df.iterrows():
        hosp_no = str(row.get('Hosp_No', '')).strip()
        if not hosp_no or hosp_no == 'nan':
            continue

        patient_id = hosp_no_to_patient_id.get(hosp_no)
        if not patient_id:
            continue

        tum_seqno = row.get('TumSeqno', 0)  # Use same format as episode/tumour imports
        episode_id = episode_mapping.get((patient_id, tum_seqno))
        tumour_id = tumour_mapping.get((patient_id, tum_seqno))

        investigation_seq = 1

        # CT Abdomen/Pelvis
        ct_abdo_date = parse_date(row.get('Dt_CT_Abdo'))
        if ct_abdo_date:
            investigation_id = f"INV-{patient_id}-CTA-{str(investigation_seq).zfill(2)}"
            investigations_collection.insert_one({
                'investigation_id': investigation_id,
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
            })
            investigations_created += 1
            investigation_seq += 1

        # CT Colonography
        ct_pneumo_date = parse_date(row.get('Dt_CT_pneumo'))
        if ct_pneumo_date:
            investigation_id = f"INV-{patient_id}-CTC-{str(investigation_seq).zfill(2)}"
            investigations_collection.insert_one({
                'investigation_id': investigation_id,
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
            })
            investigations_created += 1
            investigation_seq += 1

        # Colonoscopy
        col_date = parse_date(row.get('Date_Col'))
        if col_date:
            investigation_id = f"INV-{patient_id}-COL-{str(investigation_seq).zfill(2)}"
            investigations_collection.insert_one({
                'investigation_id': investigation_id,
                'patient_id': patient_id,
                'episode_id': episode_id,
                'tumour_id': tumour_id,
                'type': 'endoscopy',
                'subtype': 'colonoscopy',
                'date': col_date,
                'result': 'abnormal',  # Default for colonoscopy leading to cancer diagnosis
                'findings': {},
                'report_url': None,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            investigations_created += 1
            investigation_seq += 1

        # MRI Primary
        mri1_date = parse_date(row.get('Dt_MRI1'))
        if mri1_date:
            investigation_id = f"INV-{patient_id}-MRI-{str(investigation_seq).zfill(2)}"
            mri_findings = {
                't_stage': map_tnm_stage(row.get('MRI1_T')),
                'n_stage': map_tnm_stage(row.get('MRI1_N')),
                'crm_status': map_crm_status(row.get('MRI1_CRM')),
                'crm_distance_mm': float(row.get('MRI1_dist')) if pd.notna(row.get('MRI1_dist')) else None,
                'emvi': map_yes_no(row.get('EMVI'))
            }
            investigations_collection.insert_one({
                'investigation_id': investigation_id,
                'patient_id': patient_id,
                'episode_id': episode_id,
                'tumour_id': tumour_id,
                'type': 'imaging',
                'subtype': 'mri_primary',
                'date': mri1_date,
                'result': 'abnormal',
                'findings': mri_findings,
                'report_url': None,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            investigations_created += 1
            investigation_seq += 1

        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{len(df)} tumour records...")

    stats['investigations_created'] = investigations_created
    print(f"✅ Investigations imported: {investigations_created} created")


def import_followup(db, csv_path: str, hosp_no_to_patient_id: Dict, episode_mapping: Dict, stats: Dict):
    """
    Import follow-up data from followup.csv
    Adds follow-up records to episodes
    """
    print("\n" + "=" * 80)
    print("IMPORTING FOLLOW-UP DATA")
    print("=" * 80)

    df = pd.read_csv(csv_path, low_memory=False)
    print(f"Loaded {len(df)} follow-up records from CSV")

    episodes_collection = db.episodes

    for idx, row in df.iterrows():
        hosp_no = str(row.get('Hosp_No', '')).strip()
        if not hosp_no or hosp_no == 'nan':
            stats['followup_skipped_no_patient'] += 1
            continue

        patient_id = hosp_no_to_patient_id.get(hosp_no)
        if not patient_id:
            stats['followup_skipped_no_patient'] += 1
            continue

        tum_seqno = row.get('TumSeqNo', 0)
        episode_id = episode_mapping.get((patient_id, tum_seqno))

        if not episode_id:
            stats['followup_skipped_no_episode'] += 1
            continue

        # Create follow-up record
        followup_record = {
            'follow_up_date': parse_date(row.get('Date_FU')),
            'modality': map_followup_modality(row.get('ModeFol')),  # CLEANED: clinic/telephone/other
            'local_recurrence': {
                'occurred': map_yes_no(row.get('Local')),  # CLEANED: yes/no
                'date': parse_date(row.get('LocalDat')),
                'diagnosis': str(row.get('LocalDia', '')).strip() or None
            },
            'distant_recurrence': {
                'occurred': map_yes_no(row.get('Distant')),  # CLEANED: yes/no
                'date': parse_date(row.get('DistDate')),
                'sites': {
                    'liver': map_yes_no(row.get('DS_Liver')),  # CLEANED: yes/no
                    'lung': map_yes_no(row.get('DS_Lung')),  # CLEANED: yes/no
                    'bone': map_yes_no(row.get('DS_Bone')),  # CLEANED: yes/no
                    'other': map_yes_no(row.get('DS_Other'))  # CLEANED: yes/no
                }
            },
            'investigations': {
                'ct': {
                    'performed': map_yes_no(row.get('CT_FU')),  # CLEANED: yes/no
                    'date': parse_date(row.get('CT_date'))
                },
                'colonoscopy': {
                    'performed': map_yes_no(row.get('Col_FU')),  # CLEANED: yes/no
                    'date': parse_date(row.get('Col_Date'))
                }
            },
            'palliative_referral': {
                'referred': map_yes_no(row.get('Ref_Pall')),  # CLEANED: yes/no
                'date': parse_date(row.get('Dat_Pall'))
            }
        }

        # Add follow-up to episode
        episodes_collection.update_one(
            {'episode_id': episode_id},
            {'$push': {'follow_up': followup_record}}
        )
        stats['followup_added'] += 1

        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{len(df)} follow-up records...")

    print(f"✅ Follow-up data imported: {stats['followup_added']} follow-up records added to episodes")


def populate_mortality_flags(db, deceased_patients: Dict, stats: Dict):
    """
    Calculate 30-day and 90-day mortality for all treatments
    """
    print("\n" + "=" * 80)
    print("CALCULATING MORTALITY FLAGS")
    print("=" * 80)

    treatments_collection = db.treatments

    print(f"Processing {len(deceased_patients)} deceased patients...")

    for patient_id, deceased_date_str in deceased_patients.items():
        try:
            deceased_date = datetime.strptime(deceased_date_str, '%Y-%m-%d')

            # Get all surgical treatments for this patient
            treatments = treatments_collection.find({
                'patient_id': patient_id,
                'treatment_type': 'surgery'
            })

            for treatment in treatments:
                treatment_date_str = treatment.get('treatment_date')
                if not treatment_date_str:
                    continue

                try:
                    treatment_date = datetime.strptime(treatment_date_str, '%Y-%m-%d')
                    days_to_death = (deceased_date - treatment_date).days

                    if days_to_death >= 0:  # Death after treatment
                        mortality_30day = days_to_death <= 30
                        mortality_90day = days_to_death <= 90

                        treatments_collection.update_one(
                            {'_id': treatment['_id']},
                            {'$set': {
                                'outcomes.mortality_30day': mortality_30day,
                                'outcomes.mortality_90day': mortality_90day
                            }}
                        )

                        if mortality_30day:
                            stats['mortality_30day_set'] += 1
                        if mortality_90day:
                            stats['mortality_90day_set'] += 1

                except Exception as e:
                    stats['mortality_errors'] += 1

        except Exception as e:
            stats['mortality_errors'] += 1

    print(f"✅ Mortality flags calculated: {stats['mortality_30day_set']} 30-day, {stats['mortality_90day_set']} 90-day")


def consolidate_synchronous_episodes(db, stats: Dict):
    """
    Consolidate episodes for patients with multiple episodes where tumours
    have the same diagnosis date (synchronous tumours).

    Metachronous tumours (different diagnosis dates) remain as separate episodes.

    Args:
        db: Database connection
        stats: Statistics dictionary
    """
    print("\n" + "=" * 80)
    print("CONSOLIDATING SYNCHRONOUS EPISODES")
    print("=" * 80)

    # Initialize stats
    stats['episodes_consolidated'] = 0
    stats['episodes_deleted'] = 0
    stats['tumours_moved'] = 0
    stats['treatments_moved'] = 0

    # Find all patients with multiple episodes
    pipeline = [
        {"$group": {
            "_id": "$patient_id",
            "episode_count": {"$sum": 1},
            "episode_ids": {"$push": "$episode_id"}
        }},
        {"$match": {"episode_count": {"$gt": 1}}},
        {"$sort": {"_id": 1}}
    ]

    patients_with_multiple = list(db.episodes.aggregate(pipeline))
    print(f"Found {len(patients_with_multiple)} patients with multiple episodes")

    patients_needing_consolidation = 0

    for patient_data in patients_with_multiple:
        patient_id = patient_data['_id']
        episode_ids = patient_data['episode_ids']

        # Get all episodes for this patient with tumour data
        episodes = []
        for ep_id in episode_ids:
            episode = db.episodes.find_one({"episode_id": ep_id})
            if not episode:
                continue

            # Get tumour diagnosis dates
            tumour_dates = []
            for tumour_id in episode.get('tumour_ids', []):
                tumour = db.tumours.find_one({"tumour_id": tumour_id})
                if tumour and tumour.get('diagnosis_date'):
                    tumour_dates.append(tumour['diagnosis_date'])

            # Use earliest tumour date as episode date
            episode_date = min(tumour_dates) if tumour_dates else None

            episodes.append({
                'episode_id': ep_id,
                'episode': episode,
                'diagnosis_date': episode_date,
                'tumour_ids': episode.get('tumour_ids', []),
                'treatment_ids': episode.get('treatment_ids', [])
            })

        # Group episodes by diagnosis date
        from collections import defaultdict
        episodes_by_date = defaultdict(list)
        for ep_data in episodes:
            date = ep_data['diagnosis_date']
            if date:  # Only group episodes with a diagnosis date
                episodes_by_date[date].append(ep_data)

        # Check if any date has multiple episodes (needs consolidation)
        for date, eps in episodes_by_date.items():
            if len(eps) <= 1:
                continue  # Only one episode for this date

            patients_needing_consolidation += 1

            # Sort episodes by episode_id to keep the first one
            eps.sort(key=lambda x: x['episode_id'])

            # Primary episode (keep this one)
            primary = eps[0]
            redundant = eps[1:]

            # Consolidate data from redundant episodes
            all_tumour_ids = list(primary['tumour_ids'])
            all_treatment_ids = list(primary['treatment_ids'])

            for red in redundant:
                all_tumour_ids.extend(red['tumour_ids'])
                all_treatment_ids.extend(red['treatment_ids'])

                stats['tumours_moved'] += len(red['tumour_ids'])
                stats['treatments_moved'] += len(red['treatment_ids'])

            # Update primary episode with all tumours and treatments
            db.episodes.update_one(
                {'episode_id': primary['episode_id']},
                {
                    '$set': {
                        'tumour_ids': all_tumour_ids,
                        'treatment_ids': all_treatment_ids,
                        'updated_at': datetime.utcnow()
                    }
                }
            )

            # Update all tumours to point to primary episode
            for tumour_id in all_tumour_ids:
                db.tumours.update_one(
                    {'tumour_id': tumour_id},
                    {
                        '$set': {
                            'episode_id': primary['episode_id'],
                            'updated_at': datetime.utcnow()
                        }
                    }
                )

            # Update all treatments to point to primary episode
            for treatment_id in all_treatment_ids:
                db.treatments.update_one(
                    {'treatment_id': treatment_id},
                    {
                        '$set': {
                            'episode_id': primary['episode_id'],
                            'updated_at': datetime.utcnow()
                        }
                    }
                )

            # Delete redundant episodes
            for red in redundant:
                db.episodes.delete_one({'episode_id': red['episode_id']})
                stats['episodes_deleted'] += 1

            stats['episodes_consolidated'] += 1

    print(f"✅ Consolidated {stats['episodes_consolidated']} patients with synchronous tumours")
    print(f"   Episodes deleted: {stats['episodes_deleted']}")
    print(f"   Tumours moved: {stats['tumours_moved']}")
    print(f"   Treatments moved: {stats['treatments_moved']}")


# ============================================================================
# MAIN IMPORT FUNCTION
# ============================================================================

def run_comprehensive_import(db_name='impact_test', csv_dir=CSV_DIR):
    """
    Run complete import of all data
    """
    # Connect to MongoDB
    mongo_uri = os.getenv('MONGODB_URI')
    if not mongo_uri:
        raise ValueError("MONGODB_URI not found in environment")

    client = MongoClient(mongo_uri)
    db = client[db_name]

    print("\n" + "=" * 80)
    print(f"COMPREHENSIVE DATA IMPORT - Database: {db_name}")
    print("=" * 80)
    print(f"CSV Directory: {csv_dir}")
    print(f"Mode: INSERT-ONLY (skip if record exists)")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Initialize statistics
    stats = {
        'patients_inserted': 0,
        'patients_skipped_existing': 0,
        'patients_skipped_no_hosp_no': 0,
        'episodes_inserted': 0,
        'episodes_skipped_existing': 0,
        'episodes_skipped_no_patient': 0,
        'tumours_inserted': 0,
        'tumours_skipped_existing': 0,
        'tumours_skipped_no_patient': 0,
        'tumours_skipped_no_episode': 0,
        'treatments_inserted': 0,
        'treatments_skipped_existing': 0,
        'treatments_skipped_no_patient': 0,
        'pathology_updated': 0,
        'pathology_skipped_no_patient': 0,
        'pathology_skipped_no_tumour': 0,
        'oncology_rt_inserted': 0,
        'oncology_chemo_inserted': 0,
        'oncology_skipped_no_patient': 0,
        'followup_added': 0,
        'followup_skipped_no_patient': 0,
        'followup_skipped_no_episode': 0,
        'mortality_30day_set': 0,
        'mortality_90day_set': 0,
        'mortality_errors': 0
    }

    # Run imports in order
    try:
        # 0. Load clinicians from impact_system for surgeon matching
        print("\n" + "=" * 80)
        print("LOADING CLINICIANS FROM SYSTEM DATABASE")
        print("=" * 80)
        clinician_mapping = load_clinicians_mapping(client)

        # 1. Patients
        hosp_no_to_patient_id, deceased_patients = import_patients(
            db,
            f"{csv_dir}/patients.csv",
            stats
        )

        # 2. Episodes
        episode_mapping = import_episodes(
            db,
            f"{csv_dir}/tumours.csv",
            hosp_no_to_patient_id,
            stats,
            clinician_mapping  # Pass clinician mapping for lead_clinician matching
        )

        # 3. Tumours
        tumour_mapping = import_tumours(
            db,
            f"{csv_dir}/tumours.csv",
            hosp_no_to_patient_id,
            episode_mapping,
            stats
        )

        # 4. Surgical treatments
        import_treatments_surgery(
            db,
            f"{csv_dir}/treatments_surgery.csv",
            hosp_no_to_patient_id,
            episode_mapping,
            clinician_mapping,
            stats
        )

        # 5. Pathology
        import_pathology(
            db,
            f"{csv_dir}/pathology.csv",
            hosp_no_to_patient_id,
            tumour_mapping,
            stats
        )

        # 6. Oncology treatments
        import_oncology(
            db,
            f"{csv_dir}/oncology.csv",
            hosp_no_to_patient_id,
            episode_mapping,
            stats
        )

        # 7. Investigations (from tumours.csv imaging fields)
        import_investigations(
            db,
            f"{csv_dir}/tumours.csv",
            hosp_no_to_patient_id,
            episode_mapping,
            tumour_mapping,
            stats
        )

        # 8. Follow-up
        import_followup(
            db,
            f"{csv_dir}/followup.csv",
            hosp_no_to_patient_id,
            episode_mapping,
            stats
        )

        # 9. Mortality flags
        populate_mortality_flags(
            db,
            deceased_patients,
            stats
        )

        # 10. Consolidate synchronous episodes
        consolidate_synchronous_episodes(db, stats)

        # Print final summary
        print("\n" + "=" * 80)
        print("IMPORT SUMMARY")
        print("=" * 80)
        print(f"\nPATIENTS:")
        print(f"  Inserted: {stats['patients_inserted']}")
        print(f"  Skipped (existing): {stats['patients_skipped_existing']}")
        print(f"\nEPISODES:")
        print(f"  Inserted: {stats['episodes_inserted']}")
        print(f"  Skipped (existing): {stats['episodes_skipped_existing']}")
        print(f"\nTUMOURS:")
        print(f"  Inserted: {stats['tumours_inserted']}")
        print(f"  Skipped (existing): {stats['tumours_skipped_existing']}")
        print(f"\nTREATMENTS:")
        print(f"  Surgery inserted: {stats['treatments_inserted']}")
        print(f"  Surgery skipped (existing): {stats['treatments_skipped_existing']}")
        print(f"  Radiotherapy inserted: {stats['oncology_rt_inserted']}")
        print(f"  Chemotherapy inserted: {stats['oncology_chemo_inserted']}")
        print(f"\nPATHOLOGY:")
        print(f"  Tumours updated: {stats['pathology_updated']}")
        print(f"\nFOLLOW-UP:")
        print(f"  Records added: {stats['followup_added']}")
        print(f"\nMORTALITY FLAGS:")
        print(f"  30-day mortality: {stats['mortality_30day_set']}")
        print(f"  90-day mortality: {stats['mortality_90day_set']}")
        print(f"\nEPISODE CONSOLIDATION:")
        print(f"  Episodes consolidated: {stats.get('episodes_consolidated', 0)}")
        print(f"  Episodes deleted: {stats.get('episodes_deleted', 0)}")
        print(f"  Tumours moved: {stats.get('tumours_moved', 0)}")
        print(f"  Treatments moved: {stats.get('treatments_moved', 0)}")
        print("=" * 80)
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        return stats

    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Comprehensive data import to MongoDB')
    parser.add_argument('--database', default='impact_test', help='Database name (default: impact_test)')
    parser.add_argument('--csv-dir', default=CSV_DIR, help=f'CSV directory (default: {CSV_DIR})')
    args = parser.parse_args()

    try:
        stats = run_comprehensive_import(db_name=args.database, csv_dir=args.csv_dir)
        print("\n✅ Import completed successfully!\n")
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        raise
