#!/usr/bin/env python3
"""
Normalize treatment_intent values in episodes collection.

Maps:
- "C curative", "C" → "Curative"
- "Z noncurative", "Z" → "Palliative"
- "X no ca treat", "X" → "No Treatment"
- "not known", "not knnown", "Not known" → None (remove)
"""

from pymongo import MongoClient

def normalize_treatment_intent(value):
    """Normalize treatment intent to standard values."""
    if not value:
        return None
    
    value_lower = value.lower().strip()
    
    # Curative
    if 'curative' in value_lower and 'non' not in value_lower:
        return "Curative"
    if value_lower == 'c':
        return "Curative"
    
    # Palliative (includes noncurative)
    if 'noncurative' in value_lower or value_lower == 'z':
        return "Palliative"
    
    # No Treatment
    if 'no ca treat' in value_lower or value_lower == 'x':
        return "No Treatment"
    
    # Unknown -> None
    if 'not known' in value_lower or 'not knnown' in value_lower:
        return None
    
    # Default: return original if no match
    return value


def main():
    client = MongoClient('mongodb://admin:admin123@localhost:27017/')
    db = client['surgdb']
    
    print("Normalizing treatment_intent values...")
    print("="*60)
    
    # Get all episodes with treatment_intent
    episodes = db.episodes.find({'mdt_outcome.treatment_intent': {'$ne': None}})
    
    updates = {
        'Curative': 0,
        'Palliative': 0,
        'No Treatment': 0,
        'Removed (unknown)': 0
    }
    
    for episode in episodes:
        old_value = episode['mdt_outcome']['treatment_intent']
        new_value = normalize_treatment_intent(old_value)
        
        if new_value != old_value:
            if new_value is None:
                # Remove the field
                db.episodes.update_one(
                    {'_id': episode['_id']},
                    {'$unset': {'mdt_outcome.treatment_intent': ""}}
                )
                updates['Removed (unknown)'] += 1
                print(f"  {old_value:30} → (removed)")
            else:
                # Update to normalized value
                db.episodes.update_one(
                    {'_id': episode['_id']},
                    {'$set': {'mdt_outcome.treatment_intent': new_value}}
                )
                updates[new_value] += 1
                if updates[new_value] <= 3:  # Show first few examples
                    print(f"  {old_value:30} → {new_value}")
    
    print("\nNormalization Summary:")
    print("="*60)
    for key, count in updates.items():
        if count > 0:
            print(f"  {key:30} : {count:5} episodes")
    
    # Show final distribution
    print("\nFinal distribution:")
    print("="*60)
    pipeline = [
        {"$match": {"mdt_outcome.treatment_intent": {"$ne": None}}},
        {"$group": {"_id": "$mdt_outcome.treatment_intent", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    for doc in db.episodes.aggregate(pipeline):
        print(f"  {doc['_id']:30} : {doc['count']:5} episodes")
    
    print(f"\nTotal with treatment_intent: {db.episodes.count_documents({'mdt_outcome.treatment_intent': {'$ne': None}})}")
    print("✓ Normalization complete")


if __name__ == "__main__":
    main()
