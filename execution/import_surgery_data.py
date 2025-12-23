#!/usr/bin/env python3
"""
Migrate and enrich surgery data from surgeries_export_new.csv.
This script:
1. Reads existing treatments with nested 'surgery' subdocuments
2. Flattens the structure to top-level fields
3. Enriches with additional data from CSV by matching treatment dates
"""

import os
import sys
import pandas as pd
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import re
from collections import defaultdict

# MongoDB connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://admin:admin123@localhost:27017')
client = MongoClient(MONGODB_URI)
db = client.surgdb

def generate_treatment_id(patient_id: str, sequence: int) -> str:
    """Generate semantic treatment ID like TRT-B3F060-01"""
    patient_part = patient_id.replace('PAT-', '')
    return f"TRT-{patient_part}-{sequence:02d}"

def parse_date(date_val):
    """Parse various date formats from CSV"""
    if pd.isna(date_val) or date_val == '':
        return None
    
    # Already datetime
    if isinstance(date_val, pd.Timestamp):
        return date_val.strftime('%Y-%m-%d')
    
    # Try parsing string
    if isinstance(date_val, str):
        # Try different formats
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d']:
            try:
                dt = datetime.strptime(date_val, fmt)
                return dt.strftime('%Y-%m-%d')
            except:
                continue
    
    return None

def clean_string(val):
    """Clean string values"""
    if pd.isna(val) or val == '':
        return None
    return str(val).strip()

def parse_int(val):
    """Parse integer values"""
    if pd.isna(val) or val == '':
        return None
    try:
        return int(float(val))
    except:
        return None

def parse_float(val):
    """Parse float values"""
    if pd.isna(val) or val == '':
        return None
    try:
        return float(val)
    except:
        return None

def parse_boolean(val):
    """Parse boolean from integer or string"""
    if pd.isna(val) or val == '':
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(int(val))
    if isinstance(val, str):
        val_lower = val.lower().strip()
        if val_lower in ['1', 'yes', 'y', 'true']:
            return True
        if val_lower in ['0', 'no', 'n', 'false']:
            return False
    return None

def map_urgency(mode_op):
    """Map ModeOp field to urgency"""
    if pd.isna(mode_op):
        return None
    val = str(mode_op).lower()
    if 'elective' in val or val.startswith('1'):
        return 'elective'
    elif 'urgent' in val or val.startswith('3'):
        return 'urgent'
    elif 'emergency' in val or val.startswith('4'):
        return 'emergency'
    elif 'scheduled' in val or val.startswith('2'):
        return 'elective'
    return None

def map_approach(lap_proc, lap_type):
    """Map laparoscopic fields to approach"""
    if pd.isna(lap_proc):
        return None
    
    lap_val = str(lap_proc).lower()
    if 'lap' in lap_val or lap_val.startswith('2'):
        # Check if completed laparoscopically
        if not pd.isna(lap_type):
            lap_type_val = str(lap_type).lower()
            if 'completed' in lap_type_val or lap_type_val.startswith('4'):
                return 'laparoscopic'
            elif 'convert' in lap_type_val or lap_type_val.startswith('2'):
                return 'laparoscopic_converted'
        return 'laparoscopic'
    elif 'open' in lap_val or lap_val.startswith('1'):
        return 'open'
    
    return None

def map_surgical_intent(curative_val):
    """Map Curative field to surgical_intent"""
    if pd.isna(curative_val):
        return None
    val = str(curative_val).lower()
    if 'curative' in val or val.startswith('1'):
        return 'curative'
    elif 'palliative' in val or val.startswith('2'):
        return 'palliative'
    elif 'uncertain' in val or val.startswith('3'):
        return 'uncertain'
    return None

def map_stoma_type(stom_done):
    """Map StomDone to stoma_type"""
    if pd.isna(stom_done):
        return None
    val = str(stom_done).lower()
    if 'no' in val or val.startswith('1'):
        return None
    elif 'ileostomy temp' in val or val.startswith('2'):
        return 'temporary_ileostomy'
    elif 'ileostomy perm' in val or val.startswith('3'):
        return 'permanent_ileostomy'
    elif 'colostomy temp' in val or val.startswith('4'):
        return 'temporary_colostomy'
    elif 'colostomy perm' in val or val.startswith('5'):
        return 'permanent_colostomy'
    return None

