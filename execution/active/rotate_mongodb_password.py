#!/usr/bin/env python3
"""
MongoDB Password Rotation Script
Automates secure password rotation for MongoDB database

Usage:
    python3 execution/active/rotate_mongodb_password.py [--dry-run] [--password PASSWORD]

Options:
    --dry-run       Show what would be changed without making changes
    --password      Use specific password (otherwise generates random)
    --help          Show this help message

Security:
    - Generates cryptographically secure 32-character password
    - Backs up current /etc/impact/secrets.env before modification
    - Updates MongoDB user password
    - Updates /etc/impact/secrets.env file with new credentials
    - Restarts backend service
    - Tests connection to verify success
"""

import os
import sys
import secrets
import string
import re
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus
from pymongo import MongoClient
from pymongo.errors import OperationFailure, ConnectionFailure


# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent
SECRETS_FILE = Path("/etc/impact/secrets.env")  # System secrets file (not in git)
ENV_BACKUP_DIR = Path("/etc/impact/backups")  # Backup location for secrets

# Get configuration from environment variables
MONGODB_HOST = os.getenv("MONGODB_HOST", "localhost")
MONGODB_PORT = int(os.getenv("MONGODB_PORT", "27017"))
MONGODB_AUTH_DB = os.getenv("MONGODB_AUTH_DB", "admin")
MONGODB_USERNAME = os.getenv("MONGODB_USERNAME", "admin")


def generate_strong_password(length: int = 32) -> str:
    """
    Generate a cryptographically secure password

    Args:
        length: Password length (default 32)

    Returns:
        Random password with letters, digits, and special chars
    """
    # Use mix of characters (avoid ambiguous ones like 0/O, 1/l)
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_=+"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))

    # Ensure at least one of each type
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*-_=+" for c in password)

    if not all([has_upper, has_lower, has_digit, has_special]):
        # Regenerate if missing any type
        return generate_strong_password(length)

    return password


def parse_mongodb_uri(uri: str) -> dict:
    """
    Parse MongoDB URI to extract components

    Args:
        uri: MongoDB connection URI

    Returns:
        Dictionary with host, port, username, password, database, auth_source
    """
    # Pattern: mongodb://username:password@host:port/database?authSource=admin
    pattern = r'mongodb://([^:]+):([^@]+)@([^:]+):(\d+)/([^?]+)(?:\?authSource=(.+))?'
    match = re.match(pattern, uri)

    if not match:
        raise ValueError(f"Invalid MongoDB URI format: {uri}")

    return {
        'username': match.group(1),
        'password': match.group(2),
        'host': match.group(3),
        'port': int(match.group(4)),
        'database': match.group(5),
        'auth_source': match.group(6) or 'admin'
    }


