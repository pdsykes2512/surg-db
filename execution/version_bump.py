#!/usr/bin/env python3
"""
Automated Version Bumping for IMPACT
Analyzes git commits since last tag and determines semantic version bump
"""
import subprocess
import re
import sys
from pathlib import Path
from typing import Tuple, List
import json


# Semantic versioning rules based on conventional commits
COMMIT_TYPE_MAP = {
    'feat': 'minor',
    'fix': 'patch',
    'perf': 'patch',
    'refactor': 'patch',
    'style': 'patch',
    'docs': 'none',
    'test': 'none',
    'chore': 'none',
    'build': 'none',
    'ci': 'none',
}


def get_repo_root() -> Path:
    """Get the git repository root directory"""
    result = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'],
        capture_output=True,
        text=True,
        check=True
    )
    return Path(result.stdout.strip())


def get_current_version() -> str:
    """Read current version from VERSION file"""
    repo_root = get_repo_root()
    version_file = repo_root / 'VERSION'

    if not version_file.exists():
        return '0.0.0'

    return version_file.read_text().strip()


def get_last_version_tag() -> str:
    """Get the last version tag from git"""
    try:
        result = subprocess.run(
            ['git', 'describe', '--tags', '--abbrev=0', '--match', 'v*'],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None


def get_commits_since_tag(tag: str = None) -> List[str]:
    """Get all commit messages since the last tag"""
    if tag:
        cmd = ['git', 'log', f'{tag}..HEAD', '--pretty=format:%s']
    else:
        cmd = ['git', 'log', '--pretty=format:%s']

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    commits = result.stdout.strip().split('\n')
    return [c for c in commits if c]


def parse_commit_message(commit: str) -> Tuple[str, bool]:
    """
    Parse a conventional commit message
    Returns: (commit_type, is_breaking)
    """
    # Check for BREAKING CHANGE
    is_breaking = 'BREAKING CHANGE' in commit or '!' in commit.split(':')[0]

    # Extract commit type
    match = re.match(r'^(\w+)(\(.+\))?(!)?:', commit)
    if match:
        commit_type = match.group(1).lower()
        return commit_type, is_breaking

    return 'unknown', is_breaking


def determine_version_bump(commits: List[str]) -> str:
    """
    Analyze commits and determine version bump type
    Returns: 'major', 'minor', 'patch', or 'none'
    """
    bump_priority = {'major': 3, 'minor': 2, 'patch': 1, 'none': 0}
    max_bump = 'none'

    for commit in commits:
        commit_type, is_breaking = parse_commit_message(commit)

        # Breaking changes always trigger major version bump
        if is_breaking:
            return 'major'

        # Get bump type from commit type
        bump = COMMIT_TYPE_MAP.get(commit_type, 'none')

        # Track the highest priority bump
        if bump_priority[bump] > bump_priority[max_bump]:
            max_bump = bump

    return max_bump


def bump_version(version: str, bump_type: str) -> str:
    """
    Bump a semantic version string
    version: 'X.Y.Z'
    bump_type: 'major', 'minor', or 'patch'
    """
    major, minor, patch = map(int, version.split('.'))

    if bump_type == 'major':
        return f'{major + 1}.0.0'
    elif bump_type == 'minor':
        return f'{major}.{minor + 1}.0'
    elif bump_type == 'patch':
        return f'{major}.{minor}.{patch + 1}'
    else:
        return version


def update_version_file(version: str):
    """Update the VERSION file"""
    repo_root = get_repo_root()
    version_file = repo_root / 'VERSION'
    version_file.write_text(version + '\n')
    print(f'✅ Updated VERSION file: {version}')


def update_frontend_package_json(version: str):
    """Update frontend/package.json with new version"""
    repo_root = get_repo_root()
    package_json = repo_root / 'frontend' / 'package.json'

    if not package_json.exists():
        print(f'⚠️  Frontend package.json not found at {package_json}')
        return

    with open(package_json, 'r') as f:
        data = json.load(f)

    data['version'] = version

    with open(package_json, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')

    print(f'✅ Updated frontend/package.json: {version}')


def update_backend_config(version: str):
    """Update backend/app/config.py with new version"""
    repo_root = get_repo_root()
    config_file = repo_root / 'backend' / 'app' / 'config.py'

    if not config_file.exists():
        print(f'⚠️  Backend config.py not found at {config_file}')
        return

    content = config_file.read_text()

    # Replace api_version line
    new_content = re.sub(
        r'api_version: str = "[^"]+"',
        f'api_version: str = "{version}"',
        content
    )

    config_file.write_text(new_content)
    print(f'✅ Updated backend/app/config.py: {version}')


def create_git_tag(version: str, commits: List[str]):
    """Create a git tag with release notes"""
    tag_name = f'v{version}'

    # Generate release notes from commits
    release_notes = f'Release {version}\n\n'

    # Group commits by type
    features = []
    fixes = []
    others = []

    for commit in commits:
        commit_type, _ = parse_commit_message(commit)
        if commit_type == 'feat':
            features.append(commit)
        elif commit_type == 'fix':
            fixes.append(commit)
        else:
            others.append(commit)

    if features:
        release_notes += '### Features\n'
        for commit in features:
            release_notes += f'- {commit}\n'
        release_notes += '\n'

    if fixes:
        release_notes += '### Bug Fixes\n'
        for commit in fixes:
            release_notes += f'- {commit}\n'
        release_notes += '\n'

    if others:
        release_notes += '### Other Changes\n'
        for commit in others:
            release_notes += f'- {commit}\n'

    # Create annotated tag
    subprocess.run(
        ['git', 'tag', '-a', tag_name, '-m', release_notes],
        check=True
    )

    print(f'✅ Created git tag: {tag_name}')
    return tag_name


def process_commit_incrementally(commit: str, current_version: str, is_ci: bool) -> str:
    """
    Process a single commit and bump version if needed
    Returns the new version (or current if no bump)
    """
    commit_type, is_breaking = parse_commit_message(commit)

    # Determine bump type for this specific commit
    if is_breaking:
        bump_type = 'major'
    else:
        bump_type = COMMIT_TYPE_MAP.get(commit_type, 'none')

    if bump_type == 'none':
        return current_version

    # Calculate new version
    new_version = bump_version(current_version, bump_type)

    print(f'\n  📦 {current_version} → {new_version} ({bump_type})')
    print(f'     {commit}')

    # Apply version bump
    update_version_file(new_version)
    update_frontend_package_json(new_version)
    update_backend_config(new_version)

    # Create git tag
    create_git_tag(new_version, [commit])

    return new_version


def main():
    """Main version bump workflow with incremental processing"""
    print('🔍 Analyzing commits for version bump...\n')

    # Get current version
    current_version = get_current_version()
    print(f'Current version: {current_version}')

    # Get last tag
    last_tag = get_last_version_tag()
    if last_tag:
        print(f'Last version tag: {last_tag}')
    else:
        print('No previous version tags found')

    # Get commits since last tag (in chronological order - oldest first)
    commits = get_commits_since_tag(last_tag)

    if not commits:
        print('\n✨ No new commits since last version')
        return

    # Reverse to get chronological order (git log shows newest first)
    commits.reverse()

    print(f'\n📝 Found {len(commits)} commits since last version:')
    for commit in commits[:5]:  # Show first 5
        print(f'  - {commit}')
    if len(commits) > 5:
        print(f'  ... and {len(commits) - 5} more')

    # Check if any commits require version bump
    has_bump_commits = False
    for commit in commits:
        commit_type, is_breaking = parse_commit_message(commit)
        bump = COMMIT_TYPE_MAP.get(commit_type, 'none')
        if bump != 'none' or is_breaking:
            has_bump_commits = True
            break

    if not has_bump_commits:
        print('\n✨ No version bump needed (only docs/chore commits)')
        return

    # Check if running in CI (non-interactive)
    is_ci = '--ci' in sys.argv or 'CI' in subprocess.os.environ

    if not is_ci:
        # Interactive mode: ask for confirmation
        print('\n🎯 Incremental version bumping: Each commit will get its own version bump')
        response = input('❓ Apply version bumps? [y/N]: ')
        if response.lower() != 'y':
            print('❌ Version bump cancelled')
            return

    # Process commits incrementally
    print('\n🚀 Applying incremental version bumps...')
    version = current_version
    bumped_count = 0

    for commit in commits:
        new_version = process_commit_incrementally(commit, version, is_ci)
        if new_version != version:
            version = new_version
            bumped_count += 1

    if bumped_count == 0:
        print('\n✨ No version bumps applied')
        return

    print(f'\n✅ Version bumped successfully!')
    print(f'📊 Applied {bumped_count} incremental version bump(s)')
    print(f'📌 Final version: {current_version} → {version}')
    print(f'\n📌 Next steps:')
    print(f'   1. Review the changes: git diff')
    print(f'   2. Commit version files: git add VERSION frontend/package.json backend/app/config.py')
    print(f'   3. Commit: git commit -m "chore: bump version to {version}"')
    print(f'   4. Push with tags: git push && git push --tags')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f'\n❌ Git command failed: {e}')
        sys.exit(1)
    except Exception as e:
        print(f'\n❌ Error: {e}')
        sys.exit(1)
