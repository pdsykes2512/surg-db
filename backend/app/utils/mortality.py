"""Mortality calculation utilities"""
from datetime import datetime, date
from typing import Optional, Union


def calculate_days_to_death(
    treatment_date: Union[str, datetime, date],
    deceased_date: Union[str, datetime, date]
) -> Optional[int]:
    """Calculate days between treatment and death.
    
    Args:
        treatment_date: Date of treatment
        deceased_date: Date of death
        
    Returns:
        Number of days between treatment and death, or None if either date is missing
    """
    if not treatment_date or not deceased_date:
        return None
    
    # Convert to datetime if string
    if isinstance(treatment_date, str):
        treatment_date = datetime.fromisoformat(treatment_date.replace('Z', '+00:00'))
    if isinstance(deceased_date, str):
        deceased_date = datetime.fromisoformat(deceased_date.replace('Z', '+00:00'))
    
    # Convert date to datetime
    if isinstance(treatment_date, date) and not isinstance(treatment_date, datetime):
        treatment_date = datetime.combine(treatment_date, datetime.min.time())
    if isinstance(deceased_date, date) and not isinstance(deceased_date, datetime):
        deceased_date = datetime.combine(deceased_date, datetime.min.time())
    
    delta = deceased_date - treatment_date
    return delta.days


def calculate_mortality_30d(
    treatment_date: Union[str, datetime, date],
    deceased_date: Union[str, datetime, date]
) -> Optional[bool]:
    """Check if death occurred within 30 days of treatment.
    
    Args:
        treatment_date: Date of treatment
        deceased_date: Date of death
        
    Returns:
        True if death within 30 days, False if alive at 30 days, None if no death recorded
    """
    days = calculate_days_to_death(treatment_date, deceased_date)
    if days is None:
        return None
    return 0 <= days <= 30


def calculate_mortality_90d(
    treatment_date: Union[str, datetime, date],
    deceased_date: Union[str, datetime, date]
) -> Optional[bool]:
    """Check if death occurred within 90 days of treatment.
    
    Args:
        treatment_date: Date of treatment
        deceased_date: Date of death
        
    Returns:
        True if death within 90 days, False if alive at 90 days, None if no death recorded
    """
    days = calculate_days_to_death(treatment_date, deceased_date)
    if days is None:
        return None
    return 0 <= days <= 90


def calculate_mortality_1year(
    treatment_date: Union[str, datetime, date],
    deceased_date: Union[str, datetime, date]
) -> Optional[bool]:
    """Check if death occurred within 1 year of treatment.
    
    Args:
        treatment_date: Date of treatment
        deceased_date: Date of death
        
    Returns:
        True if death within 1 year, False if alive at 1 year, None if no death recorded
    """
    days = calculate_days_to_death(treatment_date, deceased_date)
    if days is None:
        return None
    return 0 <= days <= 365


def enrich_treatment_with_mortality(
    treatment: dict,
    deceased_date: Union[str, datetime, date, None]
) -> dict:
    """Enrich treatment data with computed mortality fields.
    
    Args:
        treatment: Treatment dictionary
        deceased_date: Patient's deceased date
        
    Returns:
        Treatment dict with added mortality_30d, mortality_90d, mortality_1year fields
    """
    treatment_date = treatment.get('treatment_date')
    
    if not treatment_date or not deceased_date:
        treatment['mortality_30d'] = None
        treatment['mortality_90d'] = None
        treatment['mortality_1year'] = None
        treatment['days_to_death'] = None
    else:
        days = calculate_days_to_death(treatment_date, deceased_date)
        treatment['days_to_death'] = days
        treatment['mortality_30d'] = calculate_mortality_30d(treatment_date, deceased_date)
        treatment['mortality_90d'] = calculate_mortality_90d(treatment_date, deceased_date)
        treatment['mortality_1year'] = calculate_mortality_1year(treatment_date, deceased_date)
    
    return treatment
