import pandas as pd
import geopandas as gpd
from pathlib import Path

# -----------------------
# Config
# -----------------------
CENSUS_YEARS = [1851, 1861, 1871, 1881, 1891, 1901, 1911]

CONCORDANCE = Path("Harmonization/data_outputs/1_parish_matching/parish_rd_allyears_concordance.csv")
CENTROID_ALL = Path("Harmonization/data_outputs/3_validation/rd_centroid_diagnostic_all_years.csv")

# Constructed RD geometries (one GPKG containing layers rd_{year}_constructed)
CONSTRUCTED_GPKG = Path("Harmonization/data_outputs/2_rd_construction/rd_constructed_from_1851_parishes.gpkg")

# 1851 parish polygons (WKT) used to compute parish areas + dominant parish
PARISH_1851_CSV = Path("Harmonization/1851EngWalesParishandPlace.csv")

OUT_PATH = Path("Harmonization/data_outputs/4_final_coverage/rd_year_summary_1851_backbone.csv")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

CRS_EPSG = 27700  # British National Grid

# -----------------------
# Helpers
# -----------------------
def active_at_year(df: pd.DataFrame, year: int) -> pd.Series:
    return (
        df["from_year"].notna()
        & (df["from_year"] <= year)
        & (df["to_year"].isna() | (df["to_year"] >= year))
    )

# -----------------------
# Load inputs
# -----------------------
con = pd.read_csv(CONCORDANCE)
cent = pd.read_csv(CENTROID_ALL)

# Ensure numeric years
con["from_year"] = pd.to_numeric(con["from_year"], errors="coerce")
con["to_year"] = pd.to_numeric(con["to_year"], errors="coerce")
con["matched"] = con["matched"].astype(bool)

# Load 1851 parish polygons (for dominant parish area)
par = pd.read_csv(PARISH_1851_CSV)
if "ID" not in par.columns or "PLA" not in par.columns or "geometry" not in par.columns:
    raise ValueError("1851 parish CSV must contain columns: ID, PLA, geometry (WKT).")

par["ID"] = pd.to_numeric(par["ID"], errors="coerce")
par = par[par["ID"].notna()].copy()
par["ID"] = par["ID"].astype(int)

gpar = gpd.GeoDataFrame(
    par[["ID", "PLA", "geometry"]].copy(),
    geometry=gpd.GeoSeries.from_wkt(par["geometry"]),
    crs=f"EPSG:{CRS_EPSG}",
)

# compute parish area (km^2) and make a lookup
gpar["parish_area_km2"] = gpar.geometry.area / 1_000_000.0
parish_area = gpar.set_index("ID")["parish_area_km2"].to_dict()
parish_name = gpar.set_index("ID")["PLA"].to_dict()

summary_rows = []

# -----------------------
# Build coverage + dominant parish by year
# -----------------------
for year in CENSUS_YEARS:
    dfy = con.loc[active_at_year(con, year)].copy()

    # district-level coverage stats
    g = dfy.groupby("district").agg(
        active_parish_rows=("district", "count"),
        matched_parish_rows=("matched", "sum"),
        # unique matched parish IDs contributing
        n_parishes_matched=("ID", lambda x: pd.Series(x).dropna().astype("Int64").nunique()),
    ).reset_index()

    g["matched_share"] = g["matched_parish_rows"] / g["active_parish_rows"]
    g["usable_1851_backbone"] = (g["matched_parish_rows"] > 0).astype(int)
    g["year"] = year

    # dominant parish (by 1851 parish polygon area) among matched parishes active that year
    dfy_m = dfy[dfy["matched"] & dfy["ID"].notna()].copy()
    dfy_m["ID"] = pd.to_numeric(dfy_m["ID"], errors="coerce").astype("Int64")
    dfy_m = dfy_m[dfy_m["ID"].notna()].copy()
    dfy_m["ID"] = dfy_m["ID"].astype(int)
    dfy_m["parish_area_km2"] = dfy_m["ID"].map(parish_area)

    # total area used per district (sum of contributing parish areas; parishes disjoint so ok)
    area_tot = dfy_m.groupby("district")["parish_area_km2"].sum().rename("total_area_km2")

    # pick dominant parish: max area within district
    idx = dfy_m.groupby("district")["parish_area_km2"].idxmax()
    dom = dfy_m.loc[idx, ["district", "ID", "parish_area_km2"]].copy()
    dom = dom.rename(columns={
        "ID": "dominant_parish_1851_id",
        "parish_area_km2": "dominant_parish_area_km2",
    })
    dom["dominant_parish_1851_name"] = dom["dominant_parish_1851_id"].map(parish_name)

    dom = dom.merge(area_tot.reset_index(), on="district", how="left")
    dom["dominant_parish_area_share"] = dom["dominant_parish_area_km2"] / dom["total_area_km2"]

    g = g.merge(dom[[
        "district",
        "dominant_parish_1851_id",
        "dominant_parish_1851_name",
        "dominant_parish_area_km2",
        "total_area_km2",
        "dominant_parish_area_share",
    ]], on="district", how="left")

    summary_rows.append(g)

coverage = pd.concat(summary_rows, ignore_index=True)

# -----------------------
# Merge centroid diagnostics (distance + within/nearest)
# -----------------------
cent_small = cent[[
    "year",
    "constructed_district",
    "centroid_distance_km",
    "matched_via"
]].rename(columns={
    "constructed_district": "district",
    "matched_via": "centroid_matched_via"
})

final = coverage.merge(
    cent_small,
    on=["year", "district"],
    how="left"
)

# -----------------------
# Add centroid coordinates from constructed RD layers (x,y)
# -----------------------
centroid_xy_rows = []
for year in CENSUS_YEARS:
    layer = f"rd_{year}_constructed"
    g_rd = gpd.read_file(CONSTRUCTED_GPKG, layer=layer)

    # compute centroid in EPSG:27700 (or reproject if needed)
    if g_rd.crs is None:
        g_rd = g_rd.set_crs(epsg=CRS_EPSG)
    elif int(g_rd.crs.to_epsg() or CRS_EPSG) != CRS_EPSG:
        g_rd = g_rd.to_crs(epsg=CRS_EPSG)

    c = g_rd.geometry.centroid
    tmp = pd.DataFrame({
        "year": year,
        "district": g_rd["district"].astype(str),
        "centroid_x": c.x,
        "centroid_y": c.y,
    })
    centroid_xy_rows.append(tmp)

centroid_xy = pd.concat(centroid_xy_rows, ignore_index=True)

final = final.merge(
    centroid_xy,
    on=["year", "district"],
    how="left"
)

# -----------------------
# Geometry source flag
# -----------------------
final["geometry_source"] = final["usable_1851_backbone"].map({
    1: "1851_parish_reconstruction",
    0: "not_representable_on_1851_backbone"
})

# -----------------------
# Order & save
# -----------------------
final = final[[
    "year",
    "district",
    "active_parish_rows",
    "matched_parish_rows",
    "matched_share",
    "usable_1851_backbone",
    "n_parishes_matched",
    "total_area_km2",
    "dominant_parish_1851_id",
    "dominant_parish_1851_name",
    "dominant_parish_area_km2",
    "dominant_parish_area_share",
    "centroid_x",
    "centroid_y",
    "centroid_distance_km",
    "centroid_matched_via",
    "geometry_source",
]]

final.to_csv(OUT_PATH, index=False)

print("Saved final RD-year summary to:")
print(OUT_PATH)

print("\nUsable RD counts by year:")
print(
    final.groupby("year")["usable_1851_backbone"]
         .agg(total_RDs="count", usable_RDs="sum")
)
