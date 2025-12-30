"""
NHS Provider lookup endpoints using ODS API via fetch_nhs_provider_codes.py
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict
import subprocess
import json
import sys
from pathlib import Path

router = APIRouter(prefix="/api", tags=["nhs-providers"])

# Path to the fetch script
SCRIPT_PATH = Path(__file__).parent.parent.parent.parent / "execution" / "active" / "fetch_nhs_provider_codes.py"


@router.get("/nhs-providers/search")
async def search_nhs_providers(
    query: str = Query(..., min_length=2, description="Search query for NHS provider name")
) -> List[Dict]:
    """
    Search for NHS providers by name using the ODS API.
    Returns a list of matching providers with their codes and names.
    """
    try:
        # Run the fetch script with search parameter and JSON output
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--search", query, "--json"],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Error searching NHS providers: {result.stderr}"
            )
        
        # Parse JSON output
        output = result.stdout.strip()
        if not output:
            return []
        
        try:
            providers = json.loads(output)
            return [{
                "code": provider.get("code", ""),
                "name": provider.get("name", ""),
                "type": provider.get("type", ""),
                "active": provider.get("active", True)
            } for provider in providers]
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid JSON response: {str(e)}"
            )
        
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="NHS provider search timed out"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching NHS providers: {str(e)}"
        )


@router.get("/nhs-providers/{code}")
async def get_nhs_provider(code: str) -> Dict:
    """
    Get details for a specific NHS provider code.
    Checks local cache first, then queries ODS API if needed.
    """
    try:
        # Run the fetch script with code parameter
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--code", code],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=404,
                detail=f"NHS provider code '{code}' not found"
            )
        
        # Parse JSON output
        output = result.stdout.strip()
        if not output:
            raise HTTPException(
                status_code=404,
                detail=f"NHS provider code '{code}' not found"
            )
        
        provider = json.loads(output)
        return {
            "code": provider.get("code", ""),
            "name": provider.get("name", ""),
            "type": provider.get("type", ""),
            "active": provider.get("active", True)
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="NHS provider lookup timed out"
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Invalid response from NHS provider service"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching NHS provider: {str(e)}"
        )