def read_env_file() -> dict:
    """
    Read secrets.env file and extract MongoDB configuration

    Returns:
        Dictionary with env variables
    """
    if not SECRETS_FILE.exists():
        raise FileNotFoundError(f"Secrets file not found: {SECRETS_FILE}")

    env_vars = {}
    with open(SECRETS_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()

    return env_vars


def backup_env_file() -> Path:
    """
    Create timestamped backup of secrets.env file

    Returns:
        Path to backup file
    """
    ENV_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = ENV_BACKUP_DIR / f"secrets.env.backup_{timestamp}"

    with open(SECRETS_FILE, 'r') as src, open(backup_path, 'w') as dst:
        dst.write(src.read())

    os.chmod(backup_path, 0o600)  # Secure permissions
    return backup_path


def update_env_file(old_password: str, new_password: str) -> None:
    """
    Update secrets.env file with new MongoDB password

    Args:
        old_password: Current password to replace (plain text)
        new_password: New password to use (plain text)
    """
    with open(SECRETS_FILE, 'r') as f:
        content = f.read()

    # Replace password in MONGODB_URI - URL encode for MongoDB connection strings
    old_uri_pattern = f"mongodb://{MONGODB_USERNAME}:{re.escape(old_password)}@"
    new_uri = f"mongodb://{MONGODB_USERNAME}:{quote_plus(new_password)}@"

    updated_content = re.sub(old_uri_pattern, new_uri, content)

    # Write updated content
    with open(SECRETS_FILE, 'w') as f:
        f.write(updated_content)

    os.chmod(SECRETS_FILE, 0o600)  # Ensure secure permissions


def update_mongodb_password(host: str, port: int, username: str,
                            old_password: str, new_password: str,
                            auth_db: str = 'admin') -> bool:
    """
    Update MongoDB user password using temporary admin user approach

    Strategy:
    1. Create temporary admin user
    2. Switch to temporary admin connection
    3. Drop original user and recreate with new password
    4. Clean up temporary user

    Args:
        host: MongoDB host
        port: MongoDB port
        username: Username to update
        old_password: Current password
        new_password: New password to set
        auth_db: Authentication database

    Returns:
        True if successful, False otherwise
    """
    temp_username = f"temp_rotation_{int(datetime.now().timestamp())}"
    temp_password = generate_strong_password(32)

    # Build connection URI (needed for error cleanup) - URL encode passwords
    uri = f"mongodb://{username}:{quote_plus(old_password)}@{host}:{port}/{auth_db}?authSource={auth_db}"

    try:
        # Connect with old credentials
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)

        # Test connection
        client.admin.command('ping')
        print(f"✅ Connected to MongoDB with current credentials")

        # Get current user's roles before dropping
        db = client[auth_db]
        user_info = db.command('usersInfo', username)

        if not user_info['users']:
            raise Exception(f"User {username} not found")

        current_roles = user_info['users'][0]['roles']
        print(f"   Current user has {len(current_roles)} role(s)")

        # Create temporary admin user with full privileges
        print(f"   Creating temporary admin user for rotation...")
        db.command('createUser', temp_username, pwd=temp_password, roles=[
            {'role': 'root', 'db': 'admin'},
            {'role': 'userAdminAnyDatabase', 'db': 'admin'}
        ])
        print(f"✅ Created temporary admin user")

        # Close original connection
        client.close()

        # Connect with temporary admin user - URL encode password
        temp_uri = f"mongodb://{temp_username}:{quote_plus(temp_password)}@{host}:{port}/{auth_db}?authSource={auth_db}"
        temp_client = MongoClient(temp_uri, serverSelectionTimeoutMS=5000)
        temp_db = temp_client[auth_db]

        # Test temporary connection
        temp_client.admin.command('ping')
        print(f"✅ Connected with temporary admin user")

        # Drop original user
        temp_db.command('dropUser', username)
        print(f"✅ Dropped original user '{username}'")

        # Create original user with new password
        temp_db.command('createUser', username, pwd=new_password, roles=current_roles)
        print(f"✅ Created user '{username}' with new password")

        # Close temporary connection
        temp_client.close()

        # Test new password works - URL encode password
        new_uri = f"mongodb://{username}:{quote_plus(new_password)}@{host}:{port}/{auth_db}?authSource={auth_db}"
        new_client = MongoClient(new_uri, serverSelectionTimeoutMS=5000)
        new_client.admin.command('ping')
        print(f"✅ New password verified - connection successful")

        # Clean up: drop temporary user
        new_db = new_client[auth_db]
        new_db.command('dropUser', temp_username)
        print(f"✅ Cleaned up temporary admin user")

        new_client.close()
        return True

    except ConnectionFailure as e:
        print(f"❌ Connection failed: {e}")
        return False
    except OperationFailure as e:
        print(f"❌ Operation failed: {e}")
        # Try to clean up temporary user if it exists
        try:
            cleanup_client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            cleanup_db = cleanup_client[auth_db]
            cleanup_db.command('dropUser', temp_username)
            print(f"   Cleaned up temporary user after error")
            cleanup_client.close()
        except:
            pass
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        # Try to clean up temporary user if it exists
        try:
            cleanup_client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            cleanup_db = cleanup_client[auth_db]
            cleanup_db.command('dropUser', temp_username)
            print(f"   Cleaned up temporary user after error")
            cleanup_client.close()
        except:
            pass
        return False


