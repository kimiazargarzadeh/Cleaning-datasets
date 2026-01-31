# Harmonization/match_ukbmd_to_1851_parishes.py
# Match UKBMD parish names (all years) to 1851 parish polygons,
# but only attempt geometry matching for parishes whose existence overlaps 1851.

import os
import re
import pandas as pd

# ------------------ paths ------------------
PARISH_1851_PATH = "Harmonization/1851EngWalesParishandPlace.csv"
UKBMD_MASTER_PATH = "Harmonization/data_intermediate/ukbmd_all_districts_all_years.csv"

OUT_DIR = "Harmonization/data_outputs"
os.makedirs(OUT_DIR, exist_ok=True)

# Output names updated to avoid confusion (this is now ALL-YEARS admin data)
OUT_MATCHED = os.path.join(OUT_DIR, "parish_rd_allyears_concordance.csv")
OUT_UNMATCHED = os.path.join(OUT_DIR, "parish_rd_allyears_unmatched_eligible1851.csv")
OUT_SUMMARY = os.path.join(OUT_DIR, "parish_rd_allyears_match_summary_by_district.csv")

REF_YEAR = 1851

# ------------------ helpers ------------------
def normalize_st_saint(s: str) -> str:
    """Convert St / St. / Saint -> saint (canonical token)."""
    s = re.sub(r"\bst[.]*\b", "saint", s, flags=re.IGNORECASE)
    s = re.sub(r"\bsaint\b", "saint", s, flags=re.IGNORECASE)
    return s

def strip_brackets(s: str) -> str:
    """Remove bracketed / parenthesized tags like [C51], (part), etc."""
    s = re.sub(r"\[[^\]]*\]", " ", s)   # remove [...]
    s = re.sub(r"\([^)]*\)", " ", s)    # remove (...)
    return s

def make_key(s: str, keep_comma: bool = False) -> str:
    """
    Stable matching key:
      - lowercase + strip
      - remove bracket tags [..] and (..)
      - normalize St/Saint -> saint
      - normalize '&' -> 'and'
      - normalize 'cum' -> 'with'
      - convert '-' and '/' to spaces
      - remove remaining punctuation (optionally keep comma)
      - collapse whitespace
    """
    s = str(s).lower().strip()
    s = strip_brackets(s)
    s = normalize_st_saint(s)
    s = s.replace("&", " and ")
    s = re.sub(r"\bcum\b", " with ", s)
    s = s.replace("-", " ").replace("/", " ")

    if keep_comma:
        s = re.sub(r"[^\w\s,]", " ", s)  # keep comma
    else:
        s = re.sub(r"[^\w\s]", " ", s)

    s = re.sub(r"\s+", " ", s).strip()
    return s

def coerce_year(x):
    """Make year numeric Int (or NA). UKBMD sometimes comes as float strings."""
    if pd.isna(x):
        return pd.NA
    s = str(x).strip()
    s = s.replace(".0", "")
    return int(s) if s.isdigit() else pd.NA

# ------------------ load ------------------
par = pd.read_csv(PARISH_1851_PATH)
uk = pd.read_csv(UKBMD_MASTER_PATH)

# sanity checks
required_par_cols = {"PLA", "ID"}
required_uk_cols = {"parish", "district", "from_year", "to_year"}
missing_par = required_par_cols - set(par.columns)
missing_uk = required_uk_cols - set(uk.columns)
if missing_par:
    raise ValueError(f"Missing columns in parish file: {missing_par}")
if missing_uk:
    raise ValueError(f"Missing columns in UKBMD master file: {missing_uk}")

# coerce years
uk = uk.copy()
uk["from_year"] = uk["from_year"].map(coerce_year)
uk["to_year"] = uk["to_year"].map(coerce_year)

# eligibility: parish existence overlaps 1851 (only these can map to 1851 polygons)
uk["eligible_1851"] = (
    uk["from_year"].notna()
    & (uk["from_year"] <= REF_YEAR)
    & ((uk["to_year"].isna()) | (uk["to_year"] >= REF_YEAR))
)

# ------------------ build parish lookup (1851 polygons) ------------------
par = par.copy()
par["key_full"] = par["PLA"].map(lambda x: make_key(x, keep_comma=True))

# index the part after comma(s) too (handles "DOVER, ST JAMES ..." and multi-comma names)
par["key_tail_first"] = par["key_full"].str.split(",", n=1).str[-1].str.strip()
par["key_tail_last"] = par["key_full"].str.rsplit(",", n=1).str[-1].str.strip()

# Build mapping key -> parish row index (keep first hit)
key_to_idx = {}
for idx, row in par[["key_full", "key_tail_first", "key_tail_last"]].iterrows():
    for k in row.tolist():
        if isinstance(k, str) and k and k not in key_to_idx:
            key_to_idx[k] = idx

# ------------------ match (ONLY for eligible_1851 rows) ------------------
uk["uk_key"] = pd.NA
uk.loc[uk["eligible_1851"], "uk_key"] = uk.loc[uk["eligible_1851"], "parish"].map(
    lambda x: make_key(x, keep_comma=False)
)

# IMPORTANT: initialize as nullable integer to avoid merge dtype issues
uk["matched_1851_index"] = pd.Series([pd.NA] * len(uk), dtype="Int64")
uk.loc[uk["eligible_1851"], "matched_1851_index"] = uk.loc[uk["eligible_1851"], "uk_key"].map(key_to_idx.get)

# Force to numeric Int64 (safety)
uk["matched_1851_index"] = pd.to_numeric(uk["matched_1851_index"], errors="coerce").astype("Int64")

uk["matched"] = uk["matched_1851_index"].notna()

out = uk.merge(
    par[["ID", "PLA"]],
    how="left",
    left_on="matched_1851_index",
    right_index=True
)

# ------------------ outputs ------------------
eligible_rows = int(out["eligible_1851"].sum())
eligible_matched = int((out["eligible_1851"] & out["matched"]).sum())

print("Total UKBMD rows (all years):", len(out))
print("Eligible for 1851 geometry:", eligible_rows)
print("Matched among eligible:", eligible_matched)
print("Eligible match rate:", (eligible_matched / eligible_rows) if eligible_rows else 0)

# Save full concordance (includes non-eligible rows; they just won't have ID/PLA)
out.to_csv(OUT_MATCHED, index=False)

# Save only unmatched among eligible (this is what you should improve)
unmatched_eligible = out.loc[out["eligible_1851"] & (~out["matched"])].copy()
unmatched_eligible.to_csv(OUT_UNMATCHED, index=False)

# Summary by district: restrict stats to eligible rows (otherwise meaningless)
summary = (
    out.loc[out["eligible_1851"]]
      .groupby("district", dropna=False)["matched"]
      .agg(rows="count", matched="sum")
      .reset_index()
)
summary["match_rate"] = summary["matched"] / summary["rows"]
summary = summary.sort_values(["match_rate", "rows"], ascending=[True, False])
summary.to_csv(OUT_SUMMARY, index=False)

print("Saved:", OUT_MATCHED)
print("Saved:", OUT_UNMATCHED)
print("Saved:", OUT_SUMMARY)
