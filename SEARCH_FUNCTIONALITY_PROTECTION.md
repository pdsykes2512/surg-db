# Search Functionality Protection Plan

**Date:** 2026-01-12
**Context:** Performance optimizations must NOT break the search functionality
**Critical Requirement:** Search must always query the ENTIRE database, not just paginated results

---

## Current Search Architecture (Working Correctly)

### Patient Search Implementation

**Backend:** [backend/app/routes/patients.py](backend/app/routes/patients.py)

```python
@router.get("/", response_model=List[Patient])
async def list_patients(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    # Build query FIRST based on search term
    query = {}
    if search:
        if search_encrypted_fields:
            # Hash-based lookup for MRN/NHS number
            query = {"$or": [nhs_query, mrn_query]}
        else:
            # Regex search for patient_id
            query = {"patient_id": search_pattern}

    # Aggregation pipeline applies pagination AFTER filtering
    pipeline = [
        {"$match": query},           # 1. Filter entire database by search
        {"$lookup": {...}},          # 2. Join with episodes
        {"$addFields": {...}},       # 3. Add computed fields
        {"$sort": {...}},            # 4. Sort results
        {"$skip": skip},             # 5. Apply pagination (AFTER filtering!)
        {"$limit": limit}            # 6. Limit results
    ]
```

**✅ CORRECT:** Search filters the entire database, THEN pagination is applied to results.

---

### Episode Search Implementation

