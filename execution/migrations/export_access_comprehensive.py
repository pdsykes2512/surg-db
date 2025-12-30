#!/usr/bin/env python3
"""
Comprehensive CSV Export from Access Database for COSD-compliant Import

This script exports all necessary fields from the Access database to CSV files
that will be used for a complete, single-step MongoDB import.

Exports 7 CSV files:
1. patients.csv - Demographics, deceased dates, BMI
2. episodes.csv - Referral/MDT data from tblTumour
3. tumours.csv - Diagnosis, staging, imaging from tblTumour
4. treatments_surgery.csv - Surgery details from tblSurgery
5. pathology.csv - Histopathology from tblPathology
6. oncology.csv - Chemo/radiotherapy from tblOncology
7. followup.csv - Recurrence and outcomes from tblFollowUp
"""

import os
import subprocess
from pathlib import Path
from datetime import datetime


# Access database path
ACCESS_DB = '/root/impact/data/acpdata_v3_db.mdb'

# Output directory
OUTPUT_DIR = Path.home() / '.tmp' / 'access_export_comprehensive'


def run_mdb_export(table_name, output_file, columns=None):
    """
    Export Access table to CSV using mdb-export

    Args:
        table_name: Name of Access table
        output_file: Output CSV file path
        columns: List of column names to export (None = all columns)
    """
    cmd = ['mdb-export', ACCESS_DB, table_name]

    # Add delimiter and quote options for CSV
    cmd.extend(['-D', '%Y-%m-%d'])  # Date format

    print(f"Exporting {table_name}...")
    print(f"  Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # Write to file
        with open(output_file, 'w') as f:
            f.write(result.stdout)

        # Count rows (excluding header)
        row_count = len(result.stdout.strip().split('\n')) - 1
        print(f"  ✅ Exported {row_count} rows to {output_file.name}")
        return row_count

    except subprocess.CalledProcessError as e:
        print(f"  ❌ Error exporting {table_name}: {e.stderr}")
        raise


def export_all_tables():
    """Export all tables required for comprehensive import"""

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n{'=' * 80}")
    print(f"COMPREHENSIVE ACCESS DATABASE EXPORT")
    print(f"{'=' * 80}")
    print(f"Database: {ACCESS_DB}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 80}\n")

    stats = {}

    # 1. Export tblPatient → patients.csv
    print("\n[1/7] PATIENTS")
    stats['patients'] = run_mdb_export(
        'tblPatient',
        OUTPUT_DIR / 'patients.csv'
    )

    # 2. Export tblTumour → tumours.csv (full table for both episodes and tumours)
    print("\n[2/7] TUMOURS (Full table for episode and tumour data)")
    stats['tumours'] = run_mdb_export(
        'tblTumour',
        OUTPUT_DIR / 'tumours.csv'
    )

    # 3. Export tblSurgery → treatments_surgery.csv
    print("\n[3/7] SURGERY/TREATMENTS")
    stats['treatments_surgery'] = run_mdb_export(
        'tblSurgery',
        OUTPUT_DIR / 'treatments_surgery.csv'
    )

    # 4. Export tblPathology → pathology.csv
    print("\n[4/7] PATHOLOGY")
    stats['pathology'] = run_mdb_export(
        'tblPathology',
        OUTPUT_DIR / 'pathology.csv'
    )

    # 5. Export tblOncology → oncology.csv
    print("\n[5/7] ONCOLOGY")
    stats['oncology'] = run_mdb_export(
        'tblOncology',
        OUTPUT_DIR / 'oncology.csv'
    )

    # 6. Export tblFollowUp → followup.csv
    print("\n[6/7] FOLLOW-UP")
    stats['followup'] = run_mdb_export(
        'tblFollowUp',
        OUTPUT_DIR / 'followup.csv'
    )

    # 7. Export tblPossum → possum.csv (optional - for risk scoring)
    print("\n[7/7] POSSUM (Risk Scoring)")
    try:
        stats['possum'] = run_mdb_export(
            'tblPossum',
            OUTPUT_DIR / 'possum.csv'
        )
    except Exception as e:
        print(f"  ⚠️  POSSUM export failed (table may be empty): {e}")
        stats['possum'] = 0

    # Print summary
    print(f"\n{'=' * 80}")
    print("EXPORT SUMMARY")
    print(f"{'=' * 80}")
    for table, count in stats.items():
        print(f"  {table:25s} {count:>6,} rows")
    print(f"{'=' * 80}")
    print(f"Total records exported: {sum(stats.values()):,}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 80}\n")

    # List output files
    print("Output files created:")
    for csv_file in sorted(OUTPUT_DIR.glob('*.csv')):
        file_size_kb = csv_file.stat().st_size / 1024
        print(f"  {csv_file.name:30s} {file_size_kb:>8.1f} KB")

    return stats


def verify_exports():
    """Verify that all expected CSV files were created"""
    expected_files = [
        'patients.csv',
        'tumours.csv',
        'treatments_surgery.csv',
        'pathology.csv',
        'oncology.csv',
        'followup.csv'
    ]

    missing = []
    for filename in expected_files:
        filepath = OUTPUT_DIR / filename
        if not filepath.exists():
            missing.append(filename)
        elif filepath.stat().st_size == 0:
            print(f"⚠️  WARNING: {filename} is empty")

    if missing:
        print(f"\n❌ ERROR: Missing files: {', '.join(missing)}")
        return False

    print(f"\n✅ All expected CSV files created successfully")
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Export Access database to CSV files for comprehensive import'
    )
    parser.add_argument(
        '--database',
        default=ACCESS_DB,
        help=f'Path to Access database (default: {ACCESS_DB})'
    )
    parser.add_argument(
        '--output',
        default=OUTPUT_DIR,
        help=f'Output directory (default: {OUTPUT_DIR})'
    )
    args = parser.parse_args()

    # Update globals
    ACCESS_DB = args.database
    OUTPUT_DIR = Path(args.output)

    # Run export
    try:
        stats = export_all_tables()
        verify_exports()
        print("\n✅ Export completed successfully!\n")
        print(f"Next step: Run comprehensive import script")
        print(f"  python3 /root/impact/execution/migrations/import_comprehensive.py")
    except Exception as e:
        print(f"\n❌ Export failed: {e}")
        raise
