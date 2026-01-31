import geopandas as gpd
import pandas as pd
from pathlib import Path

# -----------------------------
# Config
# -----------------------------
CENSUS_YEARS = [1851, 1861, 1871, 1881, 1891, 1901, 1911]

BASE = Path("Harmonization")
DATA_OUT = BASE / "data_outputs"
DATA_OUT.mkdir(parents=True, exist_ok=True)

CONSTRUCTED_GPKG = DATA_OUT / "rd_constructed_from_1851_parishes.gpkg"

# If your folders/files differ for some years, adjust this function
def official_shapefile_for_year(year: int) -> Path:
    return BASE / "RD_shapefiles" / f"ukds_ew{year}_regdistricts" / f"EW{year}_regdistricts.shp"

DEFAULT_CRS_EPSG = 27700

def ensure_crs(gdf, label):
    if gdf.crs is None:
        print(f"{label} CRS missing; setting EPSG:{DEFAULT_CRS_EPSG}")
        return gdf.set_crs(epsg=DEFAULT_CRS_EPSG)
    return gdf

all_years_out = []

for year in CENSUS_YEARS:
    constructed_layer = f"rd_{year}_constructed"
    official_path = official_shapefile_for_year(year)

    OUT_CSV = DATA_OUT / f"rd_centroid_diagnostic_{year}.csv"
    OUT_GPKG = DATA_OUT / f"rd_centroid_diagnostic_{year}.gpkg"
    OUT_LAYER = "centroid_diagnostic"

    print(f"\n=== YEAR {year} ===")
    print("Loading constructed layer:", constructed_layer)
    constructed = gpd.read_file(CONSTRUCTED_GPKG, layer=constructed_layer)

    print("Loading official shapefile:", official_path)
    official = gpd.read_file(official_path)

    if "district" not in constructed.columns:
        raise ValueError(f"constructed missing 'district'. Columns: {list(constructed.columns)}")

    official = ensure_crs(official, "official")
    constructed = ensure_crs(constructed, "constructed")

    if constructed.crs != official.crs:
        print(f"Reprojecting constructed → official CRS ({official.crs})")
        constructed = constructed.to_crs(official.crs)

    constructed = constructed.copy()
    official = official.copy()

    # Centroids for constructed polygons (points we will join)
    constructed["centroid_constructed"] = constructed.geometry.centroid
    constructed_pts = constructed.set_geometry("centroid_constructed")

    print("\nSpatial-joining constructed centroids into official polygons (within)...")
    j = gpd.sjoin(
        constructed_pts[["district", "centroid_constructed"]],
        official[["geometry"]],
        how="left",
        predicate="within",
        lsuffix="c",
        rsuffix="o",
    )

    leftovers = j[j["index_o"].isna()].copy()
    matched = j[j["index_o"].notna()].copy()

    print("Matched by within:", len(matched))
    print("Leftover:", len(leftovers))

    if len(leftovers) > 0:
        print("Applying nearest-neighbor fallback for leftovers...")
        leftovers2 = gpd.sjoin_nearest(
            leftovers.drop(columns=["index_o"], errors="ignore"),
            official[["geometry"]],
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

    if "index_o" not in j2.columns:
        raise ValueError(f"Expected 'index_o' after join. Columns: {list(j2.columns)}")

    # Look up official geometry for centroid computation
    official_geom = official.geometry
    j2["index_o_int"] = pd.to_numeric(j2["index_o"], errors="coerce").astype("Int64")
    j2["official_geom"] = j2["index_o_int"].map(official_geom)

    official_geom_series = gpd.GeoSeries(j2["official_geom"], crs=official.crs)
    j2["centroid_official"] = official_geom_series.centroid

    # Distance (meters → km)
    j2["centroid_distance_km"] = (
        j2["centroid_constructed"].distance(j2["centroid_official"]) / 1000.0
    )

    out = pd.DataFrame({
        "year": year,
        "constructed_district": j2["district"],
        "matched_via": j2["matched_via"],
        "centroid_distance_km": j2["centroid_distance_km"],
        "nearest_dist_m": j2["nearest_dist_m"] if "nearest_dist_m" in j2.columns else None,
        "official_index": j2["index_o_int"],
        "centroid_constructed_wkt": j2["centroid_constructed"].to_wkt(),
        "centroid_official_wkt": j2["centroid_official"].to_wkt(),
    })

    print("Saving CSV:", OUT_CSV)
    out.to_csv(OUT_CSV, index=False)

    print("Saving GPKG:", OUT_GPKG)
    gpkg = gpd.GeoDataFrame(
        out.copy(),
        geometry=gpd.GeoSeries.from_wkt(out["centroid_constructed_wkt"]),
        crs=official.crs,
    )
    gpkg.to_file(OUT_GPKG, layer=OUT_LAYER, driver="GPKG")

    # Summary
    s = out["centroid_distance_km"].astype(float)
    print("Centroid distance summary (km):")
    print(s.describe(percentiles=[0.5, 0.9, 0.95]))

    all_years_out.append(out)

# Combine all years
combined = pd.concat(all_years_out, ignore_index=True)
combined_path = DATA_OUT / "rd_centroid_diagnostic_all_years.csv"
combined.to_csv(combined_path, index=False)
print("\nSaved combined diagnostics to:", combined_path)
print("DONE.")
