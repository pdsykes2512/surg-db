#!/usr/bin/env python3
"""
Apply utility refactorings to route files.

This script demonstrates the refactorings by updating import statements
and providing a summary of changes that should be made.
"""
import os
import re
import sys

# Add backend to path
backend_dir = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_dir)


def analyze_file(filepath):
    """Analyze a file for refactoring opportunities"""
    with open(filepath, 'r') as f:
        content = f.read()

    # Count duplicate patterns
    error_blocks = len(re.findall(r'except HTTPException:\s+raise\s+except ValidationError', content, re.DOTALL))
    objectid_conversions = len(re.findall(r'\[\"_id\"\]\s*=\s*str\(.*?\[\"_id\"\]\)', content))
    mrn_patterns = len(re.findall(r'is_mrn_pattern\s*=', content))
    clinician_resolutions = len(re.findall(r'# Strategy \d+:', content))
    datetime_conversions = len(re.findall(r'\.isoformat\(\)', content))
    not_found_checks = len(re.findall(r'if not existing:\s+raise HTTPException\(\s+status_code=status\.HTTP_404', content, re.DOTALL))

    return {
        'error_blocks': error_blocks,
        'objectid_conversions': objectid_conversions,
        'mrn_patterns': mrn_patterns,
        'clinician_resolutions': clinician_resolutions,
        'datetime_conversions': datetime_conversions,
        'not_found_checks': not_found_checks
    }


def add_imports_to_file(filepath):
    """Add new utility imports to a file"""
    with open(filepath, 'r') as f:
        content = f.read()

    # Check if imports already exist
    if 'from ..utils.route_decorators import' in content:
        print(f"✓ {filepath} already has new imports")
        return False

    # Find the utils import section
    utils_import_pattern = r'(from \.\.utils\.encryption import.*?\n)'
    match = re.search(utils_import_pattern, content)

    if not match:
        print(f"⚠ Could not find utils import section in {filepath}")
        return False

    # Add new imports after existing utils imports
    new_imports = """from ..utils.route_decorators import handle_route_errors
from ..utils.search_helpers import is_mrn_or_nhs_pattern, build_encrypted_field_query
from ..utils.serializers import serialize_object_id, serialize_object_ids, serialize_datetime_fields
from ..utils.clinician_helpers import resolve_clinician_name
from ..utils.validation_helpers import check_entity_exists, check_entity_not_exists
"""

    insert_pos = match.end()
    new_content = content[:insert_pos] + new_imports + content[insert_pos:]

    with open(filepath, 'w') as f:
        f.write(new_content)

    print(f"✓ Added new utility imports to {filepath}")
    return True


def main():
    """Main refactoring analysis and import addition"""
    files_to_refactor = [
        'backend/app/routes/patients.py',
        'backend/app/routes/episodes.py',
        'backend/app/routes/treatments_surgery.py',
        'backend/app/routes/clinicians.py',
        'backend/app/routes/admin.py',
        'backend/app/routes/audit.py'
    ]

    print("="*70)
    print("REFACTORING ANALYSIS")
    print("="*70)
    print()

    total_savings = {
        'error_blocks': 0,
        'objectid_conversions': 0,
        'mrn_patterns': 0,
        'clinician_resolutions': 0,
        'datetime_conversions': 0,
        'not_found_checks': 0
    }

    for filepath in files_to_refactor:
        full_path = os.path.join(os.path.dirname(__file__), '..', filepath)
        if not os.path.exists(full_path):
            print(f"⚠ File not found: {filepath}")
            continue

        print(f"\n{filepath}:")
        stats = analyze_file(full_path)

        for key, value in stats.items():
            if value > 0:
                print(f"  - {key}: {value} occurrences")
                total_savings[key] += value

        # Add imports
        add_imports_to_file(full_path)

    print("\n" + "="*70)
    print("TOTAL REFACTORING OPPORTUNITIES")
    print("="*70)
    print()

    estimated_loc_saved = 0
    print("Pattern                  | Count | Est. LOC/each | Total Saved")
    print("-" * 70)

    patterns = [
        ('Error handling blocks', total_savings['error_blocks'], 15),
        ('ObjectId conversions', total_savings['objectid_conversions'], 0),  # Already 1 line
        ('MRN pattern checks', total_savings['mrn_patterns'], 13),
        ('Clinician resolutions', total_savings['clinician_resolutions'], 10),
        ('DateTime conversions', total_savings['datetime_conversions'], 2),
        ('Not-found checks', total_savings['not_found_checks'], 3)
    ]

    for name, count, loc_per in patterns:
        saved = count * loc_per
        estimated_loc_saved += saved
        print(f"{name:24s} | {count:5d} | {loc_per:13d} | {saved:11d}")

    print("-" * 70)
    print(f"{'TOTAL ESTIMATED SAVINGS':24s} | {'':5s} | {'':13s} | {estimated_loc_saved:11d} LOC")
    print()

    print("="*70)
    print("NEXT STEPS")
    print("="*70)
    print()
    print("1. Review the REFACTORING_GUIDE.md for before/after examples")
    print("2. Apply @handle_route_errors decorator to all endpoints")
    print("3. Replace duplicate search patterns with build_encrypted_field_query()")
    print("4. Replace ObjectId conversions with serialize_object_id()")
    print("5. Replace datetime conversions with serialize_datetime_fields()")
    print("6. Replace clinician resolution with resolve_clinician_name()")
    print("7. Replace validation checks with check_entity_exists/not_exists()")
    print("8. Run tests to ensure functionality preserved")
    print()
    print("Note: Imports have been added. Manual refactoring recommended for safety.")
    print()


if __name__ == "__main__":
    main()
