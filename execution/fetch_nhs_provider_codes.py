#!/usr/bin/env python3
"""
Fetch NHS Provider (Trust) Codes from the Organisation Data Service (ODS) FHIR API.

This script queries the official NHS ODS FHIR API to retrieve accurate organization codes
for NHS trusts and other providers. The API is open-access and requires no authentication.

Features:
- Checks local cache first to minimize API calls
- Auto-saves validated codes to local cache
- Supports partial name matching in searches

Usage:
    python3 execution/fetch_nhs_provider_codes.py [--search QUERY] [--code CODE] [--output FILE]

Examples:
    # Search for Portsmouth trust (partial match)
    python3 execution/fetch_nhs_provider_codes.py --search "Portsmouth"
    
    # Get details for a specific code (checks cache first)
    python3 execution/fetch_nhs_provider_codes.py --code RHU
    
    # Export all NHS trusts to JSON
    python3 execution/fetch_nhs_provider_codes.py --output provider_codes.json

API Documentation: https://digital.nhs.uk/developer/api-catalogue/organisation-data-service-fhir
"""

import requests
import json
import argparse
from typing import Dict, List, Optional
import sys
import os
from pathlib import Path
from datetime import datetime

# ODS FHIR API base URL
ODS_BASE_URL = "https://directory.spineservices.nhs.uk/STU3"

# Local cache file
SCRIPT_DIR = Path(__file__).parent
CACHE_FILE = SCRIPT_DIR / "nhs_provider_codes_reference.json"

# Role codes for NHS Trusts (RO codes from ODS)
NHS_TRUST_ROLES = [
    "RO197",  # NHS Trust
    "RO198",  # NHS Trust Site
]

