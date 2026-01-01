#!/usr/bin/env python3
"""
Analyze patient age distribution by year, grouped into 5-year blocks starting from age 20.

This script:
1. Connects to the MongoDB database
2. Extracts patient ages and their episode referral dates
3. Groups ages into 5-year blocks (20-24, 25-29, 30-34, etc.)
4. Creates a breakdown by year showing patient counts per age group
5. Outputs results to CSV and displays summary statistics
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


def analyze_age_distribution():
    """
    Analyze patient age distribution by year across the entire dataset.
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
    print("PATIENT AGE DISTRIBUTION ANALYSIS")
    print("=" * 80)
    print(f"\nAnalysis started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nConnecting to database...")

    # Get all patients
    patients = list(db.patients.find({}, {
        "patient_id": 1,
        "demographics.age": 1,
        "demographics.date_of_birth": 1
    }))

    print(f"Total patients in database: {len(patients)}")

    # Get all episodes with referral dates
    episodes = list(db.episodes.find({}, {
        "patient_id": 1,
        "referral_date": 1,
        "episode_id": 1
    }))

    print(f"Total episodes in database: {len(episodes)}")

    # Build patient age lookup
    patient_ages = {}
    age_unknown_count = 0

    for patient in patients:
        patient_id = patient.get("patient_id")
        demographics = patient.get("demographics", {})
        age = demographics.get("age")

        if age is not None:
            patient_ages[patient_id] = age
        else:
            age_unknown_count += 1

    print(f"Patients with known age: {len(patient_ages)}")
    print(f"Patients with unknown age: {age_unknown_count}")

    # Track age distribution by year
    # Structure: year_data[year][age_group] = count
    year_data = defaultdict(lambda: defaultdict(int))
    episodes_with_no_date = 0
    episodes_with_no_patient = 0

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

        # Extract year from referral_date
        try:
            if isinstance(referral_date, str):
                # Parse string date (YYYY-MM-DD format)
                year = int(referral_date[:4])
            else:
                # datetime object
                year = referral_date.year
        except (ValueError, AttributeError, TypeError):
            episodes_with_no_date += 1
            continue

        # Get patient age
        age = patient_ages.get(patient_id)
        age_group = get_age_group(age)

        # Increment count
        year_data[year][age_group] += 1

    print(f"\nEpisodes without referral date: {episodes_with_no_date}")
    print(f"Episodes without patient ID: {episodes_with_no_patient}")

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
    print("AGE DISTRIBUTION BY YEAR (5-Year Age Groups)")
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

    csv_file = output_dir / "age_distribution_by_year.csv"

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
    print("\nTop 5 Age Groups (Overall):")
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

    print("\n" + "=" * 80)
    print(f"Analysis completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    client.close()


if __name__ == "__main__":
    analyze_age_distribution()
