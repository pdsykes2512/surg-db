"""
Audit log routes for tracking and viewing user activity
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from datetime import datetime, timedelta
from ..database import get_audit_logs_collection
from ..models.audit_log import AuditLogEntry
from ..utils.audit import format_activity_message
from ..auth import get_current_user

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/recent")
async def get_recent_activity(
    limit: int = 20,
    user_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """
    Get recent activity log entries
    
    Args:
        limit: Maximum number of entries to return (default 20)
        user_id: Filter by specific user (if not provided, returns current user's activity)
        entity_type: Filter by entity type (patient, episode, treatment, etc.)
        days: Number of days to look back (default 30)
        current_user: Current authenticated user
    
    Returns:
        List of recent activity entries with formatted messages
    """
    collection = await get_audit_logs_collection()
    
    # Build query
    query = {}
    
    # Filter by user (default to current user)
    if user_id:
        # Only admins can view other users' activity
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can view other users' activity"
            )
        query["user_id"] = user_id
    else:
        query["user_id"] = current_user["user_id"]
    
    # Filter by entity type
    if entity_type:
        query["entity_type"] = entity_type
    
    # Filter by date range
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    query["timestamp"] = {"$gte": cutoff_date}
    
    # Fetch logs
    cursor = collection.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit)
    logs = await cursor.to_list(length=limit)
    
    # Format each log entry with a human-readable message
    for log in logs:
        log["message"] = format_activity_message(log)
        # Format timestamp for frontend
        if isinstance(log["timestamp"], datetime):
            log["timestamp"] = log["timestamp"].isoformat()
    
    return logs


@router.get("/user/{user_id}")
async def get_user_activity(
    user_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """
    Get activity history for a specific user
    
    Args:
        user_id: User ID to fetch activity for
        limit: Maximum number of entries to return
        current_user: Current authenticated user
        
    Returns:
        List of activity entries for the specified user
    """
    # Only admins or the user themselves can view activity
    if current_user.get("role") != "admin" and current_user["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own activity"
        )
    
    collection = await get_audit_logs_collection()
    
    cursor = collection.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit)
    
    logs = await cursor.to_list(length=limit)
    
    # Format logs
    for log in logs:
        log["message"] = format_activity_message(log)
        if isinstance(log["timestamp"], datetime):
            log["timestamp"] = log["timestamp"].isoformat()
    
    return logs


@router.get("/entity/{entity_type}/{entity_id}")
async def get_entity_history(
    entity_type: str,
    entity_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get audit history for a specific entity
    
    Args:
        entity_type: Type of entity (patient, episode, etc.)
        entity_id: ID of the entity
        current_user: Current authenticated user
        
    Returns:
        List of all actions performed on the specified entity
    """
    collection = await get_audit_logs_collection()
    
    cursor = collection.find(
        {
            "entity_type": entity_type,
            "entity_id": entity_id
        },
        {"_id": 0}
    ).sort("timestamp", -1)
    
    logs = await cursor.to_list(length=None)
    
    # Format logs
    for log in logs:
        log["message"] = format_activity_message(log)
        if isinstance(log["timestamp"], datetime):
            log["timestamp"] = log["timestamp"].isoformat()
    
    return logs


@router.get("/stats")
async def get_activity_stats(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """
    Get activity statistics
    
    Args:
        days: Number of days to analyze
        current_user: Current authenticated user
        
    Returns:
        Activity statistics by action type and entity type
    """
    # Only admins can view system-wide stats
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view activity statistics"
        )
    
    collection = await get_audit_logs_collection()
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Aggregate by action type
    action_pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff_date}}},
        {"$group": {"_id": "$action", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    action_stats = await collection.aggregate(action_pipeline).to_list(length=None)
    
    # Aggregate by entity type
    entity_pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff_date}}},
        {"$group": {"_id": "$entity_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    entity_stats = await collection.aggregate(entity_pipeline).to_list(length=None)
    
    # Top users
    user_pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff_date}}},
        {"$group": {"_id": "$username", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    
    user_stats = await collection.aggregate(user_pipeline).to_list(length=None)
    
    return {
        "period_days": days,
        "by_action": [{"action": s["_id"], "count": s["count"]} for s in action_stats],
        "by_entity": [{"entity_type": s["_id"], "count": s["count"]} for s in entity_stats],
        "top_users": [{"username": s["_id"], "count": s["count"]} for s in user_stats]
    }
