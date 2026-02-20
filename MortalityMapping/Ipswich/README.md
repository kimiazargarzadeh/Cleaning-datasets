# Ipswich Deaths Dataset (1871-1910)

Individual-level mortality for Ipswich with actual recorded causes of death.

## Summary

- 42,939 deaths (1871-1910)
- 99.9% with actual cause (not probabilistic)
- 44.4% with parent info (for infant/child deaths)
- 24 essential columns (cleaned from 65)
- 100% spatial linkage using official GBHGIS RD centroids

## Comparison to FreeBMD

| Feature | Ipswich | FreeBMD |
|---------|---------|---------|
| Cause of death | Actual recorded | Assigned via probabilities |
| Coverage | Ipswich only | All England & Wales |
| Parent linkage | 26% have parent names | None |
| Occupation | 64.5% | None |
| Street addresses | 78% | Only RD |

**Primary use:** Validate FreeBMD ecological inference and micro-level Ipswich analysis

## Column Design (24 columns)

### Core (5)
- final_id: Unique identifier
- death_year_clean, death_date, decade, qod: Temporal data

### Person (5)
- surname, deceaseds_forenames: Names
- sex_std, age_numeric, age_group: Demographics (standardized)

### Location (1)
- tidy_street: Street name (78% coverage, for neighborhood wealth coding)

### Family (3)
**Why keep:** 26% of deaths (11,348) are children with parent info
- relationship_of_deceased_to_relative: "Son of", "Daughter of" (identifies parent-child links)
- relatives_forenames, relatives_surname: Parent/spouse name (enables family clustering and wealth linkage)

Use cases:
- Link infant deaths to father's occupation/wealth
- Identify families with multiple child deaths
- Match to census for full household structure

### Occupation (1)
- occupation_of_relative_or_deceased: 64.5% coverage (HISCO/HISCAM coding for social class)

### Cause (3)
- cause_of_death: Verbatim text as recorded
- mo's_classification_of_cause_of_death: Medical Officer's classification (54% coverage)
- cause_of_death_category: Standardized category (100%)

Top causes: Tuberculosis (12%), Elderly conditions (9%), Bronchitis (8%), Heart (6%)

### FreeBMD Matching (2)
- surname_for_matching, forenames_for_matching: Normalized for name matching

### Spatial (4) - Geography at the end
- reg_dist_std: Sub-district name (Ipswich Eastern, Western, St Matthew, St Margaret, St Clement)
- centroid_x, centroid_y: Official GBHGIS RD centroids (British National Grid EPSG:27700)
- polygon_layer: Reference to full RD boundaries (e.g., "rd_1871_constructed")

Spatial note: Centroids use official GBHGIS data (1851-1881) with 1881 centroid extended to later years. All Ipswich sub-districts map to same RD centroid. For fine-grained spatial analysis, geocode street addresses (78% coverage).

## Quick Usage

Load and explore:
```python
import pandas as pd

df = pd.read_csv('MortalityMapping/Ipswich/data_outputs/ipswich_deaths_1871_1910_cleaned.csv')

# Top causes
print(df['cause_of_death_category'].value_counts().head(10))

# Infant deaths with parent info
infants = df[df['relationship_of_deceased_to_relative'].str.contains('Son of|Daughter of', na=False)]
print(f"Infant/child deaths with parent names: {len(infants):,}")
```

Link to parents/wealth:
```python
# Infant mortality by father's occupation
infants['father_occupation'] = infants['occupation_of_relative_or_deceased']
infant_mort_by_occ = infants.groupby('father_occupation').size().sort_values(ascending=False)
```

Match to FreeBMD (validation):
```python
# Once FreeBMD 1871-1910 is cleaned
fbmd = pd.read_csv('../data_outputs/deaths_1871_with_causes.csv')
fbmd_ipswich = fbmd[fbmd['district'].str.contains('Ipswich', case=False, na=False)]

# Match on: surname, age, sex, year
matches = df.merge(fbmd_ipswich,
    left_on=['surname_for_matching', 'age_numeric', 'sex_std', 'death_year_clean'],
    right_on=['surname_for_matching', 'age_numeric', 'sex', 'yod'],
    how='inner')

# Compare actual cause (Ipswich) vs probabilistic cause (FreeBMD)
```

## Research Applications

1. **Wealth-health gradients** - Occupation as social class proxy (see `analyze_wealth_health.py`)
2. Validate FreeBMD ecological inference - Compare actual vs assigned probabilities
3. Infant mortality by social class - Link children to father's occupation
4. Family disease clustering - Identify families with multiple deaths
5. Neighborhood health disparities - Compare sub-districts (Eastern vs Western)

### Key Finding (analyze_wealth_health.py)

**Heterogeneous health improvements (1880-1910):**
- Skilled workers: +25 years median age at death
- Elite: +7 years
- Unskilled: +1 year

Victorian health technology exacerbated inequality - skilled workers benefited enormously while the poor saw almost no improvement.

## File Structure

```
MortalityMapping/Ipswich/
├── README.md
├── clean_ipswich_deaths.py
├── analyze_wealth_health.py          (wealth-health gradient analysis)
├── data_outputs/
│   └── ipswich_deaths_1871_1910_cleaned.csv (42,939 deaths, 24 columns)
└── analysis_outputs/
    ├── wealth_health_analysis.png    (4-panel visualization)
    └── key_findings.csv              (summary statistics)
```

**Run analysis:** `python3 MortalityMapping/Ipswich/analyze_wealth_health.py`

## Data Source

UKDA-5413: Sociological Study of Fertility and Mortality in Ipswich, 1872-1910
Location: /Users/kimik/Ellen Dropbox/.../UKDA-5413-tab/tab/ipswich_deaths_1871_1910_mse.tab
Citation: Garrett, E., Reid, A., Schürer, K., Szreter, S. (2007)

Created: February 2026
Project: WealthisHealth - Victorian Mortality and Economic History