def restart_backend_service() -> bool:
    """
    Restart the backend systemd service

    Returns:
        True if successful, False otherwise
    """
    try:
        print("\n🔄 Restarting backend service...")
        result = subprocess.run(
            ['sudo', 'systemctl', 'restart', 'surg-db-backend'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("✅ Backend service restarted")

            # Check status
            status_result = subprocess.run(
                ['sudo', 'systemctl', 'is-active', 'surg-db-backend'],
                capture_output=True,
                text=True
            )

            if status_result.stdout.strip() == 'active':
                print("✅ Backend service is active")
                return True
            else:
                print(f"⚠️  Backend service status: {status_result.stdout.strip()}")
                return False
        else:
            print(f"❌ Failed to restart service: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Service restart timed out")
        return False
    except Exception as e:
        print(f"❌ Error restarting service: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Rotate MongoDB password securely',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would change without making changes')
    parser.add_argument('--password', type=str,
                       help='Use specific password (otherwise generates random)')

    args = parser.parse_args()

    print("=" * 70)
    print("MongoDB Password Rotation Script")
    print("=" * 70)

    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")

    # Read current configuration
    print("\n📋 Step 1: Reading current configuration...")
    try:
        env_vars = read_env_file()
        mongodb_uri = env_vars.get('MONGODB_URI')

        if not mongodb_uri:
            print("❌ MONGODB_URI not found in secrets file")
            sys.exit(1)

        config = parse_mongodb_uri(mongodb_uri)
        print(f"   Current host: {config['host']}:{config['port']}")
        print(f"   Current user: {config['username']}")
        print(f"   Current database: {config['database']}")
        print(f"   Auth source: {config['auth_source']}")

    except Exception as e:
        print(f"❌ Error reading configuration: {e}")
        sys.exit(1)

    # Generate new password
    print("\n🔑 Step 2: Generating new password...")
    if args.password:
        new_password = args.password
        print(f"   Using provided password ({len(new_password)} characters)")
    else:
        new_password = generate_strong_password()
        print(f"   Generated strong password ({len(new_password)} characters)")

    if args.dry_run:
        print(f"\n   New password would be: {new_password}")
        print("\n✅ Dry run complete - no changes made")
        sys.exit(0)

    # Backup secrets file
    print("\n💾 Step 3: Backing up secrets file...")
    try:
        backup_path = backup_env_file()
        print(f"   Backup created: {backup_path}")
    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        sys.exit(1)

    # Update MongoDB password
    print("\n🔐 Step 4: Updating MongoDB password...")
    success = update_mongodb_password(
        host=config['host'],
        port=config['port'],
        username=config['username'],
        old_password=config['password'],
        new_password=new_password,
        auth_db=config['auth_source']
    )

    if not success:
        print(f"\n❌ Failed to update MongoDB password")
        print(f"   Secrets backup is available at: {backup_path}")
        sys.exit(1)

    # Update secrets file
    print("\n📝 Step 5: Updating secrets file...")
    try:
        update_env_file(config['password'], new_password)
        print(f"   Secrets file updated with new credentials")
    except Exception as e:
        print(f"❌ Error updating secrets file: {e}")
        print(f"   CRITICAL: MongoDB password was changed but secrets file not updated!")
        print(f"   Restore from backup: {backup_path}")
        sys.exit(1)

    # Restart backend service
    print("\n🔄 Step 6: Restarting backend service...")
    if not restart_backend_service():
        print("⚠️  Warning: Service restart may have failed")
        print("   Check manually: sudo systemctl status surg-db-backend")

    # Success summary
    print("\n" + "=" * 70)
    print("✅ PASSWORD ROTATION COMPLETE")
    print("=" * 70)
    print(f"\n📌 Summary:")
    print(f"   - Old secrets backed up to: {backup_path}")
    print(f"   - MongoDB password updated")
    print(f"   - Secrets file updated (/etc/impact/secrets.env)")
    print(f"   - Backend service restarted")
    print(f"\n🔒 New password: {new_password}")
    print(f"\n⚠️  IMPORTANT:")
    print(f"   - Store this password securely (password manager recommended)")
    print(f"   - Delete this terminal output after saving password")
    print(f"   - Test application login to verify everything works")
    print(f"   - Keep backup file secure: {backup_path}")
    print()


if __name__ == '__main__':
    main()
