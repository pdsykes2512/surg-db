#!/usr/bin/env python3
"""
Restructure tumour data:
1. Move imaging/investigations from tumours to new investigations collection
2. Add pathology fields to tumours from pathology_export_new.csv
3. Clean up tumour documents to match TumourModal expectations
"""

import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import sys
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://admin:admin123@localhost:27017')
client = MongoClient(MONGO_URI)
db = client.surgdb

def parse_date(date_val):
    """Parse date from various formats."""
    if pd.isna(date_val):
        return None
    date_str = str(date_val).strip()
    if not date_str or date_str == 'nan':
        return None
    
    for fmt in ["%m/%d/%y %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d", "%m/%d/%y", "%m/%d/%Y"]:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except:
            continue
    return None

def normalize_coded_value(val):
    """Extract description from coded values like '1 Adenocarcinoma'."""
    if pd.isna(val):
        return None
    val_str = str(val).strip()
    if not val_str or val_str == 'nan':
        return None
    
    # Handle coded values
    if val_str and len(val_str) > 1 and val_str[0].isdigit():
        parts = val_str.split(' ', 1)
        if len(parts) == 2:
            return parts[1].strip().lower()
    
    return val_str.lower()

def map_grade(hist_grad):
    """Map HistGrad to grade."""
    if pd.isna(hist_grad):
        return None
    
    val_str = str(hist_grad).strip().upper()
    
    # Direct G1/G2/G3 mapping
    if val_str in ['G1', 'G2', 'G3', 'G4']:
        return val_str.lower()
    
    # Map coded values
    if 'WELL' in val_str or val_str == '1 WELL DIFFERENTIATED':
        return 'g1'
    elif 'MODERATE' in val_str or val_str == '2 OTHER':
        return 'g2'
    elif 'POOR' in val_str or 'G3' in val_str:
        return 'g3'
    
    return None

def map_tnm_stage(tnm_val):
    """Map TNM values to standard format."""
    if pd.isna(tnm_val):
        return None
    
    val_str = str(tnm_val).strip()
    if not val_str or val_str == 'nan':
        return None
    
    # Already in correct format (single digit or letter)
    if len(val_str) == 1:
        return val_str.lower()
    
    return val_str.lower()

def generate_investigation_id(patient_id, inv_type, seq):
    """Generate investigation ID: INV-{patient_id}-{type}-{seq:02d}"""
    return f"INV-{patient_id}-{inv_type.upper()[:3]}-{seq:02d}"