def load_cache() -> Dict:
    """Load the local provider codes cache."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load cache: {e}", file=sys.stderr)
            return {"providers": {}}
    return {"providers": {}}


def save_to_cache(code: str, org_info: Dict) -> None:
    """Save a validated provider code to the local cache."""
    cache = load_cache()
    
    # Ensure structure
    if "providers" not in cache:
        cache["providers"] = {}
    
    # Add metadata if not present
    if "reference_note" not in cache:
        cache["reference_note"] = "NHS Provider (Trust) Codes verified from ODS API - https://directory.spineservices.nhs.uk/STU3/"
    
    cache["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Add or update provider - store name in lowercase
    cache["providers"][code] = {
        "name": org_info["name"].lower(),
        "type": org_info.get("type", "").lower() if org_info.get("type") else "",
        "verified": True,
        "last_verified": datetime.now().strftime("%Y-%m-%d")
    }
    
    # Save to file
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
        print(f"✓ Saved {code} to local cache", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Could not save to cache: {e}", file=sys.stderr)


def search_cache(query: str) -> List[Dict]:
    """Search the local cache for matching providers."""
    cache = load_cache()
    results = []
    
    query_lower = query.lower()
    for code, info in cache.get("providers", {}).items():
        if query_lower in info.get("name", "").lower():
            results.append({
                "code": code,
                "name": info["name"],
                "type": info.get("type", ""),
                "active": True,
                "source": "cache"
            })
    
    return results


def get_organization_by_code(code: str, use_cache: bool = True) -> Optional[Dict]:
    """
    Fetch organization details by ODS code.
    
    Args:
        code: ODS organization code (e.g., 'RHU')
        use_cache: Check local cache first
        
    Returns:
        Dictionary with organization details or None if not found
    """
    # Check cache first
    if use_cache:
        cache = load_cache()
        if code in cache.get("providers", {}):
            cached = cache["providers"][code]
            print(f"ℹ Found {code} in local cache", file=sys.stderr)
            return {
                "code": code,
                "name": cached["name"],
                "type": cached.get("type", ""),
                "active": True,
                "source": "cache"
            }
    
    # Query API
    url = f"{ODS_BASE_URL}/Organization/{code}"
    
    try:
        print(f"ℹ Querying ODS API for {code}...", file=sys.stderr)
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract type/role information from extensions
        org_type = ""
        extensions = data.get("extension", [])
        for ext in extensions:
            if ext.get("url", "").endswith("OrganizationRole-1"):
                for sub_ext in ext.get("extension", []):
                    if sub_ext.get("url") == "role":
                        coding = sub_ext.get("valueCoding", {})
                        org_type = coding.get("display", "")
                        break
                if org_type:
                    break
        
        # Extract relevant information
        org_info = {
            "code": code,
            "name": data.get("name", ""),
            "active": data.get("active", True),  # Default to True if not specified
            "type": org_type,
            "source": "api"
        }
        
        # Extract address
        address = data.get("address", {})
        if address:
            org_info["address"] = {
                "line": address.get("line", []),
                "city": address.get("city", ""),
                "postalCode": address.get("postalCode", ""),
            }
        
        # Save to cache
        save_to_cache(code, org_info)
        
        return org_info
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"Organization code '{code}' not found", file=sys.stderr)
            return None
        else:
            print(f"HTTP error fetching {code}: {e}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Error fetching {code}: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None


def search_organizations(query: str, active_only: bool = True, use_cache: bool = True) -> List[Dict]:
    """
    Search for organizations by name (partial match supported).
    
    Args:
        query: Search query string (supports partial matching)
        active_only: Only return active organizations
        use_cache: Check local cache first
        
    Returns:
        List of matching organizations
    """
    results = []
    
    # Check cache first
    if use_cache:
        cache_results = search_cache(query)
        if cache_results:
            print(f"ℹ Found {len(cache_results)} matches in local cache", file=sys.stderr)
            results.extend(cache_results)
    
    # Also query API with partial name matching
    # The API supports wildcard searches with *
    url = f"{ODS_BASE_URL}/Organization"
    
    # Try multiple search strategies for better partial matching
    search_queries = [
        query,  # Exact query
        f"{query}*",  # Prefix match
        f"*{query}*",  # Contains match
    ]
    
    api_codes_seen = set()
    
    for search_query in search_queries:
        params = {
            "name": search_query,
            "_count": 50,
        }
        
        if active_only:
            params["active"] = "true"
        
        try:
            print(f"ℹ Querying ODS API with: {search_query}", file=sys.stderr)
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse FHIR Bundle response
            entries = data.get("entry", [])
            for entry in entries:
                resource = entry.get("resource", {})
                code = resource.get("id", "")
                
                # Skip if already seen
                if code in api_codes_seen:
                    continue
                api_codes_seen.add(code)
                
                # Extract type from extensions
                org_type = ""
                extensions = resource.get("extension", [])
                for ext in extensions:
                    if ext.get("url", "").endswith("OrganizationRole-1"):
                        for sub_ext in ext.get("extension", []):
                            if sub_ext.get("url") == "role":
                                coding = sub_ext.get("valueCoding", {})
                                org_type = coding.get("display", "")
                                break
                        if org_type:
                            break
                
                org_info = {
                    "code": code,
                    "name": resource.get("name", ""),
                    "active": resource.get("active", True),
                    "type": org_type,
                    "source": "api"
                }
                
                # Auto-save to cache
                save_to_cache(code, org_info)
                
                results.append(org_info)
            
            # If we found results, don't try other search patterns
            if entries:
                break
                
        except Exception as e:
            print(f"Error searching with '{search_query}': {e}", file=sys.stderr)
            continue
    
    return results


def get_all_nhs_trusts(limit: int = 500) -> List[Dict]:
    """
    Fetch all NHS trusts.
    
    Args:
        limit: Maximum number of results to fetch
        
    Returns:
        List of NHS trust organizations
    """
    url = f"{ODS_BASE_URL}/Organization"
    
    # Search for active NHS organizations
    # Note: The FHIR API doesn't have a direct role filter, so we search broadly
    # and filter by type
    params = {
        "active": "true",
        "_count": limit,
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        entries = data.get("entry", [])
        print(f"Fetched {len(entries)} organizations from ODS API")
        
        for entry in entries:
            resource = entry.get("resource", {})
            
            # Filter for NHS trusts based on type
            org_type = resource.get("type", [{}])[0].get("coding", [{}])[0].get("display", "")
            
            # Include NHS trusts and foundation trusts
            if any(keyword in org_type.lower() for keyword in ["trust", "nhs"]):
                org_info = {
                    "code": resource.get("id", ""),
                    "name": resource.get("name", ""),
                    "active": resource.get("active", False),
                    "type": org_type,
                }
                
                results.append(org_info)
        
        return results
        
    except Exception as e:
        print(f"Error fetching NHS trusts: {e}", file=sys.stderr)
        return []


def verify_provider_code(code: str, expected_name: str = None) -> bool:
    """
    Verify a provider code and optionally check if the name matches.
    
    Args:
        code: ODS code to verify
        expected_name: Expected organization name (optional)
        
    Returns:
        True if code is valid (and name matches if provided)
    """
    org = get_organization_by_code(code)
    
    if not org:
        return False
    
    print(f"✓ Code: {org['code']}")
    print(f"  Name: {org['name']}")
    print(f"  Active: {org['active']}")
    print(f"  Type: {org.get('type', 'N/A')}")
    
    if expected_name:
        if expected_name.lower() in org['name'].lower():
            print(f"  ✓ Name matches expected: {expected_name}")
            return True
        else:
            print(f"  ✗ Name does not match expected: {expected_name}")
            return False
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Fetch NHS Provider codes from ODS FHIR API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--search",
        help="Search for organizations by name"
    )
    
    parser.add_argument(
        "--code",
        help="Get details for a specific ODS code"
    )
    
    parser.add_argument(
        "--verify",
        nargs=2,
        metavar=("CODE", "NAME"),
        help="Verify a code matches an expected name"
    )
    
    parser.add_argument(
        "--output",
        help="Output file for results (JSON format)"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON (for API integration)"
    )
    
    parser.add_argument(
        "--all-trusts",
        action="store_true",
        help="Fetch all NHS trusts"
    )
    
    args = parser.parse_args()
    
    results = []
    
    if args.code:
        # Get specific organization
        org = get_organization_by_code(args.code)
        if org:
            print(json.dumps(org, indent=2))
            results = [org]
        else:
            sys.exit(1)
    
    elif args.verify:
        # Verify code and name
        code, name = args.verify
        if not verify_provider_code(code, name):
            sys.exit(1)
        results = [get_organization_by_code(code)]
    
    elif args.search:
        # Search organizations
        orgs = search_organizations(args.search)
        
        if args.json:
            # Output as JSON for API integration
            print(json.dumps(orgs, indent=2))
        else:
            # Human-readable output
            print(f"\nFound {len(orgs)} organizations matching '{args.search}':\n")
            
            for org in orgs:
                print(f"Code: {org['code']}")
                print(f"Name: {org['name']}")
                print(f"Type: {org.get('type', 'N/A')}")
                print(f"Active: {org['active']}")
                print()
        
        results = orgs
    
    elif args.all_trusts:
        # Fetch all NHS trusts
        print("Fetching all NHS trusts from ODS API...")
        orgs = get_all_nhs_trusts()
        print(f"\nFound {len(orgs)} NHS trusts\n")
        
        for org in sorted(orgs, key=lambda x: x['name']):
            print(f"{org['code']}: {org['name']}")
        
        results = orgs
    
    else:
        parser.print_help()
        sys.exit(1)
    
    # Save to file if requested
    if args.output and results:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
