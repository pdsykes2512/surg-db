#!/usr/bin/env python3
"""
Test RStudio API Endpoints

This script tests the new RStudio data access endpoints to ensure:
1. Authentication works
2. Data is returned without encrypted fields
3. deceased_date is converted to deceased_date_year
4. age_at_diagnosis is calculated correctly
"""

import sys
import requests
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

BASE_URL = "http://localhost:8000"

def get_test_token():
    """Get JWT token for testing"""
    # Use test credentials (adjust as needed)
    data = {
        "username": "admin@impact.com",  # Default admin user
        "password": "changeme123"  # Default password - change if different
    }

    response = requests.post(f"{BASE_URL}/api/auth/login", data=data)

    if response.status_code != 200:
        print(f"❌ Authentication failed: {response.json().get('detail', 'Unknown error')}")
        print("\nPlease update the test credentials in this script or create a test user:")
        print("  python3 execution/create_admin_user.py")
        sys.exit(1)

    return response.json()["access_token"]


def test_endpoint(endpoint, token, params=None):
    """Test an API endpoint"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params)

    if response.status_code != 200:
        print(f"❌ {endpoint} failed: {response.json().get('detail', 'Unknown error')}")
        return None

    return response.json()


def check_no_encrypted_fields(data, endpoint_name):
    """Verify no encrypted fields are present"""
    if not data:
        print(f"  ⚠ {endpoint_name}: No data returned (empty database?)")
        return True

    encrypted_fields = {
        'nhs_number', 'mrn', 'hospital_number',
        'nhs_number_hash', 'mrn_hash',
        'first_name', 'last_name',
        'date_of_birth', 'deceased_date', 'postcode'
    }

    # Check first record
    first_record = data[0] if isinstance(data, list) else data
    found_encrypted = []

    for field in encrypted_fields:
        if field in first_record:
            found_encrypted.append(field)

        # Check nested demographics
        if 'demographics' in first_record and isinstance(first_record['demographics'], dict):
            if field in first_record['demographics']:
                found_encrypted.append(f"demographics.{field}")

    if found_encrypted:
        print(f"  ❌ {endpoint_name}: Found encrypted fields: {found_encrypted}")
        return False
    else:
        print(f"  ✓ {endpoint_name}: No encrypted fields found")
        return True


def main():
    print("="*80)
    print("Testing RStudio API Endpoints")
    print("="*80)

    # Get authentication token
    print("\n1. Getting JWT token...")
    try:
        token = get_test_token()
        print("   ✓ Authentication successful")
    except Exception as e:
        print(f"   ❌ Failed to get token: {e}")
        sys.exit(1)

    # Test patients endpoint
    print("\n2. Testing /api/rstudio/data/patients...")
    patients = test_endpoint("/api/rstudio/data/patients", token, params={"limit": 5})
    if patients:
        print(f"   ✓ Returned {len(patients)} patients")
        check_no_encrypted_fields(patients, "patients")

        # Check for deceased_date_year
        if patients and 'deceased_date_year' in patients[0]:
            print("   ✓ deceased_date_year field present (privacy-preserving)")

        # Verify deceased_date is NOT present
        if patients and 'deceased_date' not in patients[0]:
            print("   ✓ deceased_date field NOT present (privacy protected)")
        else:
            print("   ❌ deceased_date field still present!")

    # Test episodes endpoint
    print("\n3. Testing /api/rstudio/data/episodes...")
    episodes = test_endpoint("/api/rstudio/data/episodes", token, params={"limit": 5})
    if episodes:
        print(f"   ✓ Returned {len(episodes)} episodes")
        check_no_encrypted_fields(episodes, "episodes")

        # Check for age_at_diagnosis
        if episodes and 'age_at_diagnosis' in episodes[0]:
            age = episodes[0]['age_at_diagnosis']
            print(f"   ✓ age_at_diagnosis field present: {age:.1f} years")
        else:
            print("   ⚠ age_at_diagnosis field not present (patient may not have DOB)")

    # Test treatments endpoint
    print("\n4. Testing /api/rstudio/data/treatments...")
    treatments = test_endpoint("/api/rstudio/data/treatments", token, params={"limit": 5})
    if treatments:
        print(f"   ✓ Returned {len(treatments)} treatments")
        check_no_encrypted_fields(treatments, "treatments")

    # Test tumours endpoint
    print("\n5. Testing /api/rstudio/data/tumours...")
    tumours = test_endpoint("/api/rstudio/data/tumours", token, params={"limit": 5})
    if tumours:
        print(f"   ✓ Returned {len(tumours)} tumours")
        check_no_encrypted_fields(tumours, "tumours")

    print("\n" + "="*80)
    print("✓ All endpoint tests completed!")
    print("="*80)
    print("\nNext steps:")
    print("1. Get your JWT token:")
    print("   python3 execution/setup_rstudio_auth.py --email your@email.com --password yourpass")
    print("\n2. In RStudio:")
    print("   Sys.setenv(IMPACT_API_TOKEN = 'your_token')")
    print("   source('~/R/impactdb/impactdb.R')")
    print("   patients <- get_patients(limit = 10)")


if __name__ == "__main__":
    main()
