"""
Map individual FreeBMD deaths to RD locations and assign cause probabilities.

Process:
  1. Load cleaned death records (post-1866 with age column)
  2. Spatial mapping: death district → RD centroid from 1851 backbone
  3. Cause assignment: ecological inference from aggregate RD-level data
     For each individual: (RD, decade, age_group, sex) → cause probability distribution

Output: deaths_{year}_with_causes.csv
  - Individual deaths with spatial coordinates (centroid_x, centroid_y)
  - Cause probability distributions (JSON format)
  - Spatial quality metrics (boundary_stability, spatial_confidence)

Method: Ecological inference + vectorized processing for speed

Note: Uses 1851 backbone centroids (not official GBHGIS) for better coverage.
      Official GBHGIS missing major cities (Liverpool, Birmingham, London districts).
      For ecological inference, coverage > precision: need RD name to match cause stats.
"""

import re
import json
import pandas as pd
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

YEAR           = 1866       # Year to process
USE_SAMPLE     = False      # True = 10k sample (testing), False = full dataset
SAMPLE_SIZE    = 10000
USE_OFFICIAL_RDS = False    # False = use 1851 backbone (better coverage for ecological inference)
RUN_SENSITIVITY = False     # True = run sensitivity analysis comparing certain vs uncertain deaths

