#!/usr/bin/env python3
"""
Setup RStudio Authentication

This script helps RStudio users authenticate and get their JWT token
for accessing the IMPACT API from R.

Usage:
    python3 execution/setup_rstudio_auth.py --email user@example.com --password yourpassword

Output:
    Prints the JWT token and R code to set it in the environment
"""

import argparse
import sys
import os
import requests
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

def get_jwt_token(email: str, password: str, base_url: str = "http://localhost:8000") -> dict:
    """
    Authenticate with the IMPACT API and get JWT tokens

    Args:
        email: User email address
        password: User password
        base_url: API base URL

    Returns:
        dict: Response containing access_token and refresh_token
    """
    url = f"{base_url}/api/auth/login"

    # OAuth2PasswordRequestForm uses form data, not JSON
    data = {
        "username": email,  # OAuth2 calls it username but we use email
        "password": password
    }

    response = requests.post(url, data=data)

    if response.status_code != 200:
        error_detail = response.json().get("detail", "Unknown error")
        raise Exception(f"Authentication failed: {error_detail}")

    return response.json()


def main():
    parser = argparse.ArgumentParser(
        description="Get JWT token for RStudio authentication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Get token for a user
    python3 execution/setup_rstudio_auth.py --email researcher@example.com --password mypassword

    # Use custom API URL
    python3 execution/setup_rstudio_auth.py --email user@example.com --password pass --url https://api.example.com
        """
    )

    parser.add_argument("--email", required=True, help="User email address")
    parser.add_argument("--password", required=True, help="User password")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL (default: http://localhost:8000)")
    parser.add_argument("--renviron", action="store_true", help="Automatically update ~/.Renviron file")

    args = parser.parse_args()

    try:
        print(f"Authenticating {args.email}...")
        result = get_jwt_token(args.email, args.password, args.url)

        access_token = result["access_token"]
        user_info = result["user"]

        print("\n✓ Authentication successful!")
        print(f"  User: {user_info['full_name']} ({user_info['email']})")
        print(f"  Role: {user_info['role']}")
        print(f"  Token expires in: {result['expires_in']} seconds")

        print("\n" + "="*80)
        print("JWT ACCESS TOKEN")
        print("="*80)
        print(access_token)
        print("="*80)

        print("\n" + "="*80)
        print("R CODE TO SET TOKEN")
        print("="*80)
        print(f"""
# Copy and paste this into your RStudio console:
Sys.setenv(IMPACT_API_TOKEN = "{access_token}")
Sys.setenv(IMPACT_API_URL = "{args.url}")

# Verify it worked:
Sys.getenv("IMPACT_API_TOKEN")

# Load the IMPACT library and test:
source("~/R/impactdb/impactdb.R")
patients <- get_patients(limit = 5)
print(patients)
        """)
        print("="*80)

        # Optionally update .Renviron
        if args.renviron:
            renviron_path = Path.home() / ".Renviron"

            # Read existing .Renviron
            existing_lines = []
            if renviron_path.exists():
                with open(renviron_path, 'r') as f:
                    existing_lines = f.readlines()

            # Remove old IMPACT_API_TOKEN and IMPACT_API_URL lines
            filtered_lines = [
                line for line in existing_lines
                if not line.startswith("IMPACT_API_TOKEN=")
                and not line.startswith("IMPACT_API_URL=")
            ]

            # Add new tokens
            filtered_lines.append(f"IMPACT_API_TOKEN={access_token}\n")
            filtered_lines.append(f"IMPACT_API_URL={args.url}\n")

            # Write back
            with open(renviron_path, 'w') as f:
                f.writelines(filtered_lines)

            print(f"\n✓ Updated {renviron_path}")
            print("  Restart your R session for changes to take effect")

        print("\n" + "="*80)
        print("SECURITY NOTE")
        print("="*80)
        print("""
⚠ Keep your JWT token secure!
- Don't share it with others
- Don't commit it to version control
- Don't paste it in public channels
- Token expires after some time - re-run this script to get a new one
        """)

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
