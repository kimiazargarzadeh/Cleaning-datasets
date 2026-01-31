import pandas as pd
import geopandas as gpd
from pathlib import Path

# -----------------------------
# Config
# -----------------------------
CENSUS_YEARS = [1851, 1861, 1871, 1881, 1891, 1901, 1911]

# Use the ALL-YEARS concordance you just created
CONCORDANCE_CSV = Path("Harmonization/data_outputs/parish_rd_allyears_concordance.csv")
PARISH_1851_CSV = Path("Harmonization/1851EngWalesParishandPlace.csv")

OUT_GPKG = Path("Harmonization/data_outputs/rd_constructed_from_1851_parishes.gpkg")
CRS_EPSG = 27700  # British National Grid

# -----------------------------
# Helpers
# -----------------------------
def coerce_year(x):
    if pd.isna(x):
        return pd.NA
    s = str(x).strip().replace(".0", "")
    return int(s) if s.isdigit() else pd.NA

def filter_membership(con: pd.DataFrame, year: int) -> pd.DataFrame:
    """
    Keep parish-RD membership rows active at 'year'.
    Only rows that have a matched 1851 parish polygon (ID not null).
    """
    c = con.copy()

    # ensure years are numeric
    c["from_year"] = c["from_year"].map(coerce_year)
    c["to_year"] = c["to_year"].map(coerce_year)

    active = (
        c["from_year"].notna()
        & (c["from_year"] <= year)
        & ((c["to_year"].isna()) | (c["to_year"] >= year))
    )

    # Only keep those that matched to 1851 polygons
    if "matched" in c.columns:
        matched = c["matched"].astype(bool)
    else:
        matched = c["ID"].notna()

    c = c[active & matched].copy()

    # Keep only ID and district
    c = c[["ID", "district"]].drop_duplicates()

    c["ID"] = pd.to_numeric(c["ID"], errors="coerce")
    c = c[c["ID"].notna()].copy()
    c["ID"] = c["ID"].astype(int)

    return c

# -----------------------------
# Load inputs once
# -----------------------------
print("Loading concordance:", CONCORDANCE_CSV)
con = pd.read_csv(CONCORDANCE_CSV)

print("Loading 1851 parish polygons:", PARISH_1851_CSV)
par = pd.read_csv(PARISH_1851_CSV)

if "ID" not in par.columns:
    raise ValueError("Parish CSV is missing 'ID' column.")
if "geometry" not in par.columns:
    raise ValueError("Parish CSV is missing 'geometry' column (WKT polygons).")

par["ID"] = pd.to_numeric(par["ID"], errors="coerce")
par = par[par["ID"].notna()].copy()
par["ID"] = par["ID"].astype(int)

gpar = gpd.GeoDataFrame(
    par,
    geometry=gpd.GeoSeries.from_wkt(par["geometry"]),
    crs=f"EPSG:{CRS_EPSG}",
)

OUT_GPKG.parent.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Loop over census years
# -----------------------------
for year in CENSUS_YEARS:
    layer = f"rd_{year}_constructed"
    print(f"\n=== Constructing {layer} ===")

    con_y = filter_membership(con, year)
    print(f"Active matched parish-RD rows at {year}: {len(con_y)}")

    # Merge parish geometries with RD labels, then dissolve
    gpar_with_rd = gpar.merge(con_y, on="ID", how="inner")

    rd_constructed = gpar_with_rd.dissolve(by="district", as_index=False)

    # QC: count unique parishes per RD
    counts = (
        gpar_with_rd.groupby("district")["ID"].nunique()
        .reset_index()
        .rename(columns={"ID": "n_parishes_matched"})
    )
    rd_constructed = rd_constructed.merge(counts, on="district", how="left")

    # Save layer
    rd_constructed.to_file(OUT_GPKG, layer=layer, driver="GPKG")

    print("Saved:", OUT_GPKG, "layer:", layer)
    print("Constructed RDs:", len(rd_constructed))
    print(
        rd_constructed[["district", "n_parishes_matched"]]
        .sort_values("n_parishes_matched")
        .head(10)
    )

print("\nDONE constructing all census-year layers into:", OUT_GPKG)
