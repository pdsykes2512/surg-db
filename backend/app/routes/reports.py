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
    """Get overall cancer episode statistics"""
    db = Database.get_database()
    episodes_collection = db.episodes
    treatments_collection = db.treatments
    
    # Get total episodes
    total_episodes = await episodes_collection.count_documents({"condition_type": "cancer"})
    
    # Get episodes with treatments
    episodes_with_treatments = await treatments_collection.count_documents({})
    
    # Get cancer type breakdown
    cancer_pipeline = [
        {"$match": {"condition_type": "cancer"}},
        {"$group": {"_id": "$cancer_type", "count": {"$sum": 1}}}
    ]
    cancer_breakdown = await episodes_collection.aggregate(cancer_pipeline).to_list(length=100)
    cancer_types = {item["_id"]: item["count"] for item in cancer_breakdown if item["_id"]}
    
    # Get status breakdown
    status_pipeline = [
        {"$match": {"condition_type": "cancer"}},
        {"$group": {"_id": "$episode_status", "count": {"$sum": 1}}}
    ]
    status_breakdown = await episodes_collection.aggregate(status_pipeline).to_list(length=100)
    statuses = {item["_id"]: item["count"] for item in status_breakdown if item["_id"]}
    
    return {
        "total_episodes": total_episodes,
        "episodes_with_treatments": episodes_with_treatments,
        "cancer_type_breakdown": cancer_types,
        "status_breakdown": statuses,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/surgeon-performance")
async def get_surgeon_performance() -> Dict[str, Any]:
    """Get clinician-specific performance metrics"""
    db = Database.get_database()
    episodes_collection = db.episodes
    
    pipeline = [
        {"$match": {"condition_type": "cancer"}},
        {"$group": {
            "_id": "$lead_clinician",
            "total_episodes": {"$sum": 1},
            "cancer_types": {"$addToSet": "$cancer_type"}
        }},
        {"$sort": {"total_episodes": -1}}
    ]
    
    clinician_stats = await episodes_collection.aggregate(pipeline).to_list(length=100)
    
    return {
        "surgeons": clinician_stats,
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
    for category_name, fields in episode_fields.items():
        field_stats = []
        for field in fields:
            complete_count = sum(1 for ep in all_episodes if ep.get(field))
            field_stats.append({
                "field": field,
                "complete_count": complete_count,
                "total_count": total_episodes,
                "completeness": round((complete_count / total_episodes * 100) if total_episodes > 0 else 0, 2),
                "missing_count": total_episodes - complete_count
            })
        
        avg_completeness = sum(f["completeness"] for f in field_stats) / len(field_stats) if field_stats else 0
        categories.append({
            "name": category_name,
            "total_fields": len(fields),
            "avg_completeness": round(avg_completeness, 2),
            "fields": field_stats
        })
    
    overall_completeness = sum(c["avg_completeness"] for c in categories) / len(categories) if categories else 0
    
    return {
        "total_episodes": total_episodes,
        "total_treatments": total_treatments,
        "total_tumours": total_tumours,
        "overall_completeness": round(overall_completeness, 2),
        "categories": categories,
        "generated_at": datetime.utcnow().isoformat()
    }