def main():
    print("="*70)
    print("TUMOUR DATA RESTRUCTURING")
    print("="*70)
    
    # Step 1: Create investigations from imaging/investigation data in tumours
    print("\n1. Extracting investigations from tumour documents...")
    tumours = list(db.tumours.find())
    investigations_created = 0
    inv_seq_counter = {}
    
    for tumour in tumours:
        patient_id = tumour.get('patient_id')
        episode_id = tumour.get('episode_id')
        tumour_id = tumour.get('tumour_id')
        
        if patient_id not in inv_seq_counter:
            inv_seq_counter[patient_id] = 0
        
        imaging = tumour.get('imaging_results', {})
        investigations_data = tumour.get('investigations', {})
        
        # Create investigation documents from imaging results
        for imaging_type, data in imaging.items():
            if not data or not any(data.values()):
                continue
            
            inv_seq_counter[patient_id] += 1
            inv_id = generate_investigation_id(patient_id, imaging_type, inv_seq_counter[patient_id])
            
            inv_doc = {
                "investigation_id": inv_id,
                "patient_id": patient_id,
                "episode_id": episode_id,
                "tumour_id": tumour_id,
                "type": "imaging",
                "subtype": imaging_type,
                "date": data.get('date'),
                "result": data.get('result'),
                "findings": {k: v for k, v in data.items() if k not in ['date', 'result'] and v is not None},
                "report_url": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            db.investigations.insert_one(inv_doc)
            investigations_created += 1
        
        # Create investigation documents from endoscopy/investigations
        for inv_type, data in investigations_data.items():
            if not data or not any(data.values()):
                continue
            
            inv_seq_counter[patient_id] += 1
            inv_id = generate_investigation_id(patient_id, inv_type, inv_seq_counter[patient_id])
            
            inv_doc = {
                "investigation_id": inv_id,
                "patient_id": patient_id,
                "episode_id": episode_id,
                "tumour_id": tumour_id,
                "type": "endoscopy",
                "subtype": inv_type,
                "date": data.get('date'),
                "result": data.get('result'),
                "findings": {k: v for k, v in data.items() if k not in ['date', 'result'] and v is not None},
                "report_url": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            db.investigations.insert_one(inv_doc)
            investigations_created += 1
    
    print(f"   Created {investigations_created} investigation documents")
    
    # Step 2: Load pathology data and map to tumours
    print("\n2. Loading pathology data...")
    pathology_df = pd.read_csv('/root/surg-db/pathology_export_new.csv')
    print(f"   Loaded {len(pathology_df)} pathology records")
    
    # Load tumours data to match TumSeqNo
    tumours_df = pd.read_csv('/root/surg-db/tumours_export_new.csv')
    
    # Create mapping: TumSeqNo -> pathology data
    pathology_map = {}
    for idx, row in pathology_df.iterrows():
        tum_seq = str(row['TumSeqNo']).strip()
        pathology_map[tum_seq] = row
    
    print("\n3. Updating tumours with pathology data...")
    tumours_updated = 0
    
    for idx, tum_row in tumours_df.iterrows():
        tum_seq = str(tum_row['TumSeqno']).strip()
        path_data = pathology_map.get(tum_seq)
        
        if path_data is None:
            continue
        
        # Find tumour in database by position
        tumour = tumours[idx]
        
        # Build pathology update
        update_fields = {
            # Basic pathology
            "grade": map_grade(path_data.get('HistGrad')),
            "histology_type": normalize_coded_value(path_data.get('HistType')),
            "size_mm": float(path_data['MaxDiam']) if not pd.isna(path_data.get('MaxDiam')) else None,
            
            # Staging - use pathological TNM from pathology, clinical TNM from tumour staging
            "pathological_t": map_tnm_stage(path_data.get('TNM_Tumr')),
            "pathological_n": map_tnm_stage(path_data.get('TNM_Nods')),
            "pathological_m": map_tnm_stage(path_data.get('TNM_Mets')),
            "pathological_stage_date": parse_date(path_data.get('Spec_Dat')),
            "tnm_version": str(path_data.get('TNM_edition')).strip() if not pd.isna(path_data.get('TNM_edition')) else '8',
            
            # Keep clinical staging from existing data
            "clinical_t": tumour.get('staging', {}).get('t_stage'),
            "clinical_n": tumour.get('staging', {}).get('n_stage'),
            "clinical_m": tumour.get('staging', {}).get('m_stage'),
            
            # Lymph nodes
            "lymph_nodes_examined": int(path_data['NoLyNoF']) if not pd.isna(path_data.get('NoLyNoF')) else None,
            "lymph_nodes_positive": int(path_data['NoLyNoP']) if not pd.isna(path_data.get('NoLyNoP')) else None,
            
            # Invasion
            "lymphovascular_invasion": bool(path_data.get('VasInv')) if not pd.isna(path_data.get('VasInv')) else False,
            "perineural_invasion": bool(path_data.get('Perineural')) if not pd.isna(path_data.get('Perineural')) else False,
            
            # Margins
            "crm_status": normalize_coded_value(path_data.get('Mar_Cir')),
            "crm_distance_mm": float(path_data.get('Dist_Cir')) if not pd.isna(path_data.get('Dist_Cir')) else None,
            "proximal_margin_mm": float(path_data.get('Dist_Cut')) if not pd.isna(path_data.get('Dist_Cut')) else None,
            "distal_margin_mm": float(path_data.get('Dist_Mar')) if not pd.isna(path_data.get('Dist_Mar')) else None,
            
            # Distance for rectal tumours (from imaging or pathology)
            "distance_from_anal_verge_cm": tumour.get('imaging_results', {}).get('mri_primary', {}).get('distance_from_anal_verge'),
            
            # Mesorectal involvement for rectal cancers
            "mesorectal_involvement": tumour.get('colonic_complications', {}).get('other', False) if tumour.get('site') == 'rectum' else False,
            
            # Keep existing fields
            "dukes_stage": tumour.get('pathology', {}).get('dukes_stage'),
            "resection_grade": normalize_coded_value(path_data.get('resect_grade')),
            
            "updated_at": datetime.utcnow()
        }
        
        # Remove imaging_results, investigations, and other non-TumourModal fields
        db.tumours.update_one(
            {"_id": tumour["_id"]},
            {
                "$set": update_fields,
                "$unset": {
                    "imaging_results": "",
                    "investigations": "",
                    "distant_metastases": "",
                    "clinical_status": "",
                    "screening": "",
                    "mdt": "",
                    "synchronous": "",
                    "colonic_complications": "",
                    "additional_info": "",
                    "anatomical_site": "",
                    "pathology": "",
                    "staging": ""
                }
            }
        )
        
        tumours_updated += 1
        
        if (idx + 1) % 500 == 0:
            print(f"   Updated {idx + 1}/{len(tumours_df)} tumours...")
    
    print(f"\n{'='*70}")
    print(f"RESTRUCTURING COMPLETE")
    print(f"  Investigations created: {investigations_created}")
    print(f"  Tumours updated: {tumours_updated}")
    print(f"{'='*70}")
    
    # Show sample updated tumour
    print("\nSample updated tumour:")
    sample = db.tumours.find_one()
    if sample:
        print(f"  Tumour ID: {sample.get('tumour_id')}")
        print(f"  Grade: {sample.get('grade')}")
        print(f"  Size: {sample.get('size_mm')}mm")
        print(f"  pTNM: T{sample.get('pathological_t')} N{sample.get('pathological_n')} M{sample.get('pathological_m')}")
        print(f"  Lymph nodes: {sample.get('lymph_nodes_positive')}/{sample.get('lymph_nodes_examined')}")
        print(f"  CRM: {sample.get('crm_status')}")
    
    print("\nSample investigation:")
    sample_inv = db.investigations.find_one()
    if sample_inv:
        print(f"  Investigation ID: {sample_inv.get('investigation_id')}")
        print(f"  Type: {sample_inv.get('type')} - {sample_inv.get('subtype')}")
        print(f"  Date: {sample_inv.get('date')}")
        print(f"  Result: {sample_inv.get('result')}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print(__doc__)
        sys.exit(0)
    
    print("\nThis will:")
    print("1. Move imaging/investigation data from tumours to investigations collection")
    print("2. Add pathology fields to tumours from pathology_export_new.csv")
    print("3. Remove non-TumourModal fields from tumours")
    print("\nAll 8,088 tumours will be restructured.")
    
    response = input("\nContinue? (y/n): ")
    if response.lower() != 'y':
        print("Aborted.")
        sys.exit(0)
    
    main()
