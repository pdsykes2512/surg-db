# ID Schema Documentation

## Overview

The system uses a hybrid ID scheme that balances human-readability with system reliability.

## Patient IDs

**Format:** 6-digit alphanumeric hash (uppercase)

**Generation:** MD5 hash of MRN, truncated to first 6 characters

**Examples:**
- MRN `00118297` → Patient ID `8645C5`
- MRN `IW123456` → Patient ID `A655B8`
- MRN `q1571530` → Patient ID `CBFAD3`

**Advantages:**
- Consistent: Same MRN always generates same ID
- Short: Easy to communicate and type
- Unique: 2.2 billion possible combinations (36^6)
- Privacy: Does not expose MRN or NHS number

**Storage:**
- `patient_id`: 6-digit hash (primary identifier)
- `mrn`: Original MRN formatted as 8 digits or IW+6 digits
- `nhs_number`: NHS number stored as clean string

## Episode/Tumour/Treatment IDs

**Format:** `{PREFIX}-{patient_id}-{sequence:02d}`

**Prefixes:**
- `E-` = Episode
- `TUM-` = Tumour
- `SUR-` = Surgery treatment
- `ONC-` = Oncology treatment (future)
- `RAD-` = Radiology treatment (future)

**Identifier:** Patient hash ID (6-digit)

**Sequence:** 2-digit sequential number starting from 01

**Examples:**
- `E-8645C5-01` = First episode for patient 8645C5
- `E-8645C5-02` = Second episode for same patient
- `TUM-8645C5-01` = First tumour for same patient
- `SUR-8645C5-01` = First surgery for same patient

**Advantages:**
- Consistent: Uses same patient_id across all records
- Privacy-preserving: No NHS number exposure
- Traceable: Easy to find all episodes/tumours for a patient
- Sequential: Shows chronology within patient records
- Reliable: Works regardless of NHS number availability

## Internal References

**MongoDB ObjectId:** Used for internal document relationships

All cross-collection references (e.g., linking episodes to tumours, treatments to episodes) use MongoDB's native ObjectId for:
- Performance: Fast indexing and lookups
- Reliability: Guaranteed uniqueness
- Flexibility: Allows updating display IDs without breaking relationships

**Example structure:**
```javascript
{
  "episode_id": "E-4184440118-01",          // Display ID
  "patient_id": "8645C5",                   // Display ID
  "patient_mongo_id": ObjectId("..."),      // Internal reference
  "tumour_mongo_ids": [ObjectId("...")]     // Internal references
}
```

## Migration Details

**Original Access Database:**
- Hospital Number (Hosp_No): Variable format
- NHS Number (NHS_No): Sometimes missing
- Sequential numbers (Su_SeqNo, TumSeqNo): Not globally unique

**Migrated Schema:**
- Patient IDs: Generated from MRN hash (consistent, unique)
- MRN: Standardized to 8 digits or IW+6 digits
- NHS Numbers: Cleaned and stored as strings
- Episode/Tumour/Treatment IDs: Sequential per NHS number
- Internal links: MongoDB ObjectIds

## Benefits

1. **Privacy:** Patient ID is a hash, not directly identifiable
2. **Usability:** NHS-based IDs are clinically meaningful
3. **Reliability:** ObjectId references prevent broken links
4. **Flexibility:** Can update display IDs without breaking system
5. **Scalability:** 2.2 billion possible patient IDs
6. **Consistency:** Deterministic hash generation

## Future Considerations

- If >100 episodes per patient: Extend sequence to 3 digits
- If NHS number format changes: Easily accommodated
- If MRN changes: Patient ID remains stable via hash
- Multi-site: Could prefix with site code (e.g., `STG-8645C5`)
