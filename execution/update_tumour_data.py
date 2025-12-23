#!/usr/bin/env python3
"""
Update existing tumours with comprehensive data from source CSV.

This script enhances the existing 8,088 tumours with additional clinical data
including imaging results, investigations, metastases, measurements, and dates.
"""

import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://admin:admin123@localhost:27017')
client = MongoClient(MONGO_URI)
db = client.surgdb

def parse_date(date_str):
    """Parse date from various formats."""
    if pd.isna(date_str):
        return None
    date_str = str(date_str).strip()
    if not date_str or date_str in ['nan', '']:
        return None
    
    # Try various date formats
    for fmt in ["%m/%d/%y %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d", "%m/%d/%y", "%m/%d/%Y"]:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except:
            continue
    return None

def normalize_value(val):
    """Normalize coded values - extract code and description."""
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

def normalize_numeric(val):
    """Extract numeric value from string."""
    if pd.isna(val):
        return None
    try:
        return float(val)
    except:
        return None

def main():
    print("Loading tumours CSV...")
    df = pd.read_csv('/root/surg-db/tumours_export_new.csv')
    print(f"Loaded {len(df)} tumour records")
    
    print("\nFetching tumours from database...")
    # Get all tumours sorted by _id (insertion order) to match CSV row order
    tumours_list = list(db.tumours.find().sort("_id", 1))
    print(f"Found {len(tumours_list)} tumours in database")
    
    if len(df) != len(tumours_list):
        print(f"ERROR: Row count mismatch! CSV has {len(df)}, DB has {len(tumours_list)}")
        return
    
    print("\nUpdating tumours with comprehensive data...")
    print("Using position-based matching (CSV row N -> DB tumour N)")
    
    updated_count = 0
    error_count = 0
    
    for idx, row in df.iterrows():
        try:
            # Match by position - row N in CSV corresponds to tumour N in database
            tumour = tumours_list[idx]
            
            # Build comprehensive update document
            update_doc = {
                # Imaging Results
                "imaging_results": {
                    "ct_abdomen": {
                        "result": normalize_value(row.get("CT_Abdo_result")),
                        "date": parse_date(row.get("Dt_CT_Abdo"))
                    },
                    "ct_chest": {
                        "result": normalize_value(row.get("CT_pneumo_result")),
                        "date": parse_date(row.get("Dt_CT_pneumo"))
                    },
                    "mri_primary": {
                        "t_stage": normalize_value(row.get("MRI1_T")),
                        "n_stage": normalize_value(row.get("MRI1_N")),
                        "crm_status": normalize_value(row.get("MRI1_CRM")),
                        "distance_from_anal_verge": normalize_numeric(row.get("MRI1_av")),
                        "emvi": normalize_value(row.get("EMVI")),
                        "date": parse_date(row.get("Dt_MRI1"))
                    },
                    "mri_restaging": {
                        "date": parse_date(row.get("Dt_MRI2")),
                        "result": normalize_value(row.get("M2result"))
                    },
                    "ultrasound_abdomen": {
                        "result": normalize_value(row.get("Abresult")),
                        "date": parse_date(row.get("Dt_Abdo"))
                    },
                    "endoscopic_ultrasound": {
                        "t_stage": normalize_value(row.get("Endo_T")),
                        "date": parse_date(row.get("Dt_Endo"))
                    }
                },
                
                # Investigations
                "investigations": {
                    "colonoscopy": {
                        "result": normalize_value(row.get("Col_scpy")),
                        "date": parse_date(row.get("Date_Col")),
                        "completion_reason": normalize_value(row.get("Rea_Inco"))
                    },
                    "flexible_sigmoidoscopy": {
                        "result": normalize_value(row.get("Fle_Sig")),
                        "date": parse_date(row.get("Date_Fle"))
                    },
                    "barium_enema": {
                        "result": normalize_value(row.get("Bar_Enem")),
                        "date": parse_date(row.get("Date_Bar"))
                    }
                },
                
                # Distant Metastases
                "distant_metastases": {
                    "liver": normalize_value(row.get("DM_Liver")),
                    "lung": normalize_value(row.get("DM_Lung")),
                    "bone": normalize_value(row.get("DM_Bone")),
                    "other": normalize_value(row.get("DM_Other"))
                },
                
                # Clinical Status
                "clinical_status": {
                    "performance_status": normalize_value(row.get("performance")),
                    "height_cm": normalize_numeric(row.get("Height")),
                    "modified_dukes": normalize_value(row.get("Mod_Duke"))
                },
                
                # Screening Data
                "screening": {
                    "bowel_cancer_screening_programme": bool(row.get("BCSP")) if not pd.isna(row.get("BCSP")) else False,
                    "screened": bool(row.get("Screened")) if not pd.isna(row.get("Screened")) else False,
                    "screening_method": normalize_value(row.get("Scrn_Yes"))
                },
                
                # MDT Information
                "mdt": {
                    "discussed": normalize_value(row.get("MDT_disc")),
                    "organization_code": str(row.get("Mdt_org")).strip() if not pd.isna(row.get("Mdt_org")) else None
                },
                
                # Synchronous Tumours
                "synchronous": {
                    "has_synchronous": bool(row.get("Sync")) if not pd.isna(row.get("Sync")) else False,
                    "type": normalize_value(row.get("TumSync")),
                    "icd10_code": str(row.get("SynICD10")).strip() if not pd.isna(row.get("SynICD10")) else None,
                    "cancer_type": normalize_value(row.get("Sync_cancer"))
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
                    "non_cancer_treatment_reason": normalize_value(row.get("Nonca_treat")),
                    "delay": bool(row.get("Delay")) if not pd.isna(row.get("Delay")) else False,
                    "priority": normalize_numeric(row.get("Priority")),
                    "referral_date": parse_date(row.get("DtRef")),
                    "visit_date": parse_date(row.get("Dt_Visit"))
                },
                
                "updated_at": datetime.utcnow()
            }
            
            # Update tumour
            result = db.tumours.update_one(
                {"_id": tumour["_id"]},
                {"$set": update_doc}
            )
            
            if result.modified_count > 0:
                updated_count += 1
            
            if (idx + 1) % 500 == 0:
                print(f"Processed {idx + 1}/{len(df)} tumours ({updated_count} updated)...")
                
        except Exception as e:
            error_count += 1
            if error_count < 10:
                print(f"ERROR at row {idx}: {str(e)}")
    
    print(f"\n{'='*70}")
    print(f"Update Summary:")
    print(f"  Total records: {len(df)}")
    print(f"  Updated: {updated_count}")
    print(f"  Errors: {error_count}")
    print(f"{'='*70}")
    
    # Show sample updated tumour
    print("\nSample updated tumour:")
    sample = db.tumours.find_one({"imaging_results": {"$exists": True}})
    if sample:
        print(f"Tumour ID: {sample.get('tumour_id')}")
        print(f"Patient ID: {sample.get('patient_id')}")
        print(f"MRI T-stage: {sample.get('imaging_results', {}).get('mri_primary', {}).get('t_stage')}")
        print(f"Distance from anal verge: {sample.get('imaging_results', {}).get('mri_primary', {}).get('distance_from_anal_verge')}")
        print(f"Liver metastases: {sample.get('distant_metastases', {}).get('liver')}")
        print(f"Performance status: {sample.get('clinical_status', {}).get('performance_status')}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print(__doc__)
        sys.exit(0)
    
    response = input("This will update all 8,088 tumours with comprehensive data. Continue? (y/n): ")
    if response.lower() != 'y':
        print("Aborted.")
        sys.exit(0)
    
    main()
