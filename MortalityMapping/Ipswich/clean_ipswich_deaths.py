"""
Clean and standardize Ipswich deaths dataset (UKDA-5413, 1871-1910)

Input:  Raw Ipswich deaths from Dropbox (tab-delimited)
Output: Cleaned CSV with:
  - Standardized names, ages, dates, causes
  - Age groups and decades (matching FreeBMD format)
  - RD spatial mapping (centroids + polygon references)
  - FreeBMD matching helpers
  - All original columns preserved
  - Geography at the end

Strategy:
  1. Load and parse all fields
  2. Standardize for analysis
  3. Add matching columns for FreeBMD linkage
  4. Map to RD spatial data (from Harmonization pipeline)
  5. Organize columns: core → cause → matching → spatial
"""

import re
import json
import pandas as pd
import numpy as np
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

# Paths
BASE_DIR = Path(__file__).parent.parent.parent  # Get to Cleaning-datasets root
IPSWICH_FILE = Path("/Users/kimik/Ellen Dropbox/Kimia Zargarzadeh/WealthisHealth/UKDA-5413-tab/tab/ipswich_deaths_1871_1910_mse.tab")
OFFICIAL_CENTROIDS_FILE = BASE_DIR / "Harmonization/data_outputs/3_validation/official_rd_centroids.csv"
CENTROIDS_FILE = BASE_DIR / "Harmonization/data_outputs/4_final_coverage/rd_year_summary_1851_backbone_with_imputed_centroids.csv"
COVERAGE_FILE = BASE_DIR / "Harmonization/data_outputs/4_final_coverage/rd_year_coverage_1851_backbone_1851_1990.csv"
OUT_DIR = Path(__file__).parent / "data_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Use official RD centroids (1851-1911) instead of reconstructed 1851 backbone
USE_OFFICIAL_RDS = True

# Age bins (matching FreeBMD format)
AGE_BINS = [
    (0, 0, "a_0"), (1, 1, "a_1"), (2, 4, "a_2_4"), (5, 9, "a_5_9"),
    (10, 14, "a_10_14"), (15, 19, "a_15_19"), (20, 24, "a_20_24"),
    (25, 34, "a_25_34"), (35, 44, "a_35_44"), (45, 54, "a_45_54"),
    (55, 64, "a_55_64"), (65, 74, "a_65_74"), (75, 999, "a_75_up"),
]

# ══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def normalize_name(s):
    """Normalize name for matching (lowercase, no special chars)."""
    if pd.isna(s) or str(s).strip() == "":
        return None
    s = str(s).lower().strip()
    # Remove special characters but keep spaces
    s = re.sub(r'[^\w\s]', '', s)
    s = ' '.join(s.split())
    return s if s else None

def normalize_district(s):
    """Normalize district name for RD matching."""
    if pd.isna(s) or str(s).strip() == "":
        return None
    s = str(s).lower().strip()
    # Remove parentheses, standardize
    s = re.sub(r'\s*\([^)]*\)', '', s)
    s = s.replace("&", "and").replace("-", " ")
    s = ' '.join(s.split())
    return s if s else None

def parse_age_to_numeric(age_str):
    """
    Parse age string to numeric value in years.

    Handles:
      - "31" → 31.0
      - "3 mths" → 0.25
      - "2 weeks" → 0.04
      - "5 days" → 0.01
    """
    if pd.isna(age_str):
        return None

    age_str = str(age_str).lower().strip()

    # Try simple numeric
    try:
        return float(age_str)
    except ValueError:
        pass

    # Parse "X mths" / "X months"
    match = re.search(r'(\d+)\s*(mth|month)', age_str)
    if match:
        return round(float(match.group(1)) / 12, 2)

    # Parse "X weeks"
    match = re.search(r'(\d+)\s*week', age_str)
    if match:
        return round(float(match.group(1)) / 52, 2)

    # Parse "X days"
    match = re.search(r'(\d+)\s*day', age_str)
    if match:
        return round(float(match.group(1)) / 365, 2)

    # If all else fails, try to extract first number
    match = re.search(r'(\d+)', age_str)
    if match:
        return float(match.group(1))

    return None

def map_age_to_group(age):
    """Map numeric age to age group bin."""
    if pd.isna(age):
        return None
    try:
        age_val = float(age)
        if age_val < 0 or age_val > 120:
            return None
        for low, high, col in AGE_BINS:
            if low <= age_val <= high:
                return col
        return "a_75_up"
    except (ValueError, TypeError):
        return None

def standardize_sex(sex_str):
    """Standardize sex to M/F."""
    if pd.isna(sex_str):
        return None
    s = str(sex_str).lower().strip()
    if s in ["m", "male"]:
        return "M"
    elif s in ["f", "female"]:
        return "F"
    return None

