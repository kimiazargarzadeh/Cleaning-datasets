import geopandas as gpd
import pandas as pd
from pathlib import Path

BASE = Path("Harmonization")
DATA_OUT = BASE / "data_outputs"
DATA_OUT.mkdir(parents=True, exist_ok=True)

CONSTRUCTED_GPKG = DATA_OUT / "rd_constructed_from_1851_parishes.gpkg"
CONSTRUCTED_LAYER = "rd_1851_constructed"
OFFICIAL_RD_SHP = BASE / "RD_shapefiles" / "ukds_ew1851_regdistricts" / "EW1851_regdistricts.shp"

OUT_CSV = DATA_OUT / "rd_centroid_diagnostic_1851.csv"
OUT_GPKG = DATA_OUT / "rd_centroid_diagnostic_1851.gpkg"
OUT_LAYER = "centroid_diagnostic"

print("Loading constructed RDs...")
constructed = gpd.read_file(CONSTRUCTED_GPKG, layer=CONSTRUCTED_LAYER)

print("Loading official 1851 RDs...")
official = gpd.read_file(OFFICIAL_RD_SHP)

if "district" not in constructed.columns:
    raise ValueError(f"constructed missing 'district'. Columns: {list(constructed.columns)}")

if official.crs is None:
    print("Official CRS missing; setting to EPSG:27700 based on README.")
    official = official.set_crs(epsg=27700)

if constructed.crs is None:
    raise ValueError("Constructed CRS missing. Set it (likely EPSG:27700).")

if constructed.crs != official.crs:
    print(f"Reprojecting constructed → official CRS ({official.crs})")
    constructed = constructed.to_crs(official.crs)

constructed = constructed.copy()
official = official.copy()

# Centroids for constructed polygons (points we will join)
constructed["centroid_constructed"] = constructed.geometry.centroid
constructed_pts = constructed.set_geometry("centroid_constructed")

print("\nBounds check (should be similar scale):")
print("Official total_bounds:", official.total_bounds)
print("Constructed total_bounds:", constructed.total_bounds)

print("\nSpatial-joining constructed centroids into official polygons...")
# IMPORTANT: join will return index_o (right index), but not right geometry in your geopandas version.
j = gpd.sjoin(
    constructed_pts[["district", "centroid_constructed"]],
    official[["G_NAME", "G_UNIT", "NATION", "G_YEAR", "geometry"]],
    how="left",
    predicate="within",
    lsuffix="c",
    rsuffix="o",
)

# Handle leftovers via nearest
leftovers = j[j["index_o"].isna()].copy()
matched = j[j["index_o"].notna()].copy()

print("Matched by within:", len(matched))
print("Leftover (no containing polygon):", len(leftovers))

if len(leftovers) > 0:
    print("Applying nearest-neighbor fallback for leftovers...")
    leftovers2 = gpd.sjoin_nearest(
        leftovers.drop(columns=["index_o"], errors="ignore"),
        official[["G_NAME", "G_UNIT", "NATION", "G_YEAR", "geometry"]],
        how="left",
        distance_col="nearest_dist_m",
        lsuffix="c",
        rsuffix="o",
    )
    leftovers2["matched_via"] = "nearest"
    matched["matched_via"] = "within"
    j2 = pd.concat([matched, leftovers2], ignore_index=True)
else:
    matched["matched_via"] = "within"
    j2 = matched

# Now j2 contains index_o which points into official.index
# We will fetch official geometry and compute official centroids from it.
if "index_o" not in j2.columns:
    raise ValueError(f"Expected 'index_o' after join. Columns: {list(j2.columns)}")

# Build a Series mapping official index -> official polygon geometry
official_geom = official.geometry

# Create official centroid by looking up geometry using index_o
# index_o may be float with NaN -> convert carefully
j2["index_o_int"] = pd.to_numeric(j2["index_o"], errors="coerce").astype("Int64")

# lookup geometry
j2["official_geom"] = j2["index_o_int"].map(official_geom)

# turn into GeoSeries to centroid
official_geom_series = gpd.GeoSeries(j2["official_geom"], crs=official.crs)
j2["centroid_official"] = official_geom_series.centroid

# Distance (meters → km)
j2["centroid_distance_km"] = (
    j2["centroid_constructed"].distance(j2["centroid_official"]) / 1000.0
)

# Output CSV
out = pd.DataFrame({
    "constructed_district": j2["district"],
    "official_G_NAME": j2["G_NAME"],
    "official_G_UNIT": j2["G_UNIT"] if "G_UNIT" in j2.columns else None,
    "NATION": j2["NATION"] if "NATION" in j2.columns else None,
    "G_YEAR": j2["G_YEAR"] if "G_YEAR" in j2.columns else None,
    "matched_via": j2["matched_via"],
    "centroid_distance_km": j2["centroid_distance_km"],
    "nearest_dist_m": j2["nearest_dist_m"] if "nearest_dist_m" in j2.columns else None,
    "centroid_constructed_wkt": j2["centroid_constructed"].to_wkt(),
    "centroid_official_wkt": j2["centroid_official"].to_wkt(),
})

print("\nSaving CSV:", OUT_CSV)
out.to_csv(OUT_CSV, index=False)

# Save GPKG (single geometry: constructed centroids)
print("Saving GPKG:", OUT_GPKG)
gpkg = gpd.GeoDataFrame(
    out.copy(),
    geometry=gpd.GeoSeries.from_wkt(out["centroid_constructed_wkt"]),
    crs=official.crs,
)
gpkg.to_file(OUT_GPKG, layer=OUT_LAYER, driver="GPKG")

# Summary
print("\n===== SUMMARY =====")
print("Constructed RDs:", len(constructed))
print("Official RDs:", len(official))
print("Matched total:", len(out))
print(out["matched_via"].value_counts(dropna=False))

s = out["centroid_distance_km"].astype(float)
print("\nCentroid distance (km) summary:")
print(s.describe(percentiles=[0.5, 0.9, 0.95]))

print("\nWorst 10 distances (km):")
worst = out.sort_values("centroid_distance_km", ascending=False).head(10)
print(worst[["constructed_district", "official_G_NAME", "matched_via", "centroid_distance_km", "nearest_dist_m"]])

print("\nDONE.")
