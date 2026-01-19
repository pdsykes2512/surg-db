#!/usr/bin/env python3
"""
Clean up lead clinician assignments for ALL clinicians

This script:
1. Gets all clinicians from impact_system.clinicians
2. For each clinician, finds episodes where they are lead_clinician
3. Checks if clinician is in any treatment's surgical team (primary/assistant/second assistant)
4. If NOT in surgical team, updates lead_clinician to primary surgeon from treatment

Author: Claude Code
Date: 2025-12-30
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from dotenv import load_dotenv


async def cleanup_all_lead_clinicians():
    """Clean up lead clinician for all clinicians in the system"""

    # Load environment variables
    load_dotenv('/etc/impact/secrets.env')
    load_dotenv('.env')

    # Connect to databases
    mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongodb_uri)
    db = client['impact']
    db_system = client['impact_system']

    episodes_collection = db.episodes
    treatments_collection = db.treatments
    clinicians_collection = db_system.clinicians

    print("=== Cleaning up Lead Clinician Assignments for All Clinicians ===\n")

    # Get all clinicians
    all_clinicians = await clinicians_collection.find({}).to_list(length=None)
    print(f"Found {len(all_clinicians)} clinicians in system")

    # Build name variants for each clinician
    clinician_names = {}
    for clinician in all_clinicians:
        first_name = clinician.get('first_name', '')
        surname = clinician.get('surname', '')
        if first_name and surname:
            full_name = f"{first_name} {surname}"
            # Store various name formats
            clinician_names[full_name.lower()] = {
                'full_name': full_name,
                'first_name': first_name,
                'surname': surname,
                'variants': [
                    full_name.lower(),
                    surname.lower(),
                    f"{first_name.lower()} {surname.lower()}"
                ]
            }

    print(f"Processing {len(clinician_names)} unique clinician names\n")

    # Track statistics
    all_episodes_to_update = []
    all_episodes_to_keep = []
    clinicians_processed = 0

    # Get all episodes with lead_clinician set
    all_episodes = await episodes_collection.find({
        "lead_clinician": {"$ne": None, "$exists": True}
    }).to_list(length=None)

    print(f"Found {len(all_episodes)} episodes with lead clinician set\n")

    # Process each episode
    for episode in all_episodes:
        episode_id = episode.get('episode_id')
        lead_clinician = episode.get('lead_clinician', '')

        if not lead_clinician:
            continue

        # Get all treatments for this episode
        treatments = await treatments_collection.find({
            "episode_id": episode_id
        }).to_list(length=None)

        # Check if lead clinician is in any surgical team
        lead_clinician_in_team = False

        for treatment in treatments:
            team = treatment.get('team', {})

            # Check primary surgeon
            primary_surgeon_text = team.get('primary_surgeon_text', '')
            if primary_surgeon_text and lead_clinician.lower() in primary_surgeon_text.lower():
                lead_clinician_in_team = True
                break

            # Also check reverse - if primary surgeon name is in lead clinician
            if primary_surgeon_text and primary_surgeon_text.lower() in lead_clinician.lower():
                lead_clinician_in_team = True
                break

            # Check assistant surgeons (array)
            assistant_surgeons = team.get('assistant_surgeons', [])
            for assistant in assistant_surgeons:
                if assistant and lead_clinician.lower() in assistant.lower():
                    lead_clinician_in_team = True
                    break
                if assistant and assistant.lower() in lead_clinician.lower():
                    lead_clinician_in_team = True
                    break

            if lead_clinician_in_team:
                break

            # Check second assistant
            second_assistant = team.get('second_assistant', '')
            if second_assistant and lead_clinician.lower() in second_assistant.lower():
                lead_clinician_in_team = True
                break
            if second_assistant and second_assistant.lower() in lead_clinician.lower():
                lead_clinician_in_team = True
                break

        # If lead clinician is NOT in surgical team, mark for update
        if not lead_clinician_in_team:
            # Find the primary surgeon from the first treatment
            new_lead_clinician = None
            if treatments:
                # Get primary surgeon from first treatment
                first_treatment = treatments[0]
                team = first_treatment.get('team', {})
                new_lead_clinician = team.get('primary_surgeon_text', None)

            all_episodes_to_update.append({
                'episode_id': episode_id,
                'current_lead_clinician': lead_clinician,
                'new_lead_clinician': new_lead_clinician,
                'treatments_count': len(treatments)
            })
        else:
            all_episodes_to_keep.append({
                'episode_id': episode_id,
                'lead_clinician': lead_clinician,
                'treatments_count': len(treatments)
            })

    # Display results
    print(f"\n=== Analysis Results ===")
    print(f"Total episodes with lead clinician: {len(all_episodes)}")
    print(f"Episodes where lead clinician IS in surgical team (keep): {len(all_episodes_to_keep)}")
    print(f"Episodes where lead clinician is NOT in surgical team (update): {len(all_episodes_to_update)}")

    if all_episodes_to_update:
        print(f"\n=== Episodes to Update (first 20) ===")
        for ep in all_episodes_to_update[:20]:
            new_lead = ep.get('new_lead_clinician', 'None')
            print(f"  - {ep['episode_id']}: {ep['current_lead_clinician']} → {new_lead} ({ep['treatments_count']} treatments)")

        if len(all_episodes_to_update) > 20:
            print(f"  ... and {len(all_episodes_to_update) - 20} more")

        # Group by current lead clinician for summary
        clinician_summary = {}
        for ep in all_episodes_to_update:
            current = ep['current_lead_clinician']
            if current not in clinician_summary:
                clinician_summary[current] = 0
            clinician_summary[current] += 1

        print(f"\n=== Episodes to Update by Current Lead Clinician ===")
        for clinician, count in sorted(clinician_summary.items(), key=lambda x: x[1], reverse=True)[:15]:
            print(f"  - {clinician}: {count} episodes")

        # Ask for confirmation
        print(f"\n⚠️  About to update lead clinician for {len(all_episodes_to_update)} episodes")
        print(f"   Will set lead_clinician to primary surgeon from treatment (or None if no treatments)")
        response = input("Continue? (yes/no): ")

        if response.lower() == 'yes':
            # Update episodes
            updated_count = 0
            for ep in all_episodes_to_update:
                new_lead_clinician = ep.get('new_lead_clinician', None)

                result = await episodes_collection.update_one(
                    {"episode_id": ep['episode_id']},
                    {
                        "$set": {
                            "lead_clinician": new_lead_clinician,
                            "last_modified_at": datetime.utcnow(),
                            "last_modified_by": "cleanup_all_lead_clinicians_script"
                        }
                    }
                )
                if result.modified_count > 0:
                    updated_count += 1

            print(f"\n✅ Successfully updated {updated_count} episodes")
            print(f"   Set lead_clinician to primary surgeon (or None if no treatments)")
        else:
            print("\n❌ Cancelled - no changes made")
    else:
        print("\n✅ No episodes need updating - all lead clinicians are in surgical teams")

    # Show summary of kept episodes
    if all_episodes_to_keep:
        print(f"\n=== Episodes Kept (lead clinician in surgical team): {len(all_episodes_to_keep)} ===")
        # Group by lead clinician
        kept_summary = {}
        for ep in all_episodes_to_keep:
            lead = ep['lead_clinician']
            if lead not in kept_summary:
                kept_summary[lead] = 0
            kept_summary[lead] += 1

        print(f"\nTop 10 clinicians with correct lead clinician assignment:")
        for clinician, count in sorted(kept_summary.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  ✓ {clinician}: {count} episodes")

    client.close()


if __name__ == "__main__":
    asyncio.run(cleanup_all_lead_clinicians())
