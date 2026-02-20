"""
Map individual FreeBMD deaths to RD polygons and assign cause probabilities.

Strategy:
  1. Load cleaned death records (post-1866 with age column)
  2. Spatial mapping: death district → RD centroid (x, y coordinates)
  3. Cause assignment: ecological inference from aggregate data
     For each individual: (RD, decade, age_group, sex) → cause probability distribution

Output:
  Two CSV files per year:
    - deaths_{year}_spatial.csv         → location + age/sex only
    - deaths_{year}_with_causes.csv     → location + cause distribution (JSON format)

Method:
  Ecological inference - assign probabilities based on RD-level cause distributions
  Optimized with vectorization for fast processing of large datasets
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

# Paths
DROPBOX_DEATHS = Path("/Users/kimik/Ellen Dropbox/Kimia Zargarzadeh/WealthisHealth/freebmd/Deaths/cleaned")
CAUSE_FILE     = Path("/Users/kimik/Ellen Dropbox/Kimia Zargarzadeh/WealthisHealth/1851-1910 Age- and Cause-Specific Mortality in E&W/tab/cause_ew_reg_dec.tab")
MORTALITY_FILE = Path("/Users/kimik/Ellen Dropbox/Kimia Zargarzadeh/WealthisHealth/1851-1910 Age- and Cause-Specific Mortality in E&W/tab/mort_age_ew_reg_dec.tab")
COVERAGE_FILE  = Path("Harmonization/data_outputs/4_final_coverage/rd_year_coverage_1851_backbone_1851_1990.csv")
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
print(f"  Using centroids from {nearest_census} (nearest census to {YEAR})")

cent = pd.read_csv(CENTROIDS_FILE)
cent = cent[cent["year"] == nearest_census].copy()
cent["district_norm"] = cent["district"].apply(normalize_district)

# Merge coverage + centroids
cov_year = cov_year.merge(
    cent[["district_norm", "centroid_x", "centroid_y"]],
    on="district_norm",
    how="left"
).drop_duplicates("district_norm")

# Join deaths to RD
df = df.merge(
    cov_year[["district_norm", "district", "centroid_x", "centroid_y", "matched_share"]],
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
    "district_norm", "rd_name", "centroid_x", "centroid_y", "matched_share"
]
keep_cols = [c for c in keep_cols if c in df.columns]
df = df[keep_cols].copy()

# (Skip spatial-only output - redundant with final output)

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 2: CAUSE ASSIGNMENT (OPTIMIZED WITH VECTORIZATION)
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

# Reorder columns: put spatial/geographic data at the end for readability
core_cols = [
    'surname', 'firstnames', 'yod', 'qod',
    'age_numeric', 'age_group', 'sex', 'decade',
    'district', 'total_deaths_in_group',
    'cause_distribution'
]
spatial_cols = [
    'district_norm', 'rd_name', 'centroid_x', 'centroid_y', 'matched_share'
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
print(f"\nOutput:")
print(f"  {out2}")
print(f"\nFormat: JSON cause distribution")
print(f"  Example: {{'Tuberculosis': 0.425, 'Pneumonia': 0.21, ...}}")
