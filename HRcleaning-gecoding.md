# Hospital Records Data Processing Summary

## Dataset Overview
| Item | Details |
|------|---------|
| **Original file** | `hospital-records.xlsx` (Sheet: "Hospital - Union Catalogue") |
| **Original records** | 3,212 hospitals |
| **Total columns** | 130 variables |

---

## Processing Steps

### Step 1: Filling Missing Geographic Data

**Problem:** Many records had missing `Town` and `Post Code` values.

**Solution:** 
- Created a supplementary lookup file (`hospitals_missing_town_filled.xlsx`) with 63 manually researched records
- Matched records using two methods:
  1. **Excel row index** — direct row-to-row matching (most reliable)
  2. **Hospital name** — fallback for any remaining gaps

**Result:** 
| Field | Filled |
|-------|--------|
| Town | 53 |
| Post Code | 19 |

---

### Step 2: Duplicate Detection & Removal

**Problem:** Dataset contained duplicate hospital entries.

**Duplicate criteria:** Records with identical values across:
- `HOSPITAL` (name)
- `Town`
- `Foundation Date`

**Safeguard applied:** Only deduplicated rows where **both** Town AND Foundation Date were filled. Records missing either field were kept as-is to avoid accidentally merging different hospitals.

**Strategy:** When duplicates found, kept the row with the **most complete data** (fewest missing values).

**Output:** `hospital_records_cleaned.xlsx`

---

### Step 3: Geocoding

**Problem:** Need latitude/longitude coordinates for geographic analysis.

**Approach:** Two-tier geocoding strategy:

| Priority | API | Rate Limit | Accuracy |
|----------|-----|------------|----------|
| Primary | Postcodes.io (UK Postcode) | None | ~100m |
| Fallback | Nominatim (OpenStreetMap) | 1 req/sec | ~1-5km |

**Features:**
- Progress tracking (updates every 50 rows)
- Auto-save every 100 rows (crash protection)
- Failed geocodes logged separately for review

**Output files:**
| File | Description |
|------|-------------|
| `hospital_records_geocoded.xlsx` | Final dataset with coordinates |
| `geocoding_failures.xlsx` | Records that couldn't be geocoded |

---

## New Columns Added

| Column | Type | Description |
|--------|------|-------------|
| `latitude` | float | Geographic latitude (decimal degrees) |
| `longitude` | float | Geographic longitude (decimal degrees) |
| `geocode_source` | string | Method used: `postcode`, `town`, or `failed` |

---

## Data Quality Notes

- ✅ Geocoding accuracy verified against known UK locations (Evesham, Aberdeen)
- ✅ Postcode-level precision where available
- ⚠️ Failed geocodes typically due to missing data or obscure/misspelled town names

---

## File Pipeline

```
hospital-records.xlsx (original)
        │
        ▼
hospital_records_updated.xlsx (filled missing data)
        │
        ▼
hospital_records_cleaned.xlsx (deduplicated)
        │
        ▼
hospital_records_geocoded.xlsx (final with coordinates)
```

---

## Tools & APIs Used

| Tool | Purpose | Cost |
|------|---------|------|
| Python + Pandas | Data manipulation | Free |
| Postcodes.io API | UK postcode geocoding | Free |
| Nominatim (OpenStreetMap) | Town geocoding | Free |