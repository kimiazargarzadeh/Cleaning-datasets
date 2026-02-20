# MortalityMapping

Individual-level mortality dataset for Victorian England (1866–1910): FreeBMD deaths + spatial locations + cause-of-death probabilities.

## What This Does

Maps individual deaths to Registration Districts and assigns cause probabilities using ecological inference:

```
INPUT:  FreeBMD deaths (name, age, sex, district, year)
        + Aggregate cause data (RD × decade × age × sex)
OUTPUT: deaths_{year}_with_causes.csv (spatial + cause probabilities)
```

**Example output:**
```csv
surname, age, sex, district, centroid_x, centroid_y, cause_distribution
Smith, 35, F, Bethnal Green, 533500, 182000, '{"Phthisis": 0.342, "Pneumonia": 0.094, ...}'
```

## Methodology

**Ecological inference:** Assign probabilities based on aggregate cause distributions.

1. Map individual → group: `(RD, decade, age_group, sex)`
2. Look up cause distribution from `cause_ew_reg_dec.tab`
3. Assign **probability distribution** (not certainty) to individual

**Key insight:** We preserve exact aggregate distributions while enabling individual-level analysis and linkage

---

## Data Sources

1. **FreeBMD Deaths** (`Dropbox/freebmd/Deaths/cleaned/`): Individual records, 1866–1910
2. **Cause data** (`cause_ew_reg_dec.tab`): ~70 causes × RD × decade × age × sex
3. **Mortality totals** (`mort_age_ew_reg_dec.tab`): Official death counts for validation
4. **RD Spatial** (`Harmonization/data_outputs/`): Centroids + polygons from 1851 backbone

---

## Output Format: `deaths_{year}_with_causes.csv`

**16 columns:**

**Core data:** surname, firstnames, yod, qod, age_numeric, age_group, sex, decade, district, total_deaths_in_group, cause_distribution

**Spatial data:** district_norm, rd_name, centroid_x, centroid_y, matched_share

**Cause distribution** (JSON format):
```json
{"Phthisis": 0.342, "Pneumonia": 0.094, "Heart Disease": 0.089, ...}
```
Probabilities sum to 1.0 per individual

---

## Centroids vs Polygons: The Strategy

**Why both?** The 1851 backbone provides RD centroids (x, y points) AND full polygons.

### Centroids (In Main Dataset)
- **What:** Single point per RD → `(533500, 182000)`
- **Size:** 16 bytes/death → 335 MB for 464k deaths
- **Use for:** Plotting, distance calculations, most analysis
- **Stored in:** `deaths_{year}_with_causes.csv` (columns: `centroid_x`, `centroid_y`)

### Polygons (Separate File)
- **What:** Full RD boundaries → `MULTIPOLYGON(...)`
- **Size:** ~1000+ bytes/death → would make CSV 100× larger
- **Use for:** Choropleth maps, area calculations, GIS work
- **Stored in:** `Harmonization/.../rd_constructed_from_1851_parishes.gpkg`

### Strategy: Keep CSV Small, Join Polygons When Needed

```python
import pandas as pd
import geopandas as gpd

# Load deaths (lightweight)
deaths = pd.read_csv('deaths_1866_with_causes.csv')

# Load polygons only when mapping
rd_polys = gpd.read_file('../Harmonization/.../rd_constructed_from_1851_parishes.gpkg')

# Join for choropleth maps
deaths_map = deaths.merge(rd_polys[['district', 'geometry']],
                          left_on='rd_name', right_on='district')
deaths_map.plot(column='top_cause', legend=True)
```

---

## Quick Usage

### Parse Cause Distributions
```python
import pandas as pd
import json

df = pd.read_csv('deaths_1866_with_causes.csv')

# Get top cause
def get_top_cause(json_str):
    if pd.isna(json_str): return None
    causes = json.loads(json_str)
    return max(causes.items(), key=lambda x: x[1])[0]

df['top_cause'] = df['cause_distribution'].apply(get_top_cause)
print(df['top_cause'].value_counts().head(10))
```

### Plot Deaths Spatially
```python
import matplotlib.pyplot as plt

plt.scatter(df['centroid_x'], df['centroid_y'], alpha=0.1, s=1)
plt.xlabel('Easting (BNG)')
plt.ylabel('Northing (BNG)')
plt.title('Death Locations, 1866')
```

---

## Coverage (1866)

- **Total deaths:** 464,383 (90.5% of raw file have valid age)
- **Spatially linked:** 425,065 (91.5%)
- **With cause probabilities:** 411,722 (88.7%)
- **Unique RDs:** 691
- **Unique groups:** 18,674 (RD × decade × age × sex)

*Missing coverage:* ~8.5% RDs without 1851 parish matches, ~2.8% no cause data

---

## File Structure

```
MortalityMapping/
├── README.md                              ← You are here
├── map_deaths_to_rd_with_causes.py       ← Main script
└── data_outputs/
    └── deaths_1866_with_causes.csv       ← Output (335 MB)
```

---

## Running the Script

```bash
# Edit YEAR in map_deaths_to_rd_with_causes.py
python3 MortalityMapping/map_deaths_to_rd_with_causes.py
```

**Performance:** ~20 seconds/year | Total 1866-1910: ~15-20 minutes

---

## Data Quality

- **matched_share:** Fraction of RD area matched to 1851 parishes (0.0–1.0; ≥0.8 = high quality)
- **Age groups:** Victorian bins (a_0, a_1, a_2_4, a_5_9, ..., a_75_up)
- **Validation:** Probabilities sum to 1.0; aggregating back reproduces exact RD-level distributions

---

## Research Applications

- **Temporal:** Disease evolution (TB decline, epidemic years)
- **Spatial:** Hotspot detection, urban/rural patterns, infrastructure effects
- **Linkage:** Probate records → wealth/mortality analysis
- **Policy:** Sanitation spending, Public Health Act effects, water infrastructure

---

**Data sources:** FreeBMD, UK Data Archive Study 9034
**Project:** WealthisHealth | **Created:** February 2026
