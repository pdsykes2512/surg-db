#!/usr/bin/env python3
"""
Migrate historical data from Access database to MongoDB
Handles CSV exports, Excel files, or direct Access database connections
"""
import os
import sys
import json
import csv
import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from pymongo import MongoClient
from bson import ObjectId
import re


class AccessToMongoMigrator:
    """Migrate Access database to MongoDB with new schema structure"""
    
    def __init__(self, mongodb_uri: str = None, database_name: str = "surgdb"):
        """Initialize migrator with MongoDB connection"""
        self.mongodb_uri = mongodb_uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.database_name = database_name
        self.client = MongoClient(self.mongodb_uri)
        self.db = self.client[self.database_name]
        
        # Collections
        self.patients = self.db.patients
        self.episodes = self.db.episodes
        self.tumours = self.db.tumours
        self.treatments = self.db.treatments
        
        # Tracking
        self.stats = {
            "patients_created": 0,
            "episodes_created": 0,
            "tumours_created": 0,
            "treatments_created": 0,
            "errors": [],
            "warnings": []
        }
        
        # ID counters for new format (P-YYYYMMDD-XXXX)
        self.patient_counter = 1
        self.episode_counter = 1
        self.treatment_counter = 1
        self.tumour_counter = 1
        
        # Mapping of old IDs to new MongoDB IDs
        self.patient_id_map = {}  # old_id -> new_patient_id
        self.episode_id_map = {}  # old_id -> new_episode_id
        
    def generate_patient_id(self, date_ref: date = None) -> str:
        """Generate new patient ID: P-YYYYMMDD-XXXX"""
        if date_ref is None:
            date_ref = date.today()
        date_str = date_ref.strftime("%Y%m%d")
        new_id = f"P-{date_str}-{self.patient_counter:04d}"
        self.patient_counter += 1
        return new_id
    
    def generate_episode_id(self, date_ref: date = None) -> str:
        """Generate new episode ID: E-YYYYMMDD-XXXX"""
        if date_ref is None:
            date_ref = date.today()
        date_str = date_ref.strftime("%Y%m%d")
        new_id = f"E-{date_str}-{self.episode_counter:04d}"
        self.episode_counter += 1
        return new_id
    
    def generate_treatment_id(self, date_ref: date = None) -> str:
        """Generate new treatment ID: T-YYYYMMDD-XXXX"""
        if date_ref is None:
            date_ref = date.today()
        date_str = date_ref.strftime("%Y%m%d")
        new_id = f"T-{date_str}-{self.treatment_counter:04d}"
        self.treatment_counter += 1
        return new_id
    
    def parse_date(self, date_str: Any) -> Optional[str]:
        """Parse various date formats to YYYY-MM-DD"""
        if pd.isna(date_str) or date_str is None or date_str == "":
            return None
        
        if isinstance(date_str, (date, datetime)):
            return date_str.strftime("%Y-%m-%d")
        
        # Try common date formats
        formats = [
            "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", 
            "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y"
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(str(date_str), fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        self.stats["warnings"].append(f"Could not parse date: {date_str}")
        return None
    
    def map_gender(self, gender: Any) -> str:
        """Standardize gender values"""
        if pd.isna(gender) or not gender:
            return "Unknown"
        
        gender_str = str(gender).strip().upper()
        mapping = {
            "M": "Male",
            "MALE": "Male",
            "F": "Female", 
            "FEMALE": "Female",
            "U": "Unknown",
            "UNKNOWN": "Unknown",
            "O": "Other",
            "OTHER": "Other"
        }
        return mapping.get(gender_str, "Unknown")
    
    def map_tumour_site(self, site: Any) -> Optional[str]:
        """Map Access tumour site to MongoDB enum values"""
        if pd.isna(site) or not site:
            return None
        
        site_str = str(site).strip().lower()
        
        # Common mappings - extend based on your Access data
        mapping = {
            "caecum": "caecum",
            "appendix": "appendix",
            "ascending": "ascending_colon",
            "ascending colon": "ascending_colon",
            "transverse": "transverse_colon",
            "transverse colon": "transverse_colon",
            "descending": "descending_colon",
            "descending colon": "descending_colon",
            "sigmoid": "sigmoid_colon",
            "sigmoid colon": "sigmoid_colon",
            "rectum": "rectum",
            "rectal": "rectum",
            "rectosigmoid": "rectosigmoid_junction",
            "liver": "liver",
            "lung": "lung",
            "peritoneum": "peritoneum",
            "lymph node": "lymph_node",
            "bone": "bone",
            "brain": "brain"
        }
        
        return mapping.get(site_str, "other")
    
    def migrate_from_csv(self, csv_directory: str, dry_run: bool = False):
        """
        Migrate from CSV exports
        Expected files in csv_directory:
        - patients.csv
        - surgeries.csv
        - tumours.csv (optional)
        - pathology.csv (optional)
        """
        print(f"Starting migration from CSV directory: {csv_directory}")
        print(f"Dry run: {dry_run}")
        print("-" * 60)
        
        # Load CSV files
        patients_file = os.path.join(csv_directory, "patients.csv")
        surgeries_file = os.path.join(csv_directory, "surgeries.csv")
        tumours_file = os.path.join(csv_directory, "tumours.csv")
        
        # Migrate patients first
        if os.path.exists(patients_file):
            print(f"\n1. Migrating patients from {patients_file}")
            self.migrate_patients_csv(patients_file, dry_run)
        else:
            print(f"WARNING: {patients_file} not found")
        
        # Migrate surgeries/treatments
        if os.path.exists(surgeries_file):
            print(f"\n2. Migrating surgeries from {surgeries_file}")
            self.migrate_surgeries_csv(surgeries_file, dry_run)
        else:
            print(f"WARNING: {surgeries_file} not found")
        
        # Migrate tumours if file exists
        if os.path.exists(tumours_file):
            print(f"\n3. Migrating tumours from {tumours_file}")
            self.migrate_tumours_csv(tumours_file, dry_run)
        
        # Print summary
        self.print_summary()
    
    def migrate_patients_csv(self, csv_path: str, dry_run: bool = False):
        """Migrate patient records from CSV"""
        df = pd.read_csv(csv_path)
        print(f"Found {len(df)} patient records")
        
        for idx, row in df.iterrows():
            try:
                # Map Access fields to MongoDB schema
                # CUSTOMIZE THESE FIELD NAMES based on your Access export
                old_patient_id = row.get("PatientID") or row.get("ID")
                nhs_number = row.get("NHS_Number") or row.get("NHSNumber")
                
                # Generate new patient ID
                dob_str = self.parse_date(row.get("DOB") or row.get("DateOfBirth"))
                dob_date = datetime.strptime(dob_str, "%Y-%m-%d").date() if dob_str else date.today()
                new_patient_id = self.generate_patient_id(dob_date)
                
                # Create patient document
                patient_doc = {
                    "patient_id": new_patient_id,
                    "nhs_number": str(nhs_number) if nhs_number else None,
                    "demographics": {
                        "date_of_birth": dob_str,
                        "age": None,  # Calculate if needed
                        "gender": self.map_gender(row.get("Gender") or row.get("Sex")),
                        "ethnicity": row.get("Ethnicity"),
                        "postcode": row.get("Postcode"),
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
                
                # Store mapping
                self.patient_id_map[old_patient_id] = {
                    "new_id": new_patient_id,
                    "mongo_id": None  # Will be set after insert
                }
                
                if not dry_run:
                    result = self.patients.insert_one(patient_doc)
                    self.patient_id_map[old_patient_id]["mongo_id"] = result.inserted_id
                    self.stats["patients_created"] += 1
                else:
                    print(f"  [DRY RUN] Would create patient: {new_patient_id}")
                    self.stats["patients_created"] += 1
                    
            except Exception as e:
                error_msg = f"Error migrating patient row {idx}: {str(e)}"
                self.stats["errors"].append(error_msg)
                print(f"  ERROR: {error_msg}")
        
        print(f"✓ Migrated {self.stats['patients_created']} patients")
    
    def migrate_surgeries_csv(self, csv_path: str, dry_run: bool = False):
        """Migrate surgery records to treatments and episodes"""
        df = pd.read_csv(csv_path)
        print(f"Found {len(df)} surgery records")
        
        for idx, row in df.iterrows():
            try:
                # CUSTOMIZE THESE FIELD NAMES based on your Access export
                old_patient_id = row.get("PatientID") or row.get("Patient_ID")
                surgery_date_str = self.parse_date(row.get("SurgeryDate") or row.get("Date"))
                
                # Find mapped patient
                if old_patient_id not in self.patient_id_map:
                    self.stats["warnings"].append(f"Surgery row {idx}: Patient {old_patient_id} not found")
                    continue
                
                patient_mapping = self.patient_id_map[old_patient_id]
                new_patient_id = patient_mapping["new_id"]
                
                # Generate IDs
                surgery_date = datetime.strptime(surgery_date_str, "%Y-%m-%d").date() if surgery_date_str else date.today()
                treatment_id = self.generate_treatment_id(surgery_date)
                episode_id = self.generate_episode_id(surgery_date)
                
                # Create treatment document (simplified - extend based on your needs)
                treatment_doc = {
                    "treatment_id": treatment_id,
                    "treatment_type": "surgery",
                    "treatment_date": surgery_date_str,
                    "treating_clinician": row.get("Surgeon") or "Unknown",
                    "treatment_intent": "curative",  # Default - adjust based on data
                    "surgery": {
                        "classification": {
                            "primary_procedure": row.get("Procedure") or row.get("Operation"),
                            "approach": row.get("Approach", "open").lower(),
                        }
                    },
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                
                # Create episode document
                episode_doc = {
                    "episode_id": episode_id,
                    "patient_id": new_patient_id,
                    "condition_type": "cancer",  # Default - adjust based on data
                    "cancer_type": "bowel",  # Default - adjust based on data
                    "episode_date": surgery_date_str,
                    "primary_diagnosis": {
                        "icd10_code": row.get("ICD10_Code"),
                        "description": row.get("Diagnosis")
                    },
                    "treatments": [treatment_id],
                    "tumours": [],  # Will link tumours separately
                    "status": "completed",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                
                if not dry_run:
                    self.treatments.insert_one(treatment_doc)
                    self.episodes.insert_one(episode_doc)
                    self.stats["treatments_created"] += 1
                    self.stats["episodes_created"] += 1
                    
                    # Store episode mapping for linking tumours
                    old_surgery_id = row.get("SurgeryID") or row.get("ID")
                    if old_surgery_id:
                        self.episode_id_map[old_surgery_id] = episode_id
                else:
                    print(f"  [DRY RUN] Would create treatment: {treatment_id} and episode: {episode_id}")
                    self.stats["treatments_created"] += 1
                    self.stats["episodes_created"] += 1
                    
            except Exception as e:
                error_msg = f"Error migrating surgery row {idx}: {str(e)}"
                self.stats["errors"].append(error_msg)
                print(f"  ERROR: {error_msg}")
        
        print(f"✓ Migrated {self.stats['treatments_created']} treatments")
        print(f"✓ Created {self.stats['episodes_created']} episodes")
    
    def migrate_tumours_csv(self, csv_path: str, dry_run: bool = False):
        """Migrate tumour/pathology records"""
        df = pd.read_csv(csv_path)
        print(f"Found {len(df)} tumour records")
        
        for idx, row in df.iterrows():
            try:
                # CUSTOMIZE THESE FIELD NAMES
                old_surgery_id = row.get("SurgeryID") or row.get("Surgery_ID")
                
                # Map to episode
                episode_id = self.episode_id_map.get(old_surgery_id)
                if not episode_id:
                    self.stats["warnings"].append(f"Tumour row {idx}: Episode not found for surgery {old_surgery_id}")
                    continue
                
                # Create tumour document
                tumour_doc = {
                    "site": self.map_tumour_site(row.get("Site") or row.get("TumourSite")),
                    "tumour_type": "primary",  # Default
                    "diagnosis_date": self.parse_date(row.get("DiagnosisDate")),
                    "histology_type": row.get("Histology"),
                    "staging": {
                        "t_stage": row.get("T_Stage"),
                        "n_stage": row.get("N_Stage"),
                        "m_stage": row.get("M_Stage"),
                        "overall_stage": row.get("Stage")
                    },
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                
                if not dry_run:
                    result = self.tumours.insert_one(tumour_doc)
                    tumour_id = str(result.inserted_id)
                    
                    # Link tumour to episode
                    self.episodes.update_one(
                        {"episode_id": episode_id},
                        {"$push": {"tumours": tumour_id}}
                    )
                    self.stats["tumours_created"] += 1
                else:
                    print(f"  [DRY RUN] Would create tumour for episode: {episode_id}")
                    self.stats["tumours_created"] += 1
                    
            except Exception as e:
                error_msg = f"Error migrating tumour row {idx}: {str(e)}"
                self.stats["errors"].append(error_msg)
                print(f"  ERROR: {error_msg}")
        
        print(f"✓ Migrated {self.stats['tumours_created']} tumours")
    
    def print_summary(self):
        """Print migration summary"""
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Patients created:   {self.stats['patients_created']}")
        print(f"Episodes created:   {self.stats['episodes_created']}")
        print(f"Treatments created: {self.stats['treatments_created']}")
        print(f"Tumours created:    {self.stats['tumours_created']}")
        print(f"\nWarnings: {len(self.stats['warnings'])}")
        print(f"Errors:   {len(self.stats['errors'])}")
        
        if self.stats['warnings']:
            print("\nWARNINGS:")
            for warning in self.stats['warnings'][:10]:  # Show first 10
                print(f"  - {warning}")
            if len(self.stats['warnings']) > 10:
                print(f"  ... and {len(self.stats['warnings']) - 10} more")
        
        if self.stats['errors']:
            print("\nERRORS:")
            for error in self.stats['errors'][:10]:  # Show first 10
                print(f"  - {error}")
            if len(self.stats['errors']) > 10:
                print(f"  ... and {len(self.stats['errors']) - 10} more")
        
        # Save detailed log
        log_path = os.path.expanduser(f"~/.tmp/migration_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'w') as f:
            json.dump(self.stats, f, indent=2, default=str)
        print(f"\nDetailed log saved to: {log_path}")


def main():
    """Main migration entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate Access database to MongoDB")
    parser.add_argument("--csv-dir", help="Directory containing CSV exports from Access")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run without inserting data")
    parser.add_argument("--mongodb-uri", help="MongoDB connection URI")
    parser.add_argument("--database", default="surgdb", help="MongoDB database name")
    
    args = parser.parse_args()
    
    if not args.csv_dir:
        print("ERROR: --csv-dir required")
        print("\nUsage:")
        print("  1. Export Access tables to CSV files")
        print("  2. Place CSV files in a directory (e.g., ~/.tmp/access_export/)")
        print("  3. Run: python migrate_access_to_mongodb.py --csv-dir ~/.tmp/access_export/ --dry-run")
        print("  4. Review output, then run without --dry-run to perform actual migration")
        sys.exit(1)
    
    # Initialize migrator
    migrator = AccessToMongoMigrator(
        mongodb_uri=args.mongodb_uri,
        database_name=args.database
    )
    
    # Run migration
    migrator.migrate_from_csv(args.csv_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
