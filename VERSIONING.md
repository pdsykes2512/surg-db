# IMPACT Version Management

**Current Version**: 1.1.1

## Quick Start

### For Developers

**Standard workflow** - Just commit with conventional commit messages:
```bash
git commit -m "feat: add patient export to PDF"
git commit -m "fix: correct date validation in forms"
git push origin main
```

GitHub Actions will automatically:
- Analyze your commits
- Bump the version appropriately
- Create a git tag
- Generate a GitHub release

**That's it!** No manual version management needed.

### Manual Version Bump (Optional)

If you want to see what version bump would happen before pushing:
```bash
python3 execution/version_bump.py
```

## Semantic Versioning

We use **Semantic Versioning**: `MAJOR.MINOR.PATCH`

### Version Increment Rules

| Commit Type | Example | Version Bump |
|-------------|---------|--------------|
| `feat:` | New feature | **MINOR** (1.1.1 → 1.2.0) |
| `fix:` | Bug fix | **PATCH** (1.1.1 → 1.1.2) |
| `perf:` | Performance | **PATCH** (1.1.1 → 1.1.2) |
| `refactor:` | Refactoring | **PATCH** (1.1.1 → 1.1.2) |
| `style:` | Styling | **PATCH** (1.1.1 → 1.1.2) |
| `docs:` | Documentation | None |
| `test:` | Tests | None |
| `chore:` | Build/tooling | None |
| `BREAKING:` | Breaking change | **MAJOR** (1.1.1 → 2.0.0) |

### Breaking Changes

To trigger a **MAJOR** version bump:

**Method 1**: Add `!` after commit type
```bash
git commit -m "feat!: redesign patient API response format"
```

**Method 2**: Add `BREAKING CHANGE:` in commit body
```bash
git commit -m "refactor: change authentication system

BREAKING CHANGE: API now requires JWT tokens instead of session cookies"
```

### Multiple Commits

**Rule**: Highest priority bump wins

```
3 × fix:  + 1 × feat:  = MINOR bump (1.1.1 → 1.2.0)
5 × docs: + 2 × fix:   = PATCH bump (1.1.1 → 1.1.2)
1 × feat! + 10 × feat: = MAJOR bump (1.1.1 → 2.0.0)
```

## Conventional Commits

### Good Examples ✅

```bash
# Features (MINOR bump)
git commit -m "feat: add export to Excel functionality"
git commit -m "feat: implement dark mode toggle"

# Bug fixes (PATCH bump)
git commit -m "fix: correct date formatting in reports"
git commit -m "fix: resolve memory leak in patient search"

# No version bump
git commit -m "docs: update README with deployment instructions"
git commit -m "chore: update dependencies"
git commit -m "test: add unit tests for patient validation"

# Breaking changes (MAJOR bump)
git commit -m "feat!: remove deprecated surgeons API"
git commit -m "refactor: change patient ID format

BREAKING CHANGE: Patient IDs now use UUID format"
```

### Bad Examples ❌

```bash
# Too vague
git commit -m "update stuff"
git commit -m "fixes"

# No type prefix
git commit -m "added new feature"
git commit -m "fixed bug"

# Wrong format
git commit -m "Feature: add export"
git commit -m "FIX: correct dates"
```

## File Structure

### Single Source of Truth
```
VERSION                    # Plain text: "1.1.1"
```

### Auto-Synced Files
```
frontend/package.json      # "version": "1.1.1"
backend/app/config.py      # api_version: str = "1.1.1"
```

The VERSION file is the **single source of truth**. All other files sync from it.

## Tools

### 1. `execution/version_bump.py`

Analyzes commits and bumps version automatically.

```bash
# Interactive mode (asks for confirmation)
python3 execution/version_bump.py

# CI mode (auto-applies)
python3 execution/version_bump.py --ci
```

**Output example**:
```
🔍 Analyzing commits for version bump...

Current version: 1.1.1
Last version tag: v1.1.0

📝 Found 15 commits since last version:
  - feat: add keyboard shortcuts
  - fix: correct height units
  - fix: resolve postcode migration
  ... and 12 more

🎯 Version bump type: MINOR
📦 New version: 1.1.1 → 1.2.0

❓ Apply this version bump? [y/N]:
```

### 2. `execution/sync_version.py`

Syncs version numbers across all files from VERSION file.

```bash
python3 execution/sync_version.py
```

**When to use**:
- After manually editing VERSION file
- To verify all files are in sync
- After resolving merge conflicts

## GitHub Actions Workflow

**File**: `.github/workflows/auto-version.yml`

### Triggers

**Automatic**:
- Every push to `main` branch (except docs/workflow changes)

**Manual**:
- Workflow dispatch (can force specific bump type)

### What It Does

