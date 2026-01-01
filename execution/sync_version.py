#!/usr/bin/env python3
"""
Sync version from VERSION file to package.json and config.py
Run this script to ensure all version numbers are in sync
"""
import json
import re
from pathlib import Path


def get_repo_root() -> Path:
    """Get the repository root directory"""
    return Path(__file__).parent.parent


def get_version_from_file() -> str:
    """Read version from VERSION file"""
    repo_root = get_repo_root()
    version_file = repo_root / 'VERSION'

    if not version_file.exists():
        raise FileNotFoundError('VERSION file not found')

    return version_file.read_text().strip()


def update_frontend_package_json(version: str):
    """Update frontend/package.json with version from VERSION file"""
    repo_root = get_repo_root()
    package_json = repo_root / 'frontend' / 'package.json'

    if not package_json.exists():
        print(f'⚠️  Frontend package.json not found at {package_json}')
        return

    with open(package_json, 'r') as f:
        data = json.load(f)

    if data.get('version') == version:
        print(f'✅ frontend/package.json already at version {version}')
        return

    data['version'] = version

    with open(package_json, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')

    print(f'✅ Updated frontend/package.json to version {version}')


def update_backend_config(version: str):
    """Update backend/app/config.py with version from VERSION file"""
    repo_root = get_repo_root()
    config_file = repo_root / 'backend' / 'app' / 'config.py'

    if not config_file.exists():
        print(f'⚠️  Backend config.py not found at {config_file}')
        return

    content = config_file.read_text()

    # Check if already at correct version
    current_version_match = re.search(r'api_version: str = "([^"]+)"', content)
    if current_version_match and current_version_match.group(1) == version:
        print(f'✅ backend/app/config.py already at version {version}')
        return

    # Replace api_version line
    new_content = re.sub(
        r'api_version: str = "[^"]+"',
        f'api_version: str = "{version}"',
        content
    )

    config_file.write_text(new_content)
    print(f'✅ Updated backend/app/config.py to version {version}')


def main():
    """Main sync workflow"""
    print('🔄 Syncing version numbers from VERSION file...\n')

    try:
        version = get_version_from_file()
        print(f'📦 Version from VERSION file: {version}\n')

        update_frontend_package_json(version)
        update_backend_config(version)

        print('\n✅ Version sync complete!')

    except FileNotFoundError as e:
        print(f'❌ Error: {e}')
        return 1
    except Exception as e:
        print(f'❌ Unexpected error: {e}')
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
