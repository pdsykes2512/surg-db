#!/usr/bin/env python3
"""
Migrate acpdata_v3_db.mdb (Access) to MongoDB surgdb
Version 2: Updated ID schema
- Patient ID = 6-digit hash (generated from MRN using MD5)
- MRN = Stored separately, formatted as 8 digits or IW+6 digits
- Episode/Tumour/Treatment IDs = PREFIX-{patient_id}-{seq:02d}
- Internal references use MongoDB ObjectId
"""
import os
import sys
import json
import pandas as pd
import re
import hashlib
from datetime import datetime, date
from typing import Dict, Optional, Any
from pymongo import MongoClient
from bson import ObjectId


class ACPDBMigrator:
    """Migrate ACP Access database to MongoDB"""
    
    def __init__(self, mongodb_uri: str = None, database_name: str = "surgdb"):
        """Initialize migrator"""
        self.mongodb_uri = mongodb_uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.database_name = database_name
        self.client = MongoClient(self.mongodb_uri)
        self.db = self.client[self.database_name]
        
        # Collections
        self.patients = self.db.patients
        self.episodes = self.db.episodes
        self.tumours = self.db.tumours
        self.treatments = self.db.treatments
        
        # Statistics
        self.stats = {
            "patients_created": 0,
            "episodes_created": 0,
            "tumours_created": 0,
            "treatments_created": 0,
            "pathology_linked": 0,
            "errors": [],
            "warnings": []
        }
        
        # ID mappings
        self.hosp_no_to_patient = {}  # Hosp_No -> {patient_id (hash), mongo_id (ObjectId), nhs_number}
        self.surgery_to_episode = {}  # Su_SeqNo -> {episode_id, episode_mongo_id, tum_seqno, hosp_no}
        self.tumour_seq_to_mongo = {}  # TumSeqNo -> {tumour_id, mongo_id (ObjectId)}
        
        # Sequence counters per patient_id for episodes/tumours/treatments
        self.patient_episode_sequences = {}  # patient_id -> next_sequence
        self.patient_tumour_sequences = {}   # patient_id -> next_sequence
        self.patient_treatment_sequences = {}  # patient_id -> next_sequence
    
    def parse_date(self, date_val: Any) -> Optional[str]:
        """Parse Access date to YYYY-MM-DD"""
        if pd.isna(date_val) or date_val is None or date_val == "":
            return None
        
        if isinstance(date_val, (date, datetime)):
            return date_val.strftime("%Y-%m-%d")
        
        date_str = str(date_val).strip()
        
        # Try common formats
        formats = [
            "%m/%d/%y %H:%M:%S",  # Access format: 07/31/26 00:00:00
            "%m/%d/%Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%m/%d/%y",
            "%m/%d/%Y",
            "%d/%m/%Y"
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                # Fix 2-digit year (assume 1900s for >=50, 2000s for <50)
                if dt.year > 2050:
                    dt = dt.replace(year=dt.year - 100)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        self.stats["warnings"].append(f"Could not parse date: {date_val}")
        return None
    
    def parse_dob(self, date_val: Any) -> Optional[str]:
        """Parse date of birth with special handling for 2-digit years"""
        if pd.isna(date_val) or date_val is None or date_val == "":
            return None
        
        if isinstance(date_val, (date, datetime)):
            dt = date_val
        else:
            date_str = str(date_val).strip()
            
            # Try common formats
            formats = [
                "%m/%d/%y %H:%M:%S",  # Access format: 07/31/26 00:00:00
                "%m/%d/%Y %H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%m/%d/%y",
                "%m/%d/%Y",
                "%d/%m/%Y"
            ]
            
            dt = None
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            
            if dt is None:
                self.stats["warnings"].append(f"Could not parse DOB: {date_val}")
                return None
        
        # Special DOB handling: If year is in future or makes person < 10 years old, assume 1900s
        current_year = datetime.now().year
        if dt.year > current_year or (current_year - dt.year) < 10:
            dt = dt.replace(year=dt.year - 100)
        
        return dt.strftime("%Y-%m-%d")
    
    def map_gender(self, sex_val: Any) -> str:
        """Map Access Sex field to gender"""
        if pd.isna(sex_val) or not sex_val:
            return "Unknown"
        
        sex_str = str(sex_val).strip().upper()
        
        # Access uses "1 Male", "2 Female" format
        if "MALE" in sex_str and "FEMALE" not in sex_str:
            return "Male"
        elif "FEMALE" in sex_str:
            return "Female"
        elif sex_str.startswith("1"):
            return "Male"
        elif sex_str.startswith("2"):
            return "Female"
        
        return "Unknown"
    
    def map_tumour_site(self, site: Any) -> Optional[str]:
        """Map Access tumour site to MongoDB enum"""
        if pd.isna(site) or not site:
            return None
        
        site_str = str(site).strip().lower()
        
        mapping = {
            "caecum": "caecum",
            "appendix": "appendix",
            "ascending": "ascending_colon",
            "ascending colon": "ascending_colon",
            "hepatic": "hepatic_flexure",
            "hepatic flexure": "hepatic_flexure",
            "transverse": "transverse_colon",
            "transverse colon": "transverse_colon",
            "splenic": "splenic_flexure",
            "splenic flexure": "splenic_flexure",
            "descending": "descending_colon",
            "descending colon": "descending_colon",
            "sigmoid": "sigmoid_colon",
            "sigmoid colon": "sigmoid_colon",
            "rectosigmoid": "rectosigmoid_junction",
            "rectum": "rectum",
            "rectal": "rectum",
            "colon": "colon_unspecified"
        }
        
        for key, value in mapping.items():
            if key in site_str:
                return value
        
        return "other"
    
    def map_approach(self, mode_op: Any, lap_proc: Any) -> str:
        """Map surgical approach"""
        mode_str = str(mode_op).lower() if not pd.isna(mode_op) else ""
        lap_str = str(lap_proc).lower() if not pd.isna(lap_proc) else ""
        
        if "lap" in mode_str or "lap" in lap_str:
            return "laparoscopic"
        elif "robot" in mode_str or "robot" in lap_str:
            return "robotic"
        else:
            return "open"
    
    def generate_hash_id(self, mrn: str) -> str:
        """Generate a 10-digit hash from MRN for use when NHS number is missing"""
        hash_obj = hashlib.md5(mrn.encode())
        # Take first 10 characters of hex digest
        return hash_obj.hexdigest()[:10].upper()
    
    def generate_patient_hash(self, mrn: str) -> str:
        """Generate 6-digit alphanumeric hash from MRN for patient_id"""
        hash_obj = hashlib.md5(mrn.encode())
        # Take first 6 characters of hex digest and convert to uppercase
        return hash_obj.hexdigest()[:6].upper()
    
    def format_mrn(self, hosp_no: str) -> str:
        """Format MRN: 8 digits or IW + 6 digits"""
        hosp_no = str(hosp_no).strip()
        # If it's all digits, pad to 8 digits
        if hosp_no.isdigit():
            return hosp_no.zfill(8)
        # If it starts with IW, ensure it's IW + 6 digits
        if hosp_no.upper().startswith('IW'):
            digits = ''.join(filter(str.isdigit, hosp_no))
            return f"IW{digits.zfill(6)}"
        # Otherwise return as-is
        return hosp_no
    
    def generate_episode_id(self, patient_id: str) -> str:
        """Generate E-{patient_id}-{seq:02d}"""
        if patient_id not in self.patient_episode_sequences:
            self.patient_episode_sequences[patient_id] = 1
        seq = self.patient_episode_sequences[patient_id]
        self.patient_episode_sequences[patient_id] += 1
        return f"E-{patient_id}-{seq:02d}"
    
    def generate_tumour_id(self, patient_id: str) -> str:
        """Generate TUM-{patient_id}-{seq:02d}"""
        if patient_id not in self.patient_tumour_sequences:
            self.patient_tumour_sequences[patient_id] = 1
        seq = self.patient_tumour_sequences[patient_id]
        self.patient_tumour_sequences[patient_id] += 1
        return f"TUM-{patient_id}-{seq:02d}"
    
    def generate_treatment_id(self, patient_id: str, treatment_type: str = "SUR") -> str:
        """Generate {TYPE}-{patient_id}-{seq:02d}"""
        if patient_id not in self.patient_treatment_sequences:
            self.patient_treatment_sequences[patient_id] = 1
        seq = self.patient_treatment_sequences[patient_id]
        self.patient_treatment_sequences[patient_id] += 1
        return f"{treatment_type}-{patient_id}-{seq:02d}"
    
    def migrate_patients(self, csv_path: str, dry_run: bool = False):
        """Migrate patient records"""
        print(f"\n1. Migrating patients from {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"   Found {len(df)} patient records")
        
        for idx, row in df.iterrows():
            try:
                hosp_no = str(row["Hosp_No"]).strip()
                nhs_no_raw = row.get("NHS_No")
                
                # Parse NHS number - ensure it's a clean string without .0
                if not pd.isna(nhs_no_raw) and nhs_no_raw:
                    nhs_no = str(int(float(nhs_no_raw))) if str(nhs_no_raw).replace('.', '').isdigit() else str(nhs_no_raw).strip()
                else:
                    nhs_no = None
                
                # Format MRN
                mrn = self.format_mrn(hosp_no)
                
                # Generate 6-digit hash as patient_id
                patient_id = self.generate_patient_hash(mrn)
                
                # Handle missing NHS number - use patient hash as fallback
                if not nhs_no:
                    nhs_no = patient_id
                    self.stats["warnings"].append(f"Patient row {idx}: No NHS number for MRN {mrn}, using patient ID {patient_id}")
                
                # Parse DOB using specialized DOB parser
                dob_str = self.parse_dob(row["P_DOB"])
                if not dob_str:
                    self.stats["errors"].append(f"Patient row {idx}: Missing DOB for {hosp_no}")
                    continue
                
                # Extract numeric values
                height = float(row["Height"]) if not pd.isna(row.get("Height")) and row.get("Height") else None
                weight = float(row["Weight"]) if not pd.isna(row.get("Weight")) and row.get("Weight") else None
                bmi = float(row["BMI"]) if not pd.isna(row.get("BMI")) and row.get("BMI") else None
                
                # Create patient document
                patient_doc = {
                    "patient_id": patient_id,  # 6-digit hash
                    "mrn": mrn,  # Formatted MRN (8 digits or IW+6 digits)
                    "nhs_number": nhs_no,
                    "demographics": {
                        "date_of_birth": dob_str,
                        "gender": self.map_gender(row["Sex"]),
                        "postcode": str(row["Postcode"]) if not pd.isna(row.get("Postcode")) else None,
                        "height_cm": height,
                        "weight_kg": weight,
                        "bmi": bmi
                    },
                    "medical_history": {
                        "conditions": [],
                        "previous_surgeries": [],
                        "medications": [],
                        "allergies": []
                    },
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                
                if not dry_run:
                    result = self.patients.insert_one(patient_doc)
                    patient_mongo_id = result.inserted_id
                else:
                    patient_mongo_id = ObjectId()  # Fake ObjectId for dry run
                
                # Store mapping with ObjectId for internal references
                self.hosp_no_to_patient[hosp_no] = {
                    "patient_id": patient_id,  # MRN for display
                    "mongo_id": patient_mongo_id,  # ObjectId for internal linking
                    "nhs_number": nhs_no
                }
                
                self.stats["patients_created"] += 1
                
                if idx % 500 == 0 and idx > 0:
                    print(f"   Processed {idx} patients...")
                    
            except Exception as e:
                error_msg = f"Patient row {idx}: {str(e)}"
                self.stats["errors"].append(error_msg)
                if len(self.stats["errors"]) < 20:  # Only print first 20 errors
                    print(f"   ERROR: {error_msg}")
        
        print(f"   ✓ Created {self.stats['patients_created']} patients")
    
    def migrate_surgeries_and_episodes(self, csv_path: str, dry_run: bool = False):
        """Migrate surgery records to treatments and episodes"""
        print(f"\n2. Migrating surgeries from {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"   Found {len(df)} surgery records")
        
        for idx, row in df.iterrows():
            try:
                hosp_no = str(row["Hosp_No"]).strip()
                su_seqno = str(row["Su_SeqNo"]).strip()
                tum_seqno = str(row["TumSeqNo"]) if not pd.isna(row.get("TumSeqNo")) else None
                
                # Find patient
                if hosp_no not in self.hosp_no_to_patient:
                    self.stats["warnings"].append(f"Surgery {su_seqno}: Patient {hosp_no} not found")
                    continue
                
                patient_mapping = self.hosp_no_to_patient[hosp_no]
                patient_id = patient_mapping["patient_id"]  # Hash ID
                patient_mongo_id = patient_mapping["mongo_id"]  # ObjectId
                nhs_number = patient_mapping["nhs_number"]
                
                # Parse surgery date
                surgery_date_str = self.parse_date(row["Surgery"])
                if not surgery_date_str:
                    self.stats["warnings"].append(f"Surgery {su_seqno}: Missing surgery date")
                
                # Generate IDs based on patient_id (hash)
                treatment_id = self.generate_treatment_id(patient_id, "SUR")
                episode_id = self.generate_episode_id(patient_id)
                
                # Map approach
                approach = self.map_approach(row.get("ModeOp"), row.get("LapProc"))
                
                # Create treatment document
                treatment_doc = {
                    "treatment_id": treatment_id,
                    "patient_mongo_id": patient_mongo_id,  # Internal reference
                    "treatment_type": "surgery",
                    "treatment_date": surgery_date_str,
                    "treating_clinician": str(row["Surgeon"]) if not pd.isna(row.get("Surgeon")) else "Unknown",
                    "treatment_intent": "curative",  # Default
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
                    "patient_id": patient_id,  # Display MRN
                    "patient_mongo_id": patient_mongo_id,  # Internal reference
                    "condition_type": "cancer",
                    "cancer_type": "bowel",
                    "episode_date": surgery_date_str,
                    "primary_diagnosis": {
                        "description": str(row.get("ProcName", ""))
                    },
                    "treatment_mongo_ids": [],  # Will link using ObjectIds
                    "tumour_mongo_ids": [],  # Will link later using ObjectIds
                    "status": "completed",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                
                if not dry_run:
                    treatment_result = self.treatments.insert_one(treatment_doc)
                    episode_result = self.episodes.insert_one(episode_doc)
                    
                    # Update episode with treatment ObjectId
                    self.episodes.update_one(
                        {"_id": episode_result.inserted_id},
                        {"$push": {"treatment_mongo_ids": treatment_result.inserted_id}}
                    )
                    
                    episode_mongo_id = episode_result.inserted_id
                else:
                    episode_mongo_id = ObjectId()  # Fake for dry run
                
                # Store mapping
                self.surgery_to_episode[su_seqno] = {
                    "episode_id": episode_id,
                    "episode_mongo_id": episode_mongo_id,
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
        
        print(f"   ✓ Created {self.stats['treatments_created']} treatments")
        print(f"   ✓ Created {self.stats['episodes_created']} episodes")
    
    def migrate_tumours(self, csv_path: str, dry_run: bool = False):
        """Migrate tumour records"""
        print(f"\n3. Migrating tumours from {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"   Found {len(df)} tumour records")
        
        for idx, row in df.iterrows():
            try:
                tum_seqno = str(row["TumSeqno"]).strip()
                hosp_no = str(row["Hosp_No"]).strip()
                
                # Verify patient exists
                if hosp_no not in self.hosp_no_to_patient:
                    self.stats["warnings"].append(f"Tumour {tum_seqno}: Patient {hosp_no} not found")
                    continue
                
                patient_mapping = self.hosp_no_to_patient[hosp_no]
                patient_id = patient_mapping["patient_id"]  # Hash ID
                patient_mongo_id = patient_mapping["mongo_id"]
                
                # Generate tumour ID based on patient_id (hash)
                tumour_id = self.generate_tumour_id(patient_id)
                
                # Create tumour document
                tumour_doc = {
                    "tumour_id": tumour_id,
                    "patient_mongo_id": patient_mongo_id,  # Internal reference
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
                    result = self.tumours.insert_one(tumour_doc)
                    tumour_mongo_id = result.inserted_id
                    
                    # Link to episode(s) with matching TumSeqNo using ObjectId
                    for su_seq, episode_info in self.surgery_to_episode.items():
                        if episode_info["tum_seqno"] == tum_seqno and episode_info["hosp_no"] == hosp_no:
                            self.episodes.update_one(
                                {"_id": episode_info["episode_mongo_id"]},
                                {"$push": {"tumour_mongo_ids": tumour_mongo_id}}
                            )
                else:
                    tumour_mongo_id = ObjectId()  # Fake for dry run
                
                self.tumour_seq_to_mongo[tum_seqno] = {
                    "tumour_id": tumour_id,
                    "mongo_id": tumour_mongo_id
                }
                
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
                path_seqno = str(row["PthSeqNo"]).strip()  # Changed from PathSeqno
                tum_seqno = str(row["TumSeqNo"]) if not pd.isna(row.get("TumSeqNo")) else None
                
                if not tum_seqno or tum_seqno not in self.tumour_seq_to_mongo:
                    self.stats["warnings"].append(f"Pathology {path_seqno}: Tumour {tum_seqno} not found")
                    continue
                
                tumour_info = self.tumour_seq_to_mongo[tum_seqno]
                tumour_mongo_id = tumour_info["mongo_id"]
                
                # Extract pathology data - map field names from Access CSV
                pathology_data = {
                    "differentiation": str(row["HistGrad"]) if not pd.isna(row.get("HistGrad")) else None,
                    "t_stage": str(row["TNM_Tumr"]) if not pd.isna(row.get("TNM_Tumr")) else None,
                    "n_stage": str(row["TNM_Nods"]) if not pd.isna(row.get("TNM_Nods")) else None,
                    "m_stage": str(row["TNM_Mets"]) if not pd.isna(row.get("TNM_Mets")) else None,
                    "resection_margin": str(row["resect_grade"]).strip() if not pd.isna(row.get("resect_grade")) else None,
                    "dukes_stage": str(row["Dukes"]).strip() if not pd.isna(row.get("Dukes")) else None
                }
                
                # Update tumour with pathology data
                if not dry_run:
                    self.tumours.update_one(
                        {"_id": tumour_mongo_id},
                        {"$set": {"pathology": pathology_data, "updated_at": datetime.utcnow()}}
                    )
                
                self.stats["pathology_linked"] += 1
                
                if idx % 500 == 0 and idx > 0:
                    print(f"   Processed {idx} pathology records...")
                    
            except Exception as e:
                error_msg = f"Pathology row {idx}: {str(e)}"
                self.stats["errors"].append(error_msg)
                if len(self.stats["errors"]) < 20:
                    print(f"   ERROR: {error_msg}")
        
        print(f"   ✓ Linked {self.stats['pathology_linked']} pathology records")
    
    def run_migration(self, export_dir: str = "~/.tmp/access_export", dry_run: bool = False):
        """Run full migration"""
        export_dir = os.path.expanduser(export_dir)
        
        print("=" * 60)
        print("ACP Access Database to MongoDB Migration v2")
        print("=" * 60)
        print(f"Target database: {self.database_name}")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        print("=" * 60)
        
        if not dry_run:
            response = input("\nThis will modify the database. Continue? (yes/no): ")
            if response.lower() != "yes":
                print("Migration cancelled.")
                return
        
        try:
            # Step 1: Migrate patients
            self.migrate_patients(f"{export_dir}/patients.csv", dry_run)
            
            # Step 2: Migrate surgeries -> treatments + episodes
            self.migrate_surgeries_and_episodes(f"{export_dir}/surgeries.csv", dry_run)
            
            # Step 3: Migrate tumours
            self.migrate_tumours(f"{export_dir}/tumours.csv", dry_run)
            
            # Step 4: Link pathology to tumours
            self.migrate_pathology(f"{export_dir}/pathology.csv", dry_run)
            
            # Print summary
            print("\n" + "=" * 60)
            print("MIGRATION SUMMARY")
            print("=" * 60)
            print(f"Patients created:      {self.stats['patients_created']}")
            print(f"Episodes created:      {self.stats['episodes_created']}")
            print(f"Treatments created:    {self.stats['treatments_created']}")
            print(f"Tumours created:       {self.stats['tumours_created']}")
            print(f"Pathology linked:      {self.stats['pathology_linked']}")
            print(f"Errors:                {len(self.stats['errors'])}")
            print(f"Warnings:              {len(self.stats['warnings'])}")
            print("=" * 60)
            
            # Save log
            log_file = os.path.expanduser(f"~/.tmp/migration_log_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(log_file, 'w') as f:
                json.dump(self.stats, f, indent=2, default=str)
            print(f"\nDetailed log saved to: {log_file}")
            
            if self.stats["errors"]:
                print("\nSample errors (first 10):")
                for err in self.stats["errors"][:10]:
                    print(f"  - {err}")
            
            if self.stats["warnings"]:
                print(f"\nTotal warnings: {len(self.stats['warnings'])} (see log file for details)")
            
        except Exception as e:
            print(f"\nMIGRATION FAILED: {str(e)}")
            raise
        finally:
            self.client.close()


if __name__ == "__main__":
    # MongoDB connection
    mongodb_uri = "mongodb://admin:admin123@localhost:27017/?authSource=admin"
    
    # Run with --dry-run to test without modifying database
    dry_run = "--dry-run" in sys.argv
    
    migrator = ACPDBMigrator(mongodb_uri=mongodb_uri, database_name="surgdb")
    migrator.run_migration(dry_run=dry_run)
