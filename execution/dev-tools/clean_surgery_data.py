#!/usr/bin/env python3
"""
Clean and standardize surgery treatment data.
Removes numbered prefixes and maps to proper terminology and OPCS-4 codes.
"""

import os
import re
from pymongo import MongoClient
from datetime import datetime

# MongoDB connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://admin:admin123@localhost:27017')
client = MongoClient(MONGODB_URI)
db = client.surgdb

# Procedure name mappings (number prefix -> clean name)
PROCEDURE_MAPPINGS = {
    '1 Right hemicolectomy': 'Right hemicolectomy',
    '2 Extended right hemicolectomy': 'Extended right hemicolectomy',
    '3 Transverse colectomy': 'Transverse colectomy',
    '4 Left hemicolectomy': 'Left hemicolectomy',
    '5 Sigmoid colectomy': 'Sigmoid colectomy',
    '6 Anterior resection': 'Anterior resection',
    '7 APER': 'Abdominoperineal excision of rectum (APER)',
    '8 Hartmann\'s procedure': 'Hartmann\'s procedure',
    '9 Subtotal colectomy': 'Subtotal colectomy',
    '10 Total colectomy': 'Total colectomy',
    '11 Panproctocolectomy': 'Panproctocolectomy',
    '12 Stent': 'Colonic stent insertion',
    '13 Polypectomy': 'Polypectomy',
    '14 Local excision': 'Local excision',
    '15 Defunctioning stoma': 'Defunctioning stoma',
    '16 Reversal of stoma': 'Reversal of stoma',
    '17 Stoma only': 'Stoma formation',
    '18 Other': 'Other colorectal procedure',
}

# OPCS-4 code descriptions (for reference/validation)
OPCS4_DESCRIPTIONS = {
    'H07.9': 'Right hemicolectomy',
    'H06.9': 'Extended right hemicolectomy',
    'H08.9': 'Transverse colectomy',
    'H09.9': 'Left hemicolectomy',
    'H10.9': 'Sigmoid colectomy',
    'H33.4': 'Anterior resection of rectum',
    'H33.1': 'Abdominoperineal excision of rectum',
    'H33.5': 'Hartmann\'s operation',
    'H04.9': 'Total colectomy',
    'H05.9': 'Panproctocolectomy',
    'G74.9': 'Endoscopic insertion of prosthesis into large intestine',
    'H23.9': 'Endoscopic polypectomy of large intestine',
    'H24.3': 'Local excision of lesion of colon',
}

# ASA score mappings
ASA_MAPPINGS = {
    'I': '1',
    'II': '2',
    'III': '3',
    'IV': '4',
    'V': '5',
    'E': 'E',  # Emergency modifier
}

def clean_numbered_field(value):
    """Remove leading number and space from field"""
    if not value or not isinstance(value, str):
        return value
    
    # Pattern: "1 Something" or "1 something" 
    match = re.match(r'^(\d+)\s+(.+)$', value.strip())
    if match:
        return match.group(2).strip()
    
    return value.strip()

def standardize_asa_score(value):
    """Standardize ASA score to numeric format"""
    if not value or not isinstance(value, str):
        return value
    
    value = value.strip().upper()
    
    # Remove "ASA" prefix if present
    value = re.sub(r'^ASA\s*', '', value)
    
    # Map Roman numerals to numbers
    if value in ASA_MAPPINGS:
        return ASA_MAPPINGS[value]
    
    # If it's already a number, keep it
    if re.match(r'^\d$', value):
        return value
    
    return value

