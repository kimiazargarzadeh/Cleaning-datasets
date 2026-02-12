import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path("Harmonization")
DATA_OUT = BASE / "data_outputs"
DATA_OUT.mkdir(parents=True, exist_ok=True)

IN_CONC = DATA_OUT / "1_parish_matching" / "parish_rd_allyears_concordance.csv"
OUT = DATA_OUT / "4_final_coverage" / "rd_year_coverage_1851_backbone_1851_1990.csv"

Y0, Y1 = 1851, 1990

df = pd.read_csv(IN_CONC)

# Clean years
df["from_year"] = pd.to_numeric(df["from_year"], errors="coerce").fillna(1837).astype(int)
df["to_year"]   = pd.to_numeric(df["to_year"],   errors="coerce").fillna(9999).astype(int)

# Ensure matched is boolean/0-1
if df["matched"].dtype != bool:
    df["matched"] = df["matched"].fillna(False).astype(bool)

# Bound intervals to [Y0, Y1]
start = np.maximum(df["from_year"].to_numpy(), Y0)
end   = np.minimum(df["to_year"].to_numpy(),   Y1)
dur   = (end - start + 1)

keep = dur > 0
df = df.loc[keep].copy()
start = start[keep]
dur = dur[keep].astype(int)

# Expand each membership row into all active years (vectorized)
n = len(df)
idx = np.repeat(np.arange(n), dur)
year_offsets = np.concatenate([np.arange(k) for k in dur])
years = start[idx] + year_offsets

exp = df.iloc[idx][["district", "parish", "matched"]].copy()
exp["year"] = years

# Aggregate to RD x year
g = exp.groupby(["year", "district"], as_index=False)
out = g.agg(
    active_parish_rows=("parish", "size"),
    active_unique_parishes=("parish", "nunique"),
    matched_parish_rows=("matched", "sum"),
)

# matched unique parishes
out2 = exp[exp["matched"]].groupby(["year", "district"], as_index=False).agg(
    matched_unique_parishes=("parish", "nunique")
)
out = out.merge(out2, on=["year", "district"], how="left")
out["matched_unique_parishes"] = out["matched_unique_parishes"].fillna(0).astype(int)

out["matched_share"] = out["matched_parish_rows"] / out["active_parish_rows"]
out["usable_1851_backbone"] = (out["matched_parish_rows"] > 0).astype(int)

out.to_csv(OUT, index=False)
print("Saved:", OUT)
print("Years covered:", out["year"].min(), "to", out["year"].max())
print("Share usable by year (first/last 5 years):")
print(pd.concat([out.groupby("year")["usable_1851_backbone"].mean().head(5),
                 out.groupby("year")["usable_1851_backbone"].mean().tail(5)]))
