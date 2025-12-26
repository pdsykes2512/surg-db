#!/usr/bin/env python3
"""
Fresh import of CSV data into NEW database with all improvements:
- Better field mappings (Hosp_No → PAS_No → mrn)
- Lead clinician population from CSV surgeon field
- Proper complication detection (excluding readmissions)
- Date fallbacks (referral_date, first_seen_date contingencies)
- Comprehensive field extraction

Imports into surgdb_v2 to preserve current data for comparison.
"""

import pandas as pd
import hashlib
from datetime import datetime, timedelta
from pymongo import MongoClient
from typing import Dict, Optional, List
import re

class ImprovedImporter:
    def __init__(self, test_db_name: str = "surgdb_v2"):
        self.client = MongoClient('mongodb://admin:admin123@localhost:27017')
        self.db = self.client[test_db_name]
        
        # Collections
        self.patients = self.db.patients
        self.episodes = self.db.episodes
        self.treatments = self.db.treatments
        self.tumours = self.db.tumours
        
        # Clear existing data
        for coll in ['patients', 'episodes', 'treatments', 'tumours']:
            self.db[coll].delete_many({})
        
        # Mappings
        self.hosp_no_to_patient_id = {}  # Hosp_No -> patient_id (mrn)
        self.pas_no_to_patient_id = {}   # PAS_No -> patient_id (mrn)
        self.patient_episode_count = {}   # patient_id -> episode count
        self.patient_tumour_count = {}    # patient_id -> tumour count
        self.patient_treatment_count = {} # patient_id -> treatment count
        
        # Stats
        self.stats = {
            'patients': 0,
            'episodes': 0,
            'treatments': 0,
            'tumours': 0,
            'lead_clinician_from_csv': 0,
            'complications_detected': 0,
            'dates_from_fallback': 0,
        }
        
    def generate_patient_id(self, pas_no: str) -> str:
        """Generate 6-char hex patient ID from PAS_No"""
        hash_obj = hashlib.md5(str(pas_no).encode())
        return hash_obj.hexdigest()[:6].upper()
    
    def parse_date(self, date_val) -> Optional[str]:
        """Parse date from various formats"""
        if pd.isna(date_val) or date_val == '' or date_val is None:
            return None
        
        if isinstance(date_val, datetime):
            return date_val.strftime('%Y-%m-%d')
        
        date_str = str(date_val).strip()
        
        formats = [
            '%m/%d/%y %H:%M:%S',
            '%m/%d/%Y %H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%m/%d/%y',
            '%m/%d/%Y',
            '%d/%m/%Y'
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                # Fix 2-digit year
                if dt.year > 2050:
                    dt = dt.replace(year=dt.year - 100)
                return dt.strftime('%Y-%m-%d')
            except:
                continue
        
        return None
    
    def parse_dob(self, date_val) -> Optional[str]:
        """Parse DOB with special handling"""
        parsed = self.parse_date(date_val)
        if not parsed:
            return None
        
        dt = datetime.strptime(parsed, '%Y-%m-%d')
        current_year = datetime.now().year
        
        # If year is in future or makes person < 10 years old, assume 1900s
        if dt.year > current_year or (current_year - dt.year) < 10:
            dt = dt.replace(year=dt.year - 100)
            return dt.strftime('%Y-%m-%d')
        
        return parsed
    
    def import_patients(self, patient_csv: str):
        """Import patients with improved mapping"""
        print("=== Importing Patients ===")
        df = pd.read_csv(patient_csv, low_memory=False)
        
        for idx, row in df.iterrows():
            pas_no = str(row.get('PAS_No', '')).strip()
            if not pas_no or pas_no == 'nan':
                continue
            
            patient_id = self.generate_patient_id(pas_no)
            
            # Build patient document
            patient_doc = {
                'patient_id': patient_id,
                'mrn': pas_no,  # Store PAS_No as MRN
                'nhs_number': str(row.get('NHS_No', '')).strip() or None,
                'hospital_number': str(row.get('Hosp_No', '')).strip() or None,  # Fixed: Hosp_No not Hospital_No
                'demographics': {
                    'first_name': str(row.get('Forename', '')).strip() or None,
                    'last_name': str(row.get('Surname', '')).strip() or None,
                    'date_of_birth': self.parse_dob(row.get('P_DOB')),  # Fixed: P_DOB not DOB
                    'gender': str(row.get('Sex', '')).strip() or 'Unknown',
                    'ethnicity': None,  # Not in CSV
                },
                'contact': {
                    'address_line_1': None,  # Not in CSV
                    'address_line_2': None,
                    'city': None,
                    'postcode': str(row.get('Postcode', '')).strip() or None,
                },
                'gp': {
                    'name': None,  # Not in CSV
                    'practice': None,
                },
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
            }
            
            self.patients.insert_one(patient_doc)
            
            # Build mappings - KEY IMPROVEMENT: Use Hosp_No
            hospital_no = str(row.get('Hosp_No', '')).strip()
            if hospital_no and hospital_no != 'nan':
                self.hosp_no_to_patient_id[hospital_no] = patient_id
            
            self.pas_no_to_patient_id[pas_no] = patient_id
            self.stats['patients'] += 1
            
            if (idx + 1) % 500 == 0:
                print(f"  Processed {idx + 1} patients...")
        
        print(f"✓ Imported {self.stats['patients']} patients")
        print(f"  - Hosp_No mappings: {len(self.hosp_no_to_patient_id)}")
        print(f"  - PAS_No mappings: {len(self.pas_no_to_patient_id)}")
    
    def has_complication(self, row) -> bool:
        """Check for TRUE complications (excluding readmissions)"""
        complication_fields = ['MJ_Leak', 'MI_Leak', 'Cardio', 'MJ_Bleed', 'MI_Bleed']
        
        for field in complication_fields:
            val = str(row.get(field, '')).strip().lower()
            if val in ['1', 'yes', 'true', 'y']:
                return True
        
        return False
    
    def import_surgeries(self, surgery_csv: str):
        """Import surgeries as episodes and treatments with IMPROVED LEAD CLINICIAN"""
        print("\n=== Importing Surgeries ===")
        df = pd.read_csv(surgery_csv, low_memory=False)
        
        for idx, row in df.iterrows():
            hosp_no = str(row.get('Hosp_No', '')).strip()
            if not hosp_no or hosp_no == 'nan':
                continue
            
            # KEY IMPROVEMENT: Use Hosp_No → patient_id mapping
            patient_id = self.hosp_no_to_patient_id.get(hosp_no)
            if not patient_id:
                continue
            
            # Generate episode ID
            ep_seq = self.patient_episode_count.get(patient_id, 0) + 1
            self.patient_episode_count[patient_id] = ep_seq
            episode_id = f"E-{patient_id}-{ep_seq:02d}"
            
            # Date handling with fallback - IMPROVEMENT
            referral_date = self.parse_date(row.get('DateRefS'))  # Fixed: DateRefS not Refferal_date
            cns_date = self.parse_date(row.get('CNS_date'))
            surgery_date = self.parse_date(row.get('Surgery'))
            
            # Use best available date
            first_seen_date = referral_date or cns_date
            if not first_seen_date and surgery_date:
                # Fallback: estimate referral as 3 months before surgery
                try:
                    surgery_dt = datetime.strptime(surgery_date, '%Y-%m-%d')
                    first_seen_date = (surgery_dt - timedelta(days=90)).strftime('%Y-%m-%d')
                    self.stats['dates_from_fallback'] += 1
                except:
                    pass
            
            # KEY IMPROVEMENT: Extract surgeon from CSV for lead_clinician
            surgeon_name = str(row.get('Surgeon', '')).strip()
            lead_clinician = None
            if surgeon_name and surgeon_name != 'nan':
                lead_clinician = surgeon_name
                self.stats['lead_clinician_from_csv'] += 1
            
            # Build episode document
            episode_doc = {
                'episode_id': episode_id,
                'patient_id': patient_id,
                'cancer_type': 'bowel',
                'referral_date': referral_date,
                'first_seen_date': first_seen_date,
                'lead_clinician': lead_clinician,  # IMPROVEMENT: Now populated!
                'mdt_date': None,  # Not directly in surgery CSV
                'tumour_site': None,  # Will be populated from tumour CSV
                'histology': None,  # Will be populated from tumour CSV
                'clinical_t_stage': None,  # Not in surgery CSV
                'clinical_n_stage': None,
                'clinical_m_stage': None,
                'treatment_ids': [],
                'tumour_ids': [],
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
            }
            
            result = self.episodes.insert_one(episode_doc)
            episode_mongo_id = result.inserted_id
            self.stats['episodes'] += 1
            
            # Create surgery treatment if surgery exists
            if surgery_date:
                treat_seq = self.patient_treatment_count.get(patient_id, 0) + 1
                self.patient_treatment_count[patient_id] = treat_seq
                treatment_id = f"T-{patient_id}-{treat_seq:02d}"
                
                # IMPROVEMENT: Detect complications properly
                has_complication = self.has_complication(row)
                if has_complication:
                    self.stats['complications_detected'] += 1
                
                # Calculate length of stay
                los = None
                date_dis = self.parse_date(row.get('Date_Dis'))
                if surgery_date and date_dis:
                    try:
                        surg_dt = datetime.strptime(surgery_date, '%Y-%m-%d')
                        dis_dt = datetime.strptime(date_dis, '%Y-%m-%d')
                        los = (dis_dt - surg_dt).days
                    except:
                        pass
                
                treatment_doc = {
                    'treatment_id': treatment_id,
                    'episode_id': episode_id,
                    'patient_id': patient_id,
                    'treatment_type': 'surgery',
                    'treatment_date': surgery_date,
                    'surgeon': surgeon_name if surgeon_name != 'nan' else None,
                    'surgery_type': str(row.get('ProcName', '')).strip() or None,  # Fixed: ProcName not Operation
                    'approach': str(row.get('ModeOp', '')).strip() or None,  # Fixed: ModeOp not Approach
                    'urgency': str(row.get('ASA', '')).strip().lower() or None,  # ASA as proxy for urgency
                    'complications': has_complication,
                    'complication_details': self.extract_complications(row),
                    'length_of_stay': los,
                    'readmission': False,  # Not tracked separately in this CSV
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                }
                
                result = self.treatments.insert_one(treatment_doc)
                
                # Link treatment to episode
                self.episodes.update_one(
                    {'_id': episode_mongo_id},
                    {'$push': {'treatment_ids': treatment_id}}
                )
                
                self.stats['treatments'] += 1
            
            if (idx + 1) % 500 == 0:
                print(f"  Processed {idx + 1} surgeries...")
        
        print(f"✓ Imported {self.stats['episodes']} episodes")
        print(f"✓ Imported {self.stats['treatments']} treatments")
        print(f"  - Lead clinicians populated: {self.stats['lead_clinician_from_csv']}")
        print(f"  - Complications detected: {self.stats['complications_detected']}")
        print(f"  - Dates from fallback: {self.stats['dates_from_fallback']}")
    
    def extract_complications(self, row) -> Optional[str]:
        """Extract complication details"""
        complications = []
        
        comp_map = {
            'MJ_Leak': 'Major anastomotic leak',
            'MI_Leak': 'Minor anastomotic leak',
            'Cardio': 'Cardiovascular complication',
            'MJ_Bleed': 'Major bleeding',
            'MI_Bleed': 'Minor bleeding',
        }
        
        for field, description in comp_map.items():
            val = str(row.get(field, '')).strip().lower()
            if val in ['1', 'yes', 'true', 'y']:
                complications.append(description)
        
        return '; '.join(complications) if complications else None
    
    def parse_int(self, val) -> Optional[int]:
        """Parse integer value"""
        if pd.isna(val) or val == '' or val is None:
            return None
        try:
            return int(float(val))
        except:
            return None
    
    def import_tumours(self, tumour_csv: str):
        """Import tumour data"""
        print("\n=== Importing Tumours ===")
        df = pd.read_csv(tumour_csv, low_memory=False)
        
        for idx, row in df.iterrows():
            hosp_no = str(row.get('Hosp_No', '')).strip()
            if not hosp_no or hosp_no == 'nan':
                continue
            
            patient_id = self.hosp_no_to_patient_id.get(hosp_no)
            if not patient_id:
                continue
            
            # Find matching episode (by patient and approximate date)
            surgery_date = self.parse_date(row.get('Surgery'))
            episode = None
            
            if surgery_date:
                # Find episode with surgery treatment around this date
                episodes = list(self.episodes.find({'patient_id': patient_id}))
                for ep in episodes:
                    for treat_id in ep.get('treatment_ids', []):
                        treatment = self.treatments.find_one({'treatment_id': treat_id})
                        if treatment and treatment.get('treatment_type') == 'surgery':
                            treat_date = treatment.get('treatment_date')
                            if treat_date:
                                # Match within 7 days
                                try:
                                    treat_dt = datetime.strptime(treat_date, '%Y-%m-%d')
                                    surg_dt = datetime.strptime(surgery_date, '%Y-%m-%d')
                                    if abs((treat_dt - surg_dt).days) <= 7:
                                        episode = ep
                                        break
                                except:
                                    pass
                    if episode:
                        break
            
            if not episode:
                # Just use first episode for this patient
                episode = self.episodes.find_one({'patient_id': patient_id})
            
            if not episode:
                continue
            
            # Generate tumour ID
            tum_seq = self.patient_tumour_count.get(patient_id, 0) + 1
            self.patient_tumour_count[patient_id] = tum_seq
            tumour_id = f"TUM-{patient_id}-{tum_seq:02d}"
            
            tumour_doc = {
                'tumour_id': tumour_id,
                'episode_id': episode['episode_id'],
                'patient_id': patient_id,
                'site': str(row.get('Primary', '')).strip() or None,
                'histology': str(row.get('Histology', '')).strip() or None,
                'grade': str(row.get('Grade', '')).strip() or None,
                'pathological_t_stage': str(row.get('Path_T', '')).strip() or None,
                'pathological_n_stage': str(row.get('Path_N', '')).strip() or None,
                'pathological_m_stage': str(row.get('Path_M', '')).strip() or None,
                'nodes_examined': self.parse_int(row.get('Nodes_examined')),
                'nodes_positive': self.parse_int(row.get('Nodes_positive')),
                'crm_involved': str(row.get('CRM', '')).strip().lower() in ['1', 'yes', 'true', 'positive'],
                'crm_distance': self.parse_int(row.get('CRM_distance')),
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
            }
            
            result = self.tumours.insert_one(tumour_doc)
            
            # Link tumour to episode
            self.episodes.update_one(
                {'episode_id': episode['episode_id']},
                {'$push': {'tumour_ids': tumour_id}}
            )
            
            self.stats['tumours'] += 1
            
            if (idx + 1) % 500 == 0:
                print(f"  Processed {idx + 1} tumours...")
        
        print(f"✓ Imported {self.stats['tumours']} tumours")
    
    def print_summary(self):
        """Print import summary"""
        print("\n" + "="*60)
        print("IMPORT SUMMARY")
        print("="*60)
        for key, value in self.stats.items():
            print(f"{key:.<40} {value:>15,}")
        print("="*60)


def main():
    print("Starting fresh import with improvements into surgdb_v2...\n")
    
    importer = ImprovedImporter(test_db_name='surgdb_v2')
    
    # Import in order
    importer.import_patients('/root/.tmp/patient_export.csv')
    importer.import_surgeries('/root/.tmp/surgery_mdt_referral_export.csv')
    importer.import_tumours('/root/.tmp/tumour_export.csv')
    
    importer.print_summary()
    
    print("\n✓ Import complete! Data is in 'surgdb_v2' database.")
    print("  Current data remains in 'surgdb' database.")


if __name__ == '__main__':
    main()
