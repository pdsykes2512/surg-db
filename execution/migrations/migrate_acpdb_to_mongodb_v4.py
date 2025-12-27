#!/usr/bin/env python3
"""
Migration script v3: Remove ObjectId references, use only human-readable IDs
- Episodes store: patient_id, treatment_ids[], tumour_ids[]
- Treatments store: patient_id, episode_id
- Tumours store: patient_id, episode_id
"""
import sys
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import hashlib
import json

class ACPDBMigratorV4:
    def __init__(self, mongodb_uri: str, database_name: str):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[database_name]
        self.patients = self.db.patients
        self.episodes = self.db.episodes
        self.treatments = self.db.treatments
        self.tumours = self.db.tumours
        
        # Tracking mappings
        self.hosp_no_to_patient = {}  # hosp_no -> {patient_id, nhs_number}
        self.surgery_to_episode = {}  # Su_SeqNo -> {episode_id, tum_seqno, hosp_no, nhs_number}
        self.tumour_seq_to_id = {}  # TumSeqNo -> tumour_id
        self.tumour_data = {}  # TumSeqNo -> full tumour data for episode enrichment
        
        # Stats initialization (must be before load_legacy_surgeons)
        self.stats = {
            "patients_created": 0,
            "episodes_created": 0,
            "treatments_created": 0,
            "tumours_created": 0,
            "pathology_updated": 0,
            "errors": [],
            "warnings": []
        }
        
        # Load legacy surgeon mappings
        self.legacy_surgeons = self.load_legacy_surgeons()
        
        # Load existing clinicians from database
        self.existing_clinicians = self.load_existing_clinicians()
        
        # Sequence trackers per patient_id
        self.patient_episode_sequences = {}
        self.patient_tumour_sequences = {}
        self.patient_treatment_sequences = {}
    
    def generate_patient_hash(self, mrn: str) -> str:
        """Generate 6-character hash from MRN"""
        hash_obj = hashlib.md5(mrn.encode())
        return hash_obj.hexdigest()[:6].upper()
    
    def format_mrn(self, hosp_no: str) -> str:
        """Format hospital number as MRN"""
        hosp_no = str(hosp_no).strip()
        if hosp_no.startswith('IW'):
            return hosp_no
        try:
            return f"{int(hosp_no):08d}"
        except:
            return hosp_no
    
    def generate_episode_id(self, patient_id: str) -> str:
        """Generate episode ID: E-{patient_id}-{seq:02d}"""
        if patient_id not in self.patient_episode_sequences:
            self.patient_episode_sequences[patient_id] = 0
        self.patient_episode_sequences[patient_id] += 1
        seq = self.patient_episode_sequences[patient_id]
        return f"E-{patient_id}-{seq:02d}"
    
    def generate_tumour_id(self, patient_id: str) -> str:
        """Generate tumour ID: TUM-{patient_id}-{seq:02d}"""
        if patient_id not in self.patient_tumour_sequences:
            self.patient_tumour_sequences[patient_id] = 0
        self.patient_tumour_sequences[patient_id] += 1
        seq = self.patient_tumour_sequences[patient_id]
        return f"TUM-{patient_id}-{seq:02d}"
    
    def generate_treatment_id(self, patient_id: str, treatment_type: str = "SUR") -> str:
        """Generate treatment ID: {TYPE}-{patient_id}-{seq:02d}"""
        if patient_id not in self.patient_treatment_sequences:
            self.patient_treatment_sequences[patient_id] = 0
        self.patient_treatment_sequences[patient_id] += 1
        seq = self.patient_treatment_sequences[patient_id]
        return f"{treatment_type}-{patient_id}-{seq:02d}"
    
    def parse_date(self, date_val) -> str:
        """Parse date with fallback handling"""
        if pd.isna(date_val):
            return None
        try:
            if isinstance(date_val, str):
                parsed = pd.to_datetime(date_val, errors='coerce')
            else:
                parsed = pd.to_datetime(date_val)
            if pd.isna(parsed):
                return None
            return parsed.strftime('%Y-%m-%d')
        except:
            return None
    
    def parse_dob(self, date_val) -> str:
        """Parse date of birth with special handling for 2-digit years"""
        if pd.isna(date_val):
            return None
        try:
            if isinstance(date_val, str):
                parsed = pd.to_datetime(date_val, errors='coerce')
            else:
                parsed = pd.to_datetime(date_val)
            
            if pd.isna(parsed):
                return None
            
            current_year = datetime.now().year
            if parsed.year >= current_year or (current_year - parsed.year) < 10:
                parsed = parsed.replace(year=parsed.year - 100)
            
            return parsed.strftime('%Y-%m-%d')
        except:
            return None
    
    def normalize_coded_value(self, val):
        """Normalize coded values - extract description and convert to lowercase."""
        if pd.isna(val):
            return None
        val_str = str(val).strip()
        if not val_str or val_str == 'nan':
            return None
        
        # Handle coded values like "1 None", "2 Abnormal"
        if val_str and len(val_str) > 1 and val_str[0].isdigit():
            parts = val_str.split(' ', 1)
            if len(parts) == 2:
                return parts[1].strip().lower()
        
        return val_str.lower()
    
    def normalize_numeric(self, val):
        """Extract numeric value from string."""
        if pd.isna(val):
            return None
        try:
            return float(val)
        except:
            return None
    
    def map_approach(self, mode_op, lap_proc):
        """Map surgical approach"""
        if not pd.isna(lap_proc):
            lap_str = str(lap_proc).lower()
            if "lap" in lap_str or "laparoscopic" in lap_str:
                return "laparoscopic"
        return "open"
    
    def map_tumour_site(self, tum_site):
        """
        Map tumour site to ICD-10 based anatomical sites.
        Returns tuple: (anatomical_site, icd10_code, display_label)
        """
        if pd.isna(tum_site):
            return None, None, None
        
        # Extract number from format like "1 Caecum" or "10 Rectum"
        site_str = str(tum_site).strip()
        
        # Site mapping with ICD-10 codes
        site_map = {
            "1": ("caecum", "C18.0", "site_1 Caecum"),
            "2": ("appendix", "C18.1", "site_2 Appendix"),
            "3": ("ascending_colon", "C18.2", "site_3 Ascending Colon"),
            "4": ("hepatic_flexure", "C18.3", "site_4 Hepatic Flexure"),
            "5": ("transverse_colon", "C18.4", "site_5 Transverse Colon"),
            "6": ("splenic_flexure", "C18.5", "site_6 Splenic Flexure"),
            "7": ("descending_colon", "C18.6", "site_7 Descending Colon"),
            "8": ("sigmoid_colon", "C18.7", "site_8 Sigmoid Colon"),
            "9": ("rectosigmoid_junction", "C19", "site_9 Recto/Sigmoid"),
            "10": ("rectum", "C20", "site_10 Rectum")
        }
        
        # Extract first token (the number)
        parts = site_str.split(None, 1)
        site_num = parts[0] if parts else ""
        
        if site_num in site_map:
            return site_map[site_num]
        
        # Fallback: return None values
        return None, None, site_str
    
    def normalize_treatment_plan(self, value):
        """
        Normalize treatment plan to standard values.
        Handles single and multi-treatment plans like "01 surgery, 02 teletherapy, 03 chemotherapy"
        Returns: Combined treatment plan as "Surgery + Chemotherapy + Radiotherapy" format
        """
        if pd.isna(value) or not value:
            return None
        
        value_str = str(value).strip().lower()
        if not value_str or value_str == 'nan':
            return None
        
        # Treatment mapping
        treatment_map = {
            '01': 'Surgery',
            '02': 'Radiotherapy',
            '03': 'Chemotherapy',
            '04': 'Combination Therapy',
            '05': 'Palliative Care',
            'surgery': 'Surgery',
            'teletherapy': 'Radiotherapy',
            'radiotherapy': 'Radiotherapy',
            'chemotherapy': 'Chemotherapy',
            'combination therapy': 'Combination Therapy',
            'palliative care': 'Palliative Care',
            'palliative': 'Palliative Care'
        }
        
        # Split by comma for multi-treatment plans
        parts = [p.strip() for p in value_str.split(',')]
        treatments = []
        
        for part in parts:
            # Check if it starts with a number code
            if part and part[0].isdigit():
                # Extract code and text
                tokens = part.split(None, 1)  # Split on first whitespace
                code = tokens[0] if tokens else ''
                text = tokens[1] if len(tokens) > 1 else ''
                
                # Try code first, then text
                if code in treatment_map:
                    treatments.append(treatment_map[code])
                elif text in treatment_map:
                    treatments.append(treatment_map[text])
            else:
                # No code, just text
                if part in treatment_map:
                    treatments.append(treatment_map[part])
        
        if not treatments:
            return None
        
        # Remove duplicates while preserving order
        seen = set()
        unique_treatments = []
        for t in treatments:
            if t not in seen:
                seen.add(t)
                unique_treatments.append(t)
        
        # Return combined format
        if len(unique_treatments) == 1:
            return unique_treatments[0]
        else:
            return ' + '.join(unique_treatments)
    
    def normalize_treatment_intent(self, value):
        """
        Normalize treatment intent to standard values.
        Maps: C curative/C → Curative, Z noncurative/Z → Palliative, X no ca treat/X → No Treatment
        """
        if pd.isna(value) or not value:
            return None
        
        value_lower = str(value).lower().strip()
        
        # Curative
        if 'curative' in value_lower and 'non' not in value_lower:
            return "Curative"
        if value_lower == 'c':
            return "Curative"
        
        # Palliative (includes noncurative)
        if 'noncurative' in value_lower or value_lower == 'z':
            return "Palliative"
        
        # No Treatment
        if 'no ca treat' in value_lower or value_lower == 'x':
            return "No Treatment"
        
        # Unknown -> None
        if 'not known' in value_lower or 'not knnown' in value_lower:
            return None
        
        # Default: return None if no match
        return None
        def extract_text_from_coded_field(self, value):
        """Extract descriptive text from fields with number prefixes like '1 Elective' -> 'Elective'"""
        if pd.isna(value) or not value:
            return None
        
        value_str = str(value).strip()
        if not value_str or value_str.lower() == 'nan':
            return None
        
        # If it starts with a digit, extract everything after the first space
        if value_str and value_str[0].isdigit():
            parts = value_str.split(' ', 1)
            if len(parts) > 1:
                return parts[1].strip()  # Return the text after the number
            else:
                return None  # Just a bare number, no description
        
        # Return as-is if no number prefix
        return value_str
    
    def map_no_surgery_reason(self, no_surg_value):
        """Map NoSurg field to readable reason - extract text after number prefix"""
        if pd.isna(no_surg_value):
            return None
        
        no_surg_str = str(no_surg_value).strip()
        
        # If it starts with a digit, extract everything after the first space
        if no_surg_str and no_surg_str[0].isdigit():
            parts = no_surg_str.split(' ', 1)
            if len(parts) > 1:
                return parts[1].strip()  # Return the text after the number
            else:
                # Just a number, map it
                if no_surg_str == '1':
                    return "Patient refused treatment"
                elif no_surg_str == '2':
                    return "Patient unfit"
                elif no_surg_str == '3':
                    return "Advanced disease"
                elif no_surg_str == '4':
                    return "Other"
        
        # Return as-is if no number prefix
        return no_surg_str if no_surg_str and no_surg_str.lower() != 'nan' else None
    
    def parse_referral_source(self, other_field):
        """Parse referral source from free text field"""
        if pd.isna(other_field):
            return None
        
        text = str(other_field).upper().strip()
        
        # Pattern matching for common sources
        if 'BCSP' in text or 'BOWEL SCREEN' in text:
            return "Bowel Cancer Screening Programme"
        elif 'GP2WW' in text or '2WW' in text or 'TWO WEEK' in text:
            return "2 Week Wait Referral"
        elif 'EMERGENCY' in text or 'A&E' in text or 'A AND E' in text:
            return "Emergency"
        elif 'GP' in text:
            return "GP Referral"
        elif 'SURVEILLANCE' in text:
            return "Surveillance"
        
        # Return original if no pattern matched
        return text if len(text) > 0 else None
    
    def normalize_referral_type(self, ref_type_text):
        """Normalize referral type to match form options: Elective, Emergency, Internal, Screening, Other"""
        if not ref_type_text or pd.isna(ref_type_text):
            return None
        
        text = str(ref_type_text).strip().lower()
        
        # Map to form options
        if text in ['elective']:
            return 'Elective'
        elif text in ['emergency', 'ae', 'ea', 'a&e']:
            return 'Emergency'
        elif text in ['internal']:
            return 'Internal'
        elif text in ['screening', 'bcsp', 'bowel screening']:
            return 'Screening'
        elif text in ['gp', 'gp referral']:
            return 'Elective'  # GP referrals are typically elective
        elif text in ['other', 'not known']:
            return 'Other'
        
        # Default to Other if unrecognized
        return 'Other'
    
    def normalize_referral_source(self, source_text):
        """Normalize referral source to match form options: gp, 2ww, screening, emergency, consultant, private, other"""
        if not source_text or pd.isna(source_text):
            return None
        
        text = str(source_text).strip().lower()
        
        # Map to form options
        if '2 week wait' in text or '2ww' in text or 'two week' in text or 'gp2ww' in text or 'twc' in text or 'cwt' in text:
            return '2ww'
        elif 'bowel cancer screening' in text or 'bcsp' in text or 'screening' in text:
            return 'screening'
        elif 'emergency' in text or 'a&e' in text or 'ea' in text or 'emer' in text:
            return 'emergency'
        elif 'gp referral' in text or text == 'gp':
            return 'gp'
        elif 'consultant' in text or 'cons' in text or any(dept in text for dept in ['urology', 'gynae', 'gi ', 'ugi', 'oncology', 'cardiology', 'respiratory', 'haematology', 'renal', 'nephrology']):
            return 'consultant'
        elif 'private' in text or 'pp' in text or 'spire' in text or 'jubilee' in text or 'istc' in text or 'isctc' in text:
            return 'private'
        elif 'surveillance' in text or 'follow up' in text or 'fu' in text or 'wfu' in text or 'f/up' in text or 'surv' in text or 'srvce' in text:
            return 'other'  # Follow-up/surveillance
        elif 'mdt' in text:
            return 'consultant'
        
        # Default to other
        return 'other'
    
    def load_legacy_surgeons(self):
        """Load legacy surgeon mappings from JSON file"""
        import os
        try:
            # Look for file in parent directory (project root)
            legacy_file = os.path.join(os.path.dirname(__file__), '..', 'legacy_surgeons.json')
            with open(legacy_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            if hasattr(self, 'stats'):
                self.stats["warnings"].append("legacy_surgeons.json not found, surgeon names will be used as-is")
            return []
    
    def load_existing_clinicians(self):
        """Load existing clinicians from database for matching"""
        clinicians = {}
        clinicians_collection = self.db.clinicians
        for clinician in clinicians_collection.find({}):
            full_name = f"{clinician.get('first_name', '')} {clinician.get('surname', '')}".strip()
            
            # Store by surname (lowercase) for matching
            surname = clinician.get('surname', '').lower()
            if surname:
                clinicians[surname] = full_name
            
            # Also store by first_name (lowercase) for matching - some legacy data has first names swapped
            first_name = clinician.get('first_name', '').lower()
            if first_name:
                clinicians[first_name] = full_name
        
        return clinicians
    
    def format_clinician_name(self, name: str) -> str:
        """Format clinician name to proper title case"""
        if not name or name.lower() == 'nan':
            return None
        
        # Handle special cases
        name = name.strip()
        
        # Check if it's an all-caps name (like O'LEARY)
        if name.isupper() or name.islower():
            # Apply title case but preserve apostrophes
            parts = name.split("'")
            formatted_parts = [part.capitalize() for part in parts]
            name = "'".join(formatted_parts)
        
        return name
    
    def match_or_format_clinician(self, legacy_name: str) -> str:
        """Match legacy name to existing clinician or format it properly"""
        if not legacy_name or legacy_name.lower() == 'nan':
            return None
        
        legacy_name = legacy_name.strip()
        legacy_lower = legacy_name.lower()
        
        # Try to match to existing clinician by surname
        if legacy_lower in self.existing_clinicians:
            return self.existing_clinicians[legacy_lower]
        
        # No match found, format the name properly
        return self.format_clinician_name(legacy_name)
    
    def load_tumour_data(self, csv_path: str):
        """Preload tumour data for episode enrichment"""
        print(f"Preloading tumour data from {csv_path}...")
        df = pd.read_csv(csv_path)
        tumour_dict = {}
        for idx, row in df.iterrows():
            tum_seqno = str(row["TumSeqno"]).strip()
            tumour_dict[tum_seqno] = row.to_dict()
        print(f"   Loaded {len(tumour_dict)} tumour records")
        return tumour_dict
    
    def migrate_patients(self, csv_path: str, dry_run: bool = False):
        """Migrate patient records"""
        print(f"\n1. Migrating patients from {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"   Found {len(df)} patients")
        
        for idx, row in df.iterrows():
            try:
                # Use PAS_No as primary identifier, fallback to Hosp_No if missing
                pas_no = row.get("PAS_No")
                hosp_no = row.get("Hosp_No")
                
                if not pd.isna(pas_no) and str(pas_no).strip():
                    identifier = str(pas_no).strip()
                elif not pd.isna(hosp_no) and str(hosp_no).strip():
                    identifier = str(hosp_no).strip()
                else:
                    self.stats["warnings"].append(f"Patient row {idx}: No PAS_No or Hosp_No")
                    continue
                
                mrn = self.format_mrn(identifier)
                patient_id = self.generate_patient_hash(mrn)
                
                # Store original hosp_no for lookup from surgeries/tumours
                hosp_no_lookup = str(hosp_no).strip() if not pd.isna(hosp_no) else identifier
                
                # Format NHS number as string without decimal point
                nhs_raw = row.get("NHS_No")
                if not pd.isna(nhs_raw):
                    try:
                        nhs_number = str(int(float(nhs_raw)))
                    except:
                        nhs_number = str(nhs_raw).strip()
                else:
                    nhs_number = None
                
                # Parse gender - remove prefix like "1 Male" -> "Male"
                gender_raw = str(row["Sex"]) if not pd.isna(row.get("Sex")) else "Unknown"
                gender = gender_raw.split()[-1] if " " in gender_raw else gender_raw
                
                patient_doc = {
                    "patient_id": patient_id,
                    "mrn": mrn,
                    "nhs_number": nhs_number,
                    "demographics": {
                        "date_of_birth": self.parse_dob(row.get("P_DOB")),
                        "age": None,
                        "gender": gender,
                        "ethnicity": None,
                        "postcode": str(row["Postcode"]) if not pd.isna(row.get("Postcode")) else None,
                        "bmi": float(row["BMI"]) if not pd.isna(row.get("BMI")) and row.get("BMI") != "" else None,
                        "weight_kg": float(row["Weight"]) if not pd.isna(row.get("Weight")) and row.get("Weight") != "" else None,
                        "height_cm": float(row["Height"]) if not pd.isna(row.get("Height")) and row.get("Height") != "" else None,
                        "deceased_date": self.parse_dob(row.get("DeathDat"))
                    },
                    "medical_history": {
                        "conditions": [],
                        "previous_surgeries": [],
                        "medications": [],
                        "allergies": [],
                        "smoking_status": None,
                        "alcohol_use": None
                    },
                    "created_at": datetime.utcnow(),
                    "created_by": None,
                    "updated_at": datetime.utcnow(),
                    "updated_by": None
                }
                
                if not dry_run:
                    result = self.patients.insert_one(patient_doc)
                
                # Store mapping using hosp_no as key (for surgery/tumour lookups)
                self.hosp_no_to_patient[hosp_no_lookup] = {
                    "patient_id": patient_id,
                    "nhs_number": nhs_number
                }
                
                self.stats["patients_created"] += 1
                
                if idx % 500 == 0 and idx > 0:
                    print(f"   Processed {idx} patients...")
                    
            except Exception as e:
                error_msg = f"Patient row {idx}: {str(e)}"
                self.stats["errors"].append(error_msg)
                if len(self.stats["errors"]) < 20:
                    print(f"   ERROR: {error_msg}")
        
        print(f"   ✓ Created {self.stats['patients_created']} patients")
    
    def migrate_surgeries(self, csv_path: str, dry_run: bool = False):
        """Migrate surgeries as episodes and treatments"""
        print(f"\n2. Migrating surgeries from {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"   Found {len(df)} surgeries")
        
        for idx, row in df.iterrows():
            try:
                su_seqno = str(row["Su_SeqNo"]).strip()
                hosp_no = str(row["Hosp_No"]).strip()
                tum_seqno = str(row["TumSeqNo"]) if not pd.isna(row.get("TumSeqNo")) else None
                
                # Verify patient exists
                if hosp_no not in self.hosp_no_to_patient:
                    self.stats["warnings"].append(f"Surgery {su_seqno}: Patient {hosp_no} not found")
                    continue
                
                patient_mapping = self.hosp_no_to_patient[hosp_no]
                patient_id = patient_mapping["patient_id"]
                nhs_number = patient_mapping["nhs_number"]
                
                # Generate IDs
                episode_id = self.generate_episode_id(patient_id)
                treatment_id = self.generate_treatment_id(patient_id, "SUR")
                
                surgery_date_str = self.parse_date(row.get("Surgery"))
                
                # Map approach
                approach = self.map_approach(row.get("ModeOp"), row.get("LapProc"))
                
                # Map lead clinician (match to existing or format properly)
                surgeon_name = str(row["Surgeon"]).strip() if not pd.isna(row.get("Surgeon")) else None
                lead_clinician = self.match_or_format_clinician(surgeon_name)
                
                # Surgery performed flag
                surgery_performed = str(row.get("SurgPerf", "")).strip() == "1"
                
                # No treatment reason
                no_treatment_reason = None
                no_treatment_reason_detail = None
                if not surgery_performed:
                    no_surgery_raw = str(row.get("NoSurg", "")).strip()
                    if no_surgery_raw and no_surgery_raw.lower() != 'nan':
                        no_treatment_reason = self.extract_text_from_coded_field(no_surgery_raw)
                        no_treatment_reason_detail = str(row.get("NoSurgS", "")).strip() if not pd.isna(row.get("NoSurgS")) else None
                
                # Get tumour data for this episode
                tumour_info = self.tumour_data.get(tum_seqno, {})
                
                # Parse referral data from tumour
                referral_type_raw = str(tumour_info.get("RefType", "")).strip()
                referral_type = self.extract_text_from_coded_field(referral_type_raw)
                # Normalize to form options
                referral_type = self.normalize_referral_type(referral_type)
                
                referral_date = self.parse_date(tumour_info.get("DtRef"))
                first_seen_date = self.parse_date(tumour_info.get("Dt_Visit"))
                
                # Referral source (from tumour.other field)
                referral_source = None
                other_field = str(tumour_info.get("other", "")).strip()
                if other_field and other_field != "nan":
                    referral_source = self.parse_referral_source(other_field)
                    # Normalize to form options
                    referral_source = self.normalize_referral_source(referral_source)
                
                # MDT data
                mdt_discussion_date = first_seen_date  # Use first seen as MDT date
                mdt_meeting_type = "colorectal"  # Lowercase value matching form options
                
                # Treatment intent and plan from tumour
                treatment_intent_raw = str(tumour_info.get("careplan", "")).strip()
                treatment_intent_extracted = self.extract_text_from_coded_field(treatment_intent_raw)
                treatment_intent = self.normalize_treatment_intent(treatment_intent_extracted)
                
                treatment_plan_raw = str(tumour_info.get("plan_treat", "")).strip()
                treatment_plan = self.normalize_treatment_plan(treatment_plan_raw)
                
                # Performance status
                performance_status = None
                perf_raw = str(tumour_info.get("performance", "")).strip()
                if perf_raw and perf_raw.isdigit() and perf_raw in ["0", "1", "2", "3", "4"]:
                    performance_status = int(perf_raw)
                
                # Provider first seen (hardcoded for RHU)
                provider_first_seen = "RHU"
                
                # Create treatment document
                treatment_doc = {
                    "treatment_id": treatment_id,
                    "patient_id": patient_id,
                    "episode_id": episode_id,
                    "treatment_type": "surgery",
                    "treatment_date": surgery_date_str,
                    "treating_clinician": lead_clinician if lead_clinician else (surgeon_name if surgeon_name else "Unknown"),
                    "treatment_intent": treatment_intent,
                    "surgery": {
                        "classification": {
                            "primary_procedure": str(row.get("ProcName", "Unknown")),
                            "approach": approach,
                            "urgency": "elective" if "elective" in str(row.get("ProcType", "")).lower() else "emergency",
                            "asa_grade": str(row["ASA"]) if not pd.isna(row.get("ASA")) else None,
                            "opcs4_code": str(row["OPCS4"]) if not pd.isna(row.get("OPCS4")) else None
                        },
                        "outcomes": {
                            "discharge_date": self.parse_date(row.get("Date_Dis"))
                        }
                    },
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                
                # Create enriched episode document with all new fields
                episode_doc = {
                    "episode_id": episode_id,
                    "patient_id": patient_id,
                    "condition_type": "cancer",
                    "cancer_type": "bowel",
                    "referral_date": referral_date if referral_date else surgery_date_str,
                    "referral_type": referral_type,
                    "referral_source": referral_source,
                    "first_seen_date": first_seen_date,
                    "provider_first_seen": provider_first_seen,
                    "lead_clinician": lead_clinician,
                    "primary_diagnosis": {
                        "description": str(row.get("ProcName", ""))
                    },
                    "surgery_performed": surgery_performed,
                    "no_treatment_reason": no_treatment_reason,
                    "no_treatment_reason_detail": no_treatment_reason_detail,
                    "mdt_outcome": {
                        "mdt_discussion_date": mdt_discussion_date,
                        "mdt_meeting_type": mdt_meeting_type,
                        "treatment_intent": treatment_intent,
                        "treatment_plan": treatment_plan
                    },
                    "performance_status": performance_status,
                    "treatment_ids": [treatment_id],
                    "tumour_ids": [],
                    "status": "completed",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                
                if not dry_run:
                    self.treatments.insert_one(treatment_doc)
                    self.episodes.insert_one(episode_doc)
                
                # Store mapping
                self.surgery_to_episode[su_seqno] = {
                    "episode_id": episode_id,
                    "tum_seqno": tum_seqno,
                    "hosp_no": hosp_no,
                    "nhs_number": nhs_number
                }
                
                self.stats["treatments_created"] += 1
                self.stats["episodes_created"] += 1
                
                if idx % 500 == 0 and idx > 0:
                    print(f"   Processed {idx} surgeries...")
                    
            except Exception as e:
                error_msg = f"Surgery row {idx}: {str(e)}"
                self.stats["errors"].append(error_msg)
                if len(self.stats["errors"]) < 20:
                    print(f"   ERROR: {error_msg}")
        
        print(f"   ✓ Created {self.stats['episodes_created']} episodes")
        print(f"   ✓ Created {self.stats['treatments_created']} treatments")
    
    def migrate_tumours(self, csv_path: str, dry_run: bool = False):
        """Migrate tumour records (run after surgeries to link episodes)"""
        print(f"\\n3. Migrating tumours from {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"   Found {len(df)} tumours")
        
        for idx, row in df.iterrows():
            try:
                tum_seqno = str(row["TumSeqno"]).strip()  # Note: lowercase 'n'
                hosp_no = str(row["Hosp_No"]).strip()
                
                # Verify patient exists
                if hosp_no not in self.hosp_no_to_patient:
                    self.stats["warnings"].append(f"Tumour {tum_seqno}: Patient {hosp_no} not found")
                    continue
                
                patient_mapping = self.hosp_no_to_patient[hosp_no]
                patient_id = patient_mapping["patient_id"]
                
                # Generate tumour ID
                tumour_id = self.generate_tumour_id(patient_id)
                
                # Find associated episode
                episode_id = None
                for su_seq, episode_info in self.surgery_to_episode.items():
                    if episode_info["tum_seqno"] == tum_seqno and episode_info["hosp_no"] == hosp_no:
                        episode_id = episode_info["episode_id"]
                        break
                
                # Map tumour site and get ICD-10 code
                anatomical_site, site_icd10, site_display = self.map_tumour_site(row.get("TumSite"))
                
                # Use ICD-10 from site if TumICD10 is empty, otherwise use TumICD10
                tumour_icd10 = str(row["TumICD10"]).strip() if not pd.isna(row.get("TumICD10")) else site_icd10
                
                # Create comprehensive tumour document
                tumour_doc = {
                    "tumour_id": tumour_id,
                    "patient_id": patient_id,
                    "episode_id": episode_id,
                    "site": anatomical_site,  # Use ICD-10 based format to match form options
                    "tumour_type": "primary",
                    "diagnosis_date": self.parse_date(row.get("Dt_Diag")),
                    "staging": {
                        "t_stage": str(row["preTNM_T"]).strip() if not pd.isna(row.get("preTNM_T")) else None,
                        "n_stage": str(row["preTNM_N"]).strip() if not pd.isna(row.get("preTNM_N")) else None,
                        "m_stage": str(row["preTNM_M"]).strip() if not pd.isna(row.get("preTNM_M")) else None,
                    },
                    "icd10_code": tumour_icd10,
                    
                    # Imaging Results
                    "imaging_results": {
                        "ct_abdomen": {
                            "result": self.normalize_coded_value(row.get("CT_Abdo_result")),
                            "date": self.parse_date(row.get("Dt_CT_Abdo"))
                        },
                        "ct_chest": {
                            "result": self.normalize_coded_value(row.get("CT_pneumo_result")),
                            "date": self.parse_date(row.get("Dt_CT_pneumo"))
                        },
                        "mri_primary": {
                            "t_stage": self.normalize_coded_value(row.get("MRI1_T")),
                            "n_stage": self.normalize_coded_value(row.get("MRI1_N")),
                            "crm_status": self.normalize_coded_value(row.get("MRI1_CRM")),
                            "distance_from_anal_verge": self.normalize_numeric(row.get("MRI1_av")),
                            "emvi": self.normalize_coded_value(row.get("EMVI")),
                            "date": self.parse_date(row.get("Dt_MRI1"))
                        },
                        "mri_restaging": {
                            "date": self.parse_date(row.get("Dt_MRI2")),
                            "result": self.normalize_coded_value(row.get("M2result"))
                        },
                        "ultrasound_abdomen": {
                            "result": self.normalize_coded_value(row.get("Abresult")),
                            "date": self.parse_date(row.get("Dt_Abdo"))
                        },
                        "endoscopic_ultrasound": {
                            "t_stage": self.normalize_coded_value(row.get("Endo_T")),
                            "date": self.parse_date(row.get("Dt_Endo"))
                        }
                    },
                    
                    # Investigations
                    "investigations": {
                        "colonoscopy": {
                            "result": self.normalize_coded_value(row.get("Col_scpy")),
                            "date": self.parse_date(row.get("Date_Col")),
                            "completion_reason": self.normalize_coded_value(row.get("Rea_Inco"))
                        },
                        "flexible_sigmoidoscopy": {
                            "result": self.normalize_coded_value(row.get("Fle_Sig")),
                            "date": self.parse_date(row.get("Date_Fle"))
                        },
                        "barium_enema": {
                            "result": self.normalize_coded_value(row.get("Bar_Enem")),
                            "date": self.parse_date(row.get("Date_Bar"))
                        }
                    },
                    
                    # Distant Metastases
                    "distant_metastases": {
                        "liver": self.normalize_coded_value(row.get("DM_Liver")),
                        "lung": self.normalize_coded_value(row.get("DM_Lung")),
                        "bone": self.normalize_coded_value(row.get("DM_Bone")),
                        "other": self.normalize_coded_value(row.get("DM_Other"))
                    },
                    
                    # Clinical Status
                    "clinical_status": {
                        "performance_status": self.normalize_coded_value(row.get("performance")),
                        "height_cm": self.normalize_numeric(row.get("Height")),
                        "modified_dukes": self.normalize_coded_value(row.get("Mod_Duke"))
                    },
                    
                    # Screening Data
                    "screening": {
                        "bowel_cancer_screening_programme": bool(row.get("BCSP")) if not pd.isna(row.get("BCSP")) else False,
                        "screened": bool(row.get("Screened")) if not pd.isna(row.get("Screened")) else False,
                        "screening_method": self.normalize_coded_value(row.get("Scrn_Yes"))
                    },
                    
                    # MDT Information
                    "mdt": {
                        "discussed": self.normalize_coded_value(row.get("MDT_disc")),
                        "organization_code": str(row.get("Mdt_org")).strip() if not pd.isna(row.get("Mdt_org")) else None
                    },
                    
                    # Synchronous Tumours
                    "synchronous": {
                        "has_synchronous": bool(row.get("Sync")) if not pd.isna(row.get("Sync")) else False,
                        "type": self.normalize_coded_value(row.get("TumSync")),
                        "icd10_code": str(row.get("SynICD10")).strip() if not pd.isna(row.get("SynICD10")) else None,
                        "cancer_type": self.normalize_coded_value(row.get("Sync_cancer"))
                    },
                    
                    # Complications/Colonic
                    "colonic_complications": {
                        "bleeding": bool(row.get("ColC_Ble")) if not pd.isna(row.get("ColC_Ble")) else False,
                        "perforation": bool(row.get("ColC_Per")) if not pd.isna(row.get("ColC_Per")) else False,
                        "obstruction": bool(row.get("ColC_Ov")) if not pd.isna(row.get("ColC_Ov")) else False,
                        "other": bool(row.get("ColC_Oth")) if not pd.isna(row.get("ColC_Oth")) else False
                    },
                    
                    # Additional Information
                    "additional_info": {
                        "other_specification": str(row.get("Oth_Spec")).strip() if not pd.isna(row.get("Oth_Spec")) else None,
                        "other_specimen": str(row.get("Ot_Speci")).strip() if not pd.isna(row.get("Ot_Speci")) else None,
                        "non_cancer_treatment_reason": self.normalize_coded_value(row.get("Nonca_treat")),
                        "delay": bool(row.get("Delay")) if not pd.isna(row.get("Delay")) else False,
                        "priority": self.normalize_numeric(row.get("Priority")),
                        "referral_date": self.parse_date(row.get("DtRef")),
                        "visit_date": self.parse_date(row.get("Dt_Visit"))
                    },
                    
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                
                if not dry_run:
                    self.tumours.insert_one(tumour_doc)
                    
                    # Link to episode
                    if episode_id:
                        self.episodes.update_one(
                            {"episode_id": episode_id},
                            {"$push": {"tumour_ids": tumour_id}}
                        )
                
                self.tumour_seq_to_id[tum_seqno] = tumour_id
                
                self.stats["tumours_created"] += 1
                
                if idx % 500 == 0 and idx > 0:
                    print(f"   Processed {idx} tumours...")
                    
            except Exception as e:
                error_msg = f"Tumour row {idx}: {str(e)}"
                self.stats["errors"].append(error_msg)
                if len(self.stats["errors"]) < 20:
                    print(f"   ERROR: {error_msg}")
        
        print(f"   ✓ Created {self.stats['tumours_created']} tumours")
    
    def migrate_pathology(self, csv_path: str, dry_run: bool = False):
        """Migrate pathology records and link to tumours"""
        print(f"\n4. Migrating pathology from {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"   Found {len(df)} pathology records")
        
        for idx, row in df.iterrows():
            try:
                path_seqno = str(row["PthSeqNo"]).strip()
                tum_seqno = str(row["TumSeqNo"]) if not pd.isna(row.get("TumSeqNo")) else None
                
                if not tum_seqno or tum_seqno not in self.tumour_seq_to_id:
                    self.stats["warnings"].append(f"Pathology {path_seqno}: Tumour {tum_seqno} not found")
                    continue
                
                tumour_id = self.tumour_seq_to_id[tum_seqno]
                
                # Extract pathology data
                pathology_data = {
                    "differentiation": str(row["Diff"]) if not pd.isna(row.get("Diff")) else None,
                    "t_stage": str(row["postTNM_T"]).strip() if not pd.isna(row.get("postTNM_T")) else None,
                    "n_stage": str(row["postTNM_N"]).strip() if not pd.isna(row.get("postTNM_N")) else None,
                    "m_stage": str(row["postTNM_M"]).strip() if not pd.isna(row.get("postTNM_M")) else None,
                    "resection_margin": str(row["RStatus"]) if not pd.isna(row.get("RStatus")) else None,
                    "dukes_stage": str(row["Dukes"]) if not pd.isna(row.get("Dukes")) else None
                }
                
                if not dry_run:
                    self.tumours.update_one(
                        {"tumour_id": tumour_id},
                        {"$set": {"pathology": pathology_data, "updated_at": datetime.utcnow()}}
                    )
                
                self.stats["pathology_updated"] += 1
                
                if idx % 500 == 0 and idx > 0:
                    print(f"   Processed {idx} pathology records...")
                    
            except Exception as e:
                error_msg = f"Pathology row {idx}: {str(e)}"
                self.stats["errors"].append(error_msg)
                if len(self.stats["errors"]) < 20:
                    print(f"   ERROR: {error_msg}")
        
        print(f"   ✓ Updated {self.stats['pathology_updated']} tumours with pathology")
    
    def run_migration(self, dry_run: bool = False):
        """Run complete migration"""
        start_time = datetime.now()
        mode = "DRY RUN" if dry_run else "LIVE"
        
        print(f"\n{'='*60}")
        print(f"ACCESS TO MONGODB MIGRATION V4 - {mode}")
        print(f"{'='*60}")
        print(f"Enhanced with 14 new clinical fields")
        print(f"Using human-readable IDs only (no ObjectId references)")
        
        try:
            # Preload tumour data before any migrations
            self.tumour_data = self.load_tumour_data("tumours_export_new.csv")
            
            if not dry_run:
                print("\nClearing existing collections (preserving users)...")
                self.patients.delete_many({})
                self.episodes.delete_many({})
                self.treatments.delete_many({})
                self.tumours.delete_many({})
                print("✓ Collections cleared (users preserved)")
            
            # Run migrations
            self.migrate_patients("patients_export_new.csv", dry_run)
            self.migrate_surgeries("surgeries_export_new.csv", dry_run)
            self.migrate_tumours("tumours_export_new.csv", dry_run)
            self.migrate_pathology("pathology_export_new.csv", dry_run)
            
            # Print summary
            duration = (datetime.now() - start_time).total_seconds()
            print(f"\n{'='*60}")
            print(f"MIGRATION COMPLETE ({duration:.1f}s)")
            print(f"{'='*60}")
            print(f"Patients:   {self.stats['patients_created']}")
            print(f"Episodes:   {self.stats['episodes_created']}")
            print(f"Treatments: {self.stats['treatments_created']}")
            print(f"Tumours:    {self.stats['tumours_created']}")
            print(f"Pathology:  {self.stats['pathology_updated']}")
            print(f"Errors:     {len(self.stats['errors'])}")
            print(f"Warnings:   {len(self.stats['warnings'])}")
            
            if self.stats["errors"]:
                print(f"\nFirst 10 errors:")
                for err in self.stats["errors"][:10]:
                    print(f"  - {err}")
            
            if self.stats["warnings"]:
                print(f"\nTotal warnings: {len(self.stats['warnings'])} (see log file for details)")
            
            # Save detailed log
            if not dry_run:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file = f"~/.tmp/migration_log_v4_{timestamp}.json"
                with open(log_file.replace("~", "/root"), "w") as f:
                    json.dump(self.stats, f, indent=2, default=str)
                print(f"\nDetailed log saved to: {log_file}")
            
        except Exception as e:
            print(f"\nMIGRATION FAILED: {str(e)}")
            raise
        finally:
            self.client.close()


if __name__ == "__main__":
    mongodb_uri = "mongodb://admin:admin123@localhost:27017/?authSource=admin"
    dry_run = "--dry-run" in sys.argv
    
    migrator = ACPDBMigratorV4(mongodb_uri=mongodb_uri, database_name="surgdb")
    migrator.run_migration(dry_run=dry_run)
