#!/bin/bash
# Export Access database tables to CSV using mdbtools
# Run this script if you have an Access .mdb or .accdb file

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <path_to_access_database.mdb>"
    echo ""
    echo "This script exports all tables from an Access database to CSV files"
    echo "Output directory: ~/.tmp/access_export/"
    echo ""
    echo "Requirements: mdbtools (sudo apt-get install mdbtools)"
    exit 1
fi

ACCESS_DB="$1"
OUTPUT_DIR="$HOME/.tmp/access_export"

# Check if file exists
if [ ! -f "$ACCESS_DB" ]; then
    echo "ERROR: File not found: $ACCESS_DB"
    exit 1
fi

# Check if mdbtools is installed
if ! command -v mdb-tables &> /dev/null; then
    echo "ERROR: mdbtools not installed"
    echo "Install with: sudo apt-get install mdbtools"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"
echo "Creating CSV exports in: $OUTPUT_DIR"
echo ""

# List all tables
echo "Tables found in database:"
mdb-tables -1 "$ACCESS_DB"
echo ""

# Export each table to CSV
for table in $(mdb-tables -1 "$ACCESS_DB"); do
    output_file="$OUTPUT_DIR/${table}.csv"
    echo "Exporting table: $table -> ${table}.csv"
    mdb-export "$ACCESS_DB" "$table" > "$output_file"
    
    # Show row count
    row_count=$(tail -n +2 "$output_file" | wc -l)
    echo "  ✓ Exported $row_count rows"
done

echo ""
echo "Export complete!"
echo "Files saved to: $OUTPUT_DIR"
echo ""
echo "Next steps:"
echo "  1. Review the CSV files in $OUTPUT_DIR"
echo "  2. Identify which tables correspond to patients, surgeries, tumours, etc."
echo "  3. Rename files if needed (e.g., 'tblPatients.csv' -> 'patients.csv')"
echo "  4. Run migration: python execution/migrate_access_to_mongodb.py --csv-dir $OUTPUT_DIR --dry-run"
