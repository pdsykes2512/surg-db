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
    """Get overall surgical outcome statistics from treatments with yearly breakdown"""
    db = Database.get_database()
    treatments_collection = db.treatments
    
    # Get all surgical treatments with valid OPCS-4 codes
    # Only count primary surgeries (RTT and reversals are captured in other metrics)
    all_treatments = await treatments_collection.find({
        "treatment_type": "surgery_primary",
        "opcs4_code": {"$exists": True, "$ne": ""}
    }).to_list(length=None)
    total_surgeries = len(all_treatments)
    
    # Helper function to calculate metrics for a list of treatments
    def calculate_metrics(treatments):
        """Calculate outcome metrics from treatment records.
        
        Computes key surgical outcome metrics including complication rates,
        mortality, readmissions, and length of stay statistics.
        
        Args:
            treatments: List of treatment dictionaries with outcomes data
        
        Returns:
            dict: Metrics dictionary with keys:
                - total_surgeries: int, count of treatments
                - complication_rate: float, percentage with complications
                - readmission_rate: float, percentage readmitted within 30 days
                - mortality_30d_rate: float, percentage died within 30 days
                - mortality_90d_rate: float, percentage died within 90 days
                - return_to_theatre_rate: float, percentage requiring RTT
                - escalation_rate: float, percentage requiring ICU
                - median_length_of_stay_days: float, median LOS
        
        Note:
            Returns zeros for all metrics if treatments list is empty.
        """
        if not treatments:
            return {
                "total_surgeries": 0,
                "complication_rate": 0,
                "readmission_rate": 0,
                "mortality_30d_rate": 0,
                "mortality_90d_rate": 0,
                "return_to_theatre_rate": 0,
                "escalation_rate": 0,
                "median_length_of_stay_days": 0
            }

        total = len(treatments)

        # Access nested fields correctly
        # Note: 'complications' is a boolean, 'occurred' fields are strings "yes"/"no"
        surgeries_with_complications = sum(1 for t in treatments
                                          if t.get('postoperative_events', {}).get('complications'))
        readmissions = sum(1 for t in treatments
                          if t.get('outcomes', {}).get('readmission_30day') == 'yes')

        # Use boolean mortality fields (auto-populated from deceased_date)
        mortality_30d_count = sum(1 for t in treatments if t.get('outcomes', {}).get('mortality_30day') == True)
        mortality_90d_count = sum(1 for t in treatments if t.get('outcomes', {}).get('mortality_90day') == True)

        return_to_theatre = sum(1 for t in treatments
                               if t.get('outcomes', {}).get('return_to_theatre') == 'yes')
        escalation_of_care = sum(1 for t in treatments
                                if t.get('postoperative_events', {}).get('icu_admission'))

        # Calculate median length of stay from nested field
        los_values = [t.get('perioperative_timeline', {}).get('length_of_stay_days')
                     for t in treatments
                     if t.get('perioperative_timeline', {}).get('length_of_stay_days') is not None]
        if los_values:
            sorted_los = sorted(los_values)
            n = len(sorted_los)
            median_los = sorted_los[n // 2] if n % 2 == 1 else (sorted_los[n // 2 - 1] + sorted_los[n // 2]) / 2
        else:
            median_los = 0
        
        return {
            "total_surgeries": total,
            "complication_rate": round((surgeries_with_complications / total * 100), 2),
            "readmission_rate": round((readmissions / total * 100), 2),
            "mortality_30d_rate": round((mortality_30d_count / total * 100), 2),
            "mortality_90d_rate": round((mortality_90d_count / total * 100), 2),
            "return_to_theatre_rate": round((return_to_theatre / total * 100), 2),
            "escalation_rate": round((escalation_of_care / total * 100), 2),
            "median_length_of_stay_days": round(median_los, 2)
        }
    
    # Split treatments by year (last 20 years)
    current_year = datetime.utcnow().year
    start_year = current_year - 19  # 20 years of data (e.g., 2006-2025)

    # Create a dictionary to hold treatments by year
    treatments_by_year = {year: [] for year in range(start_year, current_year + 1)}

    for t in all_treatments:
        treatment_date = t.get('treatment_date')
        if treatment_date:
            try:
                if isinstance(treatment_date, str):
                    # Parse ISO format date string (e.g., "2024-01-15" or "2024-01-15T10:30:00")
                    dt = datetime.fromisoformat(treatment_date.replace('Z', '+00:00'))
                else:
                    dt = treatment_date

                # Add treatment to the appropriate year if within our 20-year range
                if start_year <= dt.year <= current_year:
                    treatments_by_year[dt.year].append(t)
            except:
                pass

    # Calculate overall metrics
    overall_metrics = calculate_metrics(all_treatments)

    # Calculate yearly metrics for all years
    yearly_breakdown = {}
    for year in range(start_year, current_year + 1):
        yearly_breakdown[str(year)] = calculate_metrics(treatments_by_year[year])
    
    # Urgency breakdown - using nested field
    urgency_breakdown = {}
    for treatment in all_treatments:
        urgency = treatment.get('classification', {}).get('urgency', 'unknown')
        urgency_breakdown[urgency] = urgency_breakdown.get(urgency, 0) + 1

    # ASA score breakdown - using top-level field
    # Convert numbers to Roman numerals for frontend display
    asa_to_roman = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V'}
    asa_breakdown = {}
    for treatment in all_treatments:
        asa = treatment.get('asa_score')
        if asa is None:
            asa_key = 'unknown'
        else:
            asa_key = asa_to_roman.get(asa, str(asa))
        asa_breakdown[asa_key] = asa_breakdown.get(asa_key, 0) + 1

    return {
        **overall_metrics,
        "urgency_breakdown": urgency_breakdown,
        "asa_breakdown": asa_breakdown,
        "yearly_breakdown": yearly_breakdown,
        "filter_applied": "Only primary surgical treatments (surgery_primary) with valid OPCS-4 codes",
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/surgeon-performance")
async def get_surgeon_performance() -> Dict[str, Any]:
    """Get surgeon-specific performance metrics stratified by episode lead clinician"""
    db = Database.get_database()
    db_system = Database.get_system_database()
    treatments_collection = db.treatments
    episodes_collection = db.episodes
    clinicians_collection = db_system.clinicians
    
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
    # Database now stores lead_clinician as names (e.g., "Jim Khan")
    all_episodes = await episodes_collection.find({}).to_list(length=None)
    episode_to_lead_clinician = {}
    for episode in all_episodes:
        episode_id = episode.get('episode_id')
        lead_clinician_name = episode.get('lead_clinician')
        if episode_id and lead_clinician_name:
            # Try to match the name to a clinician ID (for filtering to active surgeons)
            lead_clinician_lower = lead_clinician_name.lower()
            matched_id = None
            for known_name, cid in clinician_name_to_id.items():
                if known_name in lead_clinician_lower or lead_clinician_lower in known_name:
                    matched_id = cid
                    break
            if matched_id:
                episode_to_lead_clinician[episode_id] = matched_id
    
    # Get all surgical treatments with valid OPCS-4 codes
    # Only count primary surgeries (RTT and reversals are captured in other metrics)
    all_treatments = await treatments_collection.find({
        "treatment_type": "surgery_primary",
        "opcs4_code": {"$exists": True, "$ne": ""}
    }).to_list(length=None)
    
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

        # Using nested fields from database structure
        # Note: 'complications' is a boolean, 'occurred' fields are strings "yes"/"no"
        if treatment.get('postoperative_events', {}).get('complications'):
            stats['surgeries_with_complications'] += 1
        if treatment.get('outcomes', {}).get('readmission_30day') == 'yes':
            stats['readmissions'] += 1

        # Use boolean mortality fields (auto-populated from deceased_date)
        if treatment.get('outcomes', {}).get('mortality_30day') == True:
            stats['mortality_30day'] += 1
        if treatment.get('outcomes', {}).get('mortality_90day') == True:
            stats['mortality_90day'] += 1

        if treatment.get('outcomes', {}).get('return_to_theatre') == 'yes':
            stats['return_to_theatre_count'] += 1
        if treatment.get('postoperative_events', {}).get('icu_admission'):
            stats['icu_admissions'] += 1

        duration = treatment.get('perioperative_timeline', {}).get('operation_duration_minutes')
        if duration:
            stats['duration_values'].append(duration)

        los = treatment.get('perioperative_timeline', {}).get('length_of_stay_days')
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
            'return_to_theatre_rate': round((stats['return_to_theatre_count'] / total * 100) if total > 0 else 0, 2),
            'mortality_30d_rate': round((stats['mortality_30day'] / total * 100) if total > 0 else 0, 2),
            'mortality_90d_rate': round((stats['mortality_90day'] / total * 100) if total > 0 else 0, 2),
            'median_duration': median_duration,
            'median_los': median_los
        })
    
    # Sort by total surgeries
    surgeon_list.sort(key=lambda x: x['total_surgeries'], reverse=True)
    
    return {
        "surgeons": surgeon_list,
        "filter_applied": "Only primary surgical treatments (surgery_primary) with valid OPCS-4 codes",
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
    
    # Treatment fields - only include treatments with valid OPCS-4 codes
    all_treatments = await treatments_collection.find({
        "opcs4_code": {"$exists": True, "$ne": ""}
    }).to_list(length=None)
    total_treatment_count = len(all_treatments)
    
    # Define treatment fields with their actual nested paths
    treatment_field_checks = [
        # Core
        ("treatment_id", "Core", lambda t: t.get("treatment_id")),
        ("treatment_type", "Core", lambda t: t.get("treatment_type")),
        ("treatment_date", "Core", lambda t: t.get("treatment_date")),
        ("provider_organisation", "Core", lambda t: t.get("provider_organisation")),
        # Surgery
        ("procedure_name", "Surgery", lambda t: t.get("procedure", {}).get("primary_procedure")),
        ("surgeon", "Surgery", lambda t: t.get("team", {}).get("primary_surgeon_text")),
        ("approach", "Surgery", lambda t: t.get("classification", {}).get("approach")),
        ("urgency", "Surgery", lambda t: t.get("classification", {}).get("urgency")),
        ("complexity", "Surgery", lambda t: t.get("classification", {}).get("complexity")),
        # Timeline
        ("admission_date", "Timeline", lambda t: t.get("perioperative_timeline", {}).get("admission_date")),
        ("discharge_date", "Timeline", lambda t: t.get("perioperative_timeline", {}).get("discharge_date")),
        ("operation_duration_minutes", "Timeline", lambda t: t.get("perioperative_timeline", {}).get("operation_duration_minutes")),
        ("length_of_stay", "Timeline", lambda t: t.get("perioperative_timeline", {}).get("length_of_stay_days")),
        # Outcomes (check for actual data, not just presence)
        ("complications", "Outcomes", lambda t: t.get("postoperative_events", {}).get("complications")),
        ("readmission_30d", "Outcomes", lambda t: t.get("outcomes", {}).get("readmission_30day") == 'yes'),
        ("return_to_theatre", "Outcomes", lambda t: t.get("postoperative_events", {}).get("return_to_theatre", {}).get("occurred") == 'yes'),
        ("clavien_dindo_grade", "Outcomes", lambda t: t.get("postoperative_events", {}).get("clavien_dindo_grade")),
        ("asa_score", "Assessment", lambda t: t.get("asa_score")),
    ]

    treatment_fields_flat = []
    for field_name, category_name, field_getter in treatment_field_checks:
        complete_count = sum(1 for t in all_treatments if field_getter(t))
        treatment_fields_flat.append({
            "field": field_name,
            "category": category_name,
            "complete_count": complete_count,
            "total_count": total_treatment_count,
            "completeness": round((complete_count / total_treatment_count * 100) if total_treatment_count > 0 else 0, 2),
            "missing_count": total_treatment_count - complete_count
        })

    # Tumour fields - TNM staging
    all_tumours = await tumours_collection.find({}).to_list(length=None)
    total_tumour_count = len(all_tumours)

    # Define tumour field checks (excluding 'x' and null as invalid)
    tumour_field_checks = [
        ("clinical_t", "TNM Staging", lambda tum: tum.get("clinical_t") not in [None, "", "x"]),
        ("clinical_n", "TNM Staging", lambda tum: tum.get("clinical_n") not in [None, "", "x"]),
        ("clinical_m", "TNM Staging", lambda tum: tum.get("clinical_m") not in [None, "", "x"]),
        ("pathological_t", "TNM Staging", lambda tum: tum.get("pathological_t") not in [None, "", "x"]),
        ("pathological_n", "TNM Staging", lambda tum: tum.get("pathological_n") not in [None, "", "x"]),
        ("pathological_m", "TNM Staging", lambda tum: tum.get("pathological_m") not in [None, "", "x"]),
    ]

    tumour_fields_flat = []
    for field_name, category_name, field_getter in tumour_field_checks:
        complete_count = sum(1 for tum in all_tumours if field_getter(tum))
        tumour_fields_flat.append({
            "field": field_name,
            "category": category_name,
            "complete_count": complete_count,
            "total_count": total_tumour_count,
            "completeness": round((complete_count / total_tumour_count * 100) if total_tumour_count > 0 else 0, 2),
            "missing_count": total_tumour_count - complete_count
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
        "tumour_fields": tumour_fields_flat,
        "filter_applied": "Only treatments with valid OPCS-4 codes",
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/cosd-completeness")
async def get_cosd_completeness(year: Optional[int] = Query(None, description="Year to filter (e.g., 2024). If not provided, returns all years.")) -> Dict[str, Any]:
    """
    Get COSD (Cancer Outcomes and Services Dataset) field completeness metrics.

    COSD fields are mandatory NHS England fields required for cancer reporting.
    This endpoint analyzes completeness by year based on treatment date.
    """
    db = Database.get_database()
    episodes_collection = db.episodes
    treatments_collection = db.treatments
    tumours_collection = db.tumours

    # Build query for year filter - only include treatments with valid OPCS-4 codes
    year_query = {
        "opcs4_code": {"$exists": True, "$ne": ""}
    }
    if year:
        # Filter treatments by year
        year_query["treatment_date"] = {
            "$gte": f"{year}-01-01",
            "$lte": f"{year}-12-31"
        }

    # Get treatments for the specified year (or all)
    all_treatments = await treatments_collection.find(year_query).to_list(length=None)
    total_treatments = len(all_treatments)

    if total_treatments == 0:
        return {
            "year": year,
            "total_treatments": 0,
            "total_episodes": 0,
            "overall_completeness": 0,
            "cosd_fields": [],
            "generated_at": datetime.utcnow().isoformat()
        }

    # Get unique episode IDs from treatments
    episode_ids = list(set(t.get("episode_id") for t in all_treatments if t.get("episode_id")))
    all_episodes = await episodes_collection.find({"episode_id": {"$in": episode_ids}}).to_list(length=None)
    total_episodes = len(all_episodes)

    # Get unique patient IDs
    patient_ids = list(set(e.get("patient_id") for e in all_episodes if e.get("patient_id")))

    # Get tumours for these episodes
    all_tumours = await tumours_collection.find({"episode_id": {"$in": episode_ids}}).to_list(length=None)

    # Define COSD mandatory fields with their field codes
    # Based on COSD v9/v10 specification
    cosd_field_checks = [
        # Patient Demographics (CR*)
        ("NHS Number", "Patient", lambda: len([e for e in all_episodes if e.get("patient_id")])),
        ("Date of Birth", "Patient", lambda: len([e for e in all_episodes if e.get("patient_id")])),
        ("Gender", "Patient", lambda: len([e for e in all_episodes if e.get("patient_id")])),
        ("Postcode", "Patient", lambda: len([e for e in all_episodes if e.get("patient_id")])),

        # Referral (CR0200-CR0230)
        ("Referral Date (CR0200)", "Referral", lambda: sum(1 for e in all_episodes if e.get("referral_date"))),
        ("Referral Source (CR0210)", "Referral", lambda: sum(1 for e in all_episodes if e.get("referral_source"))),
        ("First Seen Date (CR0220)", "Referral", lambda: sum(1 for e in all_episodes if e.get("first_seen_date"))),
        ("Provider First Seen (CR1410)", "Referral", lambda: sum(1 for e in all_episodes if e.get("provider_first_seen"))),

        # Cancer Diagnosis
        ("Primary Diagnosis Date (CR0440)", "Diagnosis", lambda: sum(1 for t in all_tumours if t.get("diagnosis_date"))),
        ("Tumour Site (ICD-10)", "Diagnosis", lambda: sum(1 for t in all_tumours if t.get("site"))),
        ("Morphology (ICD-O-3)", "Diagnosis", lambda: sum(1 for t in all_tumours if t.get("morphology"))),
        # TNM Staging - check pathological first (surgical specimens), fall back to clinical (pre-op staging)
        # Exclude 'x' (unknown) values - only count actual staging values (0, 1, 2, 3, 4, etc.)
        ("T Stage (CR2510)", "Diagnosis", lambda: sum(1 for t in all_tumours if (t.get("pathological_t") not in [None, "", "x"]) or (t.get("clinical_t") not in [None, "", "x"]))),
        ("N Stage (CR2520)", "Diagnosis", lambda: sum(1 for t in all_tumours if (t.get("pathological_n") not in [None, "", "x"]) or (t.get("clinical_n") not in [None, "", "x"]))),
        ("M Stage (CR2530)", "Diagnosis", lambda: sum(1 for t in all_tumours if (t.get("pathological_m") not in [None, "", "x"]) or (t.get("clinical_m") not in [None, "", "x"]))),

        # Treatment (CR0710+)
        ("Treatment Date (CR0710)", "Treatment", lambda: sum(1 for t in all_treatments if t.get("treatment_date"))),
        ("OPCS-4 Code (CR0720)", "Treatment", lambda: sum(1 for t in all_treatments if t.get("opcs4_code"))),
        ("Provider Organisation (CR1450)", "Treatment", lambda: sum(1 for t in all_treatments if t.get("provider_organisation"))),
        ("Treatment Intent (CR0730)", "Treatment", lambda: sum(1 for t in all_treatments if t.get("treatment_intent"))),

        # Surgery Specific
        ("Surgical Approach", "Surgery", lambda: sum(1 for t in all_treatments if t.get("classification", {}).get("approach"))),
        ("ASA Score (CR6010)", "Surgery", lambda: sum(1 for t in all_treatments if t.get("asa_score"))),
        ("Urgency (Elective/Emergency)", "Surgery", lambda: sum(1 for t in all_treatments if t.get("classification", {}).get("urgency"))),

        # Outcomes
        ("Discharge Date", "Outcomes", lambda: sum(1 for t in all_treatments if t.get("perioperative_timeline", {}).get("discharge_date"))),
        ("Length of Stay", "Outcomes", lambda: sum(1 for t in all_treatments if t.get("perioperative_timeline", {}).get("length_of_stay_days") is not None)),
        ("Complications", "Outcomes", lambda: sum(1 for t in all_treatments if t.get("postoperative_events", {}).get("complications"))),
    ]

    # Calculate completeness for each field
    cosd_fields = []
    total_completeness = 0

    for field_name, category, field_getter in cosd_field_checks:
        complete_count = field_getter()
        # Determine denominator based on category
        if category in ["Patient", "Referral", "Diagnosis"]:
            total_count = total_episodes if total_episodes > 0 else total_treatments
        else:
            total_count = total_treatments

        completeness = round((complete_count / total_count * 100) if total_count > 0 else 0, 2)

        cosd_fields.append({
            "field": field_name,
            "category": category,
            "complete_count": complete_count,
            "total_count": total_count,
            "completeness": completeness,
            "missing_count": total_count - complete_count
        })
        total_completeness += completeness

    overall_completeness = round(total_completeness / len(cosd_field_checks), 2) if cosd_field_checks else 0

    # Group by category for summary
    categories = {}
    for field in cosd_fields:
        cat = field["category"]
        if cat not in categories:
            categories[cat] = {"fields": [], "total_completeness": 0, "count": 0}
        categories[cat]["fields"].append(field)
        categories[cat]["total_completeness"] += field["completeness"]
        categories[cat]["count"] += 1

    category_summary = [
        {
            "category": cat,
            "field_count": data["count"],
            "avg_completeness": round(data["total_completeness"] / data["count"], 2),
            "fields": data["fields"]
        }
        for cat, data in categories.items()
    ]

    return {
        "year": year,
        "total_treatments": total_treatments,
        "total_episodes": total_episodes,
        "total_patients": len(patient_ids),
        "overall_completeness": overall_completeness,
        "categories": category_summary,
        "cosd_fields": cosd_fields,
        "filter_applied": "Only treatments with valid OPCS-4 codes",
        "generated_at": datetime.utcnow().isoformat()
    }
