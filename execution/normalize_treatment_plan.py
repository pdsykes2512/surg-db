#!/usr/bin/env python3
"""
Normalize treatment_plan values in episodes collection.

Converts values like:
- "01 surgery" → "Surgery"
- "02 teletherapy" → "Radiotherapy"
- "01 surgery, 02 teletherapy" → "Surgery + Radiotherapy"
- "surgery, 02, 03" → "Surgery + Radiotherapy + Chemotherapy"
"""

from pymongo import MongoClient

def normalize_treatment_plan(value):
    """
    Normalize treatment plan to standard values.
    Handles single and multi-treatment plans.
    """
    if not value:
        return None
    
    value_str = str(value).strip().lower()
    if not value_str or value_str == 'nan':
        return None
    
    # Treatment mapping
    treatment_map = {
        '01': 'Surgery',
        '02': 'Radiotherapy',
        '03': 'Chemotherapy',
        '04': 'Combination Therapy',
        '05': 'Palliative Care',
        'surgery': 'Surgery',
        'teletherapy': 'Radiotherapy',
        'radiotherapy': 'Radiotherapy',
        'chemotherapy': 'Chemotherapy',
        'combination therapy': 'Combination Therapy',
        'palliative care': 'Palliative Care',
        'palliative': 'Palliative Care'
    }
    
    # Split by comma for multi-treatment plans
    parts = [p.strip() for p in value_str.split(',')]
    treatments = []
    
    for part in parts:
        # Check if it starts with a number code
        if part and part[0].isdigit():
            # Extract code and text
            tokens = part.split(None, 1)  # Split on first whitespace
            code = tokens[0] if tokens else ''
            text = tokens[1] if len(tokens) > 1 else ''
            
            # Try code first, then text
            if code in treatment_map:
                treatments.append(treatment_map[code])
            elif text in treatment_map:
                treatments.append(treatment_map[text])
        else:
            # No code, just text
            if part in treatment_map:
                treatments.append(treatment_map[part])
    
    if not treatments:
        return None
    
    # Remove duplicates while preserving order
    seen = set()
    unique_treatments = []
    for t in treatments:
        if t not in seen:
            seen.add(t)
            unique_treatments.append(t)
    
    # Return combined format
    if len(unique_treatments) == 1:
        return unique_treatments[0]
    else:
        return ' + '.join(unique_treatments)


def main():
    client = MongoClient('mongodb://admin:admin123@localhost:27017/')
    db = client['surgdb']
    
    print("Normalizing treatment_plan values...")
    print("="*60)
    
    # Get all episodes with treatment_plan
    episodes = db.episodes.find({'mdt_outcome.treatment_plan': {'$ne': None}})
    
    updates = {}
    
    for episode in episodes:
        old_value = episode['mdt_outcome']['treatment_plan']
        new_value = normalize_treatment_plan(old_value)
        
        if new_value and new_value != old_value:
            # Update to normalized value
            db.episodes.update_one(
                {'_id': episode['_id']},
                {'$set': {'mdt_outcome.treatment_plan': new_value}}
            )
            
            # Track for summary
            key = f"{old_value} → {new_value}"
            updates[key] = updates.get(key, 0) + 1
            
            if updates[key] <= 3:  # Show first few examples of each type
                print(f"  {old_value:40} → {new_value}")
    
    print("\nNormalization Summary:")
    print("="*60)
    for key, count in sorted(updates.items(), key=lambda x: x[1], reverse=True):
        old, new = key.split(' → ')
        print(f"  {count:5} episodes: {old:30} → {new}")
    
    # Show final distribution
    print("\nFinal distribution:")
    print("="*60)
    pipeline = [
        {"$match": {"mdt_outcome.treatment_plan": {"$ne": None}}},
        {"$group": {"_id": "$mdt_outcome.treatment_plan", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    for doc in db.episodes.aggregate(pipeline):
        print(f"  {doc['_id']:40} : {doc['count']:5} episodes")
    
    print(f"\nTotal with treatment_plan: {db.episodes.count_documents({'mdt_outcome.treatment_plan': {'$ne': None}})}")
    print("✓ Normalization complete")


if __name__ == "__main__":
    main()