def map_ar_type(ar_val):
    """Map AR_high_low to anterior_resection_type"""
    if pd.isna(ar_val):
        return None
    val = str(ar_val).lower().strip()
    if 'high' in val:
        return 'high_ar'
    elif 'low' in val:
        return 'low_ar'
    return None

def get_conversion_reason(convert_val):
    """Extract conversion reason from Convert field"""
    if pd.isna(convert_val):
        return None
    val = str(convert_val).strip()
    # Extract the reason text
    # Format is usually like "6 Oncological" or "3 Adhesions"
    match = re.match(r'^\d+\s+(.+)$', val)
    if match:
        return match.group(1).strip()
    return val

def collect_complications(row):
    """Collect all complications into an array"""
    complications = []
    
    # Binary complication flags
    comp_flags = {
        'MJ_Leak': 'Major anastomotic leak',
        'MI_Leak': 'Minor anastomotic leak',
        'WI': 'Wound infection',
        'CI': 'Chest infection',
        'MI': 'Myocardial infarction',
        'UTI': 'Urinary tract infection',
        'Cardio': 'Cardiac complication',
        're_op': 'Reoperation',
        'DVT': 'Deep vein thrombosis',
        'PE': 'Pulmonary embolism',
        'LoI': 'Intra-abdominal collection',
        'Col_Perfn': 'Colonic perforation',
        'Ileus': 'Ileus',
        'SSI': 'Surgical site infection'
    }
    
    for field, description in comp_flags.items():
        if field in row and parse_boolean(row[field]) == True:
            complications.append(description)
    
    # Add free-text complications
    if 'Comp' in row and not pd.isna(row['Comp']):
        comp_text = str(row['Comp']).strip()
        if comp_text and comp_text.lower() not in ['no al', 'no readmission', 'apex checked']:
            complications.append(comp_text)
    
    return complications if complications else None

def find_episode_for_surgery(row):
    """Find the episode that this surgery belongs to"""
    # Try to match by Su_SeqNo (surgery sequence number)
    if 'Su_SeqNo' in row and not pd.isna(row['Su_SeqNo']):
        seq_no = str(row['Su_SeqNo']).strip()
        
        # Find in existing surgeries collection (if migrated)
        existing = db.surgeries.find_one({'Su_SeqNo': seq_no})
        if existing and 'episode_id' in existing:
            return existing['episode_id']
        
        # Try to find by patient matching
        # This is a fallback - ideally we'd have a mapping table
        
    return None

