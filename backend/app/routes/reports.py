"""
Report generation API routes
"""
from fastapi import APIRouter, HTTPException, status, Query
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from ..database import get_surgeries_collection


router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/summary")
async def get_summary_report() -> Dict[str, Any]:
    """Get overall outcome statistics"""
    collection = await get_surgeries_collection()
    
    # Use single aggregation pipeline to get all stats in one query for efficiency
    pipeline = [
        {
            "$facet": {
                "total": [{"$count": "count"}],
                "complications": [
                    {"$match": {"postoperative_events.complications": {"$exists": True, "$ne": []}}},
                    {"$count": "count"}
                ],
                "readmissions": [
                    {"$match": {"outcomes.readmission_30day": True}},
                    {"$count": "count"}
                ],
                "mortality": [
                    {"$match": {"outcomes.mortality_30day": True}},
                    {"$count": "count"}
                ],
                "return_to_theatre": [
                    {"$match": {"postoperative_events.return_to_theatre.occurred": True}},
                    {"$count": "count"}
                ],
                "escalation": [
                    {"$match": {"postoperative_events.escalation_of_care.occurred": True}},
                    {"$count": "count"}
                ],
                "avg_los": [
                    {"$match": {"perioperative_timeline.length_of_stay_days": {"$exists": True, "$ne": None}}},
                    {"$group": {"_id": None, "avg": {"$avg": "$perioperative_timeline.length_of_stay_days"}}}
                ],
                "urgency": [
                    {"$group": {"_id": "$classification.urgency", "count": {"$sum": 1}}}
                ]
            }
        }
    ]
    
    result = await collection.aggregate(pipeline).to_list(length=1)
    if not result:
        return {"total_surgeries": 0, "complication_rate": 0, "readmission_rate": 0, "mortality_rate": 0, 
                "return_to_theatre_rate": 0, "escalation_rate": 0, "avg_length_of_stay_days": 0, 
                "urgency_breakdown": {}, "generated_at": datetime.utcnow().isoformat()}
    
    stats = result[0]
    total_surgeries = stats["total"][0]["count"] if stats["total"] else 0
    
    surgeries_with_complications = stats["complications"][0]["count"] if stats["complications"] else 0
    complication_rate = (surgeries_with_complications / total_surgeries * 100) if total_surgeries > 0 else 0
    
    readmissions = stats["readmissions"][0]["count"] if stats["readmissions"] else 0
    readmission_rate = (readmissions / total_surgeries * 100) if total_surgeries > 0 else 0
    
    mortality_count = stats["mortality"][0]["count"] if stats["mortality"] else 0
    mortality_rate = (mortality_count / total_surgeries * 100) if total_surgeries > 0 else 0
    
    return_to_theatre = stats["return_to_theatre"][0]["count"] if stats["return_to_theatre"] else 0
    return_to_theatre_rate = (return_to_theatre / total_surgeries * 100) if total_surgeries > 0 else 0
    
    escalation_of_care = stats["escalation"][0]["count"] if stats["escalation"] else 0
    escalation_rate = (escalation_of_care / total_surgeries * 100) if total_surgeries > 0 else 0
    
    avg_length_of_stay = round(stats["avg_los"][0]["avg"], 2) if stats["avg_los"] and stats["avg_los"][0] else 0
    
    urgency_breakdown = {item["_id"]: item["count"] for item in stats["urgency"] if item["_id"]}
    # Ensure all urgencies are present
    for urgency in ["elective", "emergency", "urgent"]:
        if urgency not in urgency_breakdown:
            urgency_breakdown[urgency] = 0
    
    return {
        "total_surgeries": total_surgeries,
        "complication_rate": round(complication_rate, 2),
        "readmission_rate": round(readmission_rate, 2),
        "mortality_rate": round(mortality_rate, 2),
        "return_to_theatre_rate": round(return_to_theatre_rate, 2),
        "escalation_rate": round(escalation_rate, 2),
        "avg_length_of_stay_days": avg_length_of_stay,
        "urgency_breakdown": urgency_breakdown,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/complications")
async def get_complications_report() -> Dict[str, Any]:
    """Get detailed complication analysis"""
    collection = await get_surgeries_collection()
    
    # Unwind complications array and group by type
    pipeline = [
        {"$match": {"postoperative_events.complications": {"$exists": True, "$ne": []}}},
        {"$unwind": "$postoperative_events.complications"},
        {"$group": {
            "_id": "$postoperative_events.complications.type",
            "count": {"$sum": 1},
            "clavien_dindo_breakdown": {
                "$push": "$postoperative_events.complications.clavien_dindo_grade"
            }
        }},
        {"$sort": {"count": -1}}
    ]
    
    complication_types = await collection.aggregate(pipeline).to_list(length=100)
    
    # Count Clavien-Dindo grades
    for comp in complication_types:
        grade_counts = {}
        for grade in comp["clavien_dindo_breakdown"]:
            if grade:  # Handle None values
                grade_counts[grade] = grade_counts.get(grade, 0) + 1
        comp["clavien_dindo_breakdown"] = grade_counts
    
    return {
        "complications_by_type": complication_types,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/trends")
async def get_trends_report(
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365)
) -> Dict[str, Any]:
    """Get trends over specified time period"""
    collection = await get_surgeries_collection()
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Surgeries by date
    pipeline = [
        {"$match": {"perioperative_timeline.surgery_date": {"$gte": start_date}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$perioperative_timeline.surgery_date"}},
            "count": {"$sum": 1},
            "with_complications": {
                "$sum": {
                    "$cond": [
                        {"$gt": [{"$size": {"$ifNull": ["$postoperative_events.complications", []]}}, 0]},
                        1,
                        0
                    ]
                }
            },
            "return_to_theatre": {
                "$sum": {"$cond": ["$postoperative_events.return_to_theatre.occurred", 1, 0]}
            },
            "escalation_of_care": {
                "$sum": {"$cond": ["$postoperative_events.escalation_of_care.occurred", 1, 0]}
            }
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
    """Get surgeon-specific performance metrics"""
    collection = await get_surgeries_collection()
    
    pipeline = [
        {"$group": {
            "_id": "$team.primary_surgeon",
            "total_surgeries": {"$sum": 1},
            "surgeries_with_complications": {
                "$sum": {
                    "$cond": [
                        {"$gt": [{"$size": {"$ifNull": ["$postoperative_events.complications", []]}}, 0]},
                        1,
                        0
                    ]
                }
            },
            "return_to_theatre_count": {
                "$sum": {"$cond": ["$postoperative_events.return_to_theatre.occurred", 1, 0]}
            },
            "icu_admissions": {
                "$sum": {"$cond": ["$postoperative_events.escalation_of_care.occurred", 1, 0]}
            },
            "readmissions": {
                "$sum": {"$cond": ["$outcomes.readmission_30day", 1, 0]}
            },
            "mortality_30day": {
                "$sum": {"$cond": ["$outcomes.mortality_30day", 1, 0]}
            },
            "avg_duration": {"$avg": "$perioperative_timeline.operation_duration_minutes"},
            "avg_los": {"$avg": "$perioperative_timeline.length_of_stay_days"}
        }},
        {"$addFields": {
            "complication_rate": {
                "$multiply": [
                    {"$divide": ["$surgeries_with_complications", "$total_surgeries"]},
                    100
                ]
            },
            "readmission_rate": {
                "$multiply": [
                    {"$divide": ["$readmissions", "$total_surgeries"]},
                    100
                ]
            },
            "mortality_rate": {
                "$multiply": [
                    {"$divide": ["$mortality_30day", "$total_surgeries"]},
                    100
                ]
            }
        }},
        {"$sort": {"total_surgeries": -1}}
    ]
    
    surgeon_stats = await collection.aggregate(pipeline).to_list(length=100)
    
    # Round numeric values
    for stat in surgeon_stats:
        stat["complication_rate"] = round(stat["complication_rate"], 2)
        stat["readmission_rate"] = round(stat["readmission_rate"], 2)
        stat["mortality_rate"] = round(stat["mortality_rate"], 2)
        if stat["avg_duration"]:
            stat["avg_duration"] = round(stat["avg_duration"], 2)
        if stat["avg_los"]:
            stat["avg_los"] = round(stat["avg_los"], 2)
    
    return {
        "surgeon_performance": surgeon_stats,
        "generated_at": datetime.utcnow().isoformat()
    }