def clean_treatments(dry_run=False):
    """Clean and standardize treatment data"""
    
    treatments = list(db.treatments.find({'treatment_type': 'surgery'}))
    print(f"Found {len(treatments):,} surgery treatments")
    
    updated = 0
    
    for treatment in treatments:
        changes = {}
        
        # Clean procedure_name
        proc_name = treatment.get('procedure_name')
        if proc_name:
            # Check for exact mapping first
            if proc_name in PROCEDURE_MAPPINGS:
                changes['procedure_name'] = PROCEDURE_MAPPINGS[proc_name]
            else:
                # Generic cleaning of numbered prefix
                cleaned = clean_numbered_field(proc_name)
                if cleaned != proc_name:
                    changes['procedure_name'] = cleaned
        
        # Standardize ASA score
        asa_score = treatment.get('asa_score')
        if asa_score:
            standardized = standardize_asa_score(asa_score)
            if standardized != asa_score:
                changes['asa_score'] = standardized
        
        # Clean approach if it has numbers
        approach = treatment.get('approach')
        if approach and isinstance(approach, str):
            cleaned = clean_numbered_field(approach)
            if cleaned != approach:
                # Standardize approach values
                cleaned_lower = cleaned.lower()
                if 'open' in cleaned_lower:
                    changes['approach'] = 'open'
                elif 'laparoscopic' in cleaned_lower or 'lap' in cleaned_lower:
                    changes['approach'] = 'laparoscopic'
        
        # Clean urgency if it has numbers
        urgency = treatment.get('urgency')
        if urgency and isinstance(urgency, str):
            cleaned = clean_numbered_field(urgency)
            if cleaned != urgency:
                cleaned_lower = cleaned.lower()
                if 'elective' in cleaned_lower:
                    changes['urgency'] = 'elective'
                elif 'urgent' in cleaned_lower:
                    changes['urgency'] = 'urgent'
                elif 'emergency' in cleaned_lower:
                    changes['urgency'] = 'emergency'
        
        # Clean surgical_intent if it has numbers
        intent = treatment.get('surgical_intent')
        if intent and isinstance(intent, str):
            cleaned = clean_numbered_field(intent)
            if cleaned != intent:
                cleaned_lower = cleaned.lower()
                if 'curative' in cleaned_lower:
                    changes['surgical_intent'] = 'curative'
                elif 'palliative' in cleaned_lower:
                    changes['surgical_intent'] = 'palliative'
                elif 'uncertain' in cleaned_lower:
                    changes['surgical_intent'] = 'uncertain'
        
        # Clean stoma_type if it has numbers
        stoma_type = treatment.get('stoma_type')
        if stoma_type and isinstance(stoma_type, str):
            cleaned = clean_numbered_field(stoma_type)
            if cleaned != stoma_type:
                # Map to standard values
                cleaned_lower = cleaned.lower()
                if 'ileostomy' in cleaned_lower and 'temp' in cleaned_lower:
                    changes['stoma_type'] = 'temporary_ileostomy'
                elif 'ileostomy' in cleaned_lower and 'perm' in cleaned_lower:
                    changes['stoma_type'] = 'permanent_ileostomy'
                elif 'colostomy' in cleaned_lower and 'temp' in cleaned_lower:
                    changes['stoma_type'] = 'temporary_colostomy'
                elif 'colostomy' in cleaned_lower and 'perm' in cleaned_lower:
                    changes['stoma_type'] = 'permanent_colostomy'
        
        # Clean anterior_resection_type if it has numbers
        ar_type = treatment.get('anterior_resection_type')
        if ar_type and isinstance(ar_type, str):
            cleaned = clean_numbered_field(ar_type)
            if cleaned != ar_type:
                cleaned_lower = cleaned.lower()
                if 'high' in cleaned_lower:
                    changes['anterior_resection_type'] = 'high_ar'
                elif 'low' in cleaned_lower:
                    changes['anterior_resection_type'] = 'low_ar'
        
        # Apply changes if any
        if changes:
            changes['updated_at'] = datetime.utcnow()
            
            if not dry_run:
                db.treatments.update_one(
                    {'_id': treatment['_id']},
                    {'$set': changes}
                )
            
            updated += 1
            
            if updated % 100 == 0:
                print(f"Cleaned {updated:,} treatments...")
    
    print("\n" + "="*80)
    print(f"Cleaning {'(DRY RUN) ' if dry_run else ''}completed!")
    print(f"  Total treatments: {len(treatments):,}")
    print(f"  Updated: {updated:,}")
    print("="*80)
    
    return updated

def show_before_after_samples():
    """Show sample data before and after cleaning"""
    print("\nSample data (showing first 5 with changes):")
    print("="*80)
    
    treatments = list(db.treatments.find({
        'treatment_type': 'surgery',
        'procedure_name': {'$regex': r'^\d+\s'}
    }).limit(5))
    
    for t in treatments:
        print(f"\nTreatment: {t.get('treatment_id')}")
        print(f"  Before:")
        print(f"    procedure_name: {t.get('procedure_name')}")
        print(f"    asa_score: {t.get('asa_score')}")
        
        # Show what it would become
        proc = t.get('procedure_name')
        if proc and proc in PROCEDURE_MAPPINGS:
            print(f"  After:")
            print(f"    procedure_name: {PROCEDURE_MAPPINGS[proc]}")
            print(f"    asa_score: {standardize_asa_score(t.get('asa_score'))}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean and standardize surgery treatment data')
    parser.add_argument('--dry-run', action='store_true', help='Dry run - show what would change')
    parser.add_argument('--samples', action='store_true', help='Show before/after samples')
    
    args = parser.parse_args()
    
    if args.samples:
        show_before_after_samples()
    else:
        clean_treatments(dry_run=args.dry_run)
