# Git Workflow & Branching Strategy

## Overview

This project uses a two-branch workflow to separate unstable development from production-ready releases:

- **`develop`** - Active development branch (unstable)
- **`main`** - Stable production branch (auto-versioned)

## Branching Strategy

### Development Branch (`develop`)

**Purpose:** All active development work happens here.

**Characteristics:**
- No automatic version bumping
- No automatic releases
- Commits can be experimental or work-in-progress
- Safe to break things temporarily

**Usage:**
```bash
# Switch to develop branch
git checkout develop

# Make your changes
git add .
git commit -m "feat: add new feature"

# Push to develop
git push origin develop
```

### Main Branch (`main`)

**Purpose:** Production-ready stable releases only.

**Characteristics:**
- **Automatic version bumping** based on conventional commits
- **Automatic GitHub releases** on every merge
- Protected - should only receive merges from `develop`
- Always deployable

**Auto-versioning Rules:**
- `feat:` prefix → Minor version bump (1.8.0 → 1.9.0)
- `fix:` prefix → Patch version bump (1.8.0 → 1.8.1)
- `BREAKING CHANGE:` in commit body → Major version bump (1.8.0 → 2.0.0)
- Other prefixes → Patch version bump

## Workflow

### 1. Daily Development

Work on the `develop` branch:

```bash
# Ensure you're on develop
git checkout develop
git pull origin develop

# Make changes
# ... edit files ...

# Commit with conventional commit format
git add .
git commit -m "feat: add patient search functionality"
git push origin develop
```

### 2. When Features Are Stable

Once you've verified features are stable and ready for production:

```bash
# Switch to main branch
git checkout main
git pull origin main

# Merge develop into main
git merge develop

# Push to trigger auto-versioning
git push origin main
```

**What happens automatically:**
1. GitHub Actions workflow triggers
2. Analyzes commit messages since last version
3. Bumps version number appropriately
4. Updates `VERSION`, `frontend/package.json`, `backend/app/config.py`
5. Creates git tag (e.g., `v1.9.0`)
6. Creates GitHub release with changelog

### 3. After Merge to Main

Sync `develop` with the new version:

```bash
# Switch back to develop
git checkout develop

# Pull the version bump commit from main
git merge main

# Push updated develop
git push origin develop
```

## Conventional Commit Format

Use semantic commit messages for automatic versioning:

```
<type>: <description>

[optional body]

[optional footer]
```

### Types

| Type | Version Bump | Example |
|------|--------------|---------|
| `feat:` | Minor (1.8.0 → 1.9.0) | `feat: add patient export feature` |
| `fix:` | Patch (1.8.0 → 1.8.1) | `fix: resolve episode search crash` |
| `perf:` | Patch (1.8.0 → 1.8.1) | `perf: optimize dashboard queries` |
| `refactor:` | Patch (1.8.0 → 1.8.1) | `refactor: simplify patient modal` |
| `docs:` | None | `docs: update README` |
| `chore:` | None | `chore: update dependencies` |
| `test:` | None | `test: add episode validation tests` |
| `BREAKING CHANGE:` | Major (1.8.0 → 2.0.0) | See below |

### Breaking Changes

For major version bumps, include `BREAKING CHANGE:` in the commit body:

```
feat: redesign patient API

BREAKING CHANGE: Patient API now requires authentication headers
```

## Examples

### Scenario 1: Adding Multiple Features

```bash
# Start on develop
git checkout develop

# Work on feature 1
git commit -m "feat: add patient filtering"
git push origin develop

# Work on feature 2
git commit -m "feat: add export to CSV"
git push origin develop

# Work on bug fix
git commit -m "fix: resolve date picker issue"
git push origin develop

# Test thoroughly on develop branch
# ... testing ...

# When stable, merge to main
git checkout main
git merge develop
git push origin main
# → Auto-bumps to v1.9.0 (two features = minor bump)
```

### Scenario 2: Hotfix on Production

If you need to fix something urgent on `main`:

```bash
# Create hotfix branch from main
git checkout main
git checkout -b hotfix/critical-bug

# Fix the issue
git commit -m "fix: resolve critical authentication bug"

# Merge to main
git checkout main
git merge hotfix/critical-bug
git push origin main
# → Auto-bumps to v1.8.1 (patch)

# Merge back to develop
git checkout develop
git merge main
git push origin develop

# Delete hotfix branch
git branch -d hotfix/critical-bug
```

### Scenario 3: Weekly Stable Release

```bash
# Monday-Friday: work on develop
git checkout develop
# ... multiple commits ...

# Friday: merge to main for weekly release
git checkout main
git merge develop
git push origin main
# → Auto-creates release

# Monday: continue on develop
git checkout develop
git merge main  # Get version bump
```

## Branch Protection (Optional)

For stricter control, consider enabling branch protection on `main`:

1. Go to GitHub → Settings → Branches
2. Add rule for `main` branch:
   - ✓ Require pull request reviews before merging
   - ✓ Require status checks to pass
   - ✓ Require branches to be up to date

This forces all changes to go through pull requests from `develop` to `main`.

## Current Version

Check current version:

```bash
cat VERSION
# or
cat frontend/package.json | grep version
```

## Troubleshooting

### "No version bump needed"

The workflow skips version bumps if:
- Only documentation changed (`*.md`)
- Only workflow files changed (`.github/workflows/**`)
- Commit has `[skip ci]` in message

### Manual Version Bump

If auto-versioning fails:

```bash
# Trigger manual workflow
# Go to GitHub → Actions → Auto Version Bump → Run workflow
# Select bump type: major/minor/patch
```

### Merge Conflicts

If `develop` and `main` diverge significantly:

```bash
git checkout develop
git merge main  # Resolve conflicts
git push origin develop
```

## Summary

**Simple rule:**
- Work on `develop` until features are stable
- Merge to `main` when ready for a release
- Versioning happens automatically on `main`

**Benefits:**
- Clean production history on `main`
- Freedom to experiment on `develop`
- Automatic semantic versioning
- No manual version management
