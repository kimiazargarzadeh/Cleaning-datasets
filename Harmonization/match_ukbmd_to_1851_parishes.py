# Harmonization/match_ukbmd_to_1851_parishes.py
# Step 7.4 (updated key cleaning): match UKBMD 1851-eligible parishes to 1851 parish polygons

import os
import re
import pandas as pd

# ------------------ paths ------------------
PARISH_1851_PATH = "Harmonization/1851EngWalesParishandPlace.csv"
UKBMD_MASTER_PATH = "Harmonization/data_intermediate/ukbmd_1851_all_districts.csv"

OUT_DIR = "Harmonization/data_outputs"
OUT_MATCHED = os.path.join(OUT_DIR, "parish_rd_1851_concordance.csv")
OUT_UNMATCHED = os.path.join(OUT_DIR, "parish_rd_1851_unmatched.csv")
OUT_SUMMARY = os.path.join(OUT_DIR, "parish_rd_1851_match_summary_by_district.csv")

os.makedirs(OUT_DIR, exist_ok=True)

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
      - convert '-' and '/' to spaces (prevents word concatenation like breadstreet)
      - remove remaining punctuation (optionally keep comma)
      - collapse whitespace
    """
    s = str(s).lower().strip()

    # remove footnote-like tags common in historical place names
    s = strip_brackets(s)

    # normalize saint/st
    s = normalize_st_saint(s)

    # normalize "&"
    s = s.replace("&", " and ")

    # normalize cum
    s = re.sub(r"\bcum\b", " with ", s)

    # IMPORTANT: turn separators into spaces BEFORE stripping punctuation
    s = s.replace("-", " ").replace("/", " ")

    if keep_comma:
        s = re.sub(r"[^\w\s,]", " ", s)  # keep comma
    else:
        s = re.sub(r"[^\w\s]", " ", s)

    s = re.sub(r"\s+", " ", s).strip()
    return s

# ------------------ load ------------------
par = pd.read_csv(PARISH_1851_PATH)
uk = pd.read_csv(UKBMD_MASTER_PATH)

# sanity checks
required_par_cols = {"PLA", "ID"}
required_uk_cols = {"parish", "district"}
missing_par = required_par_cols - set(par.columns)
missing_uk = required_uk_cols - set(uk.columns)
if missing_par:
    raise ValueError(f"Missing columns in parish file: {missing_par}")
if missing_uk:
    raise ValueError(f"Missing columns in UKBMD master file: {missing_uk}")

# ------------------ build parish lookup ------------------
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

# ------------------ match ------------------
uk["uk_key"] = uk["parish"].map(lambda x: make_key(x, keep_comma=False))
uk["matched_1851_index"] = uk["uk_key"].map(key_to_idx.get)
uk["matched"] = uk["matched_1851_index"].notna()

out = uk.merge(
    par[["ID", "PLA"]],
    how="left",
    left_on="matched_1851_index",
    right_index=True
)

# ------------------ outputs ------------------
print("Total UKBMD rows:", len(out))
print("Matched rows:", int(out["matched"].sum()))
print("Match rate:", out["matched"].mean())

out.to_csv(OUT_MATCHED, index=False)

unmatched = out.loc[~out["matched"]].copy()
unmatched.to_csv(OUT_UNMATCHED, index=False)

summary = (
    out.groupby("district", dropna=False)["matched"]
      .agg(rows="count", matched="sum")
      .reset_index()
)
summary["match_rate"] = summary["matched"] / summary["rows"]
summary = summary.sort_values(["match_rate", "rows"], ascending=[True, False])
summary.to_csv(OUT_SUMMARY, index=False)

print("Saved:", OUT_MATCHED)
print("Saved:", OUT_UNMATCHED)
print("Saved:", OUT_SUMMARY)
