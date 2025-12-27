#!/usr/bin/env python3
"""
Export selective fields from Access database acpdata_v3_db.mdb to CSV
Only extracts fields needed for MongoDB migration
"""
import subprocess
import os
import csv
from pathlib import Path

# Output directory
OUTPUT_DIR = Path.home() / ".tmp" / "access_export"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ACCESS_DB = "./acpdb/acpdata_v3_db.mdb"

print(f"Exporting selective fields from {ACCESS_DB}")
print(f"Output directory: {OUTPUT_DIR}")
print("=" * 60)

def export_table(table_name, output_file):
    """Export full table to CSV"""
    print(f"\nExporting {table_name}...")
    output_path = OUTPUT_DIR / output_file
    
    cmd = ["mdb-export", ACCESS_DB, table_name]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        with open(output_path, 'w') as f:
            f.write(result.stdout)
        
        # Count rows
        with open(output_path, 'r') as f:
            row_count = sum(1 for line in f) - 1  # Exclude header
        
        print(f"✓ Exported {row_count} rows to {output_file}")
        return True
    else:
        print(f"✗ Error exporting {table_name}: {result.stderr}")
        return False

def filter_csv_columns(input_file, output_file, columns_to_keep):
    """Filter CSV to keep only specified columns"""
    input_path = OUTPUT_DIR / input_file
    output_path = OUTPUT_DIR / output_file
    
    print(f"Filtering {input_file} to keep only: {', '.join(columns_to_keep)}")
    
    with open(input_path, 'r') as infile, open(output_path, 'w', newline='') as outfile:
        reader = csv.DictReader(infile)
        
        # Check which columns exist
        available_cols = [col for col in columns_to_keep if col in reader.fieldnames]
        missing_cols = [col for col in columns_to_keep if col not in reader.fieldnames]
        
        if missing_cols:
            print(f"  Warning: Columns not found: {', '.join(missing_cols)}")
        
        writer = csv.DictWriter(outfile, fieldnames=available_cols)
        writer.writeheader()
        
        count = 0
        for row in reader:
            filtered_row = {col: row.get(col, '') for col in available_cols}
            writer.writerow(filtered_row)
            count += 1
        
        print(f"✓ Filtered to {count} rows with {len(available_cols)} columns")

# 1. Export tblPatient (full, then filter)
if export_table("tblPatient", "tblPatient_full.csv"):
    filter_csv_columns(
        "tblPatient_full.csv",
        "patients.csv",
        [
            "Hosp_No",      # Hospital number (key)
            "NHS_No",       # NHS number
            "P_DOB",        # Date of birth
            "Sex",          # Gender
            "Postcode",     # Postcode
            "Height",       # Height
            "Weight",       # Weight
            "BMI",          # BMI
        ]
    )

# 2. Export tblSurgery (full, then filter)
if export_table("tblSurgery", "tblSurgery_full.csv"):
    filter_csv_columns(
        "tblSurgery_full.csv",
        "surgeries.csv",
        [
            "Su_SeqNo",     # Surgery sequence number (key)
            "Hosp_No",      # Patient reference
            "TumSeqNo",     # Tumour reference
            "Surgery",      # Surgery date
            "Surgeon",      # Surgeon name
            "SurGrad",      # Surgeon grade
            "ModeOp",       # Mode of operation (lap/open)
            "ProcType",     # Procedure type
            "ProcResect",   # Resection type
            "ProcName",     # Procedure name
            "OPCS4",        # OPCS-4 code
            "ASA",          # ASA grade
            "Curative",     # Curative intent
            "Date_Dis",     # Discharge date
            "LapProc",      # Laparoscopic procedure
            "Convert",      # Conversion
        ]
    )

# 3. Export tblTumour (full, then filter)
if export_table("tblTumour", "tblTumour_full.csv"):
    filter_csv_columns(
        "tblTumour_full.csv",
        "tumours.csv",
        [
            "TumSeqno",     # Tumour sequence number (key)
            "Hosp_No",      # Patient reference
            "Dt_Diag",      # Diagnosis date
            "TumSite",      # Tumour site
            "TumICD10",     # ICD-10 code
            "preTNM_T",     # Pre-treatment T stage
            "preTNM_N",     # Pre-treatment N stage
            "preTNM_M",     # Pre-treatment M stage
            "DM_Liver",     # Distant metastasis - liver
            "DM_Lung",      # Distant metastasis - lung
            "Sync",         # Synchronous tumour
        ]
    )

# 4. Export tblPathology (full, then filter)
if export_table("tblPathology", "tblPathology_full.csv"):
    filter_csv_columns(
        "tblPathology_full.csv",
        "pathology.csv",
        [
            "PthSeqNo",     # Pathology sequence number (key)
            "Hosp_No",      # Patient reference
            "TumSeqNo",     # Tumour reference
            "Hist_Dat",     # Histology date
            "HistType",     # Histology type
            "HistGrad",     # Histology grade
            "TNM_Tumr",     # TNM T stage (pathological)
            "TNM_Nods",     # TNM N stage (pathological)
            "TNM_Mets",     # TNM M stage (pathological)
            "Dukes",        # Dukes stage
            "NoLyNoF",      # Number of lymph nodes found
            "NoLyNoP",      # Number of lymph nodes positive
            "VasInv",       # Vascular invasion
            "resect_grade", # Resection grade (R0/R1/R2)
        ]
    )

print("\n" + "=" * 60)
print("EXPORT COMPLETE")
print("=" * 60)
print(f"\nFiles created in: {OUTPUT_DIR}")
print("\nNext steps:")
print("  1. Review CSV files")
print("  2. Run migration with dry-run:")
print(f"     python execution/migrate_access_to_mongodb.py --csv-dir {OUTPUT_DIR} --dry-run")
print("  3. If dry-run looks good, run actual migration:")
print(f"     python execution/migrate_access_to_mongodb.py --csv-dir {OUTPUT_DIR}")
