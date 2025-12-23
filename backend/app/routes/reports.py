"""
Report generation API routes
"""
from fastapi import APIRouter, HTTPException, status, Query
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from ..database import Database


router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/summary")
async def get_summary_report() -> Dict[str, Any]:
    """Get overall surgical outcome statistics from treatments"""
    db = Database.get_database()
    treatments_collection = db.treatments
    
    # Get all surgical treatments
    all_treatments = await treatments_collection.find({"treatment_type": "surgery"}).to_list(length=None)
    total_surgeries = len(all_treatments)
    
    if total_surgeries == 0:
        return {
            "total_surgeries": 0,
            "complication_rate": 0,
            "readmission_rate": 0,
            "mortality_30d_rate": 0,
            "mortality_90d_rate": 0,
            "return_to_theatre_rate": 0,
            "escalation_rate": 0,
            "avg_length_of_stay_days": 0,
            "urgency_breakdown": {},
            "generated_at": datetime.utcnow().isoformat()
        }
    
    # Calculate metrics - using flat structure from AddTreatmentModal
    surgeries_with_complications = sum(1 for t in all_treatments if t.get('complications'))
    readmissions = sum(1 for t in all_treatments if t.get('readmission_30d'))
    mortality_30d_count = sum(1 for t in all_treatments if t.get('mortality_30d'))
    mortality_90d_count = sum(1 for t in all_treatments if t.get('mortality_90d'))
    return_to_theatre = sum(1 for t in all_treatments if t.get('return_to_theatre'))
    escalation_of_care = sum(1 for t in all_treatments if t.get('icu_admission'))
    
    # Calculate rates
    complication_rate = (surgeries_with_complications / total_surgeries * 100) if total_surgeries > 0 else 0
    readmission_rate = (readmissions / total_surgeries * 100) if total_surgeries > 0 else 0
    mortality_30d_rate = (mortality_30d_count / total_surgeries * 100) if total_surgeries > 0 else 0
    mortality_90d_rate = (mortality_90d_count / total_surgeries * 100) if total_surgeries > 0 else 0
    return_to_theatre_rate = (return_to_theatre / total_surgeries * 100) if total_surgeries > 0 else 0
    escalation_rate = (escalation_of_care / total_surgeries * 100) if total_surgeries > 0 else 0
    
    # Calculate median length of stay - using flat field
    los_values = [t.get('length_of_stay') for t in all_treatments if t.get('length_of_stay') is not None]
    if los_values:
        sorted_los = sorted(los_values)
        n = len(sorted_los)
        median_length_of_stay = sorted_los[n // 2] if n % 2 == 1 else (sorted_los[n // 2 - 1] + sorted_los[n // 2]) / 2
    else:
        median_length_of_stay = 0
    
    # Urgency breakdown - using flat field
    urgency_breakdown = {}
    for treatment in all_treatments:
        urgency = treatment.get('urgency', 'unknown')
        urgency_breakdown[urgency] = urgency_breakdown.get(urgency, 0) + 1
    
    return {
        "total_surgeries": total_surgeries,
        "complication_rate": round(complication_rate, 2),
        "readmission_rate": round(readmission_rate, 2),
        "mortality_30d_rate": round(mortality_30d_rate, 2),
        "mortality_90d_rate": round(mortality_90d_rate, 2),
        "return_to_theatre_rate": round(return_to_theatre_rate, 2),
        "escalation_rate": round(escalation_rate, 2),
        "median_length_of_stay_days": round(median_length_of_stay, 2),
        "urgency_breakdown": urgency_breakdown,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/surgeon-performance")
async def get_surgeon_performance() -> Dict[str, Any]:
    """Get surgeon-specific performance metrics stratified by episode lead clinician"""
    db = Database.get_database()
    treatments_collection = db.treatments
    episodes_collection = db.episodes
    clinicians_collection = db.clinicians
    
    # Get all current clinicians (active surgeons)
    clinicians = await clinicians_collection.find({"clinical_role": "surgeon"}).to_list(length=None)
    
    # Create a mapping of clinician ID to full name and name to ID
    clinician_id_to_name = {}
    clinician_name_to_id = {}
    clinician_ids = set()
    for clinician in clinicians:
        clinician_id = str(clinician['_id'])
        first_name = clinician.get('first_name', '')
        surname = clinician.get('surname', '')
        if first_name and surname:
            full_name = f"{first_name} {surname}"
            clinician_id_to_name[clinician_id] = full_name
            clinician_name_to_id[full_name.lower()] = clinician_id
            # Also try surname only
            clinician_name_to_id[surname.lower()] = clinician_id
            clinician_ids.add(clinician_id)
    
    # Get all episodes to build episode_id -> lead_clinician mapping
    all_episodes = await episodes_collection.find({}).to_list(length=None)
    episode_to_lead_clinician = {}
    for episode in all_episodes:
        episode_id = episode.get('episode_id')
        lead_clinician_name = episode.get('lead_clinician')
        if episode_id and lead_clinician_name:
            # Try to match the name to a clinician ID
            lead_clinician_lower = lead_clinician_name.lower()
            matched_id = None
            for known_name, cid in clinician_name_to_id.items():
                if known_name in lead_clinician_lower or lead_clinician_lower in known_name:
                    matched_id = cid
                    break
            if matched_id:
                episode_to_lead_clinician[episode_id] = matched_id
    
    # Get all surgical treatments
    all_treatments = await treatments_collection.find({"treatment_type": "surgery"}).to_list(length=None)
    
    # Group by episode lead clinician
    surgeon_stats = {}
    for treatment in all_treatments:
        episode_id = treatment.get('episode_id')
        if not episode_id:
            continue
        
        # Look up lead clinician from episode
        lead_clinician_id = episode_to_lead_clinician.get(episode_id)
        if not lead_clinician_id or lead_clinician_id not in clinician_ids:
            continue
        
        # Use the full name for display
        surgeon_name = clinician_id_to_name.get(lead_clinician_id, lead_clinician_id)
        
        if surgeon_name not in surgeon_stats:
            surgeon_stats[surgeon_name] = {
                '_id': surgeon_name,
                'total_surgeries': 0,
                'surgeries_with_complications': 0,
                'readmissions': 0,
                'mortality_30day': 0,
                'mortality_90day': 0,
                'return_to_theatre_count': 0,
                'icu_admissions': 0,
                'duration_values': [],  # Changed to list for median calculation
                'los_values': []  # Changed to list for median calculation
            }
        
        stats = surgeon_stats[surgeon_name]
        stats['total_surgeries'] += 1
        
        # Using flat fields from AddTreatmentModal
        if treatment.get('complications'):
            stats['surgeries_with_complications'] += 1
        if treatment.get('readmission_30d'):
            stats['readmissions'] += 1
        if treatment.get('mortality_30d'):
            stats['mortality_30day'] += 1
        if treatment.get('mortality_90d'):
            stats['mortality_90day'] += 1
        if treatment.get('return_to_theatre'):
            stats['return_to_theatre_count'] += 1
        if treatment.get('icu_admission'):
            stats['icu_admissions'] += 1
        
        duration = treatment.get('operation_duration_minutes')
        if duration:
            stats['duration_values'].append(duration)
        
        los = treatment.get('length_of_stay')
        if los is not None:
            stats['los_values'].append(los)
    
    # Calculate rates and medians
    surgeon_list = []
    for surgeon, stats in surgeon_stats.items():
        total = stats['total_surgeries']
        
        # Calculate median duration
        median_duration = None
        if stats['duration_values']:
            sorted_duration = sorted(stats['duration_values'])
            n = len(sorted_duration)
            median_duration = sorted_duration[n // 2] if n % 2 == 1 else (sorted_duration[n // 2 - 1] + sorted_duration[n // 2]) / 2
            median_duration = round(median_duration, 2)
        
        # Calculate median LOS
        median_los = None
        if stats['los_values']:
            sorted_los = sorted(stats['los_values'])
            n = len(sorted_los)
            median_los = sorted_los[n // 2] if n % 2 == 1 else (sorted_los[n // 2 - 1] + sorted_los[n // 2]) / 2
            median_los = round(median_los, 2)
        
        surgeon_list.append({
            '_id': surgeon,
            'total_surgeries': total,
            'complication_rate': round((stats['surgeries_with_complications'] / total * 100) if total > 0 else 0, 2),
            'readmission_rate': round((stats['readmissions'] / total * 100) if total > 0 else 0, 2),
            'mortality_30d_rate': round((stats['mortality_30day'] / total * 100) if total > 0 else 0, 2),
            'mortality_90d_rate': round((stats['mortality_90day'] / total * 100) if total > 0 else 0, 2),
            'median_duration': median_duration,
            'median_los': median_los
        })
    
    # Sort by total surgeries
    surgeon_list.sort(key=lambda x: x['total_surgeries'], reverse=True)
    
    return {
        "surgeons": surgeon_list,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/data-quality")
async def get_data_quality_report() -> Dict[str, Any]:
    """Get data completeness and quality metrics"""
    db = Database.get_database()
    episodes_collection = db.episodes
    treatments_collection = db.treatments
    tumours_collection = db.tumours
    
    # Get all episodes
    all_episodes = await episodes_collection.find({"condition_type": "cancer"}).to_list(length=None)
    total_episodes = len(all_episodes)
    
    # Get all treatments and tumours
    total_treatments = await treatments_collection.count_documents({})
    total_tumours = await tumours_collection.count_documents({})
    
    # Define required and optional fields for episodes
    episode_fields = {
        "Core": [
            "episode_id", "patient_id", "cancer_type", "lead_clinician", 
            "referral_date", "episode_status"
        ],
        "Referral": [
            "referral_source", "provider_first_seen", "first_seen_date"
        ],
        "MDT": [
            "mdt_discussion_date", "mdt_meeting_type", "mdt_team"
        ],
        "Clinical": [
            "performance_status", "cns_involved"
        ]
    }
    
    # Calculate completeness
    categories = []
    episode_fields_flat = []
    for category_name, fields in episode_fields.items():
        field_stats = []
        for field in fields:
            complete_count = sum(1 for ep in all_episodes if ep.get(field))
            field_data = {
                "field": field,
                "category": category_name,
                "complete_count": complete_count,
                "total_count": total_episodes,
                "completeness": round((complete_count / total_episodes * 100) if total_episodes > 0 else 0, 2),
                "missing_count": total_episodes - complete_count
            }
            field_stats.append(field_data)
            episode_fields_flat.append(field_data)
        
        avg_completeness = sum(f["completeness"] for f in field_stats) / len(field_stats) if field_stats else 0
        categories.append({
            "name": category_name,
            "total_fields": len(fields),
            "avg_completeness": round(avg_completeness, 2),
            "fields": field_stats
        })
    
    # Treatment fields
    all_treatments = await treatments_collection.find({}).to_list(length=None)
    total_treatment_count = len(all_treatments)
    
    treatment_field_defs = {
        "Core": ["treatment_id", "treatment_type", "treatment_date", "provider_organisation"],
        "Surgery": ["procedure_name", "surgeon", "approach", "urgency", "complexity"],
        "Timeline": ["admission_date", "discharge_date", "operation_duration_minutes", "length_of_stay"],
        "Outcomes": ["complications", "readmission_30d", "return_to_theatre", "clavien_dindo_grade"]
    }
    
    treatment_fields_flat = []
    for category_name, fields in treatment_field_defs.items():
        for field in fields:
            complete_count = sum(1 for t in all_treatments if t.get(field))
            treatment_fields_flat.append({
                "field": field,
                "category": category_name,
                "complete_count": complete_count,
                "total_count": total_treatment_count,
                "completeness": round((complete_count / total_treatment_count * 100) if total_treatment_count > 0 else 0, 2),
                "missing_count": total_treatment_count - complete_count
            })
    
    overall_completeness = sum(c["avg_completeness"] for c in categories) / len(categories) if categories else 0
    
    return {
        "total_episodes": total_episodes,
        "total_treatments": total_treatments,
        "total_tumours": total_tumours,
        "overall_completeness": round(overall_completeness, 2),
        "categories": categories,
        "episode_fields": episode_fields_flat,
        "treatment_fields": treatment_fields_flat,
        "generated_at": datetime.utcnow().isoformat()
    }

