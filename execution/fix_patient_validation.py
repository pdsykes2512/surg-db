"""Fix patient data validation issues"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

async def fix_patient_data():
    client = AsyncIOMotorClient('mongodb://admin:admin123@localhost:27017/surg_outcomes?authSource=admin')
    db = client['surg_outcomes']
    
    print('🔧 Fixing patient data validation issues...\n')
    
    # Get all patients
    patients = await db.patients.find({}).to_list(length=None)
    
    for patient in patients:
        updates = {}
        
        # Fix record_number - convert MRN to 8 digits
        record_number = patient.get('record_number', '')
        if record_number.startswith('MRN') or len(record_number) < 8:
            # Extract digits and pad to 8
            digits = ''.join(c for c in record_number if c.isdigit())
            new_record_number = digits.zfill(8)
            updates['record_number'] = new_record_number
            print(f'  Record: {record_number} → {new_record_number}')
        
        # Fix NHS number - add spaces if missing
        nhs_number = patient.get('nhs_number', '')
        clean_nhs = nhs_number.replace(' ', '')
        if len(clean_nhs) == 10 and ' ' not in nhs_number:
            new_nhs_number = f'{clean_nhs[0:3]} {clean_nhs[3:6]} {clean_nhs[6:10]}'
            updates['nhs_number'] = new_nhs_number
            print(f'  NHS: {nhs_number} → {new_nhs_number}')
        elif nhs_number != clean_nhs:
            # Already has spaces, just normalize
            new_nhs_number = f'{clean_nhs[0:3]} {clean_nhs[3:6]} {clean_nhs[6:10]}'
            if new_nhs_number != nhs_number:
                updates['nhs_number'] = new_nhs_number
                print(f'  NHS: {nhs_number} → {new_nhs_number}')
        
        if updates:
            updates['updated_at'] = datetime.utcnow()
            await db.patients.update_one(
                {'_id': patient['_id']},
                {'$set': updates}
            )
    
    print(f'\n✅ Updated {len(patients)} patients')
    client.close()

asyncio.run(fix_patient_data())
