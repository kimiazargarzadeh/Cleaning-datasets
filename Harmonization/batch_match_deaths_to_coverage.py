"""
Batch process FreeBMD death files across multiple years
Process files one-by-one, accumulate summary statistics only

USAGE:
1. Download death files for desired years to: Harmonization/freebmd_deaths/
2. Run this script - it will process all CSV files found
3. Delete processed death files (keep only the summary outputs)
4. Download next batch of years and repeat
"""
import pandas as pd
import numpy as np
from pathlib import Path
import re

# Paths
DEATHS_DIR = Path("Harmonization/data_raw/freebmd_deaths")
RD_COVERAGE = Path("Harmonization/data_outputs/4_final_coverage/rd_year_coverage_1851_backbone_1851_1990.csv")
OUT_DIR = Path("Harmonization/data_outputs/5_deaths_linkage/deaths_linkage_summary")
OUT_DIR.mkdir(parents=True, exist_ok=True)

MASTER_SUMMARY = OUT_DIR / "linkage_summary_all_years.csv"
UNLINKED_MASTER = OUT_DIR / "unlinked_districts_all_years.csv"

print("=" * 80)
print("BATCH DEATHS → RD COVERAGE LINKAGE")
print("=" * 80)

# Load RD coverage once (reuse for all years)
print("\n[1] Loading RD coverage data...")
rd_cov = pd.read_csv(RD_COVERAGE)
print(f"  Loaded {len(rd_cov):,} RD-year rows ({rd_cov['year'].min()}-{rd_cov['year'].max()})")

# Normalize district names in RD coverage
def normalize_district(s):
    if pd.isna(s) or s == "":
        return None
    s = str(s).lower().strip()
    # Remove temporal suffixes like (1837-1934)
    s = re.sub(r'\s*\(\d{4}[^)]*\)', '', s)
    s = s.replace("&", "and").replace("-", " ")
    s = " ".join(s.split())
    return s

rd_cov["district_norm"] = rd_cov["district"].map(normalize_district)

# Find all death files
print("\n[2] Finding death files...")
death_files = sorted(DEATHS_DIR.glob("cleaned_freebmd_deaths_*.csv"))
print(f"  Found {len(death_files)} death file(s)")

if len(death_files) == 0:
    print("\n❌ No death files found in Harmonization/data_raw/freebmd_deaths/")
    print("   Download files from Dropbox and place them here, then re-run.")
    exit(1)

for f in death_files:
    # Extract year from filename
    match = re.search(r'(\d{4})', f.stem)
    year = int(match.group(1)) if match else None
    print(f"    {f.name} → Year {year}")

# Process each file
print("\n[3] Processing death files...")
all_summaries = []
all_unlinked = []

for death_file in death_files:
    # Extract year
    match = re.search(r'(\d{4})', death_file.stem)
    if not match:
        print(f"  ⚠️  Skipping {death_file.name} (can't extract year)")
        continue

    year = int(match.group(1))
    print(f"\n  Processing {year}...")

    # Load deaths for this year
    deaths = pd.read_csv(death_file)
    n_deaths = len(deaths)

    # Normalize district names
    deaths["district_norm"] = deaths["district"].map(normalize_district)
    deaths["year"] = year

    # Merge with RD coverage for THIS YEAR ONLY (avoid multiple matches)
    rd_year = rd_cov[rd_cov["year"] == year].copy()

    # If there are still duplicates after filtering by year (shouldn't happen but just in case)
    # Keep first match only
    rd_year = rd_year.drop_duplicates(subset=["district_norm"], keep="first")

    matched = deaths.merge(
        rd_year[["district_norm", "district", "active_parish_rows",
                 "matched_parish_rows", "matched_share", "usable_1851_backbone"]],
        on="district_norm",
        how="left",
        suffixes=("_death", "_rd")
    )

    # Linkage statistics
    n_linked = matched["district_rd"].notna().sum()
    n_unlinked = matched["district_rd"].isna().sum()
    n_usable = matched["usable_1851_backbone"].eq(1).sum()
    n_non_usable = matched["usable_1851_backbone"].eq(0).sum()

    linked_only = matched[matched["district_rd"].notna()]

    summary = {
        "year": year,
        "total_deaths": n_deaths,
        "linked_deaths": n_linked,
        "unlinked_deaths": n_unlinked,
        "link_rate": n_linked / n_deaths if n_deaths > 0 else 0,
        "usable_1851_backbone": n_usable,
        "non_usable_1851_backbone": n_non_usable,
        "usable_rate_of_linked": n_usable / n_linked if n_linked > 0 else 0,
        "mean_matched_share": linked_only["matched_share"].mean() if len(linked_only) > 0 else None,
        "median_matched_share": linked_only["matched_share"].median() if len(linked_only) > 0 else None,
        "p10_matched_share": linked_only["matched_share"].quantile(0.10) if len(linked_only) > 0 else None,
        "p90_matched_share": linked_only["matched_share"].quantile(0.90) if len(linked_only) > 0 else None,
    }
    all_summaries.append(summary)

    print(f"    Total: {n_deaths:,} | Linked: {n_linked:,} ({n_linked/n_deaths*100:.1f}%) | Usable: {n_usable:,} ({n_usable/n_linked*100:.1f}% of linked)")

    # Track unlinked districts
    unlinked_dists = matched[matched["district_rd"].isna()]["district_norm"].value_counts()
    for dist, count in unlinked_dists.items():
        all_unlinked.append({
            "year": year,
            "district": dist,
            "death_count": count
        })

# Save master summary
print("\n[4] Saving outputs...")
summary_df = pd.DataFrame(all_summaries).sort_values("year")

# Check if master exists (append mode)
if MASTER_SUMMARY.exists():
    existing = pd.read_csv(MASTER_SUMMARY)
    # Merge: update years that were re-processed, keep others
    summary_df = pd.concat([
        existing[~existing["year"].isin(summary_df["year"])],
        summary_df
    ]).sort_values("year").reset_index(drop=True)

summary_df.to_csv(MASTER_SUMMARY, index=False)
print(f"  ✓ Saved: {MASTER_SUMMARY}")

if len(all_unlinked) > 0:
    unlinked_df = pd.DataFrame(all_unlinked)

    if UNLINKED_MASTER.exists():
        existing_unlinked = pd.read_csv(UNLINKED_MASTER)
        unlinked_df = pd.concat([
            existing_unlinked[~existing_unlinked["year"].isin(unlinked_df["year"])],
            unlinked_df
        ]).sort_values(["year", "death_count"], ascending=[True, False]).reset_index(drop=True)

    unlinked_df.to_csv(UNLINKED_MASTER, index=False)
    print(f"  ✓ Saved: {UNLINKED_MASTER}")

# Summary statistics
print("\n" + "=" * 80)
print("SUMMARY ACROSS ALL PROCESSED YEARS")
print("=" * 80)
print(f"Years processed: {summary_df['year'].min()}-{summary_df['year'].max()} ({len(summary_df)} years)")
print(f"Total deaths: {summary_df['total_deaths'].sum():,}")
print(f"Overall link rate: {summary_df['linked_deaths'].sum() / summary_df['total_deaths'].sum() * 100:.1f}%")
print(f"Overall usable rate: {summary_df['usable_1851_backbone'].sum() / summary_df['linked_deaths'].sum() * 100:.1f}%")

# Temporal trends
print(f"\nUsable rate by decade:")
summary_df["decade"] = (summary_df["year"] // 10) * 10
decade_summary = summary_df.groupby("decade").agg({
    "total_deaths": "sum",
    "usable_1851_backbone": "sum",
    "linked_deaths": "sum"
}).reset_index()
decade_summary["usable_rate"] = decade_summary["usable_1851_backbone"] / decade_summary["linked_deaths"]
for _, row in decade_summary.iterrows():
    print(f"  {int(row['decade'])}s: {row['usable_rate']*100:.1f}% usable ({row['usable_1851_backbone']:,.0f}/{row['linked_deaths']:,.0f} linked deaths)")

print("\n" + "=" * 80)
print("NEXT STEPS:")
print("=" * 80)
print("1. Review linkage_summary_all_years.csv for temporal trends")
print("2. Check unlinked_districts_all_years.csv for systematic name mismatches")
print("3. Download more years from Dropbox and re-run this script")
print("4. Once complete: visualize usable_rate decline to assess coverage problem")
print("=" * 80)
