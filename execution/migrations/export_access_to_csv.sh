#!/bin/bash
#
# Export Access Database to CSV Files
#
# This script exports tables from the Access database (acpdata_v3_db.mdb)
# to CSV format for import into IMPACT MongoDB.
#
# Prerequisites:
#   - mdb-tools package installed (apt-get install mdb-tools)
#   - Access database at /root/impact/data/acpdata_v3_db.mdb
#
# Output:
#   CSV files in ~/.tmp/access_export_mapped/
#

set -e  # Exit on error

# Configuration
ACCESS_DB="/root/impact/data/acpdata_v3_db.mdb"
OUTPUT_DIR="$HOME/.tmp/access_export_mapped"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Access DB → CSV Export"
echo "=========================================="
echo

# Check if Access DB exists
if [ ! -f "$ACCESS_DB" ]; then
    echo -e "${RED}ERROR: Access database not found at: $ACCESS_DB${NC}"
    exit 1
fi

echo -e "${GREEN}Access DB found: $ACCESS_DB${NC}"

# Check if mdb-tools is installed
if ! command -v mdb-export &> /dev/null; then
    echo -e "${RED}ERROR: mdb-tools not installed${NC}"
    echo "Install with: sudo apt-get install mdb-tools"
    exit 1
fi

echo -e "${GREEN}mdb-tools installed${NC}"
echo

# Create output directory
mkdir -p "$OUTPUT_DIR"
echo -e "${GREEN}Output directory: $OUTPUT_DIR${NC}"
echo

# Tables to export
TABLES=(
    "tblPatient"
    "Table1"
    "tblTumour"
    "tblSurgery"
    "tblPathology"
    "tblOncology"
    "tblFollowUp"
)

# Export each table
for table in "${TABLES[@]}"; do
    output_file="$OUTPUT_DIR/${table}.csv"

    echo -e "${YELLOW}Exporting table: $table${NC}"

    # Check if table exists (mdb-tables outputs space-separated list)
    if ! mdb-tables "$ACCESS_DB" | grep -qw "$table"; then
        echo -e "${RED}  ⚠️  Table not found in database, skipping${NC}"
        continue
    fi

    # Export to CSV
    if mdb-export "$ACCESS_DB" "$table" > "$output_file"; then
        # Count rows (subtract 1 for header)
        row_count=$(($(wc -l < "$output_file") - 1))
        echo -e "${GREEN}  ✅ Exported $row_count rows to: $output_file${NC}"
    else
        echo -e "${RED}  ❌ Export failed${NC}"
        exit 1
    fi
    echo
done

echo "=========================================="
echo "Export Complete"
echo "=========================================="
echo
echo "CSV files created in: $OUTPUT_DIR"
echo
echo "Next step:"
echo "  python3 execution/migrations/import_from_access_mapped.py"
echo
