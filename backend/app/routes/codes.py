"""
Code validation API routes for ICD-10 and OPCS-4
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict

from ..services.icd10_validator import ICD10Validator
from ..services.opcs4_validator import OPCS4Validator


router = APIRouter(prefix="/api/codes", tags=["codes"])


# ============== ICD-10 Endpoints ==============

@router.get("/icd10/validate/{code}")
async def validate_icd10_code(code: str):
    """Validate an ICD-10 code"""
    is_valid, error_msg = ICD10Validator.validate(code)
    
    if is_valid:
        return {
            "valid": True,
            "code": code.upper(),
            "description": ICD10Validator.lookup(code),
            "is_rectal": ICD10Validator.is_rectal_cancer(code),
            "is_colon": ICD10Validator.is_colon_cancer(code)
        }
    else:
        return {
            "valid": False,
            "code": code.upper(),
            "error": error_msg
        }


@router.get("/icd10/lookup/{code}")
async def lookup_icd10_code(code: str):
    """Look up an ICD-10 code description"""
    description = ICD10Validator.lookup(code)
    
    if description:
        return {
            "code": code.upper(),
            "description": description,
            "is_rectal": ICD10Validator.is_rectal_cancer(code),
            "is_colon": ICD10Validator.is_colon_cancer(code)
        }
    else:
        raise HTTPException(status_code=404, detail=f"ICD-10 code {code} not found")


@router.get("/icd10/search")
async def search_icd10_codes(q: str = Query(..., min_length=2, description="Search query")):
    """Search for ICD-10 codes by keyword"""
    results = ICD10Validator.search(q)
    return {
        "query": q,
        "count": len(results),
        "results": results
    }


@router.get("/icd10/site/{site}")
async def get_icd10_by_site(site: str):
    """Get all ICD-10 codes for a specific anatomical site"""
    codes = ICD10Validator.get_site_codes(site)
    
    if not codes:
        raise HTTPException(status_code=404, detail=f"Site '{site}' not found. Valid sites: colon, right_colon, left_colon, rectosigmoid, rectum, anus, colorectal")
    
    return {
        "site": site,
        "codes": [
            {
                "code": code,
                "description": ICD10Validator.lookup(code)
            }
            for code in codes
        ]
    }


@router.get("/icd10/all")
async def get_all_icd10_codes():
    """Get all valid ICD-10 codes"""
    return {
        "count": len(ICD10Validator.VALID_CODES),
        "codes": ICD10Validator.get_all_codes()
    }


@router.get("/icd10/primary")
async def get_primary_icd10_codes():
    """Get only primary colorectal cancer ICD-10 codes (excludes metastases and benign)"""
    codes = ICD10Validator.get_primary_cancer_codes()
    return {
        "count": len(codes),
        "codes": codes
    }


# ============== OPCS-4 Endpoints ==============

@router.get("/opcs4/validate/{code}")
async def validate_opcs4_code(code: str):
    """Validate an OPCS-4 code"""
    is_valid, error_msg = OPCS4Validator.validate(code)
    
    if is_valid:
        return {
            "valid": True,
            "code": code.upper(),
            "description": OPCS4Validator.lookup(code),
            "is_major_resection": OPCS4Validator.is_major_resection(code),
            "is_laparoscopic": OPCS4Validator.is_laparoscopic(code),
            "is_robotic": OPCS4Validator.is_robotic(code)
        }
    else:
        return {
            "valid": False,
            "code": code.upper(),
            "error": error_msg
        }


@router.get("/opcs4/lookup/{code}")
async def lookup_opcs4_code(code: str):
    """Look up an OPCS-4 code description"""
    description = OPCS4Validator.lookup(code)
    
    if description:
        return {
            "code": code.upper(),
            "description": description,
            "is_major_resection": OPCS4Validator.is_major_resection(code),
            "is_laparoscopic": OPCS4Validator.is_laparoscopic(code),
            "is_robotic": OPCS4Validator.is_robotic(code)
        }
    else:
        raise HTTPException(status_code=404, detail=f"OPCS-4 code {code} not found")


@router.get("/opcs4/search")
async def search_opcs4_codes(q: str = Query(..., min_length=2, description="Search query")):
    """Search for OPCS-4 codes by keyword"""
    results = OPCS4Validator.search(q)
    return {
        "query": q,
        "count": len(results),
        "results": results
    }


@router.get("/opcs4/procedure/{procedure_type}")
async def get_opcs4_by_procedure(procedure_type: str):
    """Get all OPCS-4 codes for a specific procedure type"""
    codes = OPCS4Validator.get_procedure_codes(procedure_type)
    
    if not codes:
        valid_types = ", ".join(OPCS4Validator.PROCEDURE_GROUPS.keys())
        raise HTTPException(status_code=404, detail=f"Procedure type '{procedure_type}' not found. Valid types: {valid_types}")
    
    return {
        "procedure_type": procedure_type,
        "codes": [
            {
                "code": code,
                "description": OPCS4Validator.lookup(code)
            }
            for code in codes
        ]
    }


@router.get("/opcs4/all")
async def get_all_opcs4_codes():
    """Get all valid OPCS-4 codes"""
    return {
        "count": len(OPCS4Validator.VALID_CODES),
        "codes": OPCS4Validator.get_all_codes()
    }


@router.get("/opcs4/resections")
async def get_resection_opcs4_codes():
    """Get only major resection OPCS-4 codes (H04-H10)"""
    codes = OPCS4Validator.get_resection_codes()
    return {
        "count": len(codes),
        "codes": codes
    }
