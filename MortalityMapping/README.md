# MortalityMapping

Individual-level Victorian England deaths (1866-1910) with spatial locations and cause probabilities via ecological inference.

## Overview

I map FreeBMD deaths to RD centroids and assign cause probabilities from aggregate statistics.

**Input:** Deaths (name, age, sex, district) + Cause stats (RD × decade × age × sex)
**Output:** `deaths_{year}_with_causes.csv` (23 columns)
**Method:** Ecological inference - assign probabilities based on (RD, decade, age_group, sex) groups

## Results (1866)

- Total deaths: 464,383
- Spatial coverage: 91.5% (425,065 deaths)
- With causes: 88.7% (411,722 deaths)
- Certain causes: 74.6% (346,565 deaths)
- Uncertain causes: 25.4% (117,818 deaths)

**Why uncertain (25.4%):**
- Never matched to 1851 parishes: 13.6% (Liverpool, Birmingham, London)
- Unstable boundaries over time: 11.8% (Manchester, etc.)

**Coverage includes:** Liverpool (10,896), Birmingham (5,420), London (~20,000) - 100% spatial, >99% causes

## Critical Limitation: RD Boundary Mismatch

**Problem:** Cause statistics use time-varying RD boundaries (RDs as they existed each decade), but I map deaths to fixed 1851 backbone boundaries.

**Impact:** 25.4% of deaths may have wrong cause probabilities:
- 13.6% never matched to 1851 parishes (no validation)
- 11.8% in unstable RDs (boundary changes over time)

**Sensitivity test:** Top 5 causes identical, max difference 2.2% (Diseases of Lungs) → **minimal impact**.

## How I Handle It

1. **`cause_uncertain` flag:** Marks deaths with uncertain causes (25.4%)
   - True if: never matched to parishes (13.6%) OR unstable boundaries (11.8%)
   - False if: matched to parishes AND stable boundaries (74.6%)

2. **`cause_distribution_adjusted`:** Weights probabilities by matched_share
   - For matched_share < 0.8: scales down causes, adds "uncertain_boundary_mismatch"
   - For matched_share = 0: all probability goes to uncertainty category

3. **Integrated sensitivity analysis:** Optional flag to test certain vs all deaths (set `RUN_SENSITIVITY = True`)

4. **Validation framework:** Ipswich actual causes comparison (archived for future use)

**Recommendation:** Use `cause_uncertain==False` for primary analysis (74.6% of data), report robustness with all deaths.

## Output Format (23 columns)

**Core (12):** surname, firstnames, yod, qod, age_numeric, age_group, sex, decade, district, total_deaths_in_group, cause_distribution, cause_distribution_adjusted

**Spatial (11):** district_norm, rd_name, centroid_x, centroid_y, centroid_source, matched_share, boundary_stability, boundary_change_std, spatial_quality, spatial_confidence, cause_uncertain

**Cause distributions (JSON):**
- `cause_distribution`: Original {"Phthisis": 0.342, "Pneumonia": 0.094, ...}
- `cause_distribution_adjusted`: Weighted by matched_share {"Phthisis": 0.257, ..., "uncertain_boundary_mismatch": 0.250}

## Why 1851 Backbone (Not Official GBHGIS)

**Coverage > precision for ecological inference.**

- 1851 backbone: 91.5% coverage, includes Liverpool/Birmingham/London
- Official GBHGIS: 79.9% coverage, missing major cities (640 RDs vs 682)
- Task is: death → RD name → cause lookup (not precise spatial analysis)
- RD names in 1851 backbone match cause statistics perfectly

**Trade-off:** Better coverage (91.5%) with boundary mismatch (25.4% uncertain) vs lower coverage (79.9%) with no major cities.

## Quick Usage

```python
import pandas as pd
import json

df = pd.read_csv('deaths_1866_with_causes.csv')

# Primary analysis: certain causes only
df_certain = df[df['cause_uncertain'] == False]  # 74.6% of data

# Get top cause
def get_top_cause(json_str):
    if pd.isna(json_str): return None
    causes = json.loads(json_str)
    return max(causes.items(), key=lambda x: x[1])[0]

df_certain['top_cause'] = df_certain['cause_distribution'].apply(get_top_cause)
print(df_certain['top_cause'].value_counts().head(10))
```

## Scripts

- `map_deaths_to_rd_with_causes.py` - Main script (change YEAR in config, run for each year)
- `archive/` - Validation scripts (for future use)

**Run:** `python3 MortalityMapping/map_deaths_to_rd_with_causes.py` (~20 sec/year)

**Sensitivity analysis:** Set `RUN_SENSITIVITY = True` to test certain vs uncertain deaths

## Questions for Supervisor (Before Processing 1867-1910)

**About 1866 results:**

1. **Uncertainty:** 25.4% of deaths flagged as uncertain (13.6% never matched to parishes + 11.8% unstable boundaries). Sensitivity analysis shows <2% impact on top causes. Is this acceptable for research?

2. **Data choice:** Should I continue with 1851 backbone (91.5% coverage) or wait for GBHGIS parish boundaries (better precision but currently incomplete)?

3. **Coverage:** 88.7% of deaths have cause probabilities. Is this sufficient or should I aim higher?

4. **Analysis approach:** Should I:
   - Filter to certain causes only (74.6% of data, conservative)
   - Use all causes with `cause_uncertain` flag (88.7% of data, documented limitation)
   - Use `cause_distribution_adjusted` for uncertain deaths

5. **Validation:** Should I wait for Ipswich validation results (1871-1910) before processing more years?

**Decision needed:**

✓ If approach is acceptable → Process 1867-1910 (same methodology)
✗ If issues found → Revise methodology before continuing

**Next steps if approved:**
- Process 1867-1910 once FreeBMD cleaning complete
- Validate with Ipswich (1871-1910)
- Rebuild with GBHGIS when parish boundaries available

---

Data sources: FreeBMD, UK Data Archive Study 9034
Project: WealthisHealth | Created: February 2026
