#!/usr/bin/env python3
"""
Migrate and enrich surgery treatment data.
This script flattens nested surgery data and enriches from CSV.
"""

import os
import sys
import pandas as pd
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://admin:admin123@localhost:27017')
client = MongoClient(MONGODB_URI)
db = client.surgdb

def parse_date(date_val):
    """Parse date from CSV"""
    if pd.isna(date_val) or date_val == '':
        return None
    if isinstance(date_val, pd.Timestamp):
        return date_val.strftime('%Y-%m-%d')
    if isinstance(date_val, str):
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d/%m/%y %H:%M:%S']:
            try:
                dt = datetime.strptime(date_val, fmt)
                return dt.strftime('%Y-%m-%d')
            except:
                continue
    return None

def safe_str(val):
    """Safely convert to string"""
    if pd.isna(val) or val == '':
        return None
    return str(val).strip()

def safe_int(val):
    """Safely convert to int"""
    if pd.isna(val) or val == '':
        return None
    try:
        return int(float(val))
    except:
        return None

def safe_bool(val):
    """Safely convert to bool"""
    if pd.isna(val) or val == '':
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(int(val))
    if isinstance(val, str):
        v = val.lower().strip()
        if v in ['1', 'yes', 'y', 'true']:
            return True
        if v in ['0', 'no', 'n', 'false']:
            return False
    return None

def map_urgency(val):
    """Map urgency field"""
    if pd.isna(val):
        return None
    v = str(val).lower()
    if 'elective' in v or v.startswith('1'):
        return 'elective'
    elif 'urgent' in v or v.startswith('3'):
        return 'urgent'
    elif 'emergency' in v or v.startswith('4'):
        return 'emergency'
    return None

def map_approach(lap_proc, lap_type):
    """Map approach field"""
    if pd.isna(lap_proc):
        return None
    v = str(lap_proc).lower()
    if 'lap' in v or v.startswith('2'):
        if not pd.isna(lap_type):
            lt = str(lap_type).lower()
            if 'completed' in lt or lt.startswith('4'):
                return 'laparoscopic'
            elif 'convert' in lt or lt.startswith('2'):
                return 'laparoscopic_converted'
        return 'laparoscopic'
    elif 'open' in v or v.startswith('1'):
        return 'open'
    return None

def map_surgical_intent(val):
    """Map surgical intent"""
    if pd.isna(val):
        return None
    v = str(val).lower()
    if 'curative' in v or v.startswith('1'):
        return 'curative'
    elif 'palliative' in v or v.startswith('2'):
        return 'palliative'
    elif 'uncertain' in v or v.startswith('3'):
        return 'uncertain'
    return None

def map_stoma_type(val):
    """Map stoma type"""
    if pd.isna(val):
        return None
    v = str(val).lower()
    if 'no' in v or v.startswith('1'):
        return None
    elif 'ileostomy temp' in v or v.startswith('2'):
        return 'temporary_ileostomy'
    elif 'ileostomy perm' in v or v.startswith('3'):
        return 'permanent_ileostomy'
    elif 'colostomy temp' in v or v.startswith('4'):
        return 'temporary_colostomy'
    elif 'colostomy perm' in v or v.startswith('5'):
        return 'permanent_colostomy'
    return None

def map_ar_type(val):
    """Map anterior resection type"""
    if pd.isna(val):
        return None
    v = str(val).lower().strip()
    if 'high' in v:
        return 'high_ar'
    elif 'low' in v:
        return 'low_ar'
    return None

