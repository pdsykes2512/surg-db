#!/usr/bin/env python3
"""
Remove Jim Khan as lead clinician from episodes where treatments don't have Khan in surgical team

This script:
1. Finds episodes where lead_clinician contains "Khan"
2. For each episode, checks all treatments
3. If NO treatments have Khan in primary_surgeon_text, assistant_surgeons, or second_assistant
4. Then sets lead_clinician to None for that episode

Author: Claude Code
Date: 2025-12-30
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from dotenv import load_dotenv


async def cleanup_khan_lead_clinician():
    """Remove Khan as lead clinician when not in surgical team"""

    # Load environment variables
    load_dotenv('/etc/impact/secrets.env')
    load_dotenv('.env')

    # Connect to database using credentials from secrets.env
    mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongodb_uri)
    db = client['impact']

    episodes_collection = db.episodes
    treatments_collection = db.treatments

    print("=== Cleaning up Jim Khan as Lead Clinician ===\n")

    # Find all episodes where lead_clinician contains "Khan"
    khan_episodes = await episodes_collection.find({
        "lead_clinician": {"$regex": "khan", "$options": "i"}
    }).to_list(length=None)

    print(f"Found {len(khan_episodes)} episodes with Khan as lead clinician")

    # Track statistics
    episodes_to_update = []
    episodes_to_keep = []

    for episode in khan_episodes:
        episode_id = episode.get('episode_id')
        lead_clinician = episode.get('lead_clinician', '')

        # Get all treatments for this episode
        treatments = await treatments_collection.find({
            "episode_id": episode_id
        }).to_list(length=None)

        # Check if any treatment has Khan in the surgical team
        has_khan_in_team = False

        for treatment in treatments:
            team = treatment.get('team', {})

            # Check primary surgeon
            primary_surgeon_text = team.get('primary_surgeon_text', '')
            if primary_surgeon_text and 'khan' in primary_surgeon_text.lower():
                has_khan_in_team = True
                break

            # Check assistant surgeons (array)
            assistant_surgeons = team.get('assistant_surgeons', [])
            for assistant in assistant_surgeons:
                if assistant and 'khan' in assistant.lower():
                    has_khan_in_team = True
                    break

            if has_khan_in_team:
                break

            # Check second assistant
            second_assistant = team.get('second_assistant', '')
            if second_assistant and 'khan' in second_assistant.lower():
                has_khan_in_team = True
                break

        # If Khan is NOT in any surgical team, mark for update
        if not has_khan_in_team:
            # Find the primary surgeon from the first treatment
            new_lead_clinician = None
            if treatments:
                # Get primary surgeon from first treatment
                first_treatment = treatments[0]
                team = first_treatment.get('team', {})
                new_lead_clinician = team.get('primary_surgeon_text', None)

            episodes_to_update.append({
                'episode_id': episode_id,
                'current_lead_clinician': lead_clinician,
                'new_lead_clinician': new_lead_clinician,
                'treatments_count': len(treatments)
            })
        else:
            episodes_to_keep.append({
                'episode_id': episode_id,
                'lead_clinician': lead_clinician,
                'treatments_count': len(treatments)
            })

    # Display results
    print(f"\n=== Analysis Results ===")
    print(f"Total episodes with Khan as lead clinician: {len(khan_episodes)}")
    print(f"Episodes where Khan IS in surgical team (keep): {len(episodes_to_keep)}")
    print(f"Episodes where Khan is NOT in surgical team (remove): {len(episodes_to_update)}")

    if episodes_to_update:
        print(f"\n=== Episodes to Update ===")
        for ep in episodes_to_update[:10]:  # Show first 10
            new_lead = ep.get('new_lead_clinician', 'None')
            print(f"  - {ep['episode_id']}: {ep['current_lead_clinician']} → {new_lead} ({ep['treatments_count']} treatments)")

        if len(episodes_to_update) > 10:
            print(f"  ... and {len(episodes_to_update) - 10} more")

        # Ask for confirmation
        print(f"\n⚠️  About to update lead clinician for {len(episodes_to_update)} episodes")
        print(f"   Will set lead_clinician to primary surgeon from treatment (or None if no treatments)")
        response = input("Continue? (yes/no): ")

        if response.lower() == 'yes':
            # Update episodes
            updated_count = 0
            for ep in episodes_to_update:
                new_lead_clinician = ep.get('new_lead_clinician', None)

                result = await episodes_collection.update_one(
                    {"episode_id": ep['episode_id']},
                    {
                        "$set": {
                            "lead_clinician": new_lead_clinician,
                            "last_modified_at": datetime.utcnow(),
                            "last_modified_by": "cleanup_khan_script"
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
        print("\n✅ No episodes need updating - Khan is in surgical team for all episodes")

    # Show summary of kept episodes
    if episodes_to_keep:
        print(f"\n=== Episodes Keeping Khan (first 5) ===")
        for ep in episodes_to_keep[:5]:
            print(f"  ✓ {ep['episode_id']}: {ep['lead_clinician']} ({ep['treatments_count']} treatments)")

    client.close()


if __name__ == "__main__":
    asyncio.run(cleanup_khan_lead_clinician())