1. ✅ Checks out repo with full git history
2. ✅ Runs `version_bump.py --ci`
3. ✅ Commits version changes `[skip ci]`
4. ✅ Creates git tag (e.g., `v1.2.0`)
5. ✅ Pushes commit and tag
6. ✅ Creates GitHub Release with changelog

### Skips When

- Only `.md` files changed
- Only workflow files changed
- Commit message contains `[skip ci]`

## Example Workflows

### Scenario 1: Feature Development

```bash
# Make changes
git add frontend/src/components/NewFeature.tsx
git commit -m "feat: add patient dashboard widget"

# Make more changes
git add backend/app/routes/stats.py
git commit -m "feat: add statistics API endpoint"

# Push to main
git push origin main
```

**Result**: GitHub Actions bumps version `1.1.1 → 1.2.0`, creates tag `v1.2.0`, creates release

### Scenario 2: Bug Fix

```bash
git add backend/app/models/patient.py
git commit -m "fix: correct validation for NHS number format"
git push origin main
```

**Result**: GitHub Actions bumps version `1.1.1 → 1.1.2`

### Scenario 3: Documentation Only

```bash
git add README.md
git commit -m "docs: update installation instructions"
git push origin main
```

**Result**: No version bump (docs don't trigger versioning)

### Scenario 4: Breaking Change

```bash
git add backend/app/routes/episodes.py
git commit -m "refactor!: change episode response format

BREAKING CHANGE: Episodes now return nested treatment array instead of flat structure"
git push origin main
```

**Result**: GitHub Actions bumps version `1.1.1 → 2.0.0`

## Checking Version

### Current Version

```bash
cat VERSION                            # 1.1.1
grep version frontend/package.json     # "version": "1.1.1"
grep api_version backend/app/config.py # api_version: str = "1.1.1"
```

### Version History

```bash
# Show all version tags
git tag --sort=-v:refname

# Show recent commits with tags
git log --oneline --decorate | head -20

# Show specific tag details
git show v1.1.0
```

### GitHub Releases

Visit: `https://github.com/your-org/impact/releases`

## Troubleshooting

### Problem: Version didn't bump

**Cause**: Commit messages don't follow conventional commits format

**Solution**: Use proper prefixes
```bash
# Bad
git commit -m "added feature"

# Good
git commit -m "feat: add feature"
```

### Problem: Files out of sync

**Cause**: Manual edits or merge conflicts

**Solution**: Run sync script
```bash
python3 execution/sync_version.py
```

### Problem: Wrong version bump

**Cause**: Incorrect commit type used

**Solution**: Create new commit with correct type
```bash
# If you used "feat:" but should have used "fix:"
git commit -m "fix: correct previous commit - this was a bug fix"
```

### Problem: Need to skip version bump

**Cause**: Don't want version to change

**Solution**: Use non-versioning commit types
```bash
git commit -m "docs: update README"     # Won't bump
git commit -m "chore: update .gitignore" # Won't bump
git commit -m "test: add unit tests"     # Won't bump
```

### Problem: GitHub Action failed

**Solution**: Check workflow logs
1. Go to repository → Actions tab
2. Click failed workflow run
3. Check error logs
4. Common issues:
   - Git permissions
   - Invalid conventional commit
   - Merge conflicts

## Integration with RECENT_CHANGES.md

After each version release, update `RECENT_CHANGES.md`:

```markdown
## 2026-01-01 - Version 1.2.0 Released

**Version**: 1.2.0 (MINOR bump)
**Git Tag**: v1.2.0
**GitHub Release**: https://github.com/your-org/impact/releases/tag/v1.2.0

**Features in this release**:
- ✅ Added patient export to PDF
- ✅ Implemented dark mode toggle
- ✅ Added statistics API endpoint

**Bug fixes**:
- ✅ Fixed date formatting in reports
- ✅ Resolved memory leak in patient search

**Files affected**: [list key files]
**Testing**: [verification steps]
```

## Best Practices

### ✅ DO

- Use conventional commits consistently
- Write clear, descriptive commit messages
- Group related changes in single commit
- Use `feat:` for new functionality
- Use `fix:` for bug fixes
- Use `BREAKING CHANGE:` or `!` for breaking changes

### ❌ DON'T

- Mix multiple unrelated changes in one commit
- Use vague messages like "update" or "fix stuff"
- Manually edit version numbers (use scripts)
- Force push version tags
- Skip CI checks with commits

## References

- 📚 [Semantic Versioning Specification](https://semver.org/)
- 📚 [Conventional Commits](https://www.conventionalcommits.org/)
- 📚 [GitHub Actions Documentation](https://docs.github.com/en/actions)
- 📄 [Version Management Directive](execution/directives/version_management.md)

## Support

For questions or issues with versioning:
1. Check this documentation
2. Review [execution/directives/version_management.md](execution/directives/version_management.md)
3. Check GitHub Actions workflow logs
4. Contact the development team
