# Parish–Registration District Harmonisation (1851 Anchor)

## Executive Summary

Constructed a spatial reference system that maps **Registration Districts (RDs) to 1851 civil parish geography** for the period 1851–1990, enabling spatial linkage of historical births/deaths records despite changing administrative boundaries. Achieved **93.5% match rate** through improved name normalization, with empirical validation showing coverage remains strong through the 1920s but declines post-1930s.

---

## Problem

- Death records (FreeBMD) are indexed by **Registration District** from 1837 onwards
- RD boundaries changed over time, but digitized shapefiles only exist for **1851–1911**
- No spatial boundaries available post-1911, yet death data extends to 1990+
- Need consistent geographic reference to enable spatial analysis across 140+ years

## Solution

**Anchor all RDs to 1851 civil parish geography:**
1. Scrape RD-parish composition from UKBMD (with temporal validity)
2. Match parish names to 1851 parish polygons (**93.5% success rate**)
3. Reconstruct RD boundaries by dissolving matched parishes
4. Validate using official RD centroids (1851–1911)
5. Extend coverage to 1990 using administrative membership data
6. Empirically test with actual death records to assess real-world coverage

---

## Pipeline Overview

### Input Data

| Data Source | Type | Coverage | Purpose |
|-------------|------|----------|---------|
| **1851 England & Wales Parishes** | Shapefile (WKT) | 23,177 parishes | Reference geography |
| **UKBMD Table 1** | Scraped HTML | All RDs, all years | Parish-RD membership |
| **Official RD Shapefiles** | GBHGIS shapefiles | 1851–1911 | Validation |
| **FreeBMD Deaths** | CSV | 1858–1990 | Empirical testing |

### Processing Steps

```
1. get_ukbmd_district_urls.py           → Scrape district URLs from FreeBMD
2. scrape_ukbmd_table1_all.py           → Extract parish-RD composition
3. match_ukbmd_to_1851_parishes.py      → Match parishes to 1851 geometry (93.5%)
4. construct_rd_from_1851_parishes...   → Dissolve parishes by RD (1851-1911)
5. rd_centroid_diagnostic...            → Validate against official centroids
6. impute_unmatched_to_nearest...       → Assign proxy centroids
7. build_rd_year_coverage_1851_1990.py  → Extend to 1990
8. batch_match_deaths_to_coverage.py    → Link actual death records
9. qa_rd_year_coverage_1851_1990.py     → Quality assurance
```

---

## Key Results

### 1. Parish Matching: 93.5% Success Rate

**Improved from 89.0% → 93.5%** using systematic normalization rules:

| Improvement | Parishes Gained | Method |
|-------------|-----------------|--------|
| **Substring matching** | 379 (2.5%) | "Shawdon" ⊂ "SHAWDON AND WOODHOUSE" |
| "with X" stripping | 159 (1.1%) | "Appleton with Eaton" → "Appleton" |
| Spacing variants | 84 (0.6%) | "Bessels Leigh" ↔ "Besselsleigh" |
| Vowel interchange | 21 (0.1%) | Courtenay ↔ Courteney (a↔e, e↔i) |
| Welsh variants | 8 (0.1%) | Llanvair ↔ Llanfair (v↔f, i↔y, ch↔gh) |
| **Total gain** | **+677 parishes** | **+4.5 percentage points** |

**Remaining 6.5% unmatched** are genuinely difficult cases (generic saint names, special jurisdictions, possible 1851 shapefile gaps).

### 2. Spatial Validation (1851–1911)

Centroid accuracy validated against official RD shapefiles:
- **Median distance**: 4–5 km (stable across all census years)
- **95th percentile**: ~11 km
- **Within-polygon match**: >99%

### 3. Temporal Coverage (1851–1990)

**Representability declines over time** (as expected):

| Period | Deaths Linked | Usable 1851 Backbone | Quality |
|--------|--------------|---------------------|---------|
| **1858** | 90.0% | **88.2%** | ✅ Excellent |
| **1895** | 79.4% | **85.6%** | ✅ Good |
| **1935** | 82.9% | **61.2%** | ⚠️ Moderate decline |
| **1975** | 39.4% | **30.4%** | ❌ Severe decline |

**Interpretation:**
- 1851–1920s: Strong coverage (85–90% usable)
- 1930s onward: Sharp decline due to administrative restructuring (Local Government Acts 1929, 1972)

---

## Final Outputs

### Main Deliverable

**`rd_year_coverage_1851_backbone_1851_1990.csv`**

One row per **RD × year** (1851–1990), containing:
- `district`, `year`
- `active_parish_rows`, `matched_parish_rows`, `matched_share`
- `usable_1851_backbone` (binary flag)
- `centroid_x`, `centroid_y` (British National Grid EPSG:27700)
- `location_imputed`, `geometry_source` (transparency flags)

**Location:** `data_outputs/4_final_coverage/`

### Supporting Files

| File | Location | Description |
|------|----------|-------------|
| `parish_rd_allyears_concordance.csv` | `1_parish_matching/` | Parish-RD-year membership with matched flag (93.5% rate) |
| `rd_constructed_from_1851_parishes.gpkg` | `2_rd_construction/` | Reconstructed RD polygons (1851–1911) |
| `rd_centroid_diagnostic_all_years.csv` | `3_validation/` | Spatial validation diagnostics |
| `linkage_summary_all_years.csv` | `5_deaths_linkage/` | Deaths data linkage statistics by year |

---

## Recent Work (Feb 2026)

### 1. Improved Parish Matching (89% → 93.5%)

