# Harmonization/impute_unmatched_to_nearest_1851_rd_centroid.py

import re
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

CENSUS_YEARS = [1851, 1861, 1871, 1881, 1891, 1901, 1911]

BASE = Path("Harmonization")
DATA_OUT = BASE / "data_outputs"
DATA_OUT.mkdir(parents=True, exist_ok=True)

SUMMARY_IN = DATA_OUT / "rd_year_summary_1851_backbone.csv"
CONSTRUCTED_GPKG = DATA_OUT / "rd_constructed_from_1851_parishes.gpkg"
SUMMARY_OUT = DATA_OUT / "rd_year_summary_1851_backbone_with_imputed_centroids.csv"

CRS_EPSG = 27700
TARGET_LAYER = "rd_1851_constructed"


def official_shp(year: int) -> Path:
    return BASE / "RD_shapefiles" / f"ukds_ew{year}_regdistricts" / f"EW{year}_regdistricts.shp"


def std_name(x) -> str:
    s = "" if pd.isna(x) else str(x)
    s = s.strip().lower()
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def to_epsg27700(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        return gdf.set_crs(epsg=CRS_EPSG)
    try:
        epsg = gdf.crs.to_epsg()
    except Exception:
        epsg = None
    if epsg != CRS_EPSG:
        gdf = gdf.to_crs(epsg=CRS_EPSG)
    return gdf


# -----------------------
# Load summary
# -----------------------
df = pd.read_csv(SUMMARY_IN)
df["usable_1851_backbone"] = df["usable_1851_backbone"].astype(int)

df["district_std"] = df["district"].map(std_name)

# Ensure expected columns exist
if "centroid_x" not in df.columns:
    df["centroid_x"] = pd.NA
if "centroid_y" not in df.columns:
    df["centroid_y"] = pd.NA

for col, default in [
    ("location_imputed", 0),
    ("imputation_failed", 0),
    ("imputed_from_district", pd.NA),
    ("imputed_distance_km", pd.NA),
    ("imputation_source_point", pd.NA),
]:
    if col not in df.columns:
        df[col] = default

df["location_imputed"] = df["location_imputed"].fillna(0).astype(int)
df["imputation_failed"] = df["imputation_failed"].fillna(0).astype(int)

# -----------------------
# Build fixed 1851 target centroids
# -----------------------
targets_poly = gpd.read_file(CONSTRUCTED_GPKG, layer=TARGET_LAYER)
targets_poly = to_epsg27700(targets_poly)
targets_poly["target_centroid"] = targets_poly.geometry.centroid

targets = targets_poly.set_geometry("target_centroid")[["district", "target_centroid"]].copy()
targets = targets.rename(columns={"target_centroid": "geometry"}).set_geometry("geometry")
target_geom_by_index = targets.geometry


out_frames = []

for year in CENSUS_YEARS:
    print(f"\n=== Imputation year {year} ===")
    d_y = df[df["year"] == year].copy()

    # row_id to merge back 1:1
    d_y["row_id"] = d_y.index

    needs_mask = d_y["usable_1851_backbone"] == 0
    print("Needs imputation:", int(needs_mask.sum()))

    if int(needs_mask.sum()) == 0:
        out_frames.append(d_y.drop(columns=["row_id"]))
        continue

    needs = d_y.loc[needs_mask, ["row_id", "district_std", "centroid_x", "centroid_y"]].copy()
    needs["source_geom"] = pd.Series([None] * len(needs), index=needs.index, dtype="object")
    needs["imputation_source_point_tmp"] = pd.NA

    # 1) existing XY if present
    has_xy = needs["centroid_x"].notna() & needs["centroid_y"].notna()
    print("Rows with existing centroid_x/y:", int(has_xy.sum()))

    if int(has_xy.sum()) > 0:
        needs.loc[has_xy, "source_geom"] = needs.loc[has_xy].apply(
            lambda r: Point(float(r["centroid_x"]), float(r["centroid_y"])),
            axis=1,
        )
        needs.loc[has_xy, "imputation_source_point_tmp"] = "from_existing_xy"

    # 2) official centroid by name for remaining
    no_xy = ~has_xy
    print("Rows missing centroid_x/y (will try official by name):", int(no_xy.sum()))

    if int(no_xy.sum()) > 0:
        official = gpd.read_file(official_shp(year))
        official = to_epsg27700(official)

        if "G_NAME" not in official.columns:
            candidates = [c for c in official.columns if "name" in c.lower()]
            raise KeyError(f"Expected G_NAME, found name-like: {candidates}")

        official["o_centroid"] = official.geometry.centroid
        official_pts = official.set_geometry("o_centroid")[["G_NAME", "o_centroid"]].copy()
        official_pts = official_pts.rename(columns={"G_NAME": "district_official"})
        official_pts["district_std"] = official_pts["district_official"].map(std_name)
        official_pts = official_pts.drop_duplicates("district_std")

        off_map = dict(zip(official_pts["district_std"], official_pts["o_centroid"]))

        needs.loc[no_xy, "source_geom"] = needs.loc[no_xy, "district_std"].map(off_map).astype("object")
        needs.loc[no_xy & needs["source_geom"].notna(), "imputation_source_point_tmp"] = "from_official_name"

        print("Matched to official names after std:", int((no_xy & needs["source_geom"].notna()).sum()))

    can_impute = needs["source_geom"].notna()
    cannot_impute = ~can_impute
    print("Rows with a usable source point:", int(can_impute.sum()))
    print("Rows still missing source point (FAILED):", int(cannot_impute.sum()))

    if int(cannot_impute.sum()) > 0:
        sample_bad = needs.loc[cannot_impute, "district_std"].dropna().unique().tolist()[:25]
        print("Unmatched district_std sample:", sample_bad)

    # mark failures by row_id
    failed_row_ids = needs.loc[cannot_impute, "row_id"].tolist()
    if failed_row_ids:
        d_y.loc[d_y["row_id"].isin(failed_row_ids), "imputation_failed"] = 1

    if int(can_impute.sum()) == 0:
        out_frames.append(d_y.drop(columns=["row_id"]))
        continue

    src = needs.loc[can_impute, ["row_id", "source_geom", "imputation_source_point_tmp"]].copy()
    src_gdf = gpd.GeoDataFrame(
        src.drop(columns=["source_geom"]),
        geometry=gpd.GeoSeries(src["source_geom"], crs=f"EPSG:{CRS_EPSG}"),
        crs=f"EPSG:{CRS_EPSG}",
    )

    joined = gpd.sjoin_nearest(
        src_gdf,
        targets.rename(columns={"district": "imputed_from_district"}),
        how="left",
        distance_col="dist_m",
    )
    joined["imputed_distance_km"] = joined["dist_m"] / 1000.0

    joined["target_geom"] = joined["index_right"].map(target_geom_by_index)
    tg = gpd.GeoSeries(joined["target_geom"], crs=f"EPSG:{CRS_EPSG}")
    joined["centroid_x_imp"] = tg.x
    joined["centroid_y_imp"] = tg.y

    imp = joined[[
        "row_id",
        "imputed_from_district",
        "imputed_distance_km",
        "centroid_x_imp",
        "centroid_y_imp",
        "imputation_source_point_tmp",
    ]].copy()

    # Merge back strictly 1:1 on row_id
    d_y = d_y.merge(imp, on="row_id", how="left")

    # RECOMPUTE mask after merge (avoid index alignment issues)
    needs_mask2 = d_y["usable_1851_backbone"] == 0

    got = needs_mask2 & d_y["centroid_x_imp"].notna() & d_y["centroid_y_imp"].notna()
    miss = needs_mask2 & ~got


    d_y.loc[got, "location_imputed"] = 1
    d_y.loc[miss, "imputation_failed"] = 1

    d_y.loc[got, "centroid_x"] = d_y.loc[got, "centroid_x"].fillna(d_y.loc[got, "centroid_x_imp"])
    d_y.loc[got, "centroid_y"] = d_y.loc[got, "centroid_y"].fillna(d_y.loc[got, "centroid_y_imp"])

    d_y.loc[got, "imputation_source_point"] = d_y.loc[got, "imputation_source_point"].fillna(
        d_y.loc[got, "imputation_source_point_tmp"]
    )

    d_y = d_y.drop(columns=["centroid_x_imp", "centroid_y_imp", "imputation_source_point_tmp", "row_id"])

    out_frames.append(d_y)

final = pd.concat(out_frames, ignore_index=True)

if "geometry_source" in final.columns:
    final.loc[final["location_imputed"] == 1, "geometry_source"] = "centroid_imputed_nearest_1851_rd"
    final.loc[final["imputation_failed"] == 1, "geometry_source"] = final.loc[
        final["imputation_failed"] == 1, "geometry_source"
    ].fillna("imputation_failed_no_source_point")

final.to_csv(SUMMARY_OUT, index=False)

print("\nSaved:", SUMMARY_OUT)
print("Imputed rows:", int(final["location_imputed"].sum()))
print("Failed imputations:", int(final["imputation_failed"].sum()))
print("Imputed rows by year:\n", final.groupby("year")["location_imputed"].sum())
print("Failed imputations by year:\n", final.groupby("year")["imputation_failed"].sum())
print(
    "Imputation source point counts (only imputed rows):\n",
    final.loc[final["location_imputed"] == 1, "imputation_source_point"].value_counts(dropna=False),
)
