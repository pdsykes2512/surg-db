#!/usr/bin/env python3
from pymongo import MongoClient
import json

client = MongoClient('mongodb://admin:admin123@localhost:27017/?authSource=admin')
db = client['surgdb']

# Check lead clinician values now
print('Lead Clinician Distribution (top 10):')
pipeline = [
    {'$match': {'lead_clinician': {'$ne': None}}},
    {'$group': {'_id': '$lead_clinician', 'count': {'$sum': 1}}},
    {'$sort': {'count': -1}},
    {'$limit': 10}
]
for doc in db.episodes.aggregate(pipeline):
    print(f'{doc["_id"]}: {doc["count"]} episodes')

print('\n--- Sample Episode ---')
episode = db.episodes.find_one({'lead_clinician': {'$ne': None}}, {'_id': 0, 'episode_id': 1, 'lead_clinician': 1, 'referral_source': 1, 'surgery_performed': 1})
print(json.dumps(episode, indent=2, default=str))

print('\n--- Check Users ---')
print(f'Users in database: {db.users.count_documents({})}')
