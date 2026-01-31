
# Parish–Registration District Harmonisation (1851 Anchor)

## Goal
Construct a consistent **Registration District (RD) × year spatial reference** anchored to **1851 civil parish geography**, and assess which RDs can be reliably represented on this fixed backbone over time.

The output is designed for downstream linkage of births/deaths and other RD-level outcomes to a stable historical geography.

---

## Reference geography
- **1851 England & Wales civil parish polygons**  
  Source: GBHGIS / UK Data Service  
  File: `Harmonization/1851EngWalesParishandPlace.csv` (WKT geometry)

This is the earliest complete, open parish boundary dataset available.

---

## Administrative data
- **UKBMD Registration District parish composition (Table 1)**  
  Source: UKBMD  
  Coverage: all districts, all years

Scraped and combined into an all-years parish–RD membership table.

---

## Parish–RD matching (1851 anchor)

### Temporal eligibility
Parishes are eligible for spatial matching if their period of existence overlaps 1851:



### Matching approach
Deterministic name normalisation only (no fuzzy matching):
- case folding and whitespace normalisation  
- punctuation, brackets, and parenthesis removal  
- *St / St. / Saint* harmonisation  
- `& → and`, `cum → with`  
- hyphens and slashes treated as word separators  
- handling of urban prefixes (e.g. `DOVER, …`)  

Implemented in:
- `Harmonization/match_ukbmd_to_1851_parishes.py`

### Results
- Parish–RD rows eligible for 1851 geometry: **15,976**
- Matched to 1851 parish polygons: **14,264** (**≈89%**)

Unmatched cases reflect genuine historical differences (e.g. post-1851 parish creation, urban subdivision, naming complexity).

---

## RD reconstruction by census year (1851–1911)

For each census year (1851, 1861, …, 1911):

1. Filter parish–RD membership active in that year  
2. Retain only parishes matched to 1851 geometry  
3. Dissolve 1851 parish polygons by RD  

Output:
- `Harmonization/data_outputs/rd_constructed_from_1851_parishes.gpkg`  
  - Layers: `rd_{year}_constructed`

The number of constructed RDs declines over time as some later RDs contain no 1851-eligible parishes.

---

## Spatial validation (centroid diagnostics)

### Validation data
- Official RD polygons for each census year  
  Source: GBHGIS / UK Data Service  
  Files:  
  `Harmonization/RD_shapefiles/ukds_ew{year}_regdistricts/EW{year}_regdistricts.shp`

### Method
- Compare centroids of constructed RDs to centroids of official RD polygons  
- Matching rule:
  - centroid falls within official polygon (primary)
  - nearest neighbour fallback if not

Implemented in:
- `Harmonization/rd_centroid_diagnostic_all_census.py`

### Key finding
Centroid accuracy is **stable from 1851 to 1911**:
- Median distance ≈ **4–5 km**
- 95th percentile ≈ **11 km**
- Nearest-neighbour fallback < **1%**

This supports the centroid-based validation strategy.

---

## Coverage analysis (representability)

By 1911:
- Active RDs: **631**
- RDs with zero matched 1851 parishes: **104**

These districts cannot be represented on an 1851 parish backbone for structural reasons (late creation, urban restructuring), not due to matching error.

Coverage is quantified for **each census year**, producing a time series of representability.

---

## Final harmonised output (main deliverable)

### ✅ Final file



### Structure
One row per **RD × year**, containing:
- coverage metrics (active vs matched parish rows)
- `usable_1851_backbone` flag
- number of contributing 1851 parishes
- centroid location (x, y)
- centroid diagnostic distance and match type
- dominant contributing 1851 parish (by area)
- explicit geometry source flag

This is the **analysis-ready output** of the harmonisation.

---

## Supporting files (not final outputs)
- `parish_rd_allyears_concordance.csv` — administrative parish–RD membership  
- `rd_constructed_from_1851_parishes.gpkg` — reconstructed RD geometries  
- `rd_centroid_diagnostic_all_years.csv` — validation diagnostics  

---

## Known limitations
- RDs composed entirely of post-1851 parishes cannot be reconstructed on the 1851 backbone  
- Centroid diagnostics assess location accuracy, not full boundary equivalence  
- Urban districts and multipart geometries are the primary sources of discrepancy  

---

## Conclusion
A substantial majority of Registration Districts can be consistently represented on a fixed 1851 parish geography through 1911. Where representation is possible, centroid locations remain stable and geographically plausible. Coverage loss over time is structural and explicitly documented, enabling transparent downstream analysis.
