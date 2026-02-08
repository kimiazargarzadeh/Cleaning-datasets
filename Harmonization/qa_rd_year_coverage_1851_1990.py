import pandas as pd
from pathlib import Path

INFILE = Path("Harmonization/data_outputs/rd_year_coverage_1851_backbone_1851_1990.csv")
OUTDIR = Path("Harmonization/data_outputs/qa_rd_year_coverage_1851_1990")
OUTDIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(INFILE)

# 1) Integrity checks
summary = {}
summary["year_min"] = int(df["year"].min())
summary["year_max"] = int(df["year"].max())
summary["n_rows"] = int(len(df))
summary["n_districts"] = int(df["district"].nunique())
summary["duplicate_year_district"] = int(df.duplicated(["year","district"]).sum())

bad = df[
    (df["active_parish_rows"] <= 0) |
    (df["matched_parish_rows"] < 0) |
    (df["matched_parish_rows"] > df["active_parish_rows"]) |
    (df["matched_share"] < 0) | (df["matched_share"] > 1)
]
summary["rows_violating_constraints"] = int(len(bad))

flag_inconsistent = df[(df["usable_1851_backbone"] == 1) & (df["matched_parish_rows"] == 0)]
summary["usable1_but_matched0"] = int(len(flag_inconsistent))

pd.Series(summary).to_csv(OUTDIR / "qa_summary.csv")

bad.to_csv(OUTDIR / "qa_bad_rows.csv", index=False)
flag_inconsistent.to_csv(OUTDIR / "qa_flag_inconsistent.csv", index=False)

# 2) Year summary
y = df.groupby("year").agg(
    n_districts=("district","nunique"),
    total_active_rows=("active_parish_rows","sum"),
    share_usable=("usable_1851_backbone","mean"),
    median_matched_share=("matched_share","median"),
    p10_matched_share=("matched_share", lambda s: s.quantile(0.10)),
    p90_matched_share=("matched_share", lambda s: s.quantile(0.90)),
).reset_index()

y["d_share_usable"] = y["share_usable"].diff()
y["d_n_districts"] = y["n_districts"].diff()

y.to_csv(OUTDIR / "year_summary.csv", index=False)

# 3) Outlier years
y.sort_values("d_share_usable").head(15).to_csv(OUTDIR / "biggest_drops_share_usable.csv", index=False)
y.sort_values("d_share_usable", ascending=False).head(15).to_csv(OUTDIR / "biggest_increases_share_usable.csv", index=False)
y.sort_values("d_n_districts").head(15).to_csv(OUTDIR / "biggest_drops_n_districts.csv", index=False)
y.sort_values("d_n_districts", ascending=False).head(15).to_csv(OUTDIR / "biggest_increases_n_districts.csv", index=False)

# 4) District outliers
never = df.groupby("district")["usable_1851_backbone"].max()
never = never[never == 0].reset_index()
never.to_csv(OUTDIR / "districts_never_usable.csv", index=False)

low = df[df["usable_1851_backbone"] == 1].nsmallest(200, "matched_share")
low.to_csv(OUTDIR / "lowest_matched_share_rows.csv", index=False)

print("QA outputs written to:", OUTDIR)
print(pd.Series(summary))
