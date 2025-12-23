# Data Structure Refactoring Directive

## Purpose
When making substantial changes to data structures, models, or database schemas, follow this directive to ensure a clean, revertible transition with no orphaned legacy code.

## When to Use This Directive
Apply this workflow when:
- Changing database schema (e.g., single collection → multiple collections)
- Renaming core entities (e.g., "surgeries" → "episodes")
- Modifying data relationships (e.g., embedded docs → referenced collections)
- Changing ID formats or primary keys
- Refactoring models with breaking changes to field names/types

## Workflow

### Phase 1: Planning & Branch Creation

1. **Document the Change**
   - Create a brief specification document describing:
     - What is changing (old → new structure)
     - Why the change is needed
     - What data/code will be affected
     - Migration requirements
   - Store in: `/root/.tmp/refactor_spec_YYYYMMDD.md`

2. **Create Feature Branch**
   ```bash
   git checkout -b refactor/descriptive-name
   git push -u origin refactor/descriptive-name
   ```

3. **Identify All References**
   - Search codebase for all references to old structures:
     ```bash
     # Example: search for old collection/model names
     grep -r "old_collection_name" backend/
     grep -r "OldModelName" backend/
     grep -r "old_field_name" backend/ frontend/
     ```
   - Document findings in the spec file
   - Create a checklist of files to update

### Phase 2: Implementation

4. **Create New Structure First**
   - Write new models in separate files (e.g., `model_new.py`)
   - Create new routes in separate files (e.g., `routes_v2.py`)
   - Test new code independently
   - DO NOT modify old code yet

5. **Write Migration Script**
   - Create migration script in `/root/execution/migrate_*.py`
   - Script should:
     - Transform old data to new structure
     - Validate transformed data
     - Support dry-run mode
     - Be idempotent (safe to run multiple times)
   - Test migration on sample data first

6. **Update Main Application**
   - Switch imports to use new models/routes
   - Update `main.py` to include new routes
   - Ensure frontend uses new API endpoints

### Phase 3: Legacy Removal

7. **Remove All Legacy References**
   This is CRITICAL - no half-measures:
   
   a. **Delete Old Model Files**
      ```bash
      # Example
      rm backend/app/models/old_model.py
      rm backend/app/models/old_model_v1.py
      ```
   
   b. **Delete Old Route Files**
      ```bash
      # Example
      rm backend/app/routes/old_routes.py
      ```
   
   c. **Remove Old Collection/Table Schema**
      - Update init scripts (e.g., `init_database.py`)
      - Remove old collection creation code
      - Remove old indexes
      - Update collection drop comments
   
   d. **Clean Database Init Scripts**
      - Remove old collection validators
      - Remove old indexes
      - Update print statements
   
   e. **Remove Old Data Generation**
      - Update `create_sample_data.py`
      - Remove old field names
      - Remove old ID formats
   
   f. **Update Documentation**
      - Remove old structure from README files
      - Update API documentation
      - Remove migration instructions (after merge)

8. **Verify No Orphaned Code**
   ```bash
   # Search for any remaining references
   grep -r "OldModelName\|old_collection\|old_field" backend/ frontend/
   
   # Check for unused imports
   # Check for commented-out legacy code
   # Check for old files with _v1, _old, _deprecated suffixes
   ```

### Phase 4: Testing & Validation

9. **Test Complete System**
   - Test all CRUD operations
   - Test all API endpoints
   - Test frontend integration
   - Check database queries
   - Verify no errors in logs
   - Load test with realistic data volume

10. **Document Changes**
    - Update CHANGELOG.md
    - Document breaking changes
    - Update deployment instructions if needed

### Phase 5: Merge & Cleanup

11. **Pre-Merge Checklist**
    - [ ] All legacy files deleted
    - [ ] All legacy references removed
    - [ ] All tests passing
    - [ ] No console errors
    - [ ] No database errors
    - [ ] Documentation updated
    - [ ] Migration script tested
    - [ ] Code review completed

12. **Merge to Main**
    ```bash
    git add -A
    git commit -m "refactor: migrate [old] to [new] structure - remove all legacy code"
    git push origin refactor/descriptive-name
    # Create PR, review, merge
    git checkout main
    git pull origin main
    ```

13. **Post-Merge Cleanup**
    - Delete feature branch (local and remote)
    - Archive migration script if no longer needed
    - Remove temporary spec document
    - Run migration in production
    - Monitor for issues

## Common Pitfalls to Avoid

❌ **DON'T:**
- Leave old model files with `_old` suffix "just in case"
- Comment out old code instead of deleting it
- Keep old routes alongside new ones indefinitely
- Leave old database schemas in init scripts
- Skip the search for remaining references
- Merge before removing all legacy code

✅ **DO:**
- Delete old files completely (git keeps history)
- Use feature branches for isolation
- Remove all references in one commit
- Test thoroughly before merging
- Document the changes
- Trust git history for rollback

## Emergency Rollback

If critical issues arise after merge:

1. **Quick Revert**
   ```bash
   git revert HEAD
   git push origin main
   ```

2. **Full Rollback**
   ```bash
   git checkout -b hotfix/rollback-refactor
   git revert <merge_commit_sha>
   git push origin hotfix/rollback-refactor
   # Create PR to main
   ```

3. **Database Rollback**
   - Restore from backup if data migration occurred
   - Run reverse migration script if available

## Success Criteria

A refactoring is complete when:
- ✅ All old files are deleted
- ✅ No references to old structures remain in codebase
- ✅ All tests pass
- ✅ System runs without errors
- ✅ Documentation is updated
- ✅ Code is merged to main
- ✅ Feature branch is deleted

## Example: surgeries → episodes Refactoring

**What was done:**
1. Created `Episode`, `Treatment`, `Tumour` models
2. Created `episodes_v2.py` routes
3. Wrote `migrate_ids.py` script
4. Updated `main.py` to use `episodes_v2` routes
5. **Deleted** `surgery_old.py`, `init_database_old.py`, `episodes.py` (old routes)
6. **Removed** surgeries collection from `init_database.py`
7. **Updated** field names in `create_sample_data.py`
8. **Kept** `surgery.py` (still used by `treatment.py` for surgical treatment data)

**Result:** Clean codebase with no legacy references, all functionality working.

## Conclusion

Branching + immediate legacy removal = clean, maintainable code. Always remove old code as soon as the new code is stable. Git provides version history - use it.
