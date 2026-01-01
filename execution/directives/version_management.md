# Version Management Directive

## Purpose
Automate semantic versioning for the IMPACT application based on conventional commit messages.

## Overview
The IMPACT system uses **Semantic Versioning (MAJOR.MINOR.PATCH)** with automated version bumps triggered by GitHub Actions on every push to main branch.

## Version Schema

### Format: `X.Y.Z`

- **MAJOR (X)**: Breaking changes requiring user action
  - Database schema changes requiring migration
  - API endpoint removals or breaking changes
  - Major UI/UX overhauls
  - Changes to authentication/authorization
  - **Example**: Removing surgeons collection (1.1.1 → 2.0.0)

- **MINOR (Y)**: New features, non-breaking additions
  - New API endpoints
  - New UI components/pages
  - New functionality (keyboard shortcuts, export features)
  - Non-breaking field additions
  - **Example**: Adding keyboard shortcuts (1.1.1 → 1.2.0)

- **PATCH (Z)**: Bug fixes and minor improvements
  - Bug fixes
  - Style/CSS tweaks
  - Documentation updates
  - Refactoring without behavior changes
  - **Example**: Fixing height units bug (1.1.1 → 1.1.2)

## Conventional Commit Types

Use these commit message prefixes:

```
feat:      New feature (MINOR bump)
fix:       Bug fix (PATCH bump)
perf:      Performance improvement (PATCH bump)
refactor:  Code refactoring (PATCH bump, unless breaking)
style:     Style/formatting changes (PATCH bump)
docs:      Documentation only (no bump)
test:      Test changes (no bump)
chore:     Build/tooling changes (no bump)
ci:        CI/CD changes (no bump)
```

### Breaking Changes
Add `BREAKING CHANGE:` in commit footer or `!` after type to force MAJOR bump:

```bash
# Method 1: Using ! suffix
git commit -m "feat!: remove surgeons collection"

# Method 2: Using footer
git commit -m "refactor: change patient ID format

BREAKING CHANGE: Patient IDs now use UUID format instead of sequential numbers"
```

## File Structure

### Single Source of Truth
- **`VERSION`** - Plain text file at repo root (e.g., `1.1.1`)
- All other files sync from this

### Synced Files
- `frontend/package.json` - `"version": "1.1.1"`
- `backend/app/config.py` - `api_version: str = "1.1.1"`

## Tools

### 1. `execution/version_bump.py`
**Purpose**: Analyze commits and bump version
**Usage**:
```bash
# Interactive mode (with confirmation prompt)
python3 execution/version_bump.py

# CI mode (auto-apply)
python3 execution/version_bump.py --ci
```

**What it does**:
1. Reads current version from `VERSION` file
2. Gets commits since last git tag
3. Analyzes commit messages to determine bump type
4. Calculates new version
5. Updates `VERSION`, `frontend/package.json`, `backend/app/config.py`
6. Creates git tag with release notes
7. Displays next steps

### 2. `execution/sync_version.py`
**Purpose**: Sync version numbers across all files
**Usage**:
```bash
python3 execution/sync_version.py
```

**When to use**:
- After manually editing `VERSION` file
- To verify all files are in sync
- After merging branches with version conflicts

## GitHub Actions Workflow

### Trigger: `.github/workflows/auto-version.yml`

**Runs on**:
- Every push to `main` branch
- Manual trigger via workflow_dispatch

**What it does**:
1. Checks out repo with full git history
2. Runs `version_bump.py --ci`
3. Commits version changes with `[skip ci]` to prevent loops
4. Pushes version bump commit and tags
5. Creates GitHub Release with changelog

**Skips when**:
- Only docs/markdown files changed
- Only workflow files changed
- Commit is a version bump itself

**Workflow dispatch options**:
- Can manually trigger with forced bump type (major/minor/patch/auto)

## Workflow Examples

### Standard Development Flow

