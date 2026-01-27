import pandas as pd
import geopandas as gpd
from pathlib import Path

# -----------------------------
# Paths
# -----------------------------
CONCORDANCE_CSV = Path("Harmonization/data_outputs/parish_rd_1851_concordance.csv")
PARISH_1851_CSV = Path("Harmonization/1851EngWalesParishandPlace.csv")

OUT_GPKG  = Path("Harmonization/data_outputs/rd_constructed_from_1851_parishes.gpkg")
OUT_LAYER = "rd_1851_constructed"

# -----------------------------
# 1) Load concordance (parish ID -> RD)
# -----------------------------
con = pd.read_csv(CONCORDANCE_CSV)

# If you have a matched flag, keep only matched rows
if "matched" in con.columns:
    con = con[con["matched"].astype(bool)].copy()

# Keep only what we need
# Assumes these columns exist in your concordance:
# - ID (parish id)
# - district (RD name)
con = con[["ID", "district"]].drop_duplicates()

con["ID"] = pd.to_numeric(con["ID"], errors="coerce")
con = con[con["ID"].notna()].copy()
con["ID"] = con["ID"].astype(int)

# -----------------------------
# 2) Load parish polygons from CSV (WKT in 'geometry')
# -----------------------------
par = pd.read_csv(PARISH_1851_CSV)

# Ensure required columns exist
if "ID" not in par.columns:
    raise ValueError("Parish CSV is missing 'ID' column.")
if "geometry" not in par.columns:
    raise ValueError("Parish CSV is missing 'geometry' column (WKT polygons).")

par["ID"] = pd.to_numeric(par["ID"], errors="coerce")
par = par[par["ID"].notna()].copy()
par["ID"] = par["ID"].astype(int)

# Convert WKT -> shapely geometries
gpar = gpd.GeoDataFrame(
    par,
    geometry=gpd.GeoSeries.from_wkt(par["geometry"]),
    crs="EPSG:27700"  # British National Grid
)

# -----------------------------
# 3) Merge parish geometries with RD labels, then dissolve
# -----------------------------
gpar_with_rd = gpar.merge(con, on="ID", how="inner")

rd_constructed = gpar_with_rd.dissolve(by="district", as_index=False)

# QC: count parishes used in each RD
rd_constructed["n_parishes_matched"] = (
    gpar_with_rd.groupby("district")["ID"].nunique()
    .reindex(rd_constructed["district"]).values
)

# -----------------------------
# 4) Save
# -----------------------------
OUT_GPKG.parent.mkdir(parents=True, exist_ok=True)
rd_constructed.to_file(OUT_GPKG, layer=OUT_LAYER, driver="GPKG")

print("Saved:", OUT_GPKG, "layer:", OUT_LAYER)
print("Constructed RDs:", len(rd_constructed))

# Show the weakest coverage RDs (useful given your ~90% match)
print(
    rd_constructed[["district", "n_parishes_matched"]]
    .sort_values("n_parishes_matched")
    .head(15)
)