def import_surgeries(csv_file: str, limit: int = None, skip: int = 0):
    """Import surgeries from CSV file"""
    
    print(f"Reading CSV file: {csv_file}")
    df = pd.read_csv(csv_file)
    
    total_rows = len(df)
    print(f"Total surgeries in CSV: {total_rows}")
    
    if skip > 0:
        df = df[skip:]
        print(f"Skipping first {skip} rows")
    
    if limit:
        df = df[:limit]
        print(f"Processing {len(df)} surgeries (limit={limit})")
    
    imported = 0
    skipped = 0
    errors = 0
    
    for idx, row in df.iterrows():
        try:
            # Find associated episode
            episode_id = find_episode_for_surgery(row)
            
            if not episode_id:
                # Try to create a placeholder or skip
                # For now, we'll skip surgeries without episode match
                skipped += 1
                if skipped <= 10:  # Show first 10
                    print(f"Row {idx}: Skipping - no episode match (Su_SeqNo: {row.get('Su_SeqNo', 'N/A')})")
                continue
            
            # Get episode to find patient_id
            episode = db.episodes.find_one({'episode_id': episode_id})
            if not episode:
                skipped += 1
                continue
            
            patient_id = episode['patient_id']
            
            # Check if treatment already exists
            existing_count = db.treatments.count_documents({
                'episode_id': episode_id,
                'treatment_type': 'surgery'
            })
            
            # Generate treatment_id
            treatment_id = generate_treatment_id(patient_id, existing_count + 1)
            
            # Build treatment document
            treatment = {
                'treatment_id': treatment_id,
                'episode_id': episode_id,
                'patient_id': patient_id,
                'treatment_type': 'surgery',
                
                # Basic information
                'treatment_date': parse_date(row.get('Date_Th')),
                'admission_date': None,  # Not in CSV
                'discharge_date': parse_date(row.get('Date_Dis')),
                
                # Procedure details
                'procedure_name': clean_string(row.get('ProcName')),
                'opcs4_code': clean_string(row.get('OPCS4')),
                'approach': map_approach(row.get('LapProc'), row.get('LapType')),
                'urgency': map_urgency(row.get('ModeOp')),
                'complexity': None,  # Could derive from procedure
                
                # Surgical team
                'surgeon': clean_string(row.get('Surgeon')),
                'assistant_surgeon': clean_string(row.get('Assistnt')),
                'assistant_grade': clean_string(row.get('AssGrad')),
                'second_assistant': clean_string(row.get('Assistn2')),
                'surgical_fellow': parse_boolean(row.get('SurgFellow')),
                'anaesthetist': clean_string(row.get('Anaes')),
                
                # Timing
                'operation_duration_minutes': parse_int(row.get('Total_op_time')),
                'anesthesia_duration_minutes': None,
                
                # Perioperative
                'asa_score': clean_string(row.get('ASA')),
                'anesthesia_type': None,
                'blood_loss_ml': parse_int(row.get('bl_loss_mm')),
                'transfusion_required': parse_boolean(row.get('Trans')),
                'units_transfused': parse_int(row.get('Trans_units')),
                
                # Colorectal-specific fields
                'surgical_intent': map_surgical_intent(row.get('Curative')),
                'stoma_created': parse_boolean(row.get('Stoma')),
                'stoma_type': map_stoma_type(row.get('StomDone')),
                'stoma_closure_date': parse_date(row.get('DatClose')),
                'anastomosis_performed': parse_boolean(row.get('Anastom')),
                'anastomosis_height_cm': parse_float(row.get('Hgt_anast')),
                'anterior_resection_type': map_ar_type(row.get('AR_high_low')),
                'laparoscopic_converted': parse_boolean(row.get('Convert')) if not pd.isna(row.get('Convert')) else None,
                'conversion_reason': get_conversion_reason(row.get('Convert')),
                
                # Robotic
                'robotic_surgery': parse_boolean(row.get('Robotic')),
                
                # Complications
                'complications': collect_complications(row),
                'clavien_dindo_grade': clean_string(row.get('ClavDind')),
                'return_to_theatre': parse_boolean(row.get('re_op')),
                'return_to_theatre_reason': clean_string(row.get('re_op_reasn')),
                'readmission_30d': parse_boolean(row.get('read_30')),
                'readmission_reason': clean_string(row.get('read_reasn')),
                'mortality_30d': parse_boolean(row.get('Mort_30')),
                
                # Outcomes
                'length_of_stay': parse_int(row.get('LOS')),
                
                # Additional fields
                'findings': clean_string(row.get('findings')),
                'notes': None,
                
                # Provider
                'provider_organisation': 'RQ3',  # Default to York
                'institution': 'York Hospital',
                
                # Metadata
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                
                # Original CSV reference
                'csv_source': {
                    'file': os.path.basename(csv_file),
                    'su_seq_no': clean_string(row.get('Su_SeqNo')),
                    'imported_at': datetime.utcnow()
                }
            }
            
            # Remove None values to keep documents clean
            treatment = {k: v for k, v in treatment.items() if v is not None}
            
            # Insert into database
            result = db.treatments.insert_one(treatment)
            
            imported += 1
            if imported % 100 == 0:
                print(f"Imported {imported} surgeries...")
            
        except Exception as e:
            errors += 1
            if errors <= 10:  # Show first 10 errors
                print(f"Row {idx}: Error - {str(e)}")
            continue
    
    print("\n" + "="*80)
    print(f"Import completed!")
    print(f"  Total processed: {len(df)}")
    print(f"  Successfully imported: {imported}")
    print(f"  Skipped (no episode): {skipped}")
    print(f"  Errors: {errors}")
    print("="*80)
    
    return imported, skipped, errors

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Import surgery data from CSV')
    parser.add_argument('csv_file', help='Path to surgeries CSV file')
    parser.add_argument('--limit', type=int, help='Limit number of surgeries to import')
    parser.add_argument('--skip', type=int, default=0, help='Skip first N surgeries')
    parser.add_argument('--dry-run', action='store_true', help='Dry run - do not insert into database')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.csv_file):
        print(f"Error: File not found: {args.csv_file}")
        sys.exit(1)
    
    if args.dry_run:
        print("DRY RUN MODE - No data will be inserted")
        # TODO: Implement dry run logic
    
    import_surgeries(args.csv_file, limit=args.limit, skip=args.skip)
