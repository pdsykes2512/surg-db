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

class ACPDBMigratorV3:
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
        
        # Load legacy surgeon mappings
        self.legacy_surgeons = self.load_legacy_surgeons()
        
        # Sequence trackers per patient_id
        self.patient_episode_sequences = {}
        self.patient_tumour_sequences = {}
        self.patient_treatment_sequences = {}
        
        self.stats = {
            "patients_created": 0,
            "episodes_created": 0,
            "treatments_created": 0,
            "tumours_created": 0,
            "pathology_updated": 0,
            "errors": [],
            "warnings": []
        }
    
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
    
    def map_approach(self, mode_op, lap_proc):
        """Map surgical approach"""
        if not pd.isna(lap_proc):
            lap_str = str(lap_proc).lower()
            if "lap" in lap_str or "laparoscopic" in lap_str:
                return "laparoscopic"
        return "open"
    
    def map_tumour_site(self, tum_site):
        """Map tumour site"""
        if pd.isna(tum_site):
            return None
        site_map = {
            "1": "caecum",
            "2": "ascending_colon",
            "3": "hepatic_flexure",
            "4": "transverse_colon",
            "5": "splenic_flexure",
            "6": "descending_colon",
            "7": "sigmoid_colon",
            "8": "rectosigmoid",
            "9": "rectum",
            "10": "anus"
        }
        site_str = str(tum_site).strip()
        return site_map.get(site_str, f"site_{site_str}")
    
    def map_no_surgery_reason(self, no_surg_value):
        """Map NoSurg field to readable reason"""
        if pd.isna(no_surg_value):
            return None
        
        no_surg_str = str(no_surg_value).strip()
        
        # Check if it starts with a number
        if no_surg_str.startswith('1'):
            return "Patient refused treatment"
        elif no_surg_str.startswith('2'):
            return "Patient unfit"
        elif no_surg_str.startswith('3'):
            return "Advanced disease"
        elif no_surg_str.startswith('4'):
            return "Other"
        
        return no_surg_str
    
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
    
    def load_legacy_surgeons(self):
        """Load legacy surgeon mappings"""
        try:
            with open('legacy_surgeons.json', 'r') as f:
                surgeons = json.load(f)
                return {s['name']: s['id'] for s in surgeons}
        except FileNotFoundError:
            self.stats["warnings"].append("legacy_surgeons.json not found, surgeon names will be used as-is")
            return {}

    
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
                        "height_cm": float(row["Height"]) if not pd.isna(row.get("Height")) and row.get("Height") != "" else None
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
                
                # Create treatment document
                treatment_doc = {
                    "treatment_id": treatment_id,
                    "patient_id": patient_id,
                    "episode_id": episode_id,
                    "treatment_type": "surgery",
                    "treatment_date": surgery_date_str,
                    "treating_clinician": str(row["Surgeon"]) if not pd.isna(row.get("Surgeon")) else "Unknown",
                    "treatment_intent": "curative",
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
                
                # Create episode document
                episode_doc = {
                    "episode_id": episode_id,
                    "patient_id": patient_id,
                    "condition_type": "cancer",
                    "cancer_type": "bowel",
                    "referral_date": surgery_date_str,
                    "primary_diagnosis": {
                        "description": str(row.get("ProcName", ""))
                    },
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
        """Migrate tumour records"""
        print(f"\n3. Migrating tumours from {csv_path}")
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
                
                # Create tumour document
                tumour_doc = {
                    "tumour_id": tumour_id,
                    "patient_id": patient_id,
                    "episode_id": episode_id,
                    "site": self.map_tumour_site(row.get("TumSite")),
                    "tumour_type": "primary",
                    "diagnosis_date": self.parse_date(row.get("Dt_Diag")),
                    "staging": {
                        "t_stage": str(row["preTNM_T"]).strip() if not pd.isna(row.get("preTNM_T")) else None,
                        "n_stage": str(row["preTNM_N"]).strip() if not pd.isna(row.get("preTNM_N")) else None,
                        "m_stage": str(row["preTNM_M"]).strip() if not pd.isna(row.get("preTNM_M")) else None,
                    },
                    "icd10_code": str(row["TumICD10"]) if not pd.isna(row.get("TumICD10")) else None,
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
        print(f"ACCESS TO MONGODB MIGRATION V3 - {mode}")
        print(f"{'='*60}")
        print(f"Using human-readable IDs only (no ObjectId references)")
        
        try:
            if not dry_run:
                print("\nClearing existing collections...")
                self.patients.delete_many({})
                self.episodes.delete_many({})
                self.treatments.delete_many({})
                self.tumours.delete_many({})
                print("✓ Collections cleared")
            
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
                log_file = f"~/.tmp/migration_log_v3_{timestamp}.json"
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
    
    migrator = ACPDBMigratorV3(mongodb_uri=mongodb_uri, database_name="surgdb")
    migrator.run_migration(dry_run=dry_run)
