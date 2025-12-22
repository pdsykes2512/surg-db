"""
Report generation API routes
Updated to work with cancer episodes and treatments
"""
from fastapi import APIRouter, HTTPException, status, Query
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from ..database import get_surgeries_collection, get_episodes_collection


router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/summary")
async def get_summary_report() -> Dict[str, Any]:
    """Get overall outcome statistics from episodes and surgical treatments"""
    collection = await get_episodes_collection()
    
    # Unwind treatments array to get individual surgery treatments
    pipeline = [
        {"$unwind": {"path": "$treatments", "preserveNullAndEmptyArrays": False}},
        {"$match": {"treatments.treatment_type": "surgery"}},
        {
            "$facet": {
                "total": [{"$count": "count"}],
                # For now, simplified metrics based on available flat structure
                "urgency": [
                    {"$group": {"_id": "$treatments.urgency", "count": {"$sum": 1}}}
                ],
                "avg_duration": [
                    {"$match": {"treatments.operation_duration_minutes": {"$exists": True, "$ne": None}}},
                    {"$group": {"_id": None, "avg": {"$avg": "$treatments.operation_duration_minutes"}}}
                ]
            }
        }
    ]
    
    result = await collection.aggregate(pipeline).to_list(length=1)
    if not result or not result[0]["total"]:
        return {"total_surgeries": 0, "complication_rate": 0, "readmission_rate": 0, "mortality_rate": 0, 
                "return_to_theatre_rate": 0, "escalation_rate": 0, "avg_length_of_stay_days": 0, 
                "urgency_breakdown": {}, "generated_at": datetime.utcnow().isoformat()}
    
    stats = result[0]
    total_surgeries = stats["total"][0]["count"] if stats["total"] else 0
    
    # Temporarily return zeros for metrics not yet captured in flat structure
    # These will be populated once proper surgical treatment data structure is used
    urgency_breakdown = {item["_id"] if item["_id"] else "unknown": item["count"] for item in stats["urgency"]}
    # Ensure all urgencies are present
    for urgency in ["elective", "emergency", "urgent"]:
        if urgency not in urgency_breakdown:
            urgency_breakdown[urgency] = 0
    
    avg_duration = round(stats["avg_duration"][0]["avg"], 2) if stats["avg_duration"] and stats["avg_duration"][0] else 0
    
    return {
        "total_surgeries": total_surgeries,
        "avg_operation_duration_minutes": avg_duration,
        "complication_rate": 0,  # Not yet captured in simplified structure
        "readmission_rate": 0,  # Not yet captured in simplified structure
        "mortality_rate": 0,  # Not yet captured in simplified structure
        "return_to_theatre_rate": 0,  # Not yet captured in simplified structure
        "escalation_rate": 0,  # Not yet captured in simplified structure
        "avg_length_of_stay_days": 0,  # Can be calculated from admission/discharge dates
        "urgency_breakdown": urgency_breakdown,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/complications")
async def get_complications_report() -> Dict[str, Any]:
    """Get detailed complication analysis from surgical treatments"""
    # Currently no complications data in simplified structure
    # This will need to be populated once full treatment models are used
    
    return {
        "complications_by_type": [],
        "message": "Complications tracking not yet implemented in current data structure",
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/trends")
async def get_trends_report(
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365)
) -> Dict[str, Any]:
    """Get trends over specified time period from surgical treatments"""
    collection = await get_episodes_collection()
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Surgeries by date  
    pipeline = [
        {"$unwind": {"path": "$treatments", "preserveNullAndEmptyArrays": False}},
        {"$match": {"treatments.treatment_type": "surgery"}},
        {"$match": {"treatments.treatment_date": {"$exists": True}}},
        {"$addFields": {
            "treatment_date_parsed": {
                "$dateFromString": {
                    "dateString": "$treatments.treatment_date",
                    "onError": None,
                    "onNull": None
                }
            }
        }},
        {"$match": {"treatment_date_parsed": {"$gte": start_date, "$ne": None}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$treatment_date_parsed"}},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    
    daily_trends = await collection.aggregate(pipeline).to_list(length=days)
    
    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": datetime.utcnow().isoformat(),
        "daily_trends": daily_trends,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/surgeon-performance")
async def get_surgeon_performance() -> Dict[str, Any]:
    """Get surgeon-specific performance metrics from surgical treatments"""
    collection = await get_episodes_collection()
    
    pipeline = [
        {"$unwind": {"path": "$treatments", "preserveNullAndEmptyArrays": False}},
        {"$match": {"treatments.treatment_type": "surgery"}},
        {"$group": {
            "_id": "$treatments.surgeon",
            "total_surgeries": {"$sum": 1},
            "avg_duration": {"$avg": "$treatments.operation_duration_minutes"},
        }},
        {"$sort": {"total_surgeries": -1}}
    ]
    
    surgeon_stats = await collection.aggregate(pipeline).to_list(length=100)
    
    # Round numeric values and add placeholder zeros for metrics not yet captured
    for stat in surgeon_stats:
        if stat["avg_duration"]:
            stat["avg_duration"] = round(stat["avg_duration"], 2)
        # Temporarily return zeros for complex metrics not captured in simplified structure
        stat["complication_rate"] = 0.0
        stat["readmission_rate"] = 0.0
        stat["avg_los"] = 0.0
    
    return {
        "surgeons": surgeon_stats,
        "generated_at": datetime.utcnow().isoformat()
    }
