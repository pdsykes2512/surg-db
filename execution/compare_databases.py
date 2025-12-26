#!/usr/bin/env python3
"""
Compare surgdb (current) vs surgdb_v2 (fresh import) to determine data quality improvements.
"""

from pymongo import MongoClient
from datetime import datetime, timedelta

def analyze_database(db_name: str):
    """Analyze a database and return metrics"""
    client = MongoClient('mongodb://admin:admin123@localhost:27017')
    db = client[db_name]
    
    metrics = {
        'db_name': db_name,
        'patients': {
            'total': 0,
            'with_nhs_number': 0,
            'with_dob': 0,
            'with_gender': 0,
        },
        'episodes': {
            'total': 0,
            'with_lead_clinician': 0,
            'with_referral_date': 0,
            'with_first_seen_date': 0,
            'with_mdt_date': 0,
            'with_tumour_site': 0,
            'recent_past_5_years': 0,
            'recent_with_lead_clinician': 0,
        },
        'treatments': {
            'total': 0,
            'surgeries': 0,
            'with_complications': 0,
            'with_surgeon': 0,
            'with_date': 0,
            'with_readmission': 0,
        },
        'tumours': {
            'total': 0,
            'with_path_t': 0,
            'with_path_n': 0,
            'with_nodes_examined': 0,
        },
    }
    
    # Analyze patients
    patients = list(db.patients.find({}))
    metrics['patients']['total'] = len(patients)
    
    for p in patients:
        if p.get('nhs_number'):
            metrics['patients']['with_nhs_number'] += 1
        if p.get('demographics', {}).get('date_of_birth'):
            metrics['patients']['with_dob'] += 1
        gender = p.get('demographics', {}).get('gender')
        if gender and gender not in ['Unknown', None, '']:
            metrics['patients']['with_gender'] += 1
    
    # Analyze episodes
    episodes = list(db.episodes.find({}))
    metrics['episodes']['total'] = len(episodes)
    
    cutoff_date = datetime.now() - timedelta(days=5*365)
    
    for ep in episodes:
        if ep.get('lead_clinician'):
            metrics['episodes']['with_lead_clinician'] += 1
        if ep.get('referral_date'):
            metrics['episodes']['with_referral_date'] += 1
        if ep.get('first_seen_date'):
            metrics['episodes']['with_first_seen_date'] += 1
        if ep.get('mdt_date'):
            metrics['episodes']['with_mdt_date'] += 1
        if ep.get('tumour_site'):
            metrics['episodes']['with_tumour_site'] += 1
        
        # Check if recent
        date_obj = None
        for date_field in ['referral_date', 'first_seen_date']:
            date_val = ep.get(date_field)
            if date_val:
                try:
                    if isinstance(date_val, str):
                        date_obj = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                    elif isinstance(date_val, datetime):
                        date_obj = date_val
                    break
                except:
                    pass
        
        if date_obj and date_obj >= cutoff_date:
            metrics['episodes']['recent_past_5_years'] += 1
            if ep.get('lead_clinician'):
                metrics['episodes']['recent_with_lead_clinician'] += 1
    
    # Analyze treatments
    treatments = list(db.treatments.find({}))
    metrics['treatments']['total'] = len(treatments)
    
    for t in treatments:
        if t.get('treatment_type') == 'surgery':
            metrics['treatments']['surgeries'] += 1
        if t.get('complications'):
            metrics['treatments']['with_complications'] += 1
        if t.get('surgeon'):
            metrics['treatments']['with_surgeon'] += 1
        if t.get('treatment_date'):
            metrics['treatments']['with_date'] += 1
        if t.get('readmission'):
            metrics['treatments']['with_readmission'] += 1
    
    # Analyze tumours
    tumours = list(db.tumours.find({}))
    metrics['tumours']['total'] = len(tumours)
    
    for tum in tumours:
        if tum.get('pathological_t_stage'):
            metrics['tumours']['with_path_t'] += 1
        if tum.get('pathological_n_stage'):
            metrics['tumours']['with_path_n'] += 1
        if tum.get('nodes_examined'):
            metrics['tumours']['with_nodes_examined'] += 1
    
    return metrics


