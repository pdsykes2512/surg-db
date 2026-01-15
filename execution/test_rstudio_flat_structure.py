#!/usr/bin/env python3
"""
Test that RStudio API endpoints return flat data structures
- Nested objects/arrays should be JSON strings
- No nested dicts or lists in the response
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def get_test_token():
    """Get JWT token for testing"""
    data = {
        "username": "admin@example.com",
        "password": "admin123"
    }
    response = requests.post(f"{BASE_URL}/api/auth/login", data=data)
    if response.status_code != 200:
        print(f"❌ Authentication failed: {response.json().get('detail', 'Unknown error')}")
        sys.exit(1)
    return response.json()["access_token"]

def check_flat_structure(data, path="root"):
    """Recursively check if data structure is flat (only primitives and JSON strings)"""
    issues = []

    if isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, dict):
                # Check each field in the dict
                for key, value in item.items():
                    if isinstance(value, (dict, list)):
                        # This should be a JSON string, not a nested structure
                        issues.append(f"{path}[{i}].{key} is a {type(value).__name__}, not a string")
    elif isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                issues.append(f"{path}.{key} is a {type(value).__name__}, not a string")

    return issues

def test_endpoint(endpoint_name, endpoint_path, token):
    """Test an endpoint for flat structure"""
    print(f"\nTesting {endpoint_name}...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}{endpoint_path}", headers=headers, params={"limit": 5})

    if response.status_code != 200:
        print(f"  ❌ Request failed: {response.json().get('detail', 'Unknown error')}")
        return False

    data = response.json()

    if not data:
        print(f"  ⚠ No data returned (empty database?)")
        return True

    # Check structure is flat
    issues = check_flat_structure(data, endpoint_name)

    if issues:
        print(f"  ❌ Found nested structures (should be JSON strings):")
        for issue in issues:
            print(f"     - {issue}")

        # Show example of what we got
        if isinstance(data, list) and len(data) > 0:
            print(f"\n  Example record (first item):")
            first_item = data[0]
            for key, value in first_item.items():
                value_type = type(value).__name__
                if isinstance(value, (dict, list)):
                    print(f"    {key}: {value_type} (SHOULD BE STRING)")
                else:
                    # Show first 100 chars
                    value_preview = str(value)[:100]
                    print(f"    {key}: {value_type} = {value_preview}")
        return False
    else:
        print(f"  ✅ All fields are flat (primitives or JSON strings)")

        # Show what we got
        if isinstance(data, list) and len(data) > 0:
            first_item = data[0]
            # Count string fields that look like JSON
            json_string_fields = []
            for key, value in first_item.items():
                if isinstance(value, str) and value.startswith(('[', '{')):
                    json_string_fields.append(key)

            if json_string_fields:
                print(f"  ℹ Found {len(json_string_fields)} JSON string field(s): {', '.join(json_string_fields)}")

        return True

def main():
    print("=" * 80)
    print("Testing RStudio API - Flat Structure Verification")
    print("=" * 80)

    # Get token
    print("\n1. Getting JWT token...")
    try:
        token = get_test_token()
        print("   ✅ Authentication successful")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        sys.exit(1)

    # Test all endpoints
    results = []
    results.append(test_endpoint("patients", "/api/rstudio/data/patients", token))
    results.append(test_endpoint("episodes", "/api/rstudio/data/episodes", token))
    results.append(test_endpoint("treatments", "/api/rstudio/data/treatments", token))
    results.append(test_endpoint("tumours", "/api/rstudio/data/tumours", token))

    print("\n" + "=" * 80)
    if all(results):
        print("✅ ALL TESTS PASSED - All data is properly flattened")
    else:
        print("❌ SOME TESTS FAILED - Nested structures still present")
    print("=" * 80)

if __name__ == "__main__":
    main()
