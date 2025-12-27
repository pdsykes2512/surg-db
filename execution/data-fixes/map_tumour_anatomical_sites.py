#!/usr/bin/env python3
"""
Map tumour site values from legacy format to ICD-10 based anatomical sites.

Maps:
- "site_1 Caecum" → "caecum"
- "site_2 Appendix" → "appendix"
- "site_3 Ascending Colon" → "ascending_colon"
- "site_4 Hepatic Flexure" → "hepatic_flexure"
- "site_5 Transverse Colon" → "transverse_colon"
- "site_6 Splenic Flexure" → "splenic_flexure"
- "site_7 Descending Colon" → "descending_colon"
- "site_8 Sigmoid Colon" → "sigmoid_colon"
- "site_9 Recto/Sigmoid" → "rectosigmoid_junction"
- "site_10 Rectum" → "rectum"
"""

from pymongo import MongoClient

def map_anatomical_site(site_value):
    """Map legacy site format to ICD-10 based anatomical site."""
    if not site_value:
        return None
    
    site_str = str(site_value).strip().lower()
    
    # Mapping from legacy format
    site_map = {
        'site_1 caecum': 'caecum',
        'site_2 appendix': 'appendix',
        'site_3 ascending colon': 'ascending_colon',
        'site_4 hepatic flexure': 'hepatic_flexure',
        'site_5 transverse colon': 'transverse_colon',
        'site_6 splenic flexure': 'splenic_flexure',
        'site_7 descending colon': 'descending_colon',
        'site_8 sigmoid colon': 'sigmoid_colon',
        'site_9 recto/sigmoid': 'rectosigmoid_junction',
        'site_10 rectum': 'rectum'
    }
    
    return site_map.get(site_str, None)


def get_icd10_for_site(site):
    """Get ICD-10 code for anatomical site."""
    icd10_map = {
        'caecum': 'C18.0',
        'appendix': 'C18.1',
        'ascending_colon': 'C18.2',
        'hepatic_flexure': 'C18.3',
        'transverse_colon': 'C18.4',
        'splenic_flexure': 'C18.5',
        'descending_colon': 'C18.6',
        'sigmoid_colon': 'C18.7',
        'rectosigmoid_junction': 'C19',
        'rectum': 'C20'
    }
    return icd10_map.get(site, None)


def main():
    client = MongoClient('mongodb://admin:admin123@localhost:27017/')
    db = client['surgdb']
    
    print("Mapping tumour anatomical sites to ICD-10 format...")
    print("="*70)
    
    # Get all tumours
    tumours = db.tumours.find({'site': {'$ne': None}})
    
    updates = {}
    icd10_updates = 0
    
    for tumour in tumours:
        old_site = tumour['site']
        new_site = map_anatomical_site(old_site)
        
        if new_site:
            update_doc = {}
            
            # Add anatomical_site field
            update_doc['anatomical_site'] = new_site
            
            # Update ICD-10 code if not present or matches the site
            icd10_for_site = get_icd10_for_site(new_site)
            if icd10_for_site:
                # Only update ICD-10 if it's empty or if it matches a colorectal site
                current_icd10 = tumour.get('icd10_code', '')
                if not current_icd10 or current_icd10.startswith('C18') or current_icd10 in ['C19', 'C20']:
                    update_doc['icd10_code'] = icd10_for_site
                    icd10_updates += 1
            
            # Update the document
            db.tumours.update_one(
                {'_id': tumour['_id']},
                {'$set': update_doc}
            )
            
            # Track for summary
            key = f"{old_site} → {new_site}"
            updates[key] = updates.get(key, 0) + 1
            
            if updates[key] <= 2:  # Show first few examples of each type
                print(f"  {old_site:35} → {new_site:25} (ICD-10: {icd10_for_site})")
    
    print("\nMapping Summary:")
    print("="*70)
    for key, count in sorted(updates.items(), key=lambda x: x[1], reverse=True):
        old, new = key.split(' → ')
        print(f"  {count:5} tumours: {old:30} → {new}")
    
    print(f"\nICD-10 codes updated: {icd10_updates}")
    
    # Show final distribution
    print("\nFinal anatomical_site distribution:")
    print("="*70)
    pipeline = [
        {"$match": {"anatomical_site": {"$ne": None}}},
        {"$group": {"_id": "$anatomical_site", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    for doc in db.tumours.aggregate(pipeline):
        icd10 = get_icd10_for_site(doc['_id'])
        print(f"  {doc['_id']:25} ({icd10:6}) : {doc['count']:5} tumours")
    
    print(f"\nTotal tumours with anatomical_site: {db.tumours.count_documents({'anatomical_site': {'$ne': None}})}")
    print("✓ Mapping complete")


if __name__ == "__main__":
    main()