**Backend:** [backend/app/routes/episodes.py:674-766](backend/app/routes/episodes.py#L674-L766)

```python
@router.get("/")
async def list_episodes(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    # ... other filters
):
    query = {}

    # Search filter - searches ENTIRE database first
    if search:
        # Find matching patients by MRN
        matching_patients = await patients_collection.find(
            {"mrn": search_pattern},
            {"patient_id": 1}
        ).to_list(length=None)  # ← Gets ALL matching patients

        # Build OR query
        query["$or"] = [
            {"episode_id": search_pattern},
            {"cancer_type": search_pattern},
            {"lead_clinician": search_pattern},
            {"patient_id": {"$in": matching_patient_ids}}
        ]

    # Apply pagination AFTER filtering
    cursor = collection.find(query).sort(...).skip(skip).limit(limit)
```

**✅ CORRECT:** Search queries entire database, pagination applied to filtered results.

---

### Frontend Search Components

**SearchableSelect Component:** [frontend/src/components/common/SearchableSelect.tsx](frontend/src/components/common/SearchableSelect.tsx)

```typescript
// Key feature: onSearchChange callback for server-side search
<SearchableSelect
  value={patientId}
  onChange={setPatientId}
  onSearchChange={(search) => {
    // Triggers API call with search parameter
    fetchPatients(search)  // ← Queries entire database via API
  }}
  options={patients}
  // ...
/>
```

**✅ CORRECT:** SearchableSelect triggers server-side search via API, not client-side filtering.

---

## ⚠️ INCORRECT Pattern (Found in CancerEpisodesPage)

**Location:** [frontend/src/pages/CancerEpisodesPage.tsx:61-73](frontend/src/pages/CancerEpisodesPage.tsx#L61-L73)

```typescript
// ❌ WRONG: Filters AFTER pagination
const filteredEpisodes = useMemo(() => {
  return episodes.filter(episode => {
    const matchesSearch = !searchTerm ||
      episode.episode_id.toLowerCase().includes(searchTerm.toLowerCase())
    // ...
  })
}, [episodes, searchTerm])
```

**Problem:**
1. API fetches page 1 (25 episodes)
2. Client-side filter applies to only those 25 episodes
3. User misses matching episodes on other pages!

**Example:**
- Database has 100 episodes with "breast" cancer type
- Page 1 has 5 breast episodes, 20 other types
- User filters by "breast" → only sees 5 results
- User doesn't know there are 95 more breast episodes!

---

## Optimization Strategy: Safe Approach

### Principle: **Search Before Pagination, Always**

```
┌─────────────────────────────────────────────────┐
│  CORRECT FLOW (Current Implementation)         │
├─────────────────────────────────────────────────┤
│  1. User enters search term                     │
│  2. Frontend sends: ?search=X&skip=0&limit=25   │
│  3. Backend queries ENTIRE database with filter │
│  4. Backend counts total matches                │
│  5. Backend applies skip/limit to results       │
│  6. Frontend displays: "Showing 1-25 of 487"    │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  INCORRECT FLOW (To Be Fixed)                  │
├─────────────────────────────────────────────────┤
│  1. User enters search term                     │
│  2. Frontend fetches: page 1 (25 episodes)      │
│  3. Frontend filters those 25 episodes locally  │
│  4. Frontend displays: "Showing 5 results"      │
│  ❌ User doesn't know about other 482 matches!  │
└─────────────────────────────────────────────────┘
```

---

## Planned Optimizations: Impact on Search

### ✅ SAFE: N+1 Query Fix (Episode Listing)

**Current:**
```python
# Line 752-761: One query per episode to fetch patient MRN
for episode in episodes:
    patient = await patients_collection.find_one({"patient_id": episode["patient_id"]})
```

**Optimized:**
```python
# Bulk fetch all patient MRNs in ONE query
patient_ids = [ep["patient_id"] for ep in episodes]
patients = await patients_collection.find(
    {"patient_id": {"$in": patient_ids}}
).to_list(length=len(patient_ids))

# Build lookup map
patient_map = {p["patient_id"]: p for p in patients}
```

**Impact on Search:** ✅ **NONE** - This only affects how patient data is fetched AFTER filtering.

---

### ✅ SAFE: Add Pagination to `/episodes/treatments` Endpoint

**Current:**
```python
@router.get("/treatments")
async def get_all_treatments(patient_id, episode_id):
    treatments = await treatments_collection.find(query).to_list(length=None)
    return treatments  # Returns ALL treatments (could be 10,000+)
```

**Optimized:**
```python
@router.get("/treatments")
async def get_all_treatments(
    patient_id: Optional[str] = None,
    episode_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None  # ← Add search parameter
):
    query = {}
    if patient_id:
        query["patient_id"] = patient_id
    if episode_id:
        query["episode_id"] = episode_id
    if search:
        # Search by treatment_id, procedure name, surgeon, etc.
        query["$or"] = [
            {"treatment_id": {"$regex": search, "$options": "i"}},
            {"procedure.primary_procedure": {"$regex": search, "$options": "i"}},
            {"team.primary_surgeon_text": {"$regex": search, "$options": "i"}}
        ]

    # Apply pagination AFTER search filtering
    treatments = await treatments_collection.find(query).skip(skip).limit(limit).to_list(length=limit)
    return treatments
```

**Impact on Search:** ✅ **POSITIVE** - Adds search capability where none existed before!

---

### ⚠️ MUST FIX: Client-Side Filtering in CancerEpisodesPage

**Current (BROKEN):**
```typescript
// Frontend filters paginated results
const filteredEpisodes = episodes.filter(/* ... */)
```

**Fixed:**
```typescript
// Pass filters to backend API
const fetchEpisodes = async () => {
  const response = await apiService.episodes.list({
    skip: page * limit,
    limit: limit,
    search: searchTerm,           // ← Backend searches entire DB
    cancer_type: cancerTypeFilter, // ← Backend filters entire DB
    episode_status: statusFilter   // ← Backend filters entire DB
  })
  setEpisodes(response.data)
}
```

**Impact on Search:** ✅ **FIXES BROKEN BEHAVIOR** - Search will now work correctly!

---

### ✅ SAFE: Optimize Reports with Aggregation

**Current:**
```python
# Fetches ALL episodes to calculate statistics
all_episodes = await episodes_collection.find({}).to_list(length=None)
for field in fields:
    complete_count = sum(1 for ep in all_episodes if ep.get(field))
```

**Optimized:**
```python
# Uses aggregation to calculate statistics in database
pipeline = [
    {"$match": {}},  # Can include search filters here!
    {"$facet": {
        "total": [{"$count": "count"}],
        "field_completeness": [/* ... */]
    }}
]
result = await episodes_collection.aggregate(pipeline).to_list(1)
```

**Impact on Search:** ✅ **NONE** - Reports don't have search functionality (yet).

---

### ✅ SAFE: Add Database Indexes

**Proposed Indexes:**
```javascript
// Speeds up search queries
db.episodes.createIndex({"episode_id": 1})      // Episode ID search
db.episodes.createIndex({"patient_id": 1})       // Patient lookup
db.episodes.createIndex({"cancer_type": 1})      // Cancer type filter
db.episodes.createIndex({"lead_clinician": 1})   // Clinician search

db.patients.createIndex({"patient_id": 1})       // Patient ID search
db.patients.createIndex({"mrn_hash": 1})         // MRN search (encrypted)
```

**Impact on Search:** ✅ **POSITIVE** - Makes searches 10-100x faster!

---

## Protected Search Patterns: Rules to Follow

### Rule 1: Always Filter Before Paginating

```python
# ✅ CORRECT
query = build_search_query(search_term)  # Build filter query
cursor = collection.find(query)          # Apply filter
results = cursor.skip(skip).limit(limit) # THEN paginate

# ❌ WRONG
results = collection.find({}).skip(skip).limit(limit)  # Paginate first
filtered = [r for r in results if matches_search(r)]   # Then filter
```

### Rule 2: Count Total Matches, Not Page Count

```python
# ✅ CORRECT
total_matches = await collection.count_documents(query)  # Count filtered results
return {"data": results, "total": total_matches}

# ❌ WRONG
return {"data": results, "total": len(results)}  # Only counts current page
```

### Rule 3: Pass Search Parameters to Backend

```typescript
// ✅ CORRECT
const response = await api.get('/episodes/', {
  params: { search: searchTerm, skip: 0, limit: 25 }
})

// ❌ WRONG
const response = await api.get('/episodes/')
const filtered = response.data.filter(/* ... */)
```

### Rule 4: Use Server-Side Search Components

```typescript
// ✅ CORRECT - Uses SearchableSelect with server-side search
<SearchableSelect
  onSearchChange={(search) => fetchFromAPI(search)}
  options={apiResults}
/>

// ❌ WRONG - Client-side filtering of fetched results
<select>
  {allOptions.filter(opt => opt.includes(search)).map(/* ... */)}
</select>
```

---

## Testing Checklist: Verify Search Works

After implementing optimizations, verify these scenarios:

### Patient Search
- [ ] Search by MRN returns correct patient from entire database
- [ ] Search by NHS number returns correct patient from entire database
- [ ] Search by patient_id returns correct patient from entire database
- [ ] Pagination works correctly after search (skip/limit applied to filtered results)
- [ ] Count shows total matching patients, not just current page count

### Episode Search
- [ ] Search by episode_id returns correct episodes from entire database
- [ ] Search by MRN returns all episodes for that patient
- [ ] Search by cancer type returns all matching episodes
- [ ] Search by clinician name returns all their episodes
- [ ] Filters (cancer_type, status) work with search simultaneously
- [ ] Pagination works correctly after search and filters applied

### General
- [ ] SearchableSelect component triggers API calls, not client-side filtering
- [ ] Count displays "Showing X-Y of Z" where Z = total matches in database
- [ ] Changing search term resets to page 1
- [ ] Empty search shows all records (paginated)

---

## Summary: What's Safe to Change

| Optimization | Safe? | Reason |
|--------------|-------|--------|
| Fix N+1 query in episode listing | ✅ YES | Only affects how patient data is joined, not search logic |
| Add pagination to /treatments endpoint | ✅ YES | Adds search capability with proper filter-before-paginate |
| Add database indexes | ✅ YES | Only speeds up queries, doesn't change behavior |
| Optimize reports with aggregation | ✅ YES | Reports don't have search functionality |
| Fix client-side filtering in CancerEpisodesPage | ✅ YES | Actually FIXES broken search behavior! |
| Implement React Query caching | ✅ YES | Caches API responses but doesn't change search logic |
| Memoize frontend data transformations | ✅ YES | Only affects rendering, not data fetching |

**All planned optimizations are safe and some actually improve search functionality!**

---

## Rollback Plan (If Something Breaks)

If search breaks after optimization:

1. **Check API query parameters:**
   ```javascript
   console.log('Search params:', { search, skip, limit })
   ```

2. **Verify backend query construction:**
   ```python
   logger.debug(f"Search query: {query}")
   ```

3. **Compare counts:**
   ```python
   total_in_db = await collection.count_documents({})
   total_matching = await collection.count_documents(query)
   logger.info(f"DB total: {total_in_db}, Matching: {total_matching}")
   ```

4. **Quick rollback:**
   ```bash
   git log --oneline | head -5
   git revert <commit-hash>
   sudo systemctl restart impact-backend
   ```

---

## Conclusion

**Your concern is valid and important!** The current search architecture is correctly implemented:

✅ **Patients:** Search filters entire database, then paginates
✅ **Episodes:** Search filters entire database, then paginates
⚠️ **CancerEpisodesPage:** Client-side filtering (needs fixing)

**All planned optimizations will preserve or improve search functionality.** The N+1 query fix and pagination additions follow the same "filter-before-paginate" pattern that already works correctly in the patients and episodes endpoints.

The only issue found is client-side filtering in CancerEpisodesPage, which the optimization will actually **fix**, not break!