def print_comparison(old_metrics, new_metrics):
    """Print side-by-side comparison"""
    
    print("\n" + "="*80)
    print(f"DATABASE COMPARISON: {old_metrics['db_name']} vs {new_metrics['db_name']}")
    print("="*80)
    
    sections = ['patients', 'episodes', 'treatments', 'tumours']
    
    for section in sections:
        print(f"\n{section.upper()}")
        print("-" * 80)
        print(f"{'Metric':<45} {'Old':>12} {'New':>12} {'Diff':>10}")
        print("-" * 80)
        
        old_section = old_metrics[section]
        new_section = new_metrics[section]
        
        for key in old_section.keys():
            old_val = old_section[key]
            new_val = new_section[key]
            diff = new_val - old_val
            diff_str = f"+{diff}" if diff > 0 else str(diff)
            
            # Calculate percentage if total exists
            pct_str = ""
            if key != 'total' and old_section.get('total', 0) > 0:
                old_pct = (old_val / old_section['total']) * 100
                new_pct = (new_val / new_section['total']) * 100 if new_section['total'] > 0 else 0
                pct_diff = new_pct - old_pct
                pct_str = f"  ({old_pct:.1f}% → {new_pct:.1f}%)"
            
            print(f"{key:<45} {old_val:>12,} {new_val:>12,} {diff_str:>10} {pct_str}")
    
    # Key improvements section
    print("\n" + "="*80)
    print("KEY IMPROVEMENTS")
    print("="*80)
    
    improvements = []
    
    # Lead clinician improvement
    old_lc = old_metrics['episodes']['with_lead_clinician']
    new_lc = new_metrics['episodes']['with_lead_clinician']
    old_lc_pct = (old_lc / old_metrics['episodes']['total']) * 100 if old_metrics['episodes']['total'] > 0 else 0
    new_lc_pct = (new_lc / new_metrics['episodes']['total']) * 100 if new_metrics['episodes']['total'] > 0 else 0
    improvements.append(f"Lead clinician completeness: {old_lc_pct:.1f}% → {new_lc_pct:.1f}% (+{new_lc - old_lc} episodes)")
    
    # Recent episodes with lead clinician
    old_recent_lc = old_metrics['episodes']['recent_with_lead_clinician']
    new_recent_lc = new_metrics['episodes']['recent_with_lead_clinician']
    old_recent_total = old_metrics['episodes']['recent_past_5_years']
    new_recent_total = new_metrics['episodes']['recent_past_5_years']
    old_recent_pct = (old_recent_lc / old_recent_total) * 100 if old_recent_total > 0 else 0
    new_recent_pct = (new_recent_lc / new_recent_total) * 100 if new_recent_total > 0 else 0
    improvements.append(f"Recent episodes (5y) with lead clinician: {old_recent_pct:.1f}% → {new_recent_pct:.1f}% (+{new_recent_lc - old_recent_lc})")
    
    # Complication rate
    old_comp = old_metrics['treatments']['with_complications']
    new_comp = new_metrics['treatments']['with_complications']
    old_surg = old_metrics['treatments']['surgeries']
    new_surg = new_metrics['treatments']['surgeries']
    old_comp_rate = (old_comp / old_surg) * 100 if old_surg > 0 else 0
    new_comp_rate = (new_comp / new_surg) * 100 if new_surg > 0 else 0
    improvements.append(f"Complication rate: {old_comp_rate:.2f}% → {new_comp_rate:.2f}% ({old_comp} vs {new_comp} cases)")
    
    # Date completeness
    old_dates = old_metrics['episodes']['with_first_seen_date']
    new_dates = new_metrics['episodes']['with_first_seen_date']
    old_dates_pct = (old_dates / old_metrics['episodes']['total']) * 100 if old_metrics['episodes']['total'] > 0 else 0
    new_dates_pct = (new_dates / new_metrics['episodes']['total']) * 100 if new_metrics['episodes']['total'] > 0 else 0
    improvements.append(f"First seen date completeness: {old_dates_pct:.1f}% → {new_dates_pct:.1f}% (+{new_dates - old_dates})")
    
    for imp in improvements:
        print(f"  ✓ {imp}")
    
    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)
    
    # Calculate overall improvement score
    improvements_count = 0
    total_checks = 4
    
    if new_lc > old_lc:
        improvements_count += 1
    if new_recent_lc > old_recent_lc:
        improvements_count += 1
    if new_dates > old_dates:
        improvements_count += 1
    if abs(new_comp_rate - 3.5) < abs(old_comp_rate - 3.5):  # Closer to expected rate
        improvements_count += 1
    
    if improvements_count >= 3:
        print("  ✓ RECOMMEND: Use new database (surgdb_v2)")
        print("    - Significantly better data completeness")
        print("    - More accurate field mappings")
        print("    - To switch: mongodump surgdb, mongorestore surgdb_v2 to surgdb")
    elif improvements_count >= 2:
        print("  ~ CONSIDER: New database has some improvements")
        print("    - Review specific metrics that matter most to you")
        print("    - Test with application to ensure compatibility")
    else:
        print("  ✗ KEEP CURRENT: Old database appears more complete")
        print("    - May have additional data not in CSV exports")
        print("    - Fresh import may have missed some records")
    
    print("="*80)


def main():
    print("Analyzing databases...")
    
    old_metrics = analyze_database('surgdb')
    print(f"✓ Analyzed surgdb (current)")
    
    new_metrics = analyze_database('surgdb_v2')
    print(f"✓ Analyzed surgdb_v2 (fresh import)")
    
    print_comparison(old_metrics, new_metrics)


if __name__ == '__main__':
    main()
