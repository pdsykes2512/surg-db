"""
Utility to automatically update mortality_30day and mortality_90day flags
when a patient's deceased_date is modified.
"""

from datetime import datetime
from typing import Optional
from pymongo.database import Database

from .mortality import calculate_mortality_30d, calculate_mortality_90d


async def update_mortality_flags_for_patient(
    db: Database,
    patient_id: str,
    deceased_date: Optional[datetime]
) -> int:
    """
    Update mortality_30day and mortality_90day flags for all treatments
    of a patient when their deceased_date is updated.
    
    Args:
        db: MongoDB database instance
        patient_id: Patient ID
        deceased_date: New deceased date (or None if cleared)
    
    Returns:
        Number of treatments updated
    """
    treatments_collection = db.treatments
    
    # Get all surgical treatments for this patient (all surgery types)
    treatments = await treatments_collection.find({
        "patient_id": patient_id,
        "treatment_type": {"$in": ["surgery", "surgery_primary", "surgery_rtt", "surgery_reversal"]},
        "treatment_date": {"$exists": True, "$ne": None}
    }).to_list(length=None)
    
    if not treatments:
        return 0
    
    updated_count = 0
    
    for treatment in treatments:
        treatment_date = treatment.get('treatment_date')
        
        if not treatment_date:
            continue
        
        # Calculate mortality flags
        if deceased_date:
            mortality_30d = calculate_mortality_30d(treatment_date, deceased_date)
            mortality_90d = calculate_mortality_90d(treatment_date, deceased_date)
        else:
            # Deceased date was cleared - reset flags
            mortality_30d = False
            mortality_90d = False
        
        # Update treatment
        result = await treatments_collection.update_one(
            {"_id": treatment['_id']},
            {"$set": {
                "mortality_30day": mortality_30d,
                "mortality_90day": mortality_90d
            }}
        )
        
        if result.modified_count > 0:
            updated_count += 1
    
    return updated_count