**Implemented 10 safe normalization rules:**
1. Strip Welsh accents (ô→o, â→a)
2. Handle "with X" clauses
3. Strip "on/on the" descriptors
4. Handle "nigh" (near)
5. Strip "Lower/Upper" prefixes
6. Strip 1851 suffixes (- UPPER DIVISION)
7. Remove all spaces for matching
8. Welsh spelling variants (v↔f, i↔y, ch↔gh)
9. Vowel interchange (a↔e, e↔i)
10. **Substring matching** (biggest single gain: 379 parishes)

**Result:** +677 parishes matched, reducing unmatched from 11% → 6.5%

### 2. Empirical Coverage Assessment

Linked actual FreeBMD death records to RD coverage data:
- Tested 4 sample years (1858, 1895, 1935, 1975)
- Confirmed strong coverage pre-1930s, sharp decline post-1930s
- Quantified usable rate: 88% (1858) → 61% (1935) → 30% (1975)

### 3. Repository Organization

- Consolidated to single clean matching script
- Archived analysis/diagnostic scripts
- Organized outputs with clear naming
- Documented all methodology improvements

---

## Limitations & Caveats

1. **Fixed 1851 backbone** → Post-1851 boundary changes NOT reflected in geometry
2. **Centroid-only validation** → Full boundary equivalence not tested (only location)
3. **Parish-level precision** → Cannot represent sub-parish changes
4. **Post-1930s coverage degrades** → Due to structural administrative changes, not methodology failure
5. **6.5% unmatched parishes** → Generic names, special jurisdictions, possible 1851 data gaps

---

## Next Steps

### Immediate

1. **Review remaining 6.5% unmatched parishes**
   - Manual expert verification for high-frequency cases
   - Assess if they're genuinely missing from 1851 or unsolvable name variants

2. **Rebuild downstream files with improved matching**
   - Re-run RD coverage construction with 93.5% concordance
   - Update deaths linkage with new match rates

### Medium-Term

1. **Assess post-1930s strategy**
   - Current: 61% coverage in 1935, 30% in 1975
   - Options:
     - Accept coverage loss and flag uncertainty
     - Build RD→LGD crosswalk (1911–1971) for alternative geography
     - Restrict spatial analyses to pre-1930s period

2. **Visualize results**
   - Map coverage trends 1851–1990
   - Overlay constructed vs official RD boundaries
   - Create confidence scores per RD-year

3. **Link to deaths data at scale**
   - Currently tested 4 sample years
   - Process all 140 years (1850–1990)
   - Quantify spatial uncertainty per record

### Long-Term

1. **Explore LGD crosswalk** (if post-1930s coverage critical)
   - Match RDs to Local Government Districts using name + spatial proximity
   - Leverage LGD shapefiles (1911–1971) as alternative geography

2. **Sensitivity analyses**
   - How do results change with different match rate thresholds?
   - What if we exclude RDs with matched_share < 50%?

3. **Publication**
   - Document methodology for reproducibility
   - Report coverage metrics transparently
   - Provide harmonized dataset for research community

---

## File Structure

```
Harmonization/
├── readme.md (this file)
├──
├── Reference Data
│   ├── 1851EngWalesParishandPlace.csv (1851 parish polygons)
│   └── RD_shapefiles/ (official RD boundaries 1851-1911)
│
├── Pipeline Scripts (run in order)
│   ├── 1_get_ukbmd_district_urls.py
│   ├── 2_scrape_ukbmd_table1_all.py
│   ├── 3_match_ukbmd_to_1851_parishes.py ← IMPROVED (93.5%)
│   ├── 4_construct_rd_from_1851_parishes_all_census.py
│   ├── 5_rd_centroid_diagnostic_all_census.py
│   ├── 6_rd_year_summary_1851_backbone.py
│   ├── 7_impute_unmatched_to_nearest_1851_rd_centroid.py
│   ├── 8_build_rd_year_coverage_1851_1990.py
│   ├── 9_batch_match_deaths_to_coverage.py (empirical test)
│   └── 10_qa_rd_year_coverage_1851_1990.py
│
├── data_outputs/ (organized final deliverables)
│   ├── 1_parish_matching/
│   │   ├── parish_rd_allyears_concordance.csv (93.5% match rate)
│   │   └── parish_rd_allyears_unmatched.csv
│   ├── 2_rd_construction/
│   │   └── rd_constructed_from_1851_parishes.gpkg
│   ├── 3_validation/
│   │   └── rd_centroid_diagnostic_all_years.csv
│   ├── 4_final_coverage/
│   │   └── rd_year_coverage_1851_backbone_1851_1990.csv ← MAIN OUTPUT
│   ├── 5_deaths_linkage/
│   │   └── linkage_summary_all_years.csv (empirical testing)
│   └── 6_qa/
│       └── qa_rd_year_coverage_1851_1990/ (quality assurance)
│
├── analysis/ (optional analysis scripts)
│   ├── analyze_unmatched_parishes.py
│   ├── analyze_remaining_unmatched.py
│   └── visualize_coverage_trends.py
│
└── archive/ (old versions for reference)
```

---

## Citation & Attribution

- **1851 Parish Boundaries**: GBHGIS / UK Data Service
- **RD Shapefiles (1851–1911)**: GBHGIS / UK Data Service
- **Parish Composition Data**: Scraped from UKBMD (https://www.ukbmd.org.uk/)
- **Death Records**: FreeBMD (https://www.freebmd.org.uk/)

---


**Last updated:** 12 February 2026