1. **Make changes and commit with conventional commits**:
```bash
git commit -m "feat: add patient export to CSV"
git commit -m "fix: correct date formatting in reports"
git push origin main
```

2. **GitHub Actions automatically**:
   - Analyzes commits (1 feat + 1 fix = MINOR bump)
   - Bumps version (e.g., 1.1.1 → 1.2.0)
   - Creates tag `v1.2.0`
   - Pushes changes
   - Creates GitHub release

3. **No action needed** - version is bumped automatically!

### Manual Version Bump (Local Testing)

```bash
# Test what version bump would happen
python3 execution/version_bump.py

# Review the proposed changes
# Type 'y' to apply or 'n' to cancel

# If applied, commit and push
git push && git push --tags
```

### Force Specific Version Bump

```bash
# Manually edit VERSION file
echo "2.0.0" > VERSION

# Sync to other files
python3 execution/sync_version.py

# Commit
git add VERSION frontend/package.json backend/app/config.py
git commit -m "chore: bump to version 2.0.0 for major release"
git tag -a v2.0.0 -m "Major release 2.0.0"
git push && git push --tags
```

## Edge Cases & Best Practices

### 1. Multiple Commits
**Rule**: Highest priority bump wins
```
3x fix commits + 1x feat commit = MINOR bump (1.1.1 → 1.2.0)
```

### 2. Docs-Only Changes
**Rule**: No version bump
```
docs: update README
chore: update .gitignore
```
These won't trigger version bump.

### 3. Breaking Changes
**Rule**: Always MAJOR bump
```
feat!: redesign API response format    → 2.0.0
fix: correct validation (BREAKING CHANGE: changes validation rules) → 2.0.0
```

### 4. Merge Conflicts in VERSION
**Solution**: Use sync script
```bash
# After resolving conflict, pick correct version
echo "1.2.0" > VERSION

# Sync to other files
python3 execution/sync_version.py

# Continue merge/rebase
```

### 5. Skip CI Loops
The workflow commit includes `[skip ci]` to prevent infinite loops:
```
chore: bump version to 1.2.0 [skip ci]
```

## Verification

### Check Current Version
```bash
cat VERSION                           # 1.1.1
grep version frontend/package.json    # "version": "1.1.1"
grep api_version backend/app/config.py # api_version: str = "1.1.1"
```

### Check Version History
```bash
git tag --sort=-v:refname | head -5   # Show recent version tags
git log --oneline --decorate          # See commits with tags
```

### Check GitHub Releases
- Visit `https://github.com/your-org/impact/releases`
- Each version bump creates a release

## Troubleshooting

### Problem: Version not bumping
**Solution**: Check commit messages follow conventional commits format
```bash
# Bad
git commit -m "added new feature"

# Good
git commit -m "feat: add new patient dashboard"
```

### Problem: Files out of sync
**Solution**: Run sync script
```bash
python3 execution/sync_version.py
```

### Problem: GitHub Action failing
**Solution**: Check workflow logs
1. Go to GitHub Actions tab
2. Check the failed run
3. Verify git permissions and token

### Problem: Want to skip version bump
**Solution**: Use docs/chore commits
```bash
git commit -m "docs: update changelog"  # Won't bump version
```

## Integration with RECENT_CHANGES.md

After version bump, update `RECENT_CHANGES.md`:

```markdown
## 2026-01-01 - Version 1.2.0 Released

**Version**: 1.2.0 (MINOR bump)

**Changes in this release**:
- ✅ Added patient export to CSV
- ✅ Fixed date formatting in reports
- ✅ Improved keyboard shortcuts

**Files affected**: [list files]
**Testing**: [verification steps]
```

## Future Enhancements

Potential improvements:
- [ ] Auto-update RECENT_CHANGES.md from commits
- [ ] Changelog generation in releases
- [ ] Pre-release versions (1.2.0-beta.1)
- [ ] Version badge in README
- [ ] Slack/Discord notifications on release

## References

- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub Actions](https://docs.github.com/en/actions)
