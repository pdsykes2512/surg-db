#!/usr/bin/env python3
"""
Compare the new 'impact' database against current production database.
Provides detailed quality metrics and data completeness analysis.
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime
import json

# Load secrets
load_dotenv('/etc/impact/secrets.env')
load_dotenv('.env')

class DatabaseComparison:
    def __init__(self, db1_name: str, db2_name: str):
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            raise ValueError("MONGODB_URI not found in environment")

        self.client = MongoClient(mongodb_uri)
        self.db1 = self.client[db1_name]
        self.db2 = self.client[db2_name]
        self.db1_name = db1_name
        self.db2_name = db2_name

    def count_documents(self, db, collection_name):
        """Count documents in a collection"""
        return db[collection_name].count_documents({})

    def analyze_field_coverage(self, db, collection_name, fields):
        """Analyze how many documents have non-null values for specific fields"""
        collection = db[collection_name]
        total = collection.count_documents({})

        coverage = {}
        for field in fields:
            # Handle nested fields (e.g., 'demographics.first_name')
            if '.' in field:
                query = {field: {"$exists": True, "$ne": None, "$ne": ""}}
            else:
                query = {field: {"$exists": True, "$ne": None, "$ne": ""}}

            count = collection.count_documents(query)
            coverage[field] = {
                'count': count,
                'percentage': (count / total * 100) if total > 0 else 0
            }

        return coverage

    def sample_records(self, db, collection_name, limit=5):
        """Get sample records from a collection"""
        return list(db[collection_name].find({}).limit(limit))

    def compare_patient_data(self):
        """Compare patient collections"""
        print("\n" + "="*80)
        print("PATIENT DATA COMPARISON")
        print("="*80)

        db1_count = self.count_documents(self.db1, 'patients')
        db2_count = self.count_documents(self.db2, 'patients')

        print(f"\n{'Database':<30} {'Count':>15}")
        print("-" * 47)
        print(f"{self.db1_name:<30} {db1_count:>15,}")
        print(f"{self.db2_name:<30} {db2_count:>15,}")
        print(f"{'Difference':<30} {abs(db1_count - db2_count):>15,}")

        # Analyze field coverage
        patient_fields = [
            'mrn',
            'nhs_number',
            'hospital_number',
            'demographics.first_name',
            'demographics.last_name',
            'demographics.date_of_birth',
            'demographics.age',
            'demographics.gender',
            'contact.postcode',
        ]

        print(f"\n{'Field Coverage':^80}")
        print("="*80)
        print(f"{'Field':<35} {self.db1_name:>20} {self.db2_name:>20}")
        print("-" * 80)

        db1_coverage = self.analyze_field_coverage(self.db1, 'patients', patient_fields)
        db2_coverage = self.analyze_field_coverage(self.db2, 'patients', patient_fields)

        for field in patient_fields:
            db1_pct = db1_coverage[field]['percentage']
            db2_pct = db2_coverage[field]['percentage']
            diff_indicator = "✓" if abs(db1_pct - db2_pct) < 5 else "⚠"
            print(f"{field:<35} {db1_pct:>18.1f}% {db2_pct:>18.1f}% {diff_indicator:>3}")

    def compare_episode_data(self):
        """Compare episode collections"""
        print("\n" + "="*80)
        print("EPISODE DATA COMPARISON")
        print("="*80)

        db1_count = self.count_documents(self.db1, 'episodes')
        db2_count = self.count_documents(self.db2, 'episodes')

        print(f"\n{'Database':<30} {'Count':>15}")
        print("-" * 47)
        print(f"{self.db1_name:<30} {db1_count:>15,}")
        print(f"{self.db2_name:<30} {db2_count:>15,}")
        print(f"{'Difference':<30} {abs(db1_count - db2_count):>15,}")

        # Analyze field coverage
        episode_fields = [
            'patient_id',
            'cancer_type',
            'referral_date',
            'first_seen_date',
            'lead_clinician',
            'mdt_date',
            'tumour_site',
            'histology',
        ]

        print(f"\n{'Field Coverage':^80}")
        print("="*80)
        print(f"{'Field':<35} {self.db1_name:>20} {self.db2_name:>20}")
        print("-" * 80)

        db1_coverage = self.analyze_field_coverage(self.db1, 'episodes', episode_fields)
        db2_coverage = self.analyze_field_coverage(self.db2, 'episodes', episode_fields)

        for field in episode_fields:
            db1_pct = db1_coverage[field]['percentage']
            db2_pct = db2_coverage[field]['percentage']
            diff_indicator = "✓" if abs(db1_pct - db2_pct) < 5 else "⚠"
            print(f"{field:<35} {db1_pct:>18.1f}% {db2_pct:>18.1f}% {diff_indicator:>3}")

    def compare_treatment_data(self):
        """Compare treatment collections"""
        print("\n" + "="*80)
        print("TREATMENT DATA COMPARISON")
        print("="*80)

        db1_count = self.count_documents(self.db1, 'treatments')
        db2_count = self.count_documents(self.db2, 'treatments')

        print(f"\n{'Database':<30} {'Count':>15}")
        print("-" * 47)
        print(f"{self.db1_name:<30} {db1_count:>15,}")
        print(f"{self.db2_name:<30} {db2_count:>15,}")
        print(f"{'Difference':<30} {abs(db1_count - db2_count):>15,}")

        # Count by treatment type
        print("\nTreatment Type Breakdown:")
        print("-" * 80)

        for db_name, db in [(self.db1_name, self.db1), (self.db2_name, self.db2)]:
            pipeline = [
                {"$group": {"_id": "$treatment_type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            types = list(db.treatments.aggregate(pipeline))
            print(f"\n{db_name}:")
            for item in types:
                print(f"  {item['_id'] or 'None':<25} {item['count']:>10,}")

        # Analyze field coverage
        treatment_fields = [
            'treatment_type',
            'treatment_date',
            'surgeon',
            'surgery_type',
            'approach',
            'complications',
            'length_of_stay',
        ]

        print(f"\n{'Field Coverage':^80}")
        print("="*80)
        print(f"{'Field':<35} {self.db1_name:>20} {self.db2_name:>20}")
        print("-" * 80)

        db1_coverage = self.analyze_field_coverage(self.db1, 'treatments', treatment_fields)
        db2_coverage = self.analyze_field_coverage(self.db2, 'treatments', treatment_fields)

        for field in treatment_fields:
            db1_pct = db1_coverage[field]['percentage']
            db2_pct = db2_coverage[field]['percentage']
            diff_indicator = "✓" if abs(db1_pct - db2_pct) < 5 else "⚠"
            print(f"{field:<35} {db1_pct:>18.1f}% {db2_pct:>18.1f}% {diff_indicator:>3}")

    def compare_tumour_data(self):
        """Compare tumour collections"""
        print("\n" + "="*80)
        print("TUMOUR DATA COMPARISON")
        print("="*80)

        db1_count = self.count_documents(self.db1, 'tumours')
        db2_count = self.count_documents(self.db2, 'tumours')

        print(f"\n{'Database':<30} {'Count':>15}")
        print("-" * 47)
        print(f"{self.db1_name:<30} {db1_count:>15,}")
        print(f"{self.db2_name:<30} {db2_count:>15,}")
        print(f"{'Difference':<30} {abs(db1_count - db2_count):>15,}")

        # Analyze field coverage
        tumour_fields = [
            'site',
            'histology',
            'grade',
            'pathological_t_stage',
            'pathological_n_stage',
            'pathological_m_stage',
            'nodes_examined',
            'nodes_positive',
            'crm_involved',
        ]

        print(f"\n{'Field Coverage':^80}")
        print("="*80)
        print(f"{'Field':<35} {self.db1_name:>20} {self.db2_name:>20}")
        print("-" * 80)

        db1_coverage = self.analyze_field_coverage(self.db1, 'tumours', tumour_fields)
        db2_coverage = self.analyze_field_coverage(self.db2, 'tumours', tumour_fields)

        for field in tumour_fields:
            db1_pct = db1_coverage[field]['percentage']
            db2_pct = db2_coverage[field]['percentage']
            diff_indicator = "✓" if abs(db1_pct - db2_pct) < 5 else "⚠"
            print(f"{field:<35} {db1_pct:>18.1f}% {db2_pct:>18.1f}% {diff_indicator:>3}")

    def check_data_integrity(self):
        """Check data integrity (referential integrity, ID consistency)"""
        print("\n" + "="*80)
        print("DATA INTEGRITY CHECKS")
        print("="*80)

        for db_name, db in [(self.db1_name, self.db1), (self.db2_name, self.db2)]:
            print(f"\n{db_name}:")
            print("-" * 80)

            # Check for orphaned episodes (episodes without valid patient_id)
            total_episodes = db.episodes.count_documents({})
            orphaned_episodes = 0
            for episode in db.episodes.find({}, {'patient_id': 1}):
                patient = db.patients.find_one({'patient_id': episode.get('patient_id')})
                if not patient:
                    orphaned_episodes += 1

            print(f"Episodes: {total_episodes:,}")
            print(f"Orphaned episodes (no matching patient): {orphaned_episodes:,}")

            # Check for orphaned treatments
            total_treatments = db.treatments.count_documents({})
            orphaned_treatments = 0
            for treatment in db.treatments.find({}, {'patient_id': 1, 'episode_id': 1}):
                patient = db.patients.find_one({'patient_id': treatment.get('patient_id')})
                episode = db.episodes.find_one({'episode_id': treatment.get('episode_id')})
                if not patient or not episode:
                    orphaned_treatments += 1

            print(f"Treatments: {total_treatments:,}")
            print(f"Orphaned treatments (no matching patient/episode): {orphaned_treatments:,}")

            # Check for orphaned tumours
            total_tumours = db.tumours.count_documents({})
            orphaned_tumours = 0
            for tumour in db.tumours.find({}, {'patient_id': 1, 'episode_id': 1}):
                patient = db.patients.find_one({'patient_id': tumour.get('patient_id')})
                episode = db.episodes.find_one({'episode_id': tumour.get('episode_id')})
                if not patient or not episode:
                    orphaned_tumours += 1

            print(f"Tumours: {total_tumours:,}")
            print(f"Orphaned tumours (no matching patient/episode): {orphaned_tumours:,}")

    def check_age_data(self):
        """Check for age data quality issues"""
        print("\n" + "="*80)
        print("AGE DATA QUALITY CHECK")
        print("="*80)

        for db_name, db in [(self.db1_name, self.db1), (self.db2_name, self.db2)]:
            print(f"\n{db_name}:")
            print("-" * 80)

            # Check for negative ages
            negative_ages = db.patients.count_documents({'demographics.age': {'$lt': 0}})

            # Check for ages > 120
            unrealistic_ages = db.patients.count_documents({'demographics.age': {'$gt': 120}})

            # Check for ages < 10 (unusual for bowel cancer)
            very_young = db.patients.count_documents({'demographics.age': {'$lt': 10, '$gte': 0}})

            # Check for missing ages
            missing_ages = db.patients.count_documents({
                '$or': [
                    {'demographics.age': {'$exists': False}},
                    {'demographics.age': None}
                ]
            })

            total = db.patients.count_documents({})

            print(f"Total patients: {total:,}")
            print(f"Negative ages: {negative_ages:,} ({negative_ages/total*100 if total > 0 else 0:.1f}%)")
            print(f"Ages > 120: {unrealistic_ages:,} ({unrealistic_ages/total*100 if total > 0 else 0:.1f}%)")
            print(f"Ages < 10: {very_young:,} ({very_young/total*100 if total > 0 else 0:.1f}%)")
            print(f"Missing ages: {missing_ages:,} ({missing_ages/total*100 if total > 0 else 0:.1f}%)")

            if negative_ages == 0 and unrealistic_ages == 0:
                print("✓ Age data quality: GOOD")
            else:
                print("⚠ Age data quality: NEEDS ATTENTION")

    def generate_summary(self):
        """Generate overall summary and recommendations"""
        print("\n" + "="*80)
        print("SUMMARY AND RECOMMENDATIONS")
        print("="*80)

        db1_totals = {
            'patients': self.count_documents(self.db1, 'patients'),
            'episodes': self.count_documents(self.db1, 'episodes'),
            'treatments': self.count_documents(self.db1, 'treatments'),
            'tumours': self.count_documents(self.db1, 'tumours'),
        }

        db2_totals = {
            'patients': self.count_documents(self.db2, 'patients'),
            'episodes': self.count_documents(self.db2, 'episodes'),
            'treatments': self.count_documents(self.db2, 'treatments'),
            'tumours': self.count_documents(self.db2, 'tumours'),
        }

        print(f"\n{self.db1_name} totals:")
        for key, value in db1_totals.items():
            print(f"  {key:.<25} {value:>10,}")

        print(f"\n{self.db2_name} totals:")
        for key, value in db2_totals.items():
            print(f"  {key:.<25} {value:>10,}")

        print("\nKey Differences:")
        for key in db1_totals:
            diff = db2_totals[key] - db1_totals[key]
            pct_diff = (diff / db1_totals[key] * 100) if db1_totals[key] > 0 else 0
            sign = "+" if diff >= 0 else ""
            print(f"  {key:.<25} {sign}{diff:>10,} ({sign}{pct_diff:>6.1f}%)")

        print("\nRecommendations:")

        # Check if new import has more data
        if db2_totals['patients'] >= db1_totals['patients']:
            print("  ✓ New import has equal or more patient records")
        else:
            print(f"  ⚠ New import has FEWER patient records (-{db1_totals['patients'] - db2_totals['patients']:,})")

        # Check episode count
        if db2_totals['episodes'] >= db1_totals['episodes'] * 0.95:
            print("  ✓ Episode count is within expected range")
        else:
            print(f"  ⚠ Episode count significantly lower in new import")

        # Check treatment count
        if db2_totals['treatments'] >= db1_totals['treatments'] * 0.95:
            print("  ✓ Treatment count is within expected range")
        else:
            print(f"  ⚠ Treatment count significantly lower in new import")

        print("\n" + "="*80)


def main():
    print("\n" + "="*80)
    print("DATABASE COMPARISON TOOL")
    print("="*80)

    # Get production database name from environment
    prod_db = os.getenv('MONGODB_DB_NAME', 'surgdb')
    new_db = 'impact'

    print(f"\nComparing:")
    print(f"  Production: {prod_db}")
    print(f"  New Import: {new_db}")

    comparer = DatabaseComparison(prod_db, new_db)

    # Run all comparisons
    comparer.compare_patient_data()
    comparer.compare_episode_data()
    comparer.compare_treatment_data()
    comparer.compare_tumour_data()
    comparer.check_data_integrity()
    comparer.check_age_data()
    comparer.generate_summary()

    print("\n" + "="*80)
    print("Comparison complete!")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
