#!/usr/bin/env python3
"""
Migrate acpdata_v3_db.mdb (Access) to MongoDB surgdb
Customized for the specific Access schema structure
"""
import os
import sys
import json
import pandas as pd
import re
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
        self.hosp_no_to_patient = {}  # Hosp_No -> {new_patient_id, mongo_id}
        self.surgery_to_episode = {}  # Su_SeqNo -> episode_id
        self.tumour_seq_to_mongo = {}  # TumSeqNo -> mongo tumour_id
        
        # Counters for new IDs
        self.patient_counter = 1
        self.episode_counter = 1
        self.treatment_counter = 1
    
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
    
    def generate_patient_id(self, dob: Optional[date] = None) -> str:
        """Generate P-YYYYMMDD-XXXX"""
        ref_date = dob if dob else date.today()
        date_str = ref_date.strftime("%Y%m%d")
        new_id = f"P-{date_str}-{self.patient_counter:04d}"
        self.patient_counter += 1
        return new_id
    
    def generate_episode_id(self, surgery_date: Optional[date] = None) -> str:
        """Generate E-YYYYMMDD-XXXX"""
        ref_date = surgery_date if surgery_date else date.today()
        date_str = ref_date.strftime("%Y%m%d")
        new_id = f"E-{date_str}-{self.episode_counter:04d}"
        self.episode_counter += 1
        return new_id
    
    def generate_treatment_id(self, surgery_date: Optional[date] = None) -> str:
        """Generate T-YYYYMMDD-XXXX"""
        ref_date = surgery_date if surgery_date else date.today()
        date_str = ref_date.strftime("%Y%m%d")
        new_id = f"T-{date_str}-{self.treatment_counter:04d}"
        self.treatment_counter += 1
        return new_id
    
    def migrate_patients(self, csv_path: str, dry_run: bool = False):
        """Migrate patient records"""
        print(f"\n1. Migrating patients from {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"   Found {len(df)} patient records")
        
        for idx, row in df.iterrows():
            try:
                hosp_no = str(row["Hosp_No"]).strip()
                nhs_no = str(row["NHS_No"]).strip() if not pd.isna(row.get("NHS_No")) else None
                
                # Parse DOB
                dob_str = self.parse_date(row["P_DOB"])
                if not dob_str:
                    self.stats["errors"].append(f"Patient row {idx}: Missing DOB for {hosp_no}")
                    continue
                
                dob_date = datetime.strptime(dob_str, "%Y-%m-%d").date()
                new_patient_id = self.generate_patient_id(dob_date)
                
                # Extract numeric values
                height = float(row["Height"]) if not pd.isna(row.get("Height")) and row.get("Height") else None
                weight = float(row["Weight"]) if not pd.isna(row.get("Weight")) and row.get("Weight") else None
                bmi = float(row["BMI"]) if not pd.isna(row.get("BMI")) and row.get("BMI") else None
                
                # Create patient document
                patient_doc = {
                    "patient_id": new_patient_id,
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
                    self.hosp_no_to_patient[hosp_no] = {
                        "new_id": new_patient_id,
                        "mongo_id": result.inserted_id
                    }
                else:
                    self.hosp_no_to_patient[hosp_no] = {
                        "new_id": new_patient_id,
                        "mongo_id": None
                    }
                
                self.stats["patients_created"] += 1
                
                if idx % 500 == 0 and idx > 0:
                    print(f"   Processed {idx} patients...")
                    
            except Exception as e:
                error_msg = f"Patient row {idx}: {str(e)}"
                self.stats["errors"].append(error_msg)
                if self.stats["errors"].__len__() < 20:  # Only print first 20 errors
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
                new_patient_id = patient_mapping["new_id"]
                
                # Parse surgery date
                surgery_date_str = self.parse_date(row["Surgery"])
                if not surgery_date_str:
                    self.stats["warnings"].append(f"Surgery {su_seqno}: Missing surgery date")
                    continue
                
                surgery_date = datetime.strptime(surgery_date_str, "%Y-%m-%d").date()
                
                # Generate IDs
                treatment_id = self.generate_treatment_id(surgery_date)
                episode_id = self.generate_episode_id(surgery_date)
                
                # Map approach
                approach = self.map_approach(row.get("ModeOp"), row.get("LapProc"))
                
                # Create treatment document
                treatment_doc = {
                    "treatment_id": treatment_id,
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
                    "patient_id": new_patient_id,
                    "condition_type": "cancer",
                    "cancer_type": "bowel",
                    "episode_date": surgery_date_str,
                    "primary_diagnosis": {
                        "description": str(row.get("ProcName", ""))
                    },
                    "treatments": [treatment_id],
                    "tumours": [],  # Will link later
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
                    "hosp_no": hosp_no
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
                
                # Create tumour document
                tumour_doc = {
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
                    tumour_mongo_id = str(result.inserted_id)
                    
                    # Link to episode(s) with matching TumSeqNo
                    for su_seq, episode_info in self.surgery_to_episode.items():
                        if episode_info["tum_seqno"] == tum_seqno and episode_info["hosp_no"] == hosp_no:
                            self.episodes.update_one(
                                {"episode_id": episode_info["episode_id"]},
                                {"$push": {"tumours": tumour_mongo_id}}
                            )
                    
                    self.tumour_seq_to_mongo[tum_seqno] = tumour_mongo_id
                
                self.stats["tumours_created"] += 1
                
                if idx % 500 == 0 and idx > 0:
                    print(f"   Processed {idx} tumours...")
                    
            except Exception as e:
                error_msg = f"Tumour row {idx}: {str(e)}"
                self.stats["errors"].append(error_msg)
                if len(self.stats["errors"]) < 20:
                    print(f"   ERROR: {error_msg}")
        
        print(f"   ✓ Created {self.stats['tumours_created']} tumours")
    
    def link_pathology(self, csv_path: str, dry_run: bool = False):
        """Link pathology data to tumours"""
        print(f"\n4. Linking pathology from {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"   Found {len(df)} pathology records")
        
        for idx, row in df.iterrows():
            try:
                tum_seqno = str(row["TumSeqNo"]) if not pd.isna(row.get("TumSeqNo")) else None
                
                if not tum_seqno or tum_seqno not in self.tumour_seq_to_mongo:
                    continue
                
                tumour_id = self.tumour_seq_to_mongo[tum_seqno]
                
                # Update tumour with pathology data
                pathology_update = {
                    "histology_type": str(row["HistType"]) if not pd.isna(row.get("HistType")) else None,
                    "grade": str(row["HistGrad"]) if not pd.isna(row.get("HistGrad")) else None,
                    "staging.t_stage": str(row["TNM_Tumr"]).strip() if not pd.isna(row.get("TNM_Tumr")) else None,
                    "staging.n_stage": str(row["TNM_Nods"]).strip() if not pd.isna(row.get("TNM_Nods")) else None,
                    "staging.m_stage": str(row["TNM_Mets"]).strip() if not pd.isna(row.get("TNM_Mets")) else None,
                    "staging.dukes": str(row["Dukes"]) if not pd.isna(row.get("Dukes")) else None,
                    "lymph_nodes_examined": int(row["NoLyNoF"]) if not pd.isna(row.get("NoLyNoF")) else None,
                    "lymph_nodes_positive": int(row["NoLyNoP"]) if not pd.isna(row.get("NoLyNoP")) else None,
                }
                
                # Remove None values
                pathology_update = {k: v for k, v in pathology_update.items() if v is not None}
                
                if pathology_update and not dry_run:
                    self.tumours.update_one(
                        {"_id": ObjectId(tumour_id)},
                        {"$set": pathology_update}
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
    
    def print_summary(self):
        """Print migration summary"""
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Patients:    {self.stats['patients_created']}")
        print(f"Episodes:    {self.stats['episodes_created']}")
        print(f"Treatments:  {self.stats['treatments_created']}")
        print(f"Tumours:     {self.stats['tumours_created']}")
        print(f"Pathology:   {self.stats['pathology_linked']}")
        print(f"\nWarnings:    {len(self.stats['warnings'])}")
        print(f"Errors:      {len(self.stats['errors'])}")
        
        if self.stats['warnings'] and len(self.stats['warnings']) <= 20:
            print("\nWARNINGS:")
            for warning in self.stats['warnings']:
                print(f"  - {warning}")
        elif len(self.stats['warnings']) > 20:
            print(f"\nFirst 20 WARNINGS:")
            for warning in self.stats['warnings'][:20]:
                print(f"  - {warning}")
        
        if self.stats['errors']:
            print(f"\nFirst 20 ERRORS:")
            for error in self.stats['errors'][:20]:
                print(f"  - {error}")
        
        # Save log
        log_path = os.path.expanduser(f"~/.tmp/migration_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(log_path, 'w') as f:
            json.dump(self.stats, f, indent=2)
        print(f"\nDetailed log: {log_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate ACP Access database to MongoDB")
    parser.add_argument("--csv-dir", required=True, help="Directory with CSV exports")
    parser.add_argument("--dry-run", action="store_true", help="Dry run without inserting")
    parser.add_argument("--mongodb-uri", help="MongoDB URI")
    parser.add_argument("--database", default="surgdb", help="Database name")
    
    args = parser.parse_args()
    
    csv_dir = os.path.expanduser(args.csv_dir)
    
    # Check files exist
    required_files = ["patients.csv", "surgeries.csv", "tumours.csv", "pathology.csv"]
    for f in required_files:
        fpath = os.path.join(csv_dir, f)
        if not os.path.exists(fpath):
            print(f"ERROR: {fpath} not found")
            sys.exit(1)
    
    print("=" * 60)
    print("ACP ACCESS DATABASE MIGRATION")
    print("=" * 60)
    print(f"Source: {csv_dir}")
    print(f"Target: MongoDB {args.database}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE MIGRATION'}")
    print("=" * 60)
    
    # Create migrator
    migrator = ACPDBMigrator(mongodb_uri=args.mongodb_uri, database_name=args.database)
    
    # Run migration
    migrator.migrate_patients(os.path.join(csv_dir, "patients.csv"), args.dry_run)
    migrator.migrate_surgeries_and_episodes(os.path.join(csv_dir, "surgeries.csv"), args.dry_run)
    migrator.migrate_tumours(os.path.join(csv_dir, "tumours.csv"), args.dry_run)
    migrator.link_pathology(os.path.join(csv_dir, "pathology.csv"), args.dry_run)
    
    # Print summary
    migrator.print_summary()
    
    if args.dry_run:
        print("\n⚠ DRY RUN - No data was inserted into MongoDB")
        print("Review the output, then run without --dry-run to perform actual migration")


if __name__ == "__main__":
    main()