def get_complications(row):
    """Extract complications from row"""
    comps = []
    
    # Binary flags
    flags = {
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
    
    for field, desc in flags.items():
        if field in row and safe_bool(row[field]):
            comps.append(desc)
    
    # Free text
    if 'Comp' in row and not pd.isna(row['Comp']):
        text = str(row['Comp']).strip()
        if text and text.lower() not in ['no al', 'no readmission', 'apex checked']:
            comps.append(text)
    
    return comps if comps else None

def migrate_treatments(csv_file: str, dry_run: bool = False):
    """Migrate treatments from nested structure and enrich from CSV"""
    
    print(f"Loading CSV: {csv_file}")
    df = pd.read_csv(csv_file)
    print(f"CSV has {len(df):,} surgeries")
    
    # Create lookup by patient_id and treatment_date
    csv_lookup = {}
    for idx, row in df.iterrows():
        date = parse_date(row.get('Date_Th'))
        if not date:
            continue
        # Use treatment date as key
        key = date
        if key not in csv_lookup:
            csv_lookup[key] = []
        csv_lookup[key].append(row)
    
    print(f"Created CSV lookup with {len(csv_lookup):,} unique dates")
    
    # Get all surgery treatments
    treatments = list(db.treatments.find({'treatment_type': 'surgery'}))
    print(f"Found {len(treatments):,} surgery treatments in database")
    
    updated = 0
    matched = 0
    errors = 0
    
    for treatment in treatments:
        try:
            treatment_id = treatment['treatment_id']
            treatment_date = treatment.get('treatment_date')
            
            # Build update document
            update = {
                '$set': {
                    'updated_at': datetime.utcnow()
                },
                '$unset': {}
            }
            
            # Flatten nested surgery data if it exists
            surgery = treatment.get('surgery', {})
            if surgery:
                classification = surgery.get('classification', {})
                outcomes = surgery.get('outcomes', {})
                
                # Map existing nested fields to flat structure
                if classification.get('primary_procedure'):
                    update['$set']['procedure_name'] = classification['primary_procedure']
                if classification.get('opcs4_code'):
                    update['$set']['opcs4_code'] = classification['opcs4_code']
                if classification.get('approach'):
                    update['$set']['approach'] = classification['approach']
                if classification.get('urgency'):
                    update['$set']['urgency'] = classification['urgency']
                if classification.get('asa_grade'):
                    update['$set']['asa_score'] = classification['asa_grade']
                if outcomes.get('discharge_date'):
                    update['$set']['discharge_date'] = outcomes['discharge_date']
                
                # Remove old nested structure
                update['$unset']['surgery'] = ''
            
            # Try to find matching CSV row by date
            csv_row = None
            if treatment_date and treatment_date in csv_lookup:
                candidates = csv_lookup[treatment_date]
                if len(candidates) == 1:
                    csv_row = candidates[0]
                    matched += 1
                elif len(candidates) > 1:
                    # Multiple surgeries on same date - try to match by procedure
                    proc_name = update['$set'].get('procedure_name', '')
                    for candidate in candidates:
                        csv_proc = safe_str(candidate.get('ProcName'))
                        if csv_proc and csv_proc in proc_name:
                            csv_row = candidate
                            matched += 1
                            break
                    if not csv_row:
                        csv_row = candidates[0]  # Use first one
                        matched += 1
            
            # Enrich with CSV data if available
            if csv_row is not None:
                # Surgeon and team
                if safe_str(csv_row.get('Surgeon')):
                    update['$set']['surgeon'] = safe_str(csv_row['Surgeon'])
                if safe_str(csv_row.get('Assistnt')):
                    update['$set']['assistant_surgeon'] = safe_str(csv_row['Assistnt'])
                if safe_str(csv_row.get('AssGrad')):
                    update['$set']['assistant_grade'] = safe_str(csv_row['AssGrad'])
                if safe_str(csv_row.get('Assistn2')):
                    update['$set']['second_assistant'] = safe_str(csv_row['Assistn2'])
                if safe_bool(csv_row.get('SurgFellow')) is not None:
                    update['$set']['surgical_fellow'] = safe_bool(csv_row['SurgFellow'])
                if safe_str(csv_row.get('Anaes')):
                    update['$set']['anaesthetist'] = safe_str(csv_row['Anaes'])
                
                # Timing
                if safe_int(csv_row.get('Total_op_time')):
                    update['$set']['operation_duration_minutes'] = safe_int(csv_row['Total_op_time'])
                if safe_int(csv_row.get('LOS')):
                    update['$set']['length_of_stay'] = safe_int(csv_row['LOS'])
                
                # Perioperative
                if safe_int(csv_row.get('bl_loss_mm')):
                    update['$set']['blood_loss_ml'] = safe_int(csv_row['bl_loss_mm'])
                if safe_bool(csv_row.get('Trans')) is not None:
                    update['$set']['transfusion_required'] = safe_bool(csv_row['Trans'])
                if safe_int(csv_row.get('Trans_units')):
                    update['$set']['units_transfused'] = safe_int(csv_row['Trans_units'])
                
                # Colorectal-specific
                intent = map_surgical_intent(csv_row.get('Curative'))
                if intent:
                    update['$set']['surgical_intent'] = intent
                
                if safe_bool(csv_row.get('Stoma')) is not None:
                    update['$set']['stoma_created'] = safe_bool(csv_row['Stoma'])
                
                stoma_type = map_stoma_type(csv_row.get('StomDone'))
                if stoma_type:
                    update['$set']['stoma_type'] = stoma_type
                    update['$set']['stoma_created'] = True
                
                stoma_close = parse_date(csv_row.get('DatClose'))
                if stoma_close:
                    update['$set']['stoma_closure_date'] = stoma_close
                
                if safe_bool(csv_row.get('Anastom')) is not None:
                    update['$set']['anastomosis_performed'] = safe_bool(csv_row['Anastom'])
                
                if safe_int(csv_row.get('Hgt_anast')):
                    update['$set']['anastomosis_height_cm'] = safe_int(csv_row['Hgt_anast'])
                
                ar_type = map_ar_type(csv_row.get('AR_high_low'))
                if ar_type:
                    update['$set']['anterior_resection_type'] = ar_type
                
                # Laparoscopic conversion
                convert_val = csv_row.get('Convert')
                if not pd.isna(convert_val) and convert_val != '':
                    update['$set']['laparoscopic_converted'] = True
                    convert_reason = safe_str(convert_val)
                    if convert_reason:
                        update['$set']['conversion_reason'] = convert_reason
                
                # Robotic
                if safe_bool(csv_row.get('Robotic')) is not None:
                    update['$set']['robotic_surgery'] = safe_bool(csv_row['Robotic'])
                
                # Complications
                comps = get_complications(csv_row)
                if comps:
                    update['$set']['complications'] = comps
                
                if safe_str(csv_row.get('ClavDind')):
                    update['$set']['clavien_dindo_grade'] = safe_str(csv_row['ClavDind'])
                
                if safe_bool(csv_row.get('re_op')) is not None:
                    update['$set']['return_to_theatre'] = safe_bool(csv_row['re_op'])
                if safe_str(csv_row.get('re_op_reasn')):
                    update['$set']['return_to_theatre_reason'] = safe_str(csv_row['re_op_reasn'])
                
                if safe_bool(csv_row.get('read_30')) is not None:
                    update['$set']['readmission_30d'] = safe_bool(csv_row['read_30'])
                if safe_str(csv_row.get('read_reasn')):
                    update['$set']['readmission_reason'] = safe_str(csv_row['read_reasn'])
                
                if safe_bool(csv_row.get('Mort_30')) is not None:
                    update['$set']['mortality_30d'] = safe_bool(csv_row['Mort_30'])
                
                # Findings
                if safe_str(csv_row.get('findings')):
                    update['$set']['findings'] = safe_str(csv_row['findings'])
                
                # CSV metadata
                update['$set']['csv_enriched'] = True
                update['$set']['csv_su_seq_no'] = safe_str(csv_row.get('Su_SeqNo'))
            
            # Apply update if we have changes
            if update['$set'] or update['$unset']:
                if not dry_run:
                    db.treatments.update_one(
                        {'_id': treatment['_id']},
                        update
                    )
                updated += 1
                
                if updated % 100 == 0:
                    print(f"Updated {updated:,} treatments (matched: {matched:,})...")
        
        except Exception as e:
            errors += 1
            if errors <= 10:
                print(f"Error on {treatment.get('treatment_id')}: {e}")
            continue
    
    print("\n" + "="*80)
    print(f"Migration {'(DRY RUN) ' if dry_run else ''}completed!")
    print(f"  Total treatments: {len(treatments):,}")
    print(f"  Updated: {updated:,}")
    print(f"  Matched with CSV: {matched:,}")
    print(f"  Errors: {errors}")
    print("="*80)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate and enrich surgery treatment data')
    parser.add_argument('csv_file', help='Path to surgeries CSV file')
    parser.add_argument('--dry-run', action='store_true', help='Dry run - do not update database')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.csv_file):
        print(f"Error: File not found: {args.csv_file}")
        sys.exit(1)
    
    migrate_treatments(args.csv_file, dry_run=args.dry_run)
