# Migration Helper Scripts

This document describes the helper scripts available in `execution/` for data normalization and maintenance.

## Data Normalization Scripts

### normalize_treatment_intent.py

Normalizes treatment intent values to standard options.

**Purpose:** Converts legacy coded values to clean standard values matching form options.

**Mappings:**
- `C curative`, `C` → `Curative`
- `Z noncurative`, `Z` → `Palliative`
- `X no ca treat`, `X` → `No Treatment`
- `not known`, `not knnown` → (removed)

**Usage:**
```bash
python3 execution/normalize_treatment_intent.py
```

**Output:** Updates all episodes with normalized treatment intent values.

---

### normalize_treatment_plan.py

Normalizes treatment plan values to standard options, handling multi-treatment combinations.

**Purpose:** Converts legacy coded values (e.g., "01 surgery, 02 teletherapy") to clean combined format.

**Mappings:**
- `01 surgery` → `Surgery`
- `02 teletherapy` → `Radiotherapy`
- `03 chemotherapy` → `Chemotherapy`
- `05 palliative care` → `Palliative Care`
- `01 surgery, 02 teletherapy` → `Surgery + Radiotherapy`
- `01 surgery, 02, 03` → `Surgery + Radiotherapy + Chemotherapy`

**Usage:**
```bash
python3 execution/normalize_treatment_plan.py
```

**Output:** Updates all episodes with normalized treatment plan values.

---

### map_tumour_anatomical_sites.py

Maps tumour site values from legacy format to ICD-10 based anatomical sites.

**Purpose:** Converts legacy site codes to standard anatomical site names matching form dropdown options.

**Mappings:**
- `site_1 Caecum` → `caecum` (ICD-10: C18.0)
- `site_2 Appendix` → `appendix` (ICD-10: C18.1)
- `site_3 Ascending Colon` → `ascending_colon` (ICD-10: C18.2)
- `site_4 Hepatic Flexure` → `hepatic_flexure` (ICD-10: C18.3)
- `site_5 Transverse Colon` → `transverse_colon` (ICD-10: C18.4)
- `site_6 Splenic Flexure` → `splenic_flexure` (ICD-10: C18.5)
- `site_7 Descending Colon` → `descending_colon` (ICD-10: C18.6)
- `site_8 Sigmoid Colon` → `sigmoid_colon` (ICD-10: C18.7)
- `site_9 Recto/Sigmoid` → `rectosigmoid_junction` (ICD-10: C19)
- `site_10 Rectum` → `rectum` (ICD-10: C20)

**Usage:**
```bash
python3 execution/map_tumour_anatomical_sites.py
```

**Output:** 
- Updates `anatomical_site` field for all tumours
- Updates `icd10_code` field with appropriate ICD-10 codes
- Updates `site` field to match anatomical_site

---

## NHS Provider Scripts

### fetch_nhs_provider_codes.py

Fetches NHS provider (trust) codes from the NHS Organisation Data Service (ODS) FHIR API.

**Purpose:** Query and cache NHS provider information for use in the application.

**Features:**
- Checks local cache first (stored in `nhs_provider_codes_reference.json`)
- Auto-saves validated codes to cache
- Supports partial name matching
- Stores names in lowercase for consistent formatting

**Usage:**

Search for providers:
```bash
python3 execution/fetch_nhs_provider_codes.py --search "Portsmouth" --json
```

Get specific provider by code:
```bash
python3 execution/fetch_nhs_provider_codes.py --code RHU
```

Export all NHS trusts:
```bash
python3 execution/fetch_nhs_provider_codes.py --all-trusts --output provider_codes.json
```

**Cache File:** `execution/nhs_provider_codes_reference.json`
- Provider names stored in lowercase
- Frontend formats to Title Case with "NHS" capitalized
- 144 providers currently cached

---

## Finding Data Examples

### find_episodes_with_dates.py

Finds episodes that have first_seen_date and mdt_discussion_date populated.

**Purpose:** Identify specific episode IDs for testing date display functionality.

**Usage:**
```bash
python3 .tmp/find_episodes_with_dates.py
```

**Output:** Lists 10 episodes with dates, showing Episode ID, Patient MRN, and dates.

---

## Migration Script

### migrate_acpdb_to_mongodb_v4.py

Main migration script with built-in normalization functions.

**Key Normalizations:**
1. **Treatment Intent** - Uses `normalize_treatment_intent()` during import
2. **Treatment Plan** - Uses `normalize_treatment_plan()` during import
3. **Anatomical Sites** - Uses `map_tumour_site()` to return (site, icd10, display_label)
4. **Referral Types** - Uses `normalize_referral_type()` and `normalize_referral_source()`
5. **Provider Names** - Stored in lowercase for consistent formatting

**Date Import:**
- Imports `first_seen_date` and `mdt_discussion_date` from `Dt_Visit` column
- 14.7% of episodes have dates (matches legacy data availability)

**To run full migration:**
```bash
python3 execution/migrate_acpdb_to_mongodb_v4.py
```

---

## Data Statistics (Post-Normalization)

### Treatment Intent
- 3,036 episodes: Curative (73.1%)
- 563 episodes: Palliative (13.6%)
- 551 episodes: No Treatment (13.3%)
- Total: 4,150 episodes with treatment intent (52.2%)

### Treatment Plan
- 2,765 episodes: Surgery (79.4%)
- 451 episodes: Chemotherapy (13.0%)
- 145 episodes: Radiotherapy (4.2%)
- 84 episodes: Palliative Care (2.4%)
- 36 episodes: Combination therapies (1.0%)
- Total: 3,481 episodes with treatment plan (43.7%)

### Tumour Anatomical Sites
- 2,612 tumours: Rectum (32.4%)
- 1,842 tumours: Sigmoid Colon (22.8%)
- 1,192 tumours: Caecum (14.8%)
- 885 tumours: Ascending Colon (11.0%)
- Others: 1,535 tumours (19.0%)
- Total: 8,066 tumours mapped (99.7%)

### Date Availability
- 1,168 episodes have first_seen_date and mdt_discussion_date (14.7%)
- Matches legacy data availability in source CSV files

---

## Notes

- All normalization scripts are idempotent - safe to run multiple times
- Scripts provide detailed output showing what was changed
- Always test scripts on a backup before running on production data
- Migration script includes all normalizations automatically for new imports
