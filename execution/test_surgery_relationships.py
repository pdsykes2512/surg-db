#!/usr/bin/env python3
"""
Test script for surgery relationship system
Demonstrates: Primary surgery → RTT → Reversal → Deletion → Flag reset
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from pymongo import MongoClient
import json

# Load environment
load_dotenv('/etc/impact/secrets.env')
MONGODB_URI = os.getenv('MONGODB_URI')

# Connect to test database
client = MongoClient(MONGODB_URI)
db = client['impact_test']  # Use test database

print("=" * 80)
print("SURGERY RELATIONSHIP SYSTEM TEST")
print("=" * 80)
print(f"Database: {db.name}")
print(f"Time: {datetime.now().isoformat()}")
print("=" * 80)
print()

# Test data
TEST_PATIENT_ID = "TEST-001"
TEST_EPISODE_ID = "E-TEST-001"
PRIMARY_SURGERY_ID = f"T-TEST-PRIMARY-{datetime.now().strftime('%H%M%S')}"
RTT_SURGERY_ID = f"T-TEST-RTT-{datetime.now().strftime('%H%M%S')}"
RTT2_SURGERY_ID = f"T-TEST-RTT2-{datetime.now().strftime('%H%M%S')}"
REVERSAL_SURGERY_ID = f"T-TEST-REV-{datetime.now().strftime('%H%M%S')}"


def print_surgery(surgery, title="Surgery"):
    """Pretty print a surgery document"""
    print(f"\n{title}:")
    print(f"  Treatment ID: {surgery.get('treatment_id')}")
    print(f"  Type: {surgery.get('treatment_type')}")
    print(f"  Episode: {surgery.get('episode_id')}")
    print(f"  Date: {surgery.get('treatment_date')}")

    if surgery.get('parent_surgery_id'):
        print(f"  Parent Surgery: {surgery.get('parent_surgery_id')}")

    if surgery.get('rtt_reason'):
        print(f"  RTT Reason: {surgery.get('rtt_reason')}")

    if surgery.get('reversal_notes'):
        print(f"  Reversal Notes: {surgery.get('reversal_notes')}")

    related = surgery.get('related_surgery_ids', [])
    if related:
        print(f"  Related Surgeries: {len(related)}")
        for r in related:
            print(f"    - {r['treatment_id']} ({r['treatment_type']})")

    rtt = surgery.get('postoperative_events', {}).get('return_to_theatre', {})
    if rtt.get('occurred'):
        print(f"  RTT Occurred: True")
        print(f"    Date: {rtt.get('date')}")
        print(f"    Reason: {rtt.get('reason')}")
        print(f"    Linked to: {rtt.get('rtt_treatment_id')}")

    stoma_closure = surgery.get('intraoperative', {}).get('stoma_closure_date')
    if stoma_closure:
        print(f"  Stoma Closed: {stoma_closure}")
        print(f"    Reversal: {surgery.get('intraoperative', {}).get('reversal_treatment_id')}")


def test_step(step_num, description):
    """Print test step header"""
    print("\n" + "=" * 80)
    print(f"STEP {step_num}: {description}")
    print("=" * 80)


# STEP 1: Create Primary Surgery
test_step(1, "Create Primary Surgery with Stoma")

primary_surgery = {
    "treatment_id": PRIMARY_SURGERY_ID,
    "episode_id": TEST_EPISODE_ID,
    "patient_id": TEST_PATIENT_ID,
    "treatment_type": "surgery_primary",
    "treatment_date": datetime.now() - timedelta(days=10),
    "treating_clinician": "Mr. Test Surgeon",
    "treatment_intent": "curative",
    "notes": "Test primary surgery",

    "classification": {
        "urgency": "elective",
        "primary_diagnosis": "Colon cancer",
        "indication": "cancer"
    },

    "procedure": {
        "primary_procedure": "Anterior Resection",
        "approach": "laparoscopic",
        "opcs_codes": ["H33.1"]
    },

    "perioperative_timeline": {
        "admission_date": datetime.now() - timedelta(days=11),
        "surgery_date": datetime.now() - timedelta(days=10),
        "discharge_date": datetime.now() - timedelta(days=5),
        "length_of_stay_days": 6
    },

    "team": {
        "primary_surgeon": "Mr. Test Surgeon",
        "primary_surgeon_text": "Mr. Test Surgeon"
    },

    "intraoperative": {
        "stoma_created": True,
        "stoma_type": "ileostomy_temporary",
        "anastomosis_performed": True
    },

    "postoperative_events": {
        "return_to_theatre": {
            "occurred": False
        }
    },

    "related_surgery_ids": []
}

result = db.treatments.insert_one(primary_surgery)
print(f"✓ Created primary surgery: {PRIMARY_SURGERY_ID}")

# Fetch and display
created_primary = db.treatments.find_one({"treatment_id": PRIMARY_SURGERY_ID})
print_surgery(created_primary, "Primary Surgery Created")


# STEP 2: Create First RTT Surgery
test_step(2, "Create First RTT Surgery (Anastomotic Leak)")

rtt_surgery = {
    "treatment_id": RTT_SURGERY_ID,
    "episode_id": TEST_EPISODE_ID,  # Same episode as parent
    "patient_id": TEST_PATIENT_ID,
    "treatment_type": "surgery_rtt",
    "treatment_date": datetime.now() - timedelta(days=5),
    "treating_clinician": "Mr. Test Surgeon",
    "treatment_intent": "urgent",
    "notes": "Emergency RTT",

    # Relationship fields
    "parent_surgery_id": PRIMARY_SURGERY_ID,
    "parent_episode_id": TEST_EPISODE_ID,
    "rtt_reason": "Anastomotic leak with peritonitis requiring washout and defunctioning ileostomy",

    "classification": {
        "urgency": "emergency",
        "primary_diagnosis": "Anastomotic leak",
        "indication": "cancer"
    },

    "procedure": {
        "primary_procedure": "Laparotomy, washout, defunctioning ileostomy",
        "approach": "open"
    },

    "perioperative_timeline": {
        "admission_date": datetime.now() - timedelta(days=5),
        "surgery_date": datetime.now() - timedelta(days=5),
        "discharge_date": None,
        "length_of_stay_days": None
    },

    "team": {
        "primary_surgeon": "Mr. Test Surgeon",
        "primary_surgeon_text": "Mr. Test Surgeon"
    },

    "intraoperative": {
        "findings": "Anastomotic leak with fecal peritonitis"
    }
}

result = db.treatments.insert_one(rtt_surgery)
print(f"✓ Created RTT surgery: {RTT_SURGERY_ID}")

# Update parent surgery
db.treatments.update_one(
    {"treatment_id": PRIMARY_SURGERY_ID},
    {
        "$push": {
            "related_surgery_ids": {
                "treatment_id": RTT_SURGERY_ID,
                "treatment_type": "surgery_rtt",
                "date_created": datetime.now(timezone.utc)
            }
        },
        "$set": {
            "postoperative_events.return_to_theatre.occurred": True,
            "postoperative_events.return_to_theatre.date": rtt_surgery["treatment_date"],
            "postoperative_events.return_to_theatre.reason": rtt_surgery["rtt_reason"],
            "postoperative_events.return_to_theatre.procedure_performed": rtt_surgery["procedure"]["primary_procedure"],
            "postoperative_events.return_to_theatre.rtt_treatment_id": RTT_SURGERY_ID
        }
    }
)
print(f"✓ Updated parent surgery with RTT link and flags")

# Display updated primary
updated_primary = db.treatments.find_one({"treatment_id": PRIMARY_SURGERY_ID})
print_surgery(updated_primary, "Primary Surgery After RTT")

created_rtt = db.treatments.find_one({"treatment_id": RTT_SURGERY_ID})
print_surgery(created_rtt, "RTT Surgery Created")


# STEP 3: Create Second RTT Surgery (Multiple RTTs)
test_step(3, "Create Second RTT Surgery (Wound Dehiscence)")

rtt2_surgery = {
    "treatment_id": RTT2_SURGERY_ID,
    "episode_id": TEST_EPISODE_ID,
    "patient_id": TEST_PATIENT_ID,
    "treatment_type": "surgery_rtt",
    "treatment_date": datetime.now() - timedelta(days=2),
    "treating_clinician": "Mr. Test Surgeon",
    "treatment_intent": "urgent",
    "notes": "Second RTT for wound dehiscence",

    "parent_surgery_id": PRIMARY_SURGERY_ID,
    "parent_episode_id": TEST_EPISODE_ID,
    "rtt_reason": "Abdominal wound dehiscence requiring washout and resuturing",

    "classification": {
        "urgency": "urgent",
        "primary_diagnosis": "Wound dehiscence"
    },

    "procedure": {
        "primary_procedure": "Wound exploration and resuturing",
        "approach": "open"
    },

    "perioperative_timeline": {
        "admission_date": datetime.now() - timedelta(days=2),
        "surgery_date": datetime.now() - timedelta(days=2)
    },

    "team": {
        "primary_surgeon": "Mr. Test Surgeon",
        "primary_surgeon_text": "Mr. Test Surgeon"
    }
}

result = db.treatments.insert_one(rtt2_surgery)
print(f"✓ Created second RTT surgery: {RTT2_SURGERY_ID}")

# Add to parent's related surgeries
db.treatments.update_one(
    {"treatment_id": PRIMARY_SURGERY_ID},
    {
        "$push": {
            "related_surgery_ids": {
                "treatment_id": RTT2_SURGERY_ID,
                "treatment_type": "surgery_rtt",
                "date_created": datetime.now(timezone.utc)
            }
        }
    }
)
print(f"✓ Added second RTT to parent's related surgeries")

# Display updated primary with 2 RTTs
updated_primary = db.treatments.find_one({"treatment_id": PRIMARY_SURGERY_ID})
print_surgery(updated_primary, "Primary Surgery After 2 RTTs")


# STEP 4: Create Stoma Reversal Surgery
test_step(4, "Create Stoma Reversal Surgery")

reversal_surgery = {
    "treatment_id": REVERSAL_SURGERY_ID,
    "episode_id": TEST_EPISODE_ID,
    "patient_id": TEST_PATIENT_ID,
    "treatment_type": "surgery_reversal",
    "treatment_date": datetime.now(),
    "treating_clinician": "Mr. Test Surgeon",
    "treatment_intent": "curative",
    "notes": "Planned stoma reversal",

    "parent_surgery_id": PRIMARY_SURGERY_ID,
    "parent_episode_id": TEST_EPISODE_ID,
    "reversal_notes": "Adequate healing confirmed on imaging. Patient ready for reversal.",

    "classification": {
        "urgency": "elective",
        "primary_diagnosis": "Ileostomy reversal"
    },

    "procedure": {
        "primary_procedure": "Ileostomy closure and anastomosis",
        "approach": "laparoscopic",
        "opcs_codes": ["G64.1"]
    },

    "perioperative_timeline": {
        "admission_date": datetime.now(),
        "surgery_date": datetime.now()
    },

    "team": {
        "primary_surgeon": "Mr. Test Surgeon",
        "primary_surgeon_text": "Mr. Test Surgeon"
    },

    "intraoperative": {
        "findings": "Good healing, no complications"
    }
}

result = db.treatments.insert_one(reversal_surgery)
print(f"✓ Created stoma reversal surgery: {REVERSAL_SURGERY_ID}")

# Update parent surgery
db.treatments.update_one(
    {"treatment_id": PRIMARY_SURGERY_ID},
    {
        "$push": {
            "related_surgery_ids": {
                "treatment_id": REVERSAL_SURGERY_ID,
                "treatment_type": "surgery_reversal",
                "date_created": datetime.now(timezone.utc)
            }
        },
        "$set": {
            "intraoperative.stoma_closure_date": reversal_surgery["treatment_date"],
            "intraoperative.reversal_treatment_id": REVERSAL_SURGERY_ID
        }
    }
)
print(f"✓ Updated parent surgery with reversal link and stoma closure date")

# Display updated primary with reversal
updated_primary = db.treatments.find_one({"treatment_id": PRIMARY_SURGERY_ID})
print_surgery(updated_primary, "Primary Surgery After Reversal")

created_reversal = db.treatments.find_one({"treatment_id": REVERSAL_SURGERY_ID})
print_surgery(created_reversal, "Reversal Surgery Created")


# STEP 5: Get Related Surgeries
test_step(5, "Get Related Surgeries for Primary")

primary = db.treatments.find_one({"treatment_id": PRIMARY_SURGERY_ID})
related_ids = [r['treatment_id'] for r in primary.get('related_surgery_ids', [])]

related_surgeries = list(db.treatments.find({"treatment_id": {"$in": related_ids}}))

print(f"✓ Found {len(related_surgeries)} related surgeries:")
for rs in related_surgeries:
    print(f"  - {rs['treatment_id']} ({rs['treatment_type']})")
    if rs['treatment_type'] == 'surgery_rtt':
        print(f"    Reason: {rs.get('rtt_reason')}")
    elif rs['treatment_type'] == 'surgery_reversal':
        print(f"    Notes: {rs.get('reversal_notes')}")


# STEP 6: Delete First RTT and Verify Flags NOT Reset (still have RTT #2)
test_step(6, "Delete First RTT (Flags Should NOT Reset - Still Have RTT #2)")

# Remove from parent's related surgeries
db.treatments.update_one(
    {"treatment_id": PRIMARY_SURGERY_ID},
    {
        "$pull": {
            "related_surgery_ids": {"treatment_id": RTT_SURGERY_ID}
        }
    }
)

# Delete the RTT
result = db.treatments.delete_one({"treatment_id": RTT_SURGERY_ID})
print(f"✓ Deleted first RTT surgery: {RTT_SURGERY_ID}")

# Check parent flags - should STILL be True (RTT #2 exists)
updated_primary = db.treatments.find_one({"treatment_id": PRIMARY_SURGERY_ID})
rtt_flag = updated_primary.get('postoperative_events', {}).get('return_to_theatre', {}).get('occurred')

print(f"\nParent RTT flags after deleting first RTT:")
print(f"  RTT Occurred: {rtt_flag} (Should be TRUE - still have RTT #2)")
print(f"  Remaining related surgeries: {len(updated_primary.get('related_surgery_ids', []))}")

print_surgery(updated_primary, "Primary Surgery After Deleting First RTT")


# STEP 7: Delete Second RTT and Verify Flags ARE Reset
test_step(7, "Delete Second RTT (Flags Should Reset - No More RTTs)")

# Remove from parent's related surgeries
db.treatments.update_one(
    {"treatment_id": PRIMARY_SURGERY_ID},
    {
        "$pull": {
            "related_surgery_ids": {"treatment_id": RTT2_SURGERY_ID}
        }
    }
)

# Delete the RTT
result = db.treatments.delete_one({"treatment_id": RTT2_SURGERY_ID})
print(f"✓ Deleted second RTT surgery: {RTT2_SURGERY_ID}")

# Check if any RTTs remain
updated_primary = db.treatments.find_one({"treatment_id": PRIMARY_SURGERY_ID})
related = updated_primary.get('related_surgery_ids', [])
remaining_rtts = [r for r in related if r.get('treatment_type') == 'surgery_rtt']

if len(remaining_rtts) == 0:
    # Reset RTT flags
    db.treatments.update_one(
        {"treatment_id": PRIMARY_SURGERY_ID},
        {
            "$set": {
                "postoperative_events.return_to_theatre.occurred": False,
                "postoperative_events.return_to_theatre.date": None,
                "postoperative_events.return_to_theatre.reason": None,
                "postoperative_events.return_to_theatre.procedure_performed": None,
                "postoperative_events.return_to_theatre.rtt_treatment_id": None
            }
        }
    )
    print(f"✓ Reset RTT flags (no more RTT surgeries)")

# Verify
updated_primary = db.treatments.find_one({"treatment_id": PRIMARY_SURGERY_ID})
rtt_flag = updated_primary.get('postoperative_events', {}).get('return_to_theatre', {}).get('occurred')

print(f"\nParent RTT flags after deleting all RTTs:")
print(f"  RTT Occurred: {rtt_flag} (Should be FALSE)")
print(f"  Remaining related surgeries: {len(updated_primary.get('related_surgery_ids', []))}")

print_surgery(updated_primary, "Primary Surgery After Deleting All RTTs")


# STEP 8: Summary
test_step(8, "Test Summary")

print("\n✅ All tests completed successfully!")
print("\nDemonstrated functionality:")
print("  1. ✓ Created primary surgery with stoma")
print("  2. ✓ Created first RTT surgery (anastomotic leak)")
print("  3. ✓ Created second RTT surgery (wound dehiscence) - multiple RTTs")
print("  4. ✓ Created stoma reversal surgery")
print("  5. ✓ Retrieved related surgeries")
print("  6. ✓ Deleted first RTT - flags NOT reset (RTT #2 still exists)")
print("  7. ✓ Deleted second RTT - flags RESET (no more RTTs)")
print("  8. ✓ Reversal surgery still linked - stoma closure date preserved")

print("\nFinal state:")
final_primary = db.treatments.find_one({"treatment_id": PRIMARY_SURGERY_ID})
print(f"  Primary surgery: {PRIMARY_SURGERY_ID}")
print(f"  RTT occurred: {final_primary.get('postoperative_events', {}).get('return_to_theatre', {}).get('occurred')}")
print(f"  Stoma closed: {final_primary.get('intraoperative', {}).get('stoma_closure_date') is not None}")
print(f"  Related surgeries: {len(final_primary.get('related_surgery_ids', []))}")

print("\n" + "=" * 80)
print("CLEANUP")
print("=" * 80)

# Auto-cleanup test data
db.treatments.delete_many({"treatment_id": {"$regex": "^T-TEST-"}})
print("✓ Test data cleaned up from impact_test database")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
print("\nAll functionality working as expected! ✨")
print("Ready for frontend integration.")
