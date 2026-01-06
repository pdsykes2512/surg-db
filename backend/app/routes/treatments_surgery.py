"""
Surgery treatment endpoints with relationship management
Handles surgery_primary, surgery_rtt, and surgery_reversal creation, deletion, and linking
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pymongo import MongoClient
from typing import List, Dict, Any
from datetime import datetime
import os
from dotenv import load_dotenv

from ..models.treatment import SurgeryTreatment, TreatmentType, RelatedSurgery
from ..models.surgery import ReturnToTheatre


# Load environment
load_dotenv('/etc/impact/secrets.env')
MONGODB_URI = os.getenv('MONGODB_URI')
client = MongoClient(MONGODB_URI)
db = client['impact']

router = APIRouter(prefix="/api/treatments", tags=["treatments-surgery"])


# Helper functions

def validate_surgery_relationships(surgery_data: Dict[str, Any]) -> None:
    """
    Validate surgery relationship rules
    Raises HTTPException if validation fails
    """
    treatment_type = surgery_data.get('treatment_type')
    parent_surgery_id = surgery_data.get('parent_surgery_id')
    rtt_reason = surgery_data.get('rtt_reason')

    # Rule: surgery_rtt MUST have parent_surgery_id and rtt_reason
    if treatment_type == 'surgery_rtt':
        if not parent_surgery_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="surgery_rtt requires parent_surgery_id"
            )
        if not rtt_reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="surgery_rtt requires rtt_reason"
            )

    # Rule: surgery_reversal MUST have parent_surgery_id
    if treatment_type == 'surgery_reversal':
        if not parent_surgery_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="surgery_reversal requires parent_surgery_id"
            )

    # Rule: surgery_primary MUST NOT have parent_surgery_id
    if treatment_type == 'surgery_primary':
        if parent_surgery_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="surgery_primary cannot have parent_surgery_id"
            )

    # If parent_surgery_id provided, validate parent exists and is surgery_primary
    if parent_surgery_id:
        parent = db.treatments.find_one({'treatment_id': parent_surgery_id})
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent surgery {parent_surgery_id} not found"
            )
        if parent.get('treatment_type') != 'surgery_primary':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parent surgery must be surgery_primary, got {parent.get('treatment_type')}"
            )

        # Auto-populate episode_id from parent
        surgery_data['parent_episode_id'] = parent.get('episode_id')
        surgery_data['episode_id'] = parent.get('episode_id')

        # For surgery_reversal, validate parent has stoma
        if treatment_type == 'surgery_reversal':
            if not parent.get('intraoperative', {}).get('stoma_created'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent surgery must have stoma_created=True for reversal"
                )


def update_parent_surgery_for_rtt(parent_id: str, rtt_surgery: Dict[str, Any]) -> None:
    """Update parent surgery when RTT surgery is created"""
    # Add to related_surgery_ids array
    db.treatments.update_one(
        {'treatment_id': parent_id},
        {
            '$push': {
                'related_surgery_ids': {
                    'treatment_id': rtt_surgery['treatment_id'],
                    'treatment_type': 'surgery_rtt',
                    'date_created': datetime.utcnow()
                }
            }
        }
    )

    # Update return_to_theatre flags (only if this is the first RTT)
    parent = db.treatments.find_one({'treatment_id': parent_id})
    if not parent.get('postoperative_events', {}).get('return_to_theatre', {}).get('occurred'):
        db.treatments.update_one(
            {'treatment_id': parent_id},
            {
                '$set': {
                    'postoperative_events.return_to_theatre.occurred': True,
                    'postoperative_events.return_to_theatre.date': rtt_surgery.get('treatment_date'),
                    'postoperative_events.return_to_theatre.reason': rtt_surgery.get('rtt_reason'),
                    'postoperative_events.return_to_theatre.procedure_performed': rtt_surgery.get('procedure', {}).get('primary_procedure'),
                    'postoperative_events.return_to_theatre.rtt_treatment_id': rtt_surgery['treatment_id']
                }
            }
        )


def update_parent_surgery_for_reversal(parent_id: str, reversal_surgery: Dict[str, Any]) -> None:
    """Update parent surgery when reversal surgery is created"""
    # Add to related_surgery_ids array
    db.treatments.update_one(
        {'treatment_id': parent_id},
        {
            '$push': {
                'related_surgery_ids': {
                    'treatment_id': reversal_surgery['treatment_id'],
                    'treatment_type': 'surgery_reversal',
                    'date_created': datetime.utcnow()
                }
            }
        }
    )

    # Update stoma closure date and reversal link
    db.treatments.update_one(
        {'treatment_id': parent_id},
        {
            '$set': {
                'intraoperative.stoma_closure_date': reversal_surgery.get('treatment_date'),
                'intraoperative.reversal_treatment_id': reversal_surgery['treatment_id']
            }
        }
    )


def reset_parent_surgery_flags(parent_id: str, deleted_type: str) -> None:
    """
    Reset parent surgery flags when RTT/reversal is deleted
    Only resets if no other related surgeries of that type exist
    """
    parent = db.treatments.find_one({'treatment_id': parent_id})
    if not parent:
        return

    related_surgeries = parent.get('related_surgery_ids', [])

    if deleted_type == 'surgery_rtt':
        # Check if any other RTT surgeries exist
        other_rtts = [r for r in related_surgeries if r.get('treatment_type') == 'surgery_rtt']
        if len(other_rtts) == 0:
            # Reset RTT flags
            db.treatments.update_one(
                {'treatment_id': parent_id},
                {
                    '$set': {
                        'postoperative_events.return_to_theatre.occurred': False,
                        'postoperative_events.return_to_theatre.date': None,
                        'postoperative_events.return_to_theatre.reason': None,
                        'postoperative_events.return_to_theatre.procedure_performed': None,
                        'postoperative_events.return_to_theatre.rtt_treatment_id': None
                    }
                }
            )

    elif deleted_type == 'surgery_reversal':
        # Check if any other reversal surgeries exist
        other_reversals = [r for r in related_surgeries if r.get('treatment_type') == 'surgery_reversal']
        if len(other_reversals) == 0:
            # Reset stoma closure fields
            db.treatments.update_one(
                {'treatment_id': parent_id},
                {
                    '$set': {
                        'intraoperative.stoma_closure_date': None,
                        'intraoperative.reversal_treatment_id': None
                    }
                }
            )


# Endpoints

@router.post("/surgery", status_code=status.HTTP_201_CREATED)
async def create_surgery(surgery: SurgeryTreatment):
    """
    Create a surgery treatment (primary, RTT, or reversal)

    Validation:
    - surgery_rtt: requires parent_surgery_id and rtt_reason
    - surgery_reversal: requires parent_surgery_id, parent must have stoma
    - surgery_primary: cannot have parent_surgery_id

    Auto-population:
    - RTT/reversal: episode_id copied from parent
    - RTT: Updates parent's return_to_theatre flags
    - Reversal: Updates parent's stoma_closure_date
    """
    # Convert to dict for validation and storage
    surgery_dict = surgery.model_dump(exclude_none=True)

    # Validate relationships
    validate_surgery_relationships(surgery_dict)

    # Check if treatment_id already exists
    existing = db.treatments.find_one({'treatment_id': surgery_dict['treatment_id']})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Treatment {surgery_dict['treatment_id']} already exists"
        )

    # Insert surgery
    result = db.treatments.insert_one(surgery_dict)

    # Update parent surgery if this is RTT or reversal
    parent_id = surgery_dict.get('parent_surgery_id')
    if parent_id:
        if surgery_dict['treatment_type'] == 'surgery_rtt':
            update_parent_surgery_for_rtt(parent_id, surgery_dict)
        elif surgery_dict['treatment_type'] == 'surgery_reversal':
            update_parent_surgery_for_reversal(parent_id, surgery_dict)

    # Fetch and return created surgery
    created = db.treatments.find_one({'_id': result.inserted_id})
    created['_id'] = str(created['_id'])

    return {
        "message": "Surgery created successfully",
        "treatment_id": surgery_dict['treatment_id'],
        "treatment_type": surgery_dict['treatment_type'],
        "data": created
    }


@router.delete("/{treatment_id}", status_code=status.HTTP_200_OK)
async def delete_surgery(treatment_id: str):
    """
    Delete a surgery treatment

    For surgery_rtt or surgery_reversal:
    - Removes from parent's related_surgery_ids
    - Resets parent's flags if no other related surgeries exist
    - Deletes the treatment

    For surgery_primary with related surgeries:
    - Returns error - user must delete related surgeries first
    """
    # Find the surgery
    surgery = db.treatments.find_one({'treatment_id': treatment_id})
    if not surgery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Treatment {treatment_id} not found"
        )

    treatment_type = surgery.get('treatment_type')

    # If surgery_primary with related surgeries, prevent deletion
    if treatment_type == 'surgery_primary':
        related = surgery.get('related_surgery_ids', [])
        if related:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete primary surgery with {len(related)} related surgeries. Delete related surgeries first."
            )

    # If RTT or reversal, unlink from parent
    parent_id = surgery.get('parent_surgery_id')
    if parent_id:
        # Remove from parent's related_surgery_ids
        db.treatments.update_one(
            {'treatment_id': parent_id},
            {
                '$pull': {
                    'related_surgery_ids': {'treatment_id': treatment_id}
                }
            }
        )

        # Reset parent flags if needed
        reset_parent_surgery_flags(parent_id, treatment_type)

    # Delete the surgery
    result = db.treatments.delete_one({'treatment_id': treatment_id})

    return {
        "message": "Surgery deleted successfully",
        "treatment_id": treatment_id,
        "deleted_count": result.deleted_count
    }


@router.get("/{treatment_id}/related-surgeries", status_code=status.HTTP_200_OK)
async def get_related_surgeries(treatment_id: str):
    """
    Get all RTT and reversal surgeries linked to a primary surgery

    Returns:
    - Array of related surgeries grouped by type
    """
    # Find the primary surgery
    surgery = db.treatments.find_one({'treatment_id': treatment_id})
    if not surgery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Treatment {treatment_id} not found"
        )

    if surgery.get('treatment_type') != 'surgery_primary':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only get related surgeries for surgery_primary"
        )

    # Get related surgery IDs
    related_ids = [r['treatment_id'] for r in surgery.get('related_surgery_ids', [])]

    if not related_ids:
        return {
            "treatment_id": treatment_id,
            "related_surgeries": [],
            "rtt_surgeries": [],
            "reversal_surgeries": []
        }

    # Fetch all related surgeries
    related_surgeries = list(db.treatments.find({'treatment_id': {'$in': related_ids}}))

    # Convert ObjectId to string
    for rs in related_surgeries:
        rs['_id'] = str(rs['_id'])

    # Group by type
    rtt_surgeries = [s for s in related_surgeries if s.get('treatment_type') == 'surgery_rtt']
    reversal_surgeries = [s for s in related_surgeries if s.get('treatment_type') == 'surgery_reversal']

    return {
        "treatment_id": treatment_id,
        "related_surgeries": related_surgeries,
        "rtt_surgeries": rtt_surgeries,
        "reversal_surgeries": reversal_surgeries,
        "total_count": len(related_surgeries)
    }
