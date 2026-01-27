# Parish–Registration District Harmonisation (1851 Anchor)

## Goal
Assess whether UKBMD Registration District (RD) parish lists can be reliably linked to a spatial parish backbone, and whether parish-based reconstruction provides an adequate spatial representation of RDs in 1851.

## Reference geography
- **1851 England & Wales civil parish polygons**  
  Source: GBHGIS / UK Data Service  
  File: `Harmonization/1851EngWalesParishandPlace.csv` (geometry column)

This is the earliest complete, open parish boundary dataset available.

## Temporal filter
Parishes retained if their period of existence overlaps 1851  
(`From ≤ 1851 ≤ To`, using UKBMD dates).

Implemented in:
- `Harmonization/match_ukbmd_to_1851_parishes.py`

## Data construction
1. **Parish–RD composition**
   - Scraped UKBMD Registration District pages (Table 1: parish composition)
   - Output:  
     `Harmonization/data_outputs/parish_rd_1851_concordance.csv`

2. **Parish ↔ RD concordance (1851)**
   - National parish–Registration District lookup constructed from UKBMD
   - Key output used in all downstream steps:
     - `parish_rd_1851_concordance.csv`

3. **Constructed RD geometries**
   - 1851 parish polygons dissolved by Registration District
   - Script:
     - `Harmonization/construct_rd_from_1851_parishes.py`
   - Output:
     - `Harmonization/data_outputs/rd_constructed_from_1851_parishes.gpkg`
     - Layer: `rd_1851_constructed`

## Matching approach (parish level)
Deterministic name normalisation only (no fuzzy matching):
- case folding and whitespace normalisation
- punctuation, brackets, and parenthesis removal
- *St / St. / Saint* harmonisation
- `& → and`, `cum → with`
- hyphens and slashes treated as word separators
- handling of urban prefixes (e.g. `DOVER, …`)
- partial handling of subdivided urban parishes (ongoing)

Implemented in:
- `Harmonization/match_ukbmd_to_1851_parishes.py`

## Parish-level results
- Total parish–district rows: **15,976**
- Matched to 1851 parish polygons: **14,264** (**≈89%**)

Unmatched cases largely reflect genuine historical differences (e.g. parishes not distinct in 1851, urban sub-districts, or complex naming variants).

## Spatial validation (Registration District level)

### Validation data
- **Official 1851 Registration District polygons**  
  Source: GBHGIS / UK Data Service (Study 9032)  
  File:
  - `Harmonization/RD_shapefiles/ukds_ew1851_regdistricts/EW1851_regdistricts.shp`

### Validation method
- Constructed RD polygons compared to official 1851 RD polygons
- Validation based on **centroid proximity**
- Script:
  - `Harmonization/rd_centroid_diagnostic_1851.py`

Matching rule:
- reconstructed RD centroid falls within official RD polygon (primary)
- nearest official polygon used as fallback (8 cases)

### Centroid distance summary
- Median: **4.8 km**
- 90th percentile: **≈10 km**
- 95th percentile: **≈11.5 km**
- Maximum: **≈22 km**

Outputs:
- `Harmonization/data_outputs/rd_centroid_diagnostic_1851.csv`
- `Harmonization/data_outputs/rd_centroid_diagnostic_1851.gpkg`

These results indicate that parish-based RD reconstruction places districts in broadly correct geographic locations at national scale.

## Known limitations
- Centroid proximity does not guarantee identical parish composition
- A small number of RDs show larger centroid offsets or ambiguous nearest matches
- Urban districts and multipart geometries are the main sources of discrepancy

## Conclusion
Linking UKBMD Registration District parish lists to the 1851 parish geography is feasible at national scale. Parish-based reconstruction provides a reasonable spatial approximation of Registration Districts in 1851 and is suitable as a baseline spatial anchor for downstream harmonisation and linkage tasks.

## Next steps
- Replace centroid-based diagnostics with **polygon overlap–based validation**
- Quantify overlap shares between constructed and official RD polygons
- Manually review high-discrepancy and nearest-matched cases
- Extend reconstruction forward using parish evolution where data permit