# Paths
DROPBOX_DEATHS = Path("/Users/kimik/Ellen Dropbox/Kimia Zargarzadeh/WealthisHealth/freebmd/Deaths/cleaned")
CAUSE_FILE     = Path("/Users/kimik/Ellen Dropbox/Kimia Zargarzadeh/WealthisHealth/1851-1910 Age- and Cause-Specific Mortality in E&W/tab/cause_ew_reg_dec.tab")
MORTALITY_FILE = Path("/Users/kimik/Ellen Dropbox/Kimia Zargarzadeh/WealthisHealth/1851-1910 Age- and Cause-Specific Mortality in E&W/tab/mort_age_ew_reg_dec.tab")
COVERAGE_FILE  = Path("Harmonization/data_outputs/4_final_coverage/rd_year_coverage_1851_backbone_1851_1990.csv")
OFFICIAL_CENTROIDS_FILE = Path("Harmonization/data_outputs/3_validation/official_rd_centroids.csv")
CENTROIDS_FILE = Path("Harmonization/data_outputs/4_final_coverage/rd_year_summary_1851_backbone_with_imputed_centroids.csv")
OUT_DIR        = Path("MortalityMapping/data_outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Constants
DECADE         = (YEAR // 10) * 10  # 1866 → 1860
MAX_AGE        = 105
MIN_AGE        = 0

# Age bins (matching cause file structure)
AGE_BINS = [
    (0, 0, "a_0"), (1, 1, "a_1"), (2, 4, "a_2_4"), (5, 9, "a_5_9"),
    (10, 14, "a_10_14"), (15, 19, "a_15_19"), (20, 24, "a_20_24"),
    (25, 34, "a_25_34"), (35, 44, "a_35_44"), (45, 54, "a_45_54"),
    (55, 64, "a_55_64"), (65, 74, "a_65_74"), (75, 999, "a_75_up"),
]

# ══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def normalize_district(s):
    """Normalize district name for matching."""
    if pd.isna(s) or str(s).strip() == "":
        return None
    s = str(s).lower().strip()
    s = re.sub(r'\s*\(\d{4}[^)]*\)', '', s)
    s = s.replace("&", "and").replace("-", " ")
    return " ".join(s.split())

def map_age_to_group(age):
    """Map individual age to aggregate age group."""
    try:
        age_val = float(age)
        if not (MIN_AGE <= age_val <= MAX_AGE):
            return None
        for low, high, col in AGE_BINS:
            if low <= age_val <= high:
                return col
        return "a_75_up"
    except (ValueError, TypeError):
        return None

def map_sex(gender):
    """Map gender to M/F."""
    if pd.isna(gender):
        return None
    g = str(gender).lower().strip()
    if g in ["m", "male"]:
        return "M"
    elif g in ["f", "female"]:
        return "F"
    return None

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 1: LOAD & SPATIAL MAPPING
# ══════════════════════════════════════════════════════════════════════════════

print("="*70)
print(f"Processing {YEAR} deaths")
print("="*70)

# Load deaths
fpath = DROPBOX_DEATHS / f"cleaned_freebmd_deaths_{YEAR}.csv"
print(f"Loading: {fpath.name}")
df = pd.read_csv(fpath, low_memory=False)
n_total = len(df)

# Filter valid age
if "age" not in df.columns:
    raise ValueError("No age column - this script requires post-1866 data with age")

df["age_numeric"] = pd.to_numeric(df["age"], errors="coerce")
df = df[df["age_numeric"].between(MIN_AGE, MAX_AGE)].copy()
print(f"  {len(df):,} with valid age ({len(df)/n_total*100:.1f}%)")

# Sample if requested
if USE_SAMPLE:
    df = df.sample(n=min(SAMPLE_SIZE, len(df)), random_state=42).copy()
    print(f"  Using {len(df):,} sample for testing")

n_records = len(df)

# Map age, sex, and decade
df["age_group"] = df["age_numeric"].apply(map_age_to_group)
df["sex"] = df.get("gender_final", pd.Series(dtype=str)).apply(map_sex)
df["decade"] = DECADE  # Explicit decade column for transparency
df["district_norm"] = df["district"].apply(normalize_district)

# Load RD coverage
print(f"\nSpatial mapping:")
cov = pd.read_csv(COVERAGE_FILE)
cov["district_norm"] = cov["district"].apply(normalize_district)
cov_year = cov[cov["year"] == YEAR].copy()

# Get centroids from nearest census year
CENSUS_YEARS = [1851, 1861, 1871, 1881, 1891, 1901, 1911]
nearest_census = min(CENSUS_YEARS, key=lambda y: abs(y - YEAR))

if USE_OFFICIAL_RDS:
    print(f"  Using official GBHGIS RD centroids from {nearest_census}")
    cent = pd.read_csv(OFFICIAL_CENTROIDS_FILE)
    cent = cent[cent["year"] == nearest_census].copy()
    cent = cent.rename(columns={'official_x': 'centroid_x', 'official_y': 'centroid_y'})
    cent["district_norm"] = cent["district"].apply(normalize_district)
    cent["centroid_source"] = "official_rd"
else:
    print(f"  Using 1851 backbone centroids from {nearest_census}")
    cent = pd.read_csv(CENTROIDS_FILE)
    cent = cent[cent["year"] == nearest_census].copy()
    cent["district_norm"] = cent["district"].apply(normalize_district)
    cent["centroid_source"] = "1851_backbone"

# Merge coverage + centroids
centroid_cols = ["district_norm", "centroid_x", "centroid_y"]
if "centroid_source" in cent.columns:
    centroid_cols.append("centroid_source")

cov_year = cov_year.merge(
    cent[centroid_cols],
    on="district_norm",
    how="left"
).drop_duplicates("district_norm")

# Join deaths to RD
merge_cols = ["district_norm", "district", "centroid_x", "centroid_y", "matched_share"]
if "centroid_source" in cov_year.columns:
    merge_cols.append("centroid_source")

df = df.merge(
    cov_year[merge_cols],
    on="district_norm",
    how="left",
    suffixes=("", "_rd")
)

if "district_rd" in df.columns:
    df = df.rename(columns={"district_rd": "rd_name"})

n_linked = df["centroid_x"].notna().sum()
print(f"  Linked: {n_linked:,} / {n_records:,} ({n_linked/n_records*100:.1f}%)")

# Keep essential columns only
keep_cols = [
    "surname", "firstnames", "district", "yod", "qod",
    "age_numeric", "age_group", "sex", "decade",
    "district_norm", "rd_name", "centroid_x", "centroid_y", "centroid_source", "matched_share"
]
keep_cols = [c for c in keep_cols if c in df.columns]
df = df[keep_cols].copy()

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 2: CAUSE ASSIGNMENT (VECTORIZED FOR SPEED)
# ══════════════════════════════════════════════════════════════════════════════

print(f"\nCause assignment (decade {DECADE}):")

# Load cause data
cause = pd.read_csv(CAUSE_FILE, sep="\t", low_memory=False)
cause_decade = cause[cause["decade"] == DECADE].copy()

# Exclude aggregate rows
EXCLUDE = ["Mean Population", "Total Deaths", "All Causes", "Total Births"]
cause_decade = cause_decade[~cause_decade["cause"].isin(EXCLUDE)].copy()
print(f"  {len(cause_decade):,} cause records loaded")

# Normalize district names
cause_decade["reg_dist_norm"] = cause_decade["reg_dist"].apply(normalize_district)

# Load mortality data (for official totals and population)
print(f"  Loading mortality data for validation...")
mort = pd.read_csv(MORTALITY_FILE, sep="\t", low_memory=False)
mort_decade = mort[mort["decade"] == DECADE].copy()
mort_decade["reg_dist_norm"] = mort_decade["reg_dist"].apply(normalize_district)

# OPTIMIZATION: Pre-compute cause distributions for unique (RD, sex, age_group) combinations
# This is 10-50× faster than row-by-row iteration

print(f"  Building cause distribution lookup...")

# Get unique groups in death data
unique_groups = df[['district_norm', 'sex', 'age_group']].drop_duplicates()
print(f"    {len(unique_groups):,} unique (RD, sex, age) groups")

# Build lookup: group_key → cause_distribution_json + total_deaths
cause_lookup = {}
total_deaths_lookup = {}

for _, row in unique_groups.iterrows():
    rd_norm = row['district_norm']
    sex = row['sex']
    age_group = row['age_group']

    # Skip if any field is missing
    if pd.isna(rd_norm) or pd.isna(sex) or pd.isna(age_group):
        continue

    # Create key
    key = f"{rd_norm}|{sex}|{age_group}"

    # Get official total deaths from mortality file
    # Column naming: m_35_44 for males, f_35_44 for females
    sex_prefix = sex.lower() if sex in ['M', 'F'] else None
    if sex_prefix:
        mort_col = f"{sex_prefix.lower()}_{age_group.replace('a_', '')}"
        mort_row = mort_decade[mort_decade["reg_dist_norm"] == rd_norm]

        if len(mort_row) > 0 and mort_col in mort_row.columns:
            total_official = mort_row.iloc[0][mort_col]
            total_deaths_lookup[key] = total_official
        else:
            total_official = None
    else:
        total_official = None

    # Get cause distribution for this group
    subset = cause_decade[
        (cause_decade["reg_dist_norm"] == rd_norm) &
        (cause_decade["sex"] == sex)
    ]

    if len(subset) == 0 or age_group not in subset.columns:
        cause_lookup[key] = None
        continue

    # Extract deaths by cause for this age group
    dist = subset[["cause", age_group]].copy()
    dist = dist.rename(columns={age_group: "deaths"})
    dist["deaths"] = pd.to_numeric(dist["deaths"], errors="coerce").fillna(0)

    # Use official total if available, otherwise sum causes
    if total_official and total_official > 0:
        total = total_official
    else:
        total = dist["deaths"].sum()

    # Compute probabilities
    if total > 0:
        dist["probability"] = dist["deaths"] / total

        # Convert to dictionary and then JSON
        cause_dict = dict(zip(dist["cause"], dist["probability"].round(4)))
        cause_lookup[key] = json.dumps(cause_dict, ensure_ascii=False)
    else:
        cause_lookup[key] = None

print(f"    Computed distributions for {len(cause_lookup):,} groups")

# VECTORIZED MAPPING: Use pandas map instead of row-by-row iteration
print(f"  Mapping to {n_records:,} deaths...")

# Create temporary key column
df['_key'] = (
    df['district_norm'].fillna('') + '|' +
    df['sex'].fillna('') + '|' +
    df['age_group'].fillna('')
)

# Map cause distributions and total deaths
df['cause_distribution'] = df['_key'].map(cause_lookup)
df['total_deaths_in_group'] = df['_key'].map(total_deaths_lookup)

# Clean up
df = df.drop(columns=['_key'])

# Load RD boundary stability from harmonization
# This tells us which RDs had changing boundaries over time
coverage_full = pd.read_csv(COVERAGE_FILE)
census_years = [1851, 1861, 1871, 1881, 1891, 1901, 1911]
coverage_census = coverage_full[coverage_full['year'].isin(census_years)].copy()

stability = coverage_census.groupby('district').agg({
    'matched_share': 'std'
}).round(3)
stability.columns = ['boundary_change_std']
stability['boundary_stability'] = 'stable'
stability.loc[stability['boundary_change_std'] > 0.2, 'boundary_stability'] = 'unstable'
stability.loc[stability['boundary_change_std'] > 0.3, 'boundary_stability'] = 'very_unstable'
stability = stability.reset_index()

# Merge stability to deaths
df = df.merge(stability[['district', 'boundary_stability', 'boundary_change_std']],
              left_on='rd_name', right_on='district', how='left', suffixes=('', '_stab'))
df = df.drop(columns=['district_stab'], errors='ignore')

# Add spatial quality flag based on matched_share
df['spatial_quality'] = 'missing'
df.loc[df['matched_share'] >= 0.8, 'spatial_quality'] = 'high'
df.loc[(df['matched_share'] >= 0.5) & (df['matched_share'] < 0.8), 'spatial_quality'] = 'medium'
df.loc[(df['matched_share'] < 0.5) & (df['matched_share'].notna()), 'spatial_quality'] = 'low'

# Combined spatial confidence (set in order: low -> medium -> high to avoid overwriting)
df['spatial_confidence'] = 'low'
df.loc[(df['matched_share'] >= 0.5) & (df['boundary_stability'].isin(['stable', 'unstable'])), 'spatial_confidence'] = 'medium'
df.loc[(df['matched_share'] >= 0.8) & (df['boundary_stability'] == 'stable'), 'spatial_confidence'] = 'high'

# Flag deaths with uncertain cause probabilities due to RD boundary mismatch
# Problem: Cause stats use time-varying RD boundaries, deaths mapped to fixed 1851 backbone
# Uncertain if: (1) unstable boundaries OR (2) matched_share = 0 (never matched to 1851 parishes)
df['cause_uncertain'] = False
df.loc[df['boundary_stability'].isin(['unstable', 'very_unstable']), 'cause_uncertain'] = True
df.loc[df['matched_share'] == 0.0, 'cause_uncertain'] = True  # Never matched to parishes

# Create adjusted cause distribution weighted by matched_share
# For low matched_share, add "uncertain_boundary" category to reflect spatial uncertainty
def adjust_cause_distribution(row):
    """Adjust cause probabilities based on matched_share to account for boundary uncertainty."""
    if pd.isna(row['cause_distribution']) or pd.isna(row['matched_share']):
        return row['cause_distribution']

    if row['matched_share'] >= 0.8:
        # High confidence - use original distribution
        return row['cause_distribution']

    # Low/medium confidence - scale probabilities and add uncertainty
    try:
        causes = json.loads(row['cause_distribution'])
        matched = row['matched_share']

        # Scale down all cause probabilities by matched_share
        adjusted = {cause: round(prob * matched, 4) for cause, prob in causes.items()}
        # Add uncertainty category for unmatched portion
        adjusted['uncertain_boundary_mismatch'] = round(1 - matched, 4)

        return json.dumps(adjusted, ensure_ascii=False)
    except:
        return row['cause_distribution']

df['cause_distribution_adjusted'] = df.apply(adjust_cause_distribution, axis=1)

# Reorder columns: put spatial/geographic data at the end for readability
core_cols = [
    'surname', 'firstnames', 'yod', 'qod',
    'age_numeric', 'age_group', 'sex', 'decade',
    'district', 'total_deaths_in_group',
    'cause_distribution', 'cause_distribution_adjusted'
]
spatial_cols = [
    'district_norm', 'rd_name',
    'centroid_x', 'centroid_y', 'centroid_source',
    'matched_share', 'boundary_stability', 'boundary_change_std',
    'spatial_quality', 'spatial_confidence', 'cause_uncertain'
]

# Keep only columns that exist
core_cols = [c for c in core_cols if c in df.columns]
spatial_cols = [c for c in spatial_cols if c in df.columns]
df = df[core_cols + spatial_cols]

n_assigned = df['cause_distribution'].notna().sum()
print(f"  Assigned: {n_assigned:,} / {n_records:,} ({n_assigned/n_records*100:.1f}%)")

# Save Stage 2: with causes
out2 = OUT_DIR / f"deaths_{YEAR}_with_causes.csv"
df.to_csv(out2, index=False)
print(f"  ✓ Saved: {out2.name}")

# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"Year:           {YEAR} (decade {DECADE} for causes)")
print(f"Deaths:         {n_records:,}")
print(f"Spatial:        {n_linked:,} ({n_linked/n_records*100:.1f}%)")
print(f"Causes:         {n_assigned:,} ({n_assigned/n_records*100:.1f}%)")
if 'cause_uncertain' in df.columns:
    n_certain = (df['cause_uncertain'] == False).sum()
    n_uncertain = df['cause_uncertain'].sum()
    print(f"Certain:        {n_certain:,} ({n_certain/n_records*100:.1f}%)")
    print(f"Uncertain:      {n_uncertain:,} ({n_uncertain/n_records*100:.1f}%)")
print(f"\nOutput:")
print(f"  {out2}")
print(f"\nFormat: JSON cause distribution")
print(f"  Example: {{'Tuberculosis': 0.425, 'Pneumonia': 0.21, ...}}")

# ══════════════════════════════════════════════════════════════════════════════
# SENSITIVITY ANALYSIS (Optional)
# ══════════════════════════════════════════════════════════════════════════════

if RUN_SENSITIVITY and 'cause_uncertain' in df.columns:
    print("\n" + "="*70)
    print("SENSITIVITY ANALYSIS: Certain vs All Deaths")
    print("="*70)

    # Split by uncertainty
    certain = df[df['cause_uncertain'] == False]
    uncertain = df[df['cause_uncertain'] == True]

    print(f"\nData split:")
    print(f"  Certain:   {len(certain):6,} ({len(certain)/len(df)*100:5.1f}%)")
    print(f"  Uncertain: {len(uncertain):6,} ({len(uncertain)/len(df)*100:5.1f}%)")

    # Get top causes
    def get_top_cause(json_str):
        if pd.isna(json_str): return None
        try:
            causes = json.loads(json_str)
            return max(causes.items(), key=lambda x: x[1])[0]
        except:
            return None

    df['top_cause'] = df['cause_distribution'].apply(get_top_cause)
    certain['top_cause'] = certain['cause_distribution'].apply(get_top_cause)

    print("\n" + "-"*70)
    print("Top 10 causes - All deaths:")
    all_top = df['top_cause'].value_counts(normalize=True).head(10)
    for cause, pct in all_top.items():
        print(f"  {cause:40s} {pct*100:5.1f}%")

    print("\nTop 10 causes - Certain deaths only:")
    certain_top = certain['top_cause'].value_counts(normalize=True).head(10)
    for cause, pct in certain_top.items():
        print(f"  {cause:40s} {pct*100:5.1f}%")

    # Compare
    print("\n" + "-"*70)
    print("COMPARISON:")
    print("-"*70)

    all_top_names = set(all_top.head(5).index)
    certain_top_names = set(certain_top.head(5).index)

    if all_top_names == certain_top_names:
        print("✓ Top 5 causes identical")
        print("  → Uncertainty not affecting top cause rankings")
    else:
        print("✗ Top 5 causes differ")
        print(f"  All:     {all_top_names}")
        print(f"  Certain: {certain_top_names}")

    # Check magnitude
    max_diff = 0
    for cause in all_top.head(10).index:
        if cause in certain_top.index:
            diff = abs(all_top[cause] - certain_top[cause])
            max_diff = max(max_diff, diff)
            if diff > 0.02:
                print(f"\n  Large difference for {cause}:")
                print(f"    All: {all_top[cause]*100:.1f}%  Certain: {certain_top[cause]*100:.1f}%  Diff: {diff*100:.1f}%")

    if max_diff < 0.02:
        print("\n✓ All differences <2 percentage points")
        print("  → Uncertainty has minimal impact on conclusions")
    else:
        print(f"\n✗ Maximum difference: {max_diff*100:.1f} percentage points")
        print("  → Consider filtering to certain deaths for primary analysis")

    # Save summary
    sensitivity_dir = OUT_DIR.parent / "archive" / "sensitivity_outputs"
    sensitivity_dir.mkdir(parents=True, exist_ok=True)

    summary = pd.DataFrame({
        'metric': ['Total deaths', 'Certain', 'Uncertain',
                   'Top cause (all)', 'Top cause (certain)', 'Max difference (pp)'],
        'value': [len(df), len(certain), len(uncertain),
                  all_top.index[0] if len(all_top) > 0 else 'N/A',
                  certain_top.index[0] if len(certain_top) > 0 else 'N/A',
                  f"{max_diff*100:.1f}"]
    })

    out_sens = sensitivity_dir / f"sensitivity_summary_{YEAR}.csv"
    summary.to_csv(out_sens, index=False)
    print(f"\n  ✓ Saved: {out_sens}")
    print("="*70)