def parse_death_date(row):
    """
    Parse death date from multiple columns.
    Priority: death_year, death_month, death_day_
    Returns: YYYY-MM-DD string (with NaNs as None)
    """
    year = row.get('death_year')
    month = row.get('death_month')
    day = row.get('death_day_')

    # Convert month name to number
    month_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }

    if pd.isna(year):
        return None

    # Extract year number (handle "1891 *" or other junk)
    try:
        if isinstance(year, str):
            year_match = re.search(r'(\d{4})', year)
            year_int = int(year_match.group(1)) if year_match else None
        else:
            year_int = int(year)
    except (ValueError, AttributeError):
        year_int = None

    # Extract month
    if pd.isna(month):
        month_int = None
    elif isinstance(month, str):
        month_int = month_map.get(month.lower().strip()[:3])
    else:
        try:
            month_int = int(month)
        except (ValueError, TypeError):
            month_int = None

    # Extract day (handle messy text like "Found dead in bed on  3")
    if pd.isna(day):
        day_int = None
    else:
        try:
            if isinstance(day, str):
                day_match = re.search(r'(\d+)', day)
                day_int = int(day_match.group(1)) if day_match else None
            else:
                day_int = int(day)
        except (ValueError, AttributeError):
            day_int = None

    # Build date string
    if year_int and month_int and day_int:
        return f"{year_int:04d}-{month_int:02d}-{day_int:02d}"
    elif year_int and month_int:
        return f"{year_int:04d}-{month_int:02d}"
    elif year_int:
        return f"{year_int:04d}"

    return None

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 1: LOAD AND PARSE
# ══════════════════════════════════════════════════════════════════════════════

print("="*80)
print("IPSWICH DEATHS CLEANING PIPELINE")
print("="*80)

print("\nLoading raw data...")
df = pd.read_csv(IPSWICH_FILE, sep='\t', encoding='latin1',
                 on_bad_lines='skip', low_memory=False)

n_total = len(df)
print(f"  Loaded: {n_total:,} records")

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 2: CLEAN AND STANDARDIZE
# ══════════════════════════════════════════════════════════════════════════════

print("\nCleaning and standardizing...")

# Parse age
df['age_numeric'] = df['age'].apply(parse_age_to_numeric)
df['age_group'] = df['age_numeric'].apply(map_age_to_group)
print(f"  Age parsed: {df['age_numeric'].notna().sum():,} / {n_total:,}")

# Standardize sex
df['sex_std'] = df['sex'].apply(standardize_sex)
print(f"  Sex standardized: {df['sex_std'].notna().sum():,} / {n_total:,}")

# Parse death date
df['death_date'] = df.apply(parse_death_date, axis=1)
df['death_year_clean'] = pd.to_numeric(df['death_year'], errors='coerce').astype('Int64')

# Filter out garbage years (found 1092, 9102 in data)
df = df[df['death_year_clean'].between(1871, 1910)].copy()
n_valid_years = len(df)
print(f"  Valid years (1871-1910): {n_valid_years:,} / {n_total:,}")

