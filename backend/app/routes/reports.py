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
    """Get overall surgical outcome statistics from treatments with yearly breakdown

    Optimized version using MongoDB aggregation instead of in-memory processing.
    This significantly improves performance for large datasets (10K+ treatments).
    """
    db = Database.get_database()
    treatments_collection = db.treatments

    # Use MongoDB aggregation to compute metrics efficiently
    # Match only primary surgeries with valid OPCS-4 codes
    pipeline = [
        {
            "$match": {
                "treatment_type": "surgery_primary",
                "opcs4_code": {"$exists": True, "$ne": ""}
            }
        },
        {
            "$facet": {
                # Count total surgeries
                "total": [{"$count": "count"}],

                # Calculate outcome metrics
                "outcomes": [
                    {
                        "$group": {
                            "_id": None,
                            "total": {"$sum": 1},
                            "complications": {
                                "$sum": {
                                    "$cond": [
                                        {"$eq": ["$postoperative_events.complications", True]},
                                        1,
                                        0
                                    ]
                                }
                            },
                            "readmissions": {
                                "$sum": {
                                    "$cond": [
                                        {"$eq": ["$outcomes.readmission_30day", "yes"]},
                                        1,
                                        0
                                    ]
                                }
                            },
                            "mortality_30d": {
                                "$sum": {
                                    "$cond": [
                                        {"$eq": ["$outcomes.mortality_30day", True]},
                                        1,
                                        0
                                    ]
                                }
                            },
                            "mortality_90d": {
                                "$sum": {
                                    "$cond": [
                                        {"$eq": ["$outcomes.mortality_90day", True]},
                                        1,
                                        0
                                    ]
                                }
                            },
                            "return_to_theatre": {
                                "$sum": {
                                    "$cond": [
                                        {"$eq": ["$outcomes.return_to_theatre", "yes"]},
                                        1,
                                        0
                                    ]
                                }
                            },
                            "icu_admission": {
                                "$sum": {
                                    "$cond": [
                                        {"$eq": ["$postoperative_events.icu_admission", True]},
                                        1,
                                        0
                                    ]
                                }
                            },
                            "los_values": {
                                "$push": {
                                    "$cond": [
                                        {"$ne": ["$perioperative_timeline.length_of_stay_days", None]},
                                        "$perioperative_timeline.length_of_stay_days",
                                        "$$REMOVE"
                                    ]
                                }
                            }
                        }
                    }
                ],

                # Get yearly breakdown
                "yearly": [
                    {
                        "$addFields": {
                            "treatment_year": {
                                "$cond": [
                                    {"$ne": ["$treatment_date", None]},
                                    {
                                        "$year": {
                                            "$cond": [
                                                {"$eq": [{"$type": "$treatment_date"}, "string"]},
                                                {"$dateFromString": {"dateString": "$treatment_date"}},
                                                "$treatment_date"
                                            ]
                                        }
                                    },
                                    None
                                ]
                            }
                        }
                    },
                    {
                        "$match": {
                            "treatment_year": {"$ne": None}
                        }
                    },
                    {
                        "$group": {
                            "_id": "$treatment_year",
                            "total": {"$sum": 1},
                            "complications": {
                                "$sum": {
                                    "$cond": [
                                        {"$eq": ["$postoperative_events.complications", True]},
                                        1,
                                        0
                                    ]
                                }
                            },
                            "readmissions": {
                                "$sum": {
                                    "$cond": [
                                        {"$eq": ["$outcomes.readmission_30day", "yes"]},
                                        1,
                                        0
                                    ]
                                }
                            },
                            "mortality_30d": {
                                "$sum": {
                                    "$cond": [
                                        {"$eq": ["$outcomes.mortality_30day", True]},
                                        1,
                                        0
                                    ]
                                }
                            },
                            "mortality_90d": {
                                "$sum": {
                                    "$cond": [
                                        {"$eq": ["$outcomes.mortality_90day", True]},
                                        1,
                                        0
                                    ]
                                }
                            },
                            "return_to_theatre": {
                                "$sum": {
                                    "$cond": [
                                        {"$eq": ["$outcomes.return_to_theatre", "yes"]},
                                        1,
                                        0
                                    ]
                                }
                            },
                            "icu_admission": {
                                "$sum": {
                                    "$cond": [
                                        {"$eq": ["$postoperative_events.icu_admission", True]},
                                        1,
                                        0
                                    ]
                                }
                            },
                            "los_values": {
                                "$push": {
                                    "$cond": [
                                        {"$ne": ["$perioperative_timeline.length_of_stay_days", None]},
                                        "$perioperative_timeline.length_of_stay_days",
                                        "$$REMOVE"
                                    ]
                                }
                            }
                        }
                    }
                ],

                # Get urgency breakdown
                "urgency": [
                    {
                        "$group": {
                            "_id": "$classification.urgency",
                            "count": {"$sum": 1}
                        }
                    }
                ],

                # Get specialty breakdown
                "specialty": [
                    {
                        "$group": {
                            "_id": "$classification.specialty",
                            "count": {"$sum": 1}
                        }
                    }
                ]
            }
        }
    ]

    # Execute aggregation
    results = await treatments_collection.aggregate(pipeline).to_list(length=1)
    if not results:
        # Return empty metrics if no data
        return {
            "total_surgeries": 0,
            "overall_metrics": {
                "total_surgeries": 0,
                "complication_rate": 0,
                "readmission_rate": 0,
                "mortality_30d_rate": 0,
                "mortality_90d_rate": 0,
                "return_to_theatre_rate": 0,
                "escalation_rate": 0,
                "median_length_of_stay_days": 0
            },
            "yearly_breakdown": {},
            "urgency_breakdown": {},
            "specialty_breakdown": {}
        }

    result = results[0]
    total_surgeries = result["total"][0]["count"] if result["total"] else 0

    # Process aggregation results
    overall_outcomes = result["outcomes"][0] if result["outcomes"] else None
    if overall_outcomes and overall_outcomes["total"] > 0:
        total = overall_outcomes["total"]
        # Calculate median LOS from los_values array
        los_values = sorted(overall_outcomes.get("los_values", []))
        if los_values:
            n = len(los_values)
            median_los = los_values[n // 2] if n % 2 == 1 else (los_values[n // 2 - 1] + los_values[n // 2]) / 2
        else:
            median_los = 0

        overall_metrics = {
            "total_surgeries": total,
            "complication_rate": round((overall_outcomes["complications"] / total * 100), 2),
            "readmission_rate": round((overall_outcomes["readmissions"] / total * 100), 2),
            "mortality_30d_rate": round((overall_outcomes["mortality_30d"] / total * 100), 2),
            "mortality_90d_rate": round((overall_outcomes["mortality_90d"] / total * 100), 2),
            "return_to_theatre_rate": round((overall_outcomes["return_to_theatre"] / total * 100), 2),
            "escalation_rate": round((overall_outcomes["icu_admission"] / total * 100), 2),
            "median_length_of_stay_days": round(median_los, 1)
        }
    else:
        overall_metrics = {
            "total_surgeries": 0,
            "complication_rate": 0,
            "readmission_rate": 0,
            "mortality_30d_rate": 0,
            "mortality_90d_rate": 0,
            "return_to_theatre_rate": 0,
            "escalation_rate": 0,
            "median_length_of_stay_days": 0
        }

    # Build yearly breakdown
    yearly_breakdown = {}
    for year_data in result.get("yearly", []):
        if year_data["_id"] and year_data["total"] > 0:
            year = str(year_data["_id"])
            total = year_data["total"]
            # Calculate median LOS for this year
            los_values = sorted(year_data.get("los_values", []))
            if los_values:
                n = len(los_values)
                median_los = los_values[n // 2] if n % 2 == 1 else (los_values[n // 2 - 1] + los_values[n // 2]) / 2
            else:
                median_los = 0

            yearly_breakdown[year] = {
                "total_surgeries": total,
                "complication_rate": round((year_data["complications"] / total * 100), 2),
                "readmission_rate": round((year_data["readmissions"] / total * 100), 2),
                "mortality_30d_rate": round((year_data["mortality_30d"] / total * 100), 2),
                "mortality_90d_rate": round((year_data["mortality_90d"] / total * 100), 2),
                "return_to_theatre_rate": round((year_data["return_to_theatre"] / total * 100), 2),
                "escalation_rate": round((year_data["icu_admission"] / total * 100), 2),
                "median_length_of_stay_days": round(median_los, 1)
            }

    # Build urgency breakdown
    urgency_breakdown = {item["_id"]: item["count"] for item in result.get("urgency", []) if item["_id"]}

    # Build specialty breakdown
    specialty_breakdown = {item["_id"]: item["count"] for item in result.get("specialty", []) if item["_id"]}

    return {
        **overall_metrics,
        "urgency_breakdown": urgency_breakdown,
        "specialty_breakdown": specialty_breakdown,
        "yearly_breakdown": yearly_breakdown,
        "filter_applied": "Only primary surgical treatments (surgery_primary) with valid OPCS-4 codes",
        "generated_at": datetime.utcnow().isoformat()
    }



@router.get("/surgeon-performance")
async def get_surgeon_performance(specialty: Optional[str] = Query(None, description="Filter by subspecialty: colorectal, urology, breast, upper_gi, gynae_onc, other")) -> Dict[str, Any]:
    """Get surgeon-specific performance metrics stratified by episode lead clinician"""
    db = Database.get_database()
    db_system = Database.get_system_database()
    treatments_collection = db.treatments
    episodes_collection = db.episodes
    clinicians_collection = db_system.clinicians

    # Mapping between subspecialties and cancer types
    specialty_to_cancer_types = {
        "colorectal": ["bowel"],
        "urology": ["kidney", "prostate"],
        "breast": ["breast_primary", "breast_metastatic"],
        "upper_gi": ["oesophageal"],
        "gynae_onc": ["ovarian"],
        "other": []  # No specific cancer type filter for 'other'
    }

    # Hybrid approach: Use aggregation for treatments+episodes (same DB),
    # then efficiently join with clinicians (different DB) in Python

    # Step 1: Get clinicians from system DB (with filters)
    clinician_query = {"clinical_role": "surgeon"}
    if specialty:
        clinician_query["subspecialty_leads"] = specialty

    # Only fetch needed fields to minimize memory
    clinician_projection = {"first_name": 1, "surname": 1, "subspecialty_leads": 1}
    clinicians = await clinicians_collection.find(clinician_query, clinician_projection).to_list(length=None)

    # Build name lookup maps (efficient O(1) lookups later)
    clinician_name_to_info = {}
    for clinician in clinicians:
        first_name = clinician.get('first_name', '')
        surname = clinician.get('surname', '')
        if first_name and surname:
            full_name = f"{first_name} {surname}"
            clinician_name_to_info[full_name.lower()] = full_name
            # Also index by surname only for flexible matching
            clinician_name_to_info[surname.lower()] = full_name

    # If no clinicians match filters, return empty result early
    if not clinician_name_to_info:
        return {
            "surgeons": [],
            "specialty_filter": specialty,
            "filter_applied": f"Filtered by subspecialty: {specialty}" if specialty else "All subspecialties",
            "generated_at": datetime.utcnow().isoformat()
        }

    # Step 2: Build aggregation pipeline for treatments + episodes
    pipeline = []

    # Stage 1: Match treatments (only primary surgeries with valid OPCS-4 codes)
    pipeline.append({
        "$match": {
            "treatment_type": "surgery_primary",
            "opcs4_code": {"$exists": True, "$ne": ""}
        }
    })

    # Stage 2: Lookup episode to get lead_clinician name and cancer_type
    pipeline.append({
        "$lookup": {
            "from": "episodes",
            "localField": "episode_id",
            "foreignField": "episode_id",
            "as": "episode"
        }
    })

    # Stage 3: Unwind episode array (should be 1-to-1)
    pipeline.append({
        "$unwind": {
            "path": "$episode",
            "preserveNullAndEmptyArrays": False  # Skip treatments without episodes
        }
    })

    # Stage 4: Filter by cancer type if specialty is specified
    if specialty and specialty in specialty_to_cancer_types:
        cancer_types = specialty_to_cancer_types[specialty]
        if cancer_types:  # Only filter if there are specific cancer types (not 'other')
            pipeline.append({
                "$match": {
                    "episode.cancer_type": {"$in": cancer_types}
                }
            })

    # Stage 5: Group by lead clinician name and calculate statistics
    pipeline.append({
        "$group": {
            "_id": "$episode.lead_clinician",
            "total_surgeries": {"$sum": 1},
            "surgeries_with_complications": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$postoperative_events.complications", True]},
                        1,
                        0
                    ]
                }
            },
            "readmissions": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$outcomes.readmission_30day", "yes"]},
                        1,
                        0
                    ]
                }
            },
            "mortality_30day": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$outcomes.mortality_30day", True]},
                        1,
                        0
                    ]
                }
            },
            "mortality_90day": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$outcomes.mortality_90day", True]},
                        1,
                        0
                    ]
                }
            },
            "return_to_theatre_count": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$outcomes.return_to_theatre", "yes"]},
                        1,
                        0
                    ]
                }
            },
            "icu_admissions": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$postoperative_events.icu_admission", True]},
                        1,
                        0
                    ]
                }
            },
            "duration_values": {
                "$push": {
                    "$cond": [
                        {"$ne": ["$perioperative_timeline.operation_duration_minutes", None]},
                        "$perioperative_timeline.operation_duration_minutes",
                        "$$REMOVE"
                    ]
                }
            },
            "los_values": {
                "$push": {
                    "$cond": [
                        {"$ne": ["$perioperative_timeline.length_of_stay_days", None]},
                        "$perioperative_timeline.length_of_stay_days",
                        "$$REMOVE"
                    ]
                }
            }
        }
    })

    # Stage 6: Keep raw values and counts for accurate merging later
    # Don't calculate rates/medians yet - we'll merge raw data first, then calculate
    pipeline.append({
        "$project": {
            "_id": 1,
            "total_surgeries": 1,
            "surgeries_with_complications": 1,
            "readmissions": 1,
            "mortality_30day": 1,
            "mortality_90day": 1,
            "return_to_theatre_count": 1,
            "duration_values": 1,
            "los_values": 1
        }
    })

    # Execute aggregation pipeline - returns results grouped by lead_clinician name
    aggregated_results = await treatments_collection.aggregate(pipeline).to_list(length=None)

    # Step 3: Filter results to only include known surgeons and calculate statistics
    # Helper function to calculate median
    def calculate_median(values):
        """Calculate true median from array of values"""
        if not values:
            return None
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n % 2 == 1:
            return round(sorted_values[n // 2], 2)
        else:
            return round((sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2, 2)

    surgeon_list = []
    for result in aggregated_results:
        lead_clinician_name = result.get('_id')
        if not lead_clinician_name:
            continue

        # Only include if exact match with known surgeon (case-insensitive)
        lead_clinician_lower = lead_clinician_name.lower()
        if lead_clinician_lower in clinician_name_to_info:
            matched_name = clinician_name_to_info[lead_clinician_lower]
            total = result['total_surgeries']

            surgeon_list.append({
                '_id': matched_name,
                'total_surgeries': total,
                'complication_rate': round((result['surgeries_with_complications'] / total) * 100, 2) if total > 0 else 0.0,
                'readmission_rate': round((result['readmissions'] / total) * 100, 2) if total > 0 else 0.0,
                'return_to_theatre_rate': round((result['return_to_theatre_count'] / total) * 100, 2) if total > 0 else 0.0,
                'mortality_30d_rate': round((result['mortality_30day'] / total) * 100, 2) if total > 0 else 0.0,
                'mortality_90d_rate': round((result['mortality_90day'] / total) * 100, 2) if total > 0 else 0.0,
                'median_duration': calculate_median(result.get('duration_values', [])),
                'median_los': calculate_median(result.get('los_values', []))
            })

    # Sort by total surgeries descending
    surgeon_list.sort(key=lambda x: x['total_surgeries'], reverse=True)
    
    filter_description = "Only primary surgical treatments (surgery_primary) with valid OPCS-4 codes"
    if specialty:
        filter_description += f" | Filtered by subspecialty: {specialty}"
        if specialty in specialty_to_cancer_types and specialty_to_cancer_types[specialty]:
            cancer_types_str = ", ".join(specialty_to_cancer_types[specialty])
            filter_description += f" (cancer types: {cancer_types_str})"

    return {
        "surgeons": surgeon_list,
        "specialty_filter": specialty,
        "filter_applied": filter_description,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/data-quality")
async def get_data_quality_report() -> Dict[str, Any]:
    """Get data completeness and quality metrics using aggregation"""
    db = Database.get_database()
    episodes_collection = db.episodes
    treatments_collection = db.treatments
    tumours_collection = db.tumours

    # Count episodes using aggregation (much faster than fetch + len)
    episode_count_result = await episodes_collection.aggregate([
        {"$match": {"condition_type": "cancer"}},
        {"$count": "total"}
    ]).to_list(1)
    total_episodes = episode_count_result[0]["total"] if episode_count_result else 0
    
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

    # Use aggregation to count field completeness (much faster than fetch + loop)
    categories = []
    episode_fields_flat = []

    for category_name, fields in episode_fields.items():
        field_stats = []

        # Build aggregation pipeline to count complete fields for all fields at once
        facet_stages = {}
        for field in fields:
            facet_stages[field] = [
                {
                    "$match": {
                        "condition_type": "cancer",
                        field: {"$exists": True, "$ne": None, "$ne": ""}
                    }
                },
                {"$count": "count"}
            ]

        # Execute aggregation
        pipeline = [
            {"$match": {"condition_type": "cancer"}},
            {"$facet": facet_stages}
        ]

        result = await episodes_collection.aggregate(pipeline).to_list(1)
        field_counts = result[0] if result else {}

        # Process results
        for field in fields:
            field_result = field_counts.get(field, [])
            complete_count = field_result[0].get("count", 0) if field_result else 0
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
    
    # Treatment fields - count using aggregation (much faster)
    treatment_count_result = await treatments_collection.aggregate([
        {"$match": {"opcs4_code": {"$exists": True, "$ne": ""}}},
        {"$count": "total"}
    ]).to_list(1)
    total_treatment_count = treatment_count_result[0]["total"] if treatment_count_result else 0

    # Define treatment field paths for aggregation
    treatment_field_paths = [
        # Core
        ("treatment_id", "Core", "treatment_id"),
        ("treatment_type", "Core", "treatment_type"),
        ("treatment_date", "Core", "treatment_date"),
        ("provider_organisation", "Core", "provider_organisation"),
        # Surgery
        ("procedure_name", "Surgery", "procedure.primary_procedure"),
        ("surgeon", "Surgery", "team.primary_surgeon_text"),
        ("approach", "Surgery", "classification.approach"),
        ("urgency", "Surgery", "classification.urgency"),
        ("complexity", "Surgery", "classification.complexity"),
        # Timeline
        ("admission_date", "Timeline", "perioperative_timeline.admission_date"),
        ("discharge_date", "Timeline", "perioperative_timeline.discharge_date"),
        ("operation_duration_minutes", "Timeline", "perioperative_timeline.operation_duration_minutes"),
        ("length_of_stay", "Timeline", "perioperative_timeline.length_of_stay_days"),
        # Outcomes
        ("complications", "Outcomes", "postoperative_events.complications"),
        ("clavien_dindo_grade", "Outcomes", "postoperative_events.clavien_dindo_grade"),
        ("asa_score", "Assessment", "asa_score"),
    ]

    # Build facet stages for all treatment fields
    treatment_facet_stages = {}
    for field_name, category_name, field_path in treatment_field_paths:
        treatment_facet_stages[field_name] = [
            {
                "$match": {
                    "opcs4_code": {"$exists": True, "$ne": ""},
                    field_path: {"$exists": True, "$ne": None, "$ne": ""}
                }
            },
            {"$count": "count"}
        ]

    # Special handling for yes/no fields
    treatment_facet_stages["readmission_30d"] = [
        {
            "$match": {
                "opcs4_code": {"$exists": True, "$ne": ""},
                "outcomes.readmission_30day": "yes"
            }
        },
        {"$count": "count"}
    ]
    treatment_facet_stages["return_to_theatre"] = [
        {
            "$match": {
                "opcs4_code": {"$exists": True, "$ne": ""},
                "postoperative_events.return_to_theatre.occurred": "yes"
            }
        },
        {"$count": "count"}
    ]

    # Execute aggregation
    treatment_pipeline = [
        {"$match": {"opcs4_code": {"$exists": True, "$ne": ""}}},
        {"$facet": treatment_facet_stages}
    ]

    treatment_result = await treatments_collection.aggregate(treatment_pipeline).to_list(1)
    treatment_field_counts = treatment_result[0] if treatment_result else {}

    # Build treatment fields flat list
    treatment_fields_flat = []
    for field_name, category_name, _ in treatment_field_paths:
        field_result = treatment_field_counts.get(field_name, [])
        complete_count = field_result[0].get("count", 0) if field_result else 0
        treatment_fields_flat.append({
            "field": field_name,
            "category": category_name,
            "complete_count": complete_count,
            "total_count": total_treatment_count,
            "completeness": round((complete_count / total_treatment_count * 100) if total_treatment_count > 0 else 0, 2),
            "missing_count": total_treatment_count - complete_count
        })

    # Add special yes/no fields
    for field_name, category_name in [("readmission_30d", "Outcomes"), ("return_to_theatre", "Outcomes")]:
        field_result = treatment_field_counts.get(field_name, [])
        complete_count = field_result[0].get("count", 0) if field_result else 0
        treatment_fields_flat.append({
            "field": field_name,
            "category": category_name,
            "complete_count": complete_count,
            "total_count": total_treatment_count,
            "completeness": round((complete_count / total_treatment_count * 100) if total_treatment_count > 0 else 0, 2),
            "missing_count": total_treatment_count - complete_count
        })

    # Tumour fields - count using aggregation
    tumour_count_result = await tumours_collection.aggregate([
        {"$count": "total"}
    ]).to_list(1)
    total_tumour_count = tumour_count_result[0]["total"] if tumour_count_result else 0

    # Define tumour fields (excluding 'x' and null as invalid)
    tumour_fields = [
        ("clinical_t", "TNM Staging"),
        ("clinical_n", "TNM Staging"),
        ("clinical_m", "TNM Staging"),
        ("pathological_t", "TNM Staging"),
        ("pathological_n", "TNM Staging"),
        ("pathological_m", "TNM Staging"),
    ]

    # Build facet stages for tumour fields
    tumour_facet_stages = {}
    for field_name, _ in tumour_fields:
        tumour_facet_stages[field_name] = [
            {
                "$match": {
                    field_name: {
                        "$exists": True,
                        "$ne": None,
                        "$ne": "",
                        "$ne": "x"
                    }
                }
            },
            {"$count": "count"}
        ]

    # Execute aggregation
    tumour_pipeline = [{"$facet": tumour_facet_stages}]
    tumour_result = await tumours_collection.aggregate(tumour_pipeline).to_list(1)
    tumour_field_counts = tumour_result[0] if tumour_result else {}

    # Build tumour fields flat list
    tumour_fields_flat = []
    for field_name, category_name in tumour_fields:
        complete_count = tumour_field_counts.get(field_name, [{}])[0].get("count", 0)
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
