#!/usr/bin/env python3
"""
Analyze patient age AT DIAGNOSIS by year, grouped into 5-year blocks starting from age 20.

This script:
1. Connects to the MongoDB database
2. Calculates patient age AT THE TIME OF REFERRAL (not current age)
3. Groups ages into 5-year blocks (20-24, 25-29, 30-34, etc.)
4. Creates a breakdown by year showing patient counts per age group
5. Outputs results to CSV and displays summary statistics

IMPORTANT: This calculates age at diagnosis, not current age.
"""

import os
import sys
from datetime import datetime
from collections import defaultdict
from pathlib import Path
import csv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_age_group(age):
    """
    Convert age to 5-year block starting from 20.

    Args:
        age: Patient age (integer)

    Returns:
        String representing age group (e.g., "20-24", "25-29")
        Returns "Under 20" for ages < 20
        Returns "Unknown" for None/invalid ages
    """
    if age is None:
        return "Unknown"

    try:
        age = int(age)
    except (ValueError, TypeError):
        return "Unknown"

    if age < 20:
        return "Under 20"

    # Calculate 5-year block
    lower_bound = (age // 5) * 5
    upper_bound = lower_bound + 4

    return f"{lower_bound}-{upper_bound}"


def parse_date(date_value):
    """
    Parse a date value that could be string or datetime object.

    Args:
        date_value: Either a string (YYYY-MM-DD) or datetime object

    Returns:
        datetime object or None if parsing fails
    """
    if date_value is None:
        return None

    # Already a datetime
    if hasattr(date_value, 'year'):
        return date_value

    # Try parsing string
    if isinstance(date_value, str):
        try:
            # Try YYYY-MM-DD format
            return datetime.strptime(date_value[:10], '%Y-%m-%d')
        except (ValueError, AttributeError):
            pass

    return None


def calculate_age_at_date(current_age, current_date, reference_date):
    """
    Calculate age at a specific reference date using current age and working backwards.

    Since DOB is encrypted in the database, we use the patient's current age
    and calculate backwards to find their age at the reference date.

    Args:
        current_age: Patient's current age (integer)
        current_date: Date when current_age was calculated (datetime)
        reference_date: Date to calculate age for (string YYYY-MM-DD or datetime)

    Returns:
        Age in years (integer) or None if calculation fails
    """
    if current_age is None:
        return None

    ref_dt = parse_date(reference_date)

    if ref_dt is None or current_date is None:
        return None

    # Calculate years difference
    years_diff = current_date.year - ref_dt.year

    # Age at reference date = current age - years difference
    age_at_ref = current_age - years_diff

    return age_at_ref


def analyze_age_at_diagnosis():
    """
    Analyze patient age AT DIAGNOSIS by year across the entire dataset.
    Groups ages into 5-year blocks starting from age 20.
    """

    # Connect to MongoDB
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        print("Error: MONGODB_URI not found in environment variables")
        sys.exit(1)

    client = MongoClient(mongodb_uri)
    db = client.impact

    print("=" * 80)
    print("PATIENT AGE AT DIAGNOSIS ANALYSIS")
    print("=" * 80)
    print(f"\nAnalysis started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nConnecting to database...")

    # Get all patients
    # Note: DOB is encrypted, so we'll use current age and updated_at to calculate backwards
    patients = list(db.patients.find({}, {
        "patient_id": 1,
        "demographics.age": 1,
        "updated_at": 1
    }))

    print(f"Total patients in database: {len(patients)}")

    # Build patient age lookup
    # Store: (current_age, date_when_age_calculated)
    patient_ages = {}
    age_missing_count = 0

    # Use a reference date for age calculation (when ages were last updated)
    # We'll use 2026-01-01 as the reference (today)
    age_calculation_date = datetime(2026, 1, 1)

    for patient in patients:
        patient_id = patient.get("patient_id")
        demographics = patient.get("demographics", {})
        current_age = demographics.get("age")

        if current_age is not None:
            patient_ages[patient_id] = (current_age, age_calculation_date)
        else:
            age_missing_count += 1

    print(f"Patients with age: {len(patient_ages)}")
    print(f"Patients without age: {age_missing_count}")
    print(f"Age calculation reference date: {age_calculation_date.strftime('%Y-%m-%d')}")

    # Get all episodes with referral dates
    episodes = list(db.episodes.find({}, {
        "patient_id": 1,
        "referral_date": 1,
        "episode_id": 1
    }))

    print(f"Total episodes in database: {len(episodes)}")

    # Track age distribution by year
    # Structure: year_data[year][age_group] = count
    year_data = defaultdict(lambda: defaultdict(int))
    episodes_processed = 0
    episodes_with_no_date = 0
    episodes_with_no_patient = 0
    episodes_with_no_age = 0
    episodes_with_invalid_age = 0

    for episode in episodes:
        patient_id = episode.get("patient_id")
        referral_date = episode.get("referral_date")

        # Skip if no patient_id
        if not patient_id:
            episodes_with_no_patient += 1
            continue

        # Skip if no referral date
        if not referral_date:
            episodes_with_no_date += 1
            continue

        # Get patient age data
        age_data = patient_ages.get(patient_id)
        if not age_data:
            episodes_with_no_age += 1
            continue

        current_age, age_calc_date = age_data

        # Calculate age at referral
        age_at_referral = calculate_age_at_date(current_age, age_calc_date, referral_date)

        if age_at_referral is None:
            episodes_with_invalid_age += 1
            continue

        # Sanity check: age should be reasonable
        if age_at_referral < 0 or age_at_referral > 120:
            episodes_with_invalid_age += 1
            continue

        # Extract year from referral_date
        try:
            ref_dt = parse_date(referral_date)
            if ref_dt:
                year = ref_dt.year
            else:
                episodes_with_no_date += 1
                continue
        except (ValueError, AttributeError, TypeError):
            episodes_with_no_date += 1
            continue

        # Get age group
        age_group = get_age_group(age_at_referral)

        # Increment count
        year_data[year][age_group] += 1
        episodes_processed += 1

    print(f"\nEpisodes processed successfully: {episodes_processed}")
    print(f"Episodes without referral date: {episodes_with_no_date}")
    print(f"Episodes without patient ID: {episodes_with_no_patient}")
    print(f"Episodes without patient age: {episodes_with_no_age}")
    print(f"Episodes with invalid age calculation: {episodes_with_invalid_age}")

    # Get all unique age groups and sort them
    all_age_groups = set()
    for year_groups in year_data.values():
        all_age_groups.update(year_groups.keys())

    # Sort age groups
    def age_group_sort_key(group):
        """Sort key for age groups"""
        if group == "Unknown":
            return (999, 0)
        elif group == "Under 20":
            return (0, 0)
        else:
            # Extract lower bound from "XX-YY"
            try:
                lower = int(group.split('-')[0])
                return (1, lower)
            except:
                return (999, 0)

    sorted_age_groups = sorted(all_age_groups, key=age_group_sort_key)

    # Get sorted years
    sorted_years = sorted(year_data.keys())

    # Print summary by year
    print("\n" + "=" * 80)
    print("AGE AT DIAGNOSIS BY YEAR (5-Year Age Groups)")
    print("=" * 80)

    # Print header
    header = ["Year"] + sorted_age_groups + ["Total"]
    col_widths = [6] + [max(12, len(group) + 2) for group in sorted_age_groups] + [8]

    header_line = ""
    for i, col in enumerate(header):
        header_line += col.ljust(col_widths[i])
    print("\n" + header_line)
    print("-" * len(header_line))

    # Print data rows
    for year in sorted_years:
        row = [str(year)]
        year_total = 0

        for age_group in sorted_age_groups:
            count = year_data[year][age_group]
            row.append(str(count) if count > 0 else "-")
            year_total += count

        row.append(str(year_total))

        row_line = ""
        for i, val in enumerate(row):
            row_line += val.ljust(col_widths[i])
        print(row_line)

    # Print totals row
    print("-" * len(header_line))
    totals_row = ["TOTAL"]
    grand_total = 0

    for age_group in sorted_age_groups:
        group_total = sum(year_data[year][age_group] for year in sorted_years)
        totals_row.append(str(group_total))
        grand_total += group_total

    totals_row.append(str(grand_total))

    row_line = ""
    for i, val in enumerate(totals_row):
        row_line += val.ljust(col_widths[i])
    print(row_line)

    # Export to CSV
    output_dir = Path("/root/impact/.tmp")
    output_dir.mkdir(exist_ok=True)

    csv_file = output_dir / "age_at_diagnosis_by_year.csv"

    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow(header)

        # Write data rows
        for year in sorted_years:
            row = [str(year)]
            year_total = 0

            for age_group in sorted_age_groups:
                count = year_data[year][age_group]
                row.append(count)
                year_total += count

            row.append(year_total)
            writer.writerow(row)

        # Write totals
        writer.writerow(totals_row)

    print(f"\n✅ Results exported to: {csv_file}")

    # Print summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"\nTotal episodes analyzed: {grand_total}")
    print(f"Years covered: {min(sorted_years)} - {max(sorted_years)}")
    print(f"Number of years: {len(sorted_years)}")

    # Most common age groups
    print("\nTop 5 Age Groups at Diagnosis (Overall):")
    age_group_totals = []
    for age_group in sorted_age_groups:
        if age_group not in ["Unknown"]:
            total = sum(year_data[year][age_group] for year in sorted_years)
            age_group_totals.append((age_group, total))

    age_group_totals.sort(key=lambda x: x[1], reverse=True)

    for i, (age_group, total) in enumerate(age_group_totals[:5], 1):
        percentage = (total / grand_total) * 100 if grand_total > 0 else 0
        print(f"  {i}. {age_group}: {total} episodes ({percentage:.1f}%)")

    # Year with most episodes
    year_totals = [(year, sum(year_data[year].values())) for year in sorted_years]
    year_totals.sort(key=lambda x: x[1], reverse=True)

    print(f"\nYear with most episodes: {year_totals[0][0]} ({year_totals[0][1]} episodes)")

    # Age statistics
    all_ages = []
    for year in year_data:
        for age_group in year_data[year]:
            if age_group not in ["Unknown", "Under 20"]:
                try:
                    # Get midpoint of age range
                    lower = int(age_group.split('-')[0])
                    midpoint = lower + 2  # Midpoint of 5-year range
                    count = year_data[year][age_group]
                    all_ages.extend([midpoint] * count)
                except:
                    pass

    if all_ages:
        mean_age = sum(all_ages) / len(all_ages)
        all_ages.sort()
        median_age = all_ages[len(all_ages) // 2]

        print(f"\nApproximate mean age at diagnosis: {mean_age:.1f} years")
        print(f"Approximate median age at diagnosis: {median_age} years")

    print("\n" + "=" * 80)
    print(f"Analysis completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    client.close()


if __name__ == "__main__":
    analyze_age_at_diagnosis()