# Add decade
df['decade'] = (df['death_year_clean'] // 10) * 10

# Normalize names for matching
df['surname_for_matching'] = df['surname'].apply(normalize_name)
df['forenames_for_matching'] = df['deceaseds_forenames'].apply(normalize_name)

# Standardize registration district
df['reg_dist_std'] = df['reg_dist'].apply(normalize_district)

print(f"  Names normalized: {df['surname_for_matching'].notna().sum():,}")

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 3: RD SPATIAL MAPPING
# ══════════════════════════════════════════════════════════════════════════════

print("\nMapping to RD spatial data...")

# Load RD coverage and centroids
coverage = pd.read_csv(COVERAGE_FILE)

if USE_OFFICIAL_RDS:
    print("  Using official RD centroids (1851-1881), extending 1881 centroid to 1891-1911")

    # Load official centroids (1851-1911, but Ipswich only exists 1851-1881)
    official = pd.read_csv(OFFICIAL_CENTROIDS_FILE)
    official = official.rename(columns={'official_x': 'centroid_x', 'official_y': 'centroid_y'})
    official['district_norm'] = official['district'].apply(normalize_district)

    # Get Ipswich official centroids (1851-1881)
    ipswich_official = official[official['district_norm'] == 'ipswich'][['district_norm', 'year', 'centroid_x', 'centroid_y']].copy()

    # For missing years (1891, 1901, 1911), use 1881 centroid
    # This is more accurate than reconstructed data which has incorrect coordinates
    centroid_1881 = ipswich_official[ipswich_official['year'] == 1881].iloc[0]
    missing_years = [1891, 1901, 1911]

    for year in missing_years:
        ipswich_official = pd.concat([
            ipswich_official,
            pd.DataFrame([{
                'district_norm': 'ipswich',
                'year': year,
                'centroid_x': centroid_1881['centroid_x'],
                'centroid_y': centroid_1881['centroid_y']
            }])
        ], ignore_index=True)

    centroids = ipswich_official.sort_values('year')
    print(f"    Using 1881 centroid ({centroid_1881['centroid_x']:.1f}, {centroid_1881['centroid_y']:.1f}) for all years")
else:
    print("  Using reconstructed centroids from 1851 backbone")
    centroids = pd.read_csv(CENTROIDS_FILE)
    centroids['district_norm'] = centroids['district'].apply(normalize_district)

# Normalize district names in spatial files
coverage['district_norm'] = coverage['district'].apply(normalize_district)

# Strategy: Match Ipswich sub-districts to "Ipswich" RD
# Ipswich Eastern, Ipswich Western, St Matthew, St Margaret, St Clement → all map to "Ipswich" RD

# Create mapping: normalize to "ipswich" for all Ipswich-related districts
def map_to_main_rd(district_norm):
    """Map Ipswich sub-districts to main Ipswich RD."""
    if pd.isna(district_norm):
        return None
    if 'ipswich' in district_norm or district_norm in ['st matthew', 'st margaret', 'st clement']:
        return 'ipswich'
    return district_norm

df['rd_name_mapped'] = df['reg_dist_std'].apply(map_to_main_rd)

# For each death, get RD centroid from nearest census year
CENSUS_YEARS = [1851, 1861, 1871, 1881, 1891, 1901, 1911]

def get_nearest_census(year):
    """Get nearest census year."""
    if pd.isna(year):
        return None
    return min(CENSUS_YEARS, key=lambda y: abs(y - year))

df['nearest_census'] = df['death_year_clean'].apply(get_nearest_census)

# Merge centroids
# For each row, match: rd_name_mapped + nearest_census → centroid
centroids_merge = centroids[['district_norm', 'year', 'centroid_x', 'centroid_y']].copy()
centroids_merge = centroids_merge.rename(columns={'district_norm': 'rd_name_mapped', 'year': 'nearest_census'})

df = df.merge(
    centroids_merge,
    on=['rd_name_mapped', 'nearest_census'],
    how='left'
)

n_spatial = df['centroid_x'].notna().sum()
print(f"  Spatially linked: {n_spatial:,} / {n_valid_years:,} ({n_spatial/n_valid_years*100:.1f}%)")

# Add matched_share and polygon reference from coverage
# Match on: rd_name_mapped + death_year_clean
coverage_merge = coverage[['district_norm', 'year', 'matched_share', 'usable_1851_backbone']].copy()
coverage_merge = coverage_merge.rename(columns={'district_norm': 'rd_name_mapped', 'year': 'death_year_clean'})

df = df.merge(
    coverage_merge,
    on=['rd_name_mapped', 'death_year_clean'],
    how='left'
)

# Add polygon reference (constructed RD from 1851 backbone)
# Note: Actual polygons stored in: Harmonization/data_outputs/2_rd_construction/rd_constructed_from_1851_parishes.gpkg
df['polygon_source'] = 'Harmonization/data_outputs/2_rd_construction/rd_constructed_from_1851_parishes.gpkg'
df['polygon_layer'] = df['nearest_census'].apply(lambda y: f"rd_{y}_constructed" if pd.notna(y) else None)

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 4: IMPROVE RD ASSIGNMENT
# ══════════════════════════════════════════════════════════════════════════════

print("\nImproving RD assignment...")

# For records without reg_dist, try to infer from parish or assume Ipswich
# (Since this is Ipswich-specific dataset, safe assumption)
df.loc[df['rd_name_mapped'].isna(), 'rd_name_mapped'] = 'ipswich'
df.loc[df['reg_dist_std'].isna(), 'reg_dist_std'] = 'inferred_ipswich'

print(f"  RD assigned: {df['rd_name_mapped'].notna().sum():,} / {len(df):,} (100%)")

# Re-merge centroids with improved mapping
def get_available_census(year):
    """Get nearest available census year in centroids file."""
    if pd.isna(year):
        return None
    if USE_OFFICIAL_RDS:
        # Official centroids have all census years 1851-1911
        available = [1851, 1861, 1871, 1881, 1891, 1901, 1911]
    else:
        # Reconstructed centroids missing 1891
        available = [1851, 1861, 1871, 1881, 1901, 1911]
        if 1886 <= year <= 1895:
            return 1881
    return min(available, key=lambda y: abs(y - year))

df['nearest_census'] = df['death_year_clean'].apply(get_available_census)

# Drop old centroid columns and re-merge
df = df.drop(columns=['centroid_x', 'centroid_y', 'matched_share', 'usable_1851_backbone'], errors='ignore')

centroids_merge = centroids[['district_norm', 'year', 'centroid_x', 'centroid_y']].copy()
centroids_merge = centroids_merge.rename(columns={'district_norm': 'rd_name_mapped', 'year': 'nearest_census'})

df = df.merge(
    centroids_merge,
    on=['rd_name_mapped', 'nearest_census'],
    how='left'
)

# Re-merge coverage
df = df.drop(columns=['matched_share', 'usable_1851_backbone'], errors='ignore')
coverage_merge = coverage[['district_norm', 'year', 'matched_share', 'usable_1851_backbone']].copy()
coverage_merge = coverage_merge.rename(columns={'district_norm': 'rd_name_mapped', 'year': 'death_year_clean'})

df = df.merge(
    coverage_merge,
    on=['rd_name_mapped', 'death_year_clean'],
    how='left'
)

n_spatial_improved = df['centroid_x'].notna().sum()
print(f"  Spatially linked (improved): {n_spatial_improved:,} / {len(df):,} ({n_spatial_improved/len(df)*100:.1f}%)")

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 5: COLUMN CLEANUP - KEEP ONLY MOST INFORMATIVE
# ══════════════════════════════════════════════════════════════════════════════

print("\nCleaning up redundant columns...")

# Keep only essential columns (remove duplicates/messy versions)
keep_cols = [
    # Core ID and dates
    'final_id', 'death_year_clean', 'death_date', 'decade', 'qod',

    # Personal (cleaned versions only)
    'surname', 'deceaseds_forenames',
    'sex_std', 'age_numeric', 'age_group',

    # Address (cleaned versions only)
    'tidy_street',

    # Family (KEEP - 26% have parent info for infant/child deaths!)
    'relationship_of_deceased_to_relative',
    'relatives_forenames', 'relatives_surname',

    # Occupation (wealth proxy)
    'occupation_of_relative_or_deceased',

    # Cause (keep all - this is the key data!)
    'cause_of_death',
    "mo's_classification_of_cause_of_death",
    'cause_of_death_category',

    # FreeBMD matching
    'surname_for_matching',
    'forenames_for_matching',

    # Spatial (at the end)
    'reg_dist_std',
    'centroid_x', 'centroid_y',
    'polygon_layer',
]

# Add quarter of death if it exists
if 'qod' not in df.columns and 'quarter' in df.columns:
    df['qod'] = df['quarter']
elif 'qod' not in df.columns:
    # Infer from death_month
    def month_to_quarter(month_str):
        if pd.isna(month_str):
            return None
        month_map = {'jan':1,'feb':1,'mar':1,'apr':2,'may':2,'jun':2,
                     'jul':3,'aug':3,'sep':3,'oct':4,'nov':4,'dec':4}
        if isinstance(month_str, str):
            return month_map.get(month_str.lower().strip()[:3])
        return None
    df['qod'] = df['death_month'].apply(month_to_quarter)

# Keep only columns that exist
final_cols = [c for c in keep_cols if c in df.columns]

df = df[final_cols]

n_cols = len(df.columns)
print(f"  Reduced from 65 to {n_cols} essential columns")
print(f"  Kept relatives columns: {n_cols} includes parent info for 26% of deaths")

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 6: SORT AND SAVE
# ══════════════════════════════════════════════════════════════════════════════

print("\nSorting by year and saving...")

# Sort by death year, then by id
df = df.sort_values(['death_year_clean', 'final_id']).reset_index(drop=True)

# Save
out_file = OUT_DIR / "ipswich_deaths_1871_1910_cleaned.csv"
df.to_csv(out_file, index=False)

print(f"  ✓ Saved: {out_file.name}")

# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Total records:       {len(df):,}")
print(f"Years:               {df['death_year_clean'].min()}-{df['death_year_clean'].max()}")
print(f"With age:            {df['age_numeric'].notna().sum():,} ({df['age_numeric'].notna().mean()*100:.1f}%)")
print(f"With sex:            {df['sex_std'].notna().sum():,} ({df['sex_std'].notna().mean()*100:.1f}%)")
print(f"With cause:          {df['cause_of_death'].notna().sum():,} ({df['cause_of_death'].notna().mean()*100:.1f}%)")
print(f"With parent info:    {df['relationship_of_deceased_to_relative'].notna().sum():,} ({df['relationship_of_deceased_to_relative'].notna().mean()*100:.1f}%)")
print(f"\nOutput: {out_file}")
print(f"Columns: {len(df.columns)}")
print(f"\nReady for:")
print("  - Analysis (standardized fields, age groups, decades)")
print("  - FreeBMD matching (normalized names, age, sex, year)")
print("  - Family linkage (26% have parent info)")
print("  - Validation (actual causes vs ecological inference)")
