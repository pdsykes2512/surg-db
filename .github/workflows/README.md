# GitHub Actions Workflows

This directory contains automated workflows for the IMPACT application.

## Available Workflows

### `auto-version.yml` - Automated Semantic Versioning

**Purpose**: Automatically bump version numbers based on conventional commit messages

**Triggers**:
- Every push to `main` branch
- Manual trigger via workflow_dispatch

**What it does**:
1. Analyzes conventional commits since last version tag
2. Determines version bump type (major/minor/patch)
3. Updates VERSION, frontend/package.json, backend/app/config.py
4. Creates git tag with release notes
5. Pushes changes and tags
6. Creates GitHub Release

**Usage**:
Developers just need to use conventional commits:
```bash
git commit -m "feat: add new feature"  # MINOR bump
git commit -m "fix: fix bug"           # PATCH bump
git commit -m "feat!: breaking change" # MAJOR bump
```

See [VERSIONING.md](../../VERSIONING.md) for complete documentation.

## Workflow Permissions

The workflows require:
- `contents: write` - To push version commits and tags

These are configured in the workflow files and use the automatic `GITHUB_TOKEN`.

## Disabling Workflows

To temporarily disable versioning workflow:
1. Go to repository Settings → Actions → General
2. Disable specific workflow or all workflows

Or add `[skip ci]` to commit messages:
```bash
git commit -m "docs: update README [skip ci]"
```
