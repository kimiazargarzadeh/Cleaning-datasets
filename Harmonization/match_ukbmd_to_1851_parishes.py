"""
IMPROVED parish matching with better normalization rules
Based on analysis of unmatched patterns

Improvements over original (SAFE IMPROVEMENTS ONLY):
1. Strip Welsh accents (ô→o, â→a, etc.)
2. Handle "with X" clauses (try with and without)
3. Handle "on/on the" variants
4. Handle "nigh" (meaning near)
5. Strip "Lower/Upper" prefixes
6. Handle 1851 suffixes (- UPPER DIVISION, etc.)
7. Strip all spaces (Bessels Leigh ↔ Besselsleigh)
8. Welsh spelling variants (v↔f, i↔y, ch↔gh)
   - Llanvair ↔ Llanfair
   - Dihewid ↔ Dihewyd
   - Clarach ↔ Claragh
9. Vowel interchange (a↔e, e↔i)
   - Courtenay ↔ Courteney
   - Tedworth ↔ Tidworth
10. Substring matching
   - "Shawdon" ⊂ "SHAWDON AND WOODHOUSE"
   - "Durnford" ⊂ "GREAT DURNFORD"

NOTE: Fuzzy matching is SKIPPED to avoid false positives.
Remaining unmatched parishes should be reviewed manually.
"""
import os
import re
import pandas as pd
import unicodedata
from difflib import SequenceMatcher

# Paths
PARISH_1851_PATH = "Harmonization/1851EngWalesParishandPlace.csv"
UKBMD_MASTER_PATH = "Harmonization/data_intermediate/ukbmd_all_districts_all_years.csv"

OUT_DIR = "Harmonization/data_outputs/1_parish_matching"
os.makedirs(OUT_DIR, exist_ok=True)

OUT_MATCHED = os.path.join(OUT_DIR, "parish_rd_allyears_concordance.csv")
OUT_UNMATCHED = os.path.join(OUT_DIR, "parish_rd_allyears_unmatched.csv")
OUT_SUMMARY = os.path.join(OUT_DIR, "parish_rd_allyears_match_summary_by_district.csv")

REF_YEAR = 1851

print("=" * 80)
print("IMPROVED PARISH MATCHING")
print("=" * 80)

# ==================== IMPROVED NORMALIZATION ====================

def strip_accents(s):
    """Remove Welsh and other diacritical marks: ô→o, â→a, ŵ→w, etc."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )

def normalize_st_saint(s):
    s = re.sub(r'\bst[.]*\b', 'saint', s, flags=re.IGNORECASE)
    s = re.sub(r'\bsaint\b', 'saint', s, flags=re.IGNORECASE)
    return s

def strip_brackets(s):
    s = re.sub(r'\[[^\]]*\]', ' ', s)
    s = re.sub(r'\([^)]*\)', ' ', s)
    return s

def make_key_improved(s, keep_comma=False):
    """Improved normalization with Welsh accent handling"""
    s = str(s).lower().strip()
    s = strip_accents(s)  # NEW: Remove accents
    s = strip_brackets(s)
    s = normalize_st_saint(s)
    s = s.replace("&", " and ")
    s = re.sub(r'\bcum\b', ' with ', s)
    s = s.replace("-", " ").replace("/", " ")

    if keep_comma:
        s = re.sub(r'[^\w\s,]', ' ', s)
    else:
        s = re.sub(r'[^\w\s]', ' ', s)

    s = re.sub(r'\s+', ' ', s).strip()
    return s

def make_welsh_variants(s):
    """Generate Welsh spelling variants (v↔f, i↔y, ch↔gh)"""
    variants = []

    # v ↔ f (Llanvair ↔ Llanfair)
    if 'v' in s:
        variants.append(s.replace('v', 'f'))
    if 'f' in s:
        variants.append(s.replace('f', 'v'))

    # i ↔ y (Dihewid ↔ Dihewyd)
    if 'i' in s:
        variants.append(s.replace('i', 'y'))
    if 'y' in s:
        variants.append(s.replace('y', 'i'))

    # ch ↔ gh (Clarach ↔ Claragh)
    if 'ch' in s:
        variants.append(s.replace('ch', 'gh'))
    if 'gh' in s:
        variants.append(s.replace('gh', 'ch'))

    return variants

def make_vowel_variants(s):
    """Generate common vowel interchange variants (a↔e, e↔i)"""
    variants = []

    # a ↔ e (Courtenay ↔ Courteney, Tedworth ↔ Tidworth)
    if 'a' in s:
        variants.append(s.replace('a', 'e'))
    if 'e' in s and 'a' not in s:  # Avoid double replacement
        variants.append(s.replace('e', 'a'))

    # e ↔ i (Tedworth ↔ Tidworth)
    if 'e' in s:
        variants.append(s.replace('e', 'i'))
    if 'i' in s:
        variants.append(s.replace('i', 'e'))

    return variants

def make_variants(s):
    """Generate multiple matching variants for a parish name"""
    variants = []
    base = make_key_improved(s)
    variants.append((base, "exact"))

    # NEW: Welsh spelling variants (v↔f, i↔y, ch↔gh)
    for welsh_var in make_welsh_variants(base):
        if welsh_var != base:
            variants.append((welsh_var, "welsh_variant"))

    # NEW: Vowel interchange (a↔e, e↔i)
    for vowel_var in make_vowel_variants(base):
        if vowel_var != base:
            variants.append((vowel_var, "vowel_variant"))

    # Strip ALL spaces (catches "Bessels Leigh" vs "Besselsleigh")
    no_spaces = base.replace(' ', '')
    if no_spaces != base:
        variants.append((no_spaces, "no_spaces"))
        # Also try Welsh + vowel variants without spaces
        for welsh_var in make_welsh_variants(no_spaces):
            if welsh_var != no_spaces:
                variants.append((welsh_var, "welsh_variant_no_spaces"))
        for vowel_var in make_vowel_variants(no_spaces):
            if vowel_var != no_spaces:
                variants.append((vowel_var, "vowel_variant_no_spaces"))

    # Strip "with X" clause
    if ' with ' in base:
        without_with = re.sub(r'\s+with\s+.*', '', base).strip()
        if without_with:
            variants.append((without_with, "without_with"))
            # Also try without_with + no spaces
            variants.append((without_with.replace(' ', ''), "without_with_no_spaces"))

    # Strip "on" / "on the"
    if ' on ' in base:
        without_on = re.sub(r'\s+on\s+(the\s+)?.*', '', base).strip()
        if without_on:
            variants.append((without_on, "without_on"))

    # Strip "nigh"
    if ' nigh ' in base:
        without_nigh = re.sub(r'\s+nigh\s+.*', '', base).strip()
        if without_nigh:
            variants.append((without_nigh, "without_nigh"))

    # Strip Lower/Upper prefix
    if base.startswith('lower '):
        without_prefix = base[6:].strip()
        if without_prefix:
            variants.append((without_prefix, "without_lower"))
            variants.append((without_prefix.replace(' ', ''), "without_lower_no_spaces"))
            # Welsh variants of lower/upper stripped versions
            for welsh_var in make_welsh_variants(without_prefix.replace(' ', '')):
                if welsh_var != without_prefix.replace(' ', ''):
                    variants.append((welsh_var, "without_lower_welsh"))
    elif base.startswith('upper '):
        without_prefix = base[6:].strip()
        if without_prefix:
            variants.append((without_prefix, "without_upper"))
            variants.append((without_prefix.replace(' ', ''), "without_upper_no_spaces"))
            # Welsh variants of lower/upper stripped versions
            for welsh_var in make_welsh_variants(without_prefix.replace(' ', '')):
                if welsh_var != without_prefix.replace(' ', ''):
                    variants.append((welsh_var, "without_upper_welsh"))

    return variants

def levenshtein_distance(s1, s2):
    """Calculate Levenshtein distance between two strings"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def coerce_year(x):
    if pd.isna(x):
        return pd.NA
    s = str(x).strip().replace(".0", "")
    return int(s) if s.isdigit() else pd.NA

# ==================== LOAD DATA ====================

print("\n[1/6] Loading data...")
par = pd.read_csv(PARISH_1851_PATH)
uk = pd.read_csv(UKBMD_MASTER_PATH)

print(f"  1851 parishes: {len(par):,}")
print(f"  UKBMD parish-RD rows: {len(uk):,}")

# Coerce years
uk = uk.copy()
uk["from_year"] = uk["from_year"].map(coerce_year)
uk["to_year"] = uk["to_year"].map(coerce_year)

# 1851 eligibility
uk["eligible_1851"] = (
    uk["from_year"].notna()
    & (uk["from_year"] <= REF_YEAR)
    & ((uk["to_year"].isna()) | (uk["to_year"] >= REF_YEAR))
)

# ==================== BUILD PARISH LOOKUP ====================

print("\n[2/6] Building 1851 parish lookup with improved normalization...")
par = par.copy()
par["key_full"] = par["PLA"].map(lambda x: make_key_improved(x, keep_comma=True))
par["key_no_comma"] = par["PLA"].map(lambda x: make_key_improved(x, keep_comma=False))

# Strip suffixes like " - UPPER DIVISION", " - LOWER DIVISION", " - CITRA AND ULTRA DIVISIONS"
par["key_no_suffix"] = par["key_no_comma"].str.replace(
    r'\s+(upper|lower|citra|ultra)\s+(and\s+)?(division|divisions?)', '', regex=True
).str.strip()

# Build lookup dictionary
lookup = {}
for _, row in par.iterrows():
    keys_to_add = [row["key_full"], row["key_no_comma"], row["key_no_suffix"]]

    # Also add no-space variants for each key
    for key in keys_to_add[:]:  # Copy list to avoid modifying during iteration
        if key:
            keys_to_add.append(key.replace(' ', ''))

    # NEW: Add Welsh + vowel variants for all keys
    all_keys_with_variants = []
    for key in keys_to_add:
        if key:
            all_keys_with_variants.append(key)
            # Add Welsh variants
            for welsh_var in make_welsh_variants(key):
                if welsh_var != key:
                    all_keys_with_variants.append(welsh_var)
            # Add vowel variants
            for vowel_var in make_vowel_variants(key):
                if vowel_var != key:
                    all_keys_with_variants.append(vowel_var)

    for key in all_keys_with_variants:
        if key and key not in lookup:
            lookup[key] = row["ID"]

print(f"  Parish lookup keys: {len(lookup):,}")

# Also create list for fuzzy matching
parish_keys_for_fuzzy = list(lookup.keys())

# ==================== STAGE 1: EXACT + VARIANT MATCHING ====================

print("\n[3/6] Stage 1: Matching with exact + variants...")
uk_parishes = uk["parish"].unique()
stage1_matches = {}
stage1_methods = {}

for parish_name in uk_parishes:
    if pd.isna(parish_name):
        continue

    variants = make_variants(parish_name)
    for variant_key, method in variants:
        if variant_key in lookup:
            stage1_matches[parish_name] = lookup[variant_key]
            stage1_methods[parish_name] = method
            break

matched_stage1 = len(stage1_matches)
print(f"  Matched in Stage 1 (exact + variants): {matched_stage1:,}")

# ==================== STAGE 1B: SUBSTRING MATCHING ====================

print("\n[3b/6] Stage 1b: Substring matching...")
print("  (UKBMD name is substring of 1851 name)")

# Build reverse lookup for substring matching
par_keys_list = list(parish_keys_for_fuzzy)

stage1b_matches = {}
stage1b_methods = {}

for parish_name in uk_parishes:
    if pd.isna(parish_name) or parish_name in stage1_matches:
        continue

    base_key = make_key_improved(parish_name).replace(' ', '')

    # Only try substring if name is long enough
    if len(base_key) < 5:
        continue

    # Find 1851 parishes where UKBMD name is a substring
    for key_1851 in par_keys_list:
        # Is UKBMD a substring of 1851?
        if base_key in key_1851 and base_key != key_1851:
            # Check if length difference is reasonable (not too different)
            if len(key_1851) - len(base_key) <= 15:
                stage1b_matches[parish_name] = lookup[key_1851]
                stage1b_methods[parish_name] = "substring_match"
                break

matched_stage1b = len(stage1b_matches)
print(f"  Matched in Stage 1b (substring): {matched_stage1b:,}")

# Combine Stage 1 and 1b
all_stage1_matches = {**stage1_matches, **stage1b_matches}
all_stage1_methods = {**stage1_methods, **stage1b_methods}

# ==================== SKIP FUZZY MATCHING (TOO RISKY) ====================

print("\n[4/6] Stage 2: Fuzzy matching SKIPPED (manual review preferred)")
print(f"  Unmatched after all stages: {len([p for p in uk_parishes if pd.notna(p) and p not in all_stage1_matches]):,}")

# ==================== COMBINE RESULTS ====================

print("\n[5/6] Combining results...")
all_matches = all_stage1_matches
all_methods = all_stage1_methods

uk["matched_1851_index"] = uk["parish"].map(all_matches)
uk["matched"] = uk["matched_1851_index"].notna()
uk["match_method"] = uk["parish"].map(all_methods)

# Merge with 1851 parish data
uk = uk.merge(
    par[["ID", "PLA"]],
    left_on="matched_1851_index",
    right_on="ID",
    how="left"
)

# ==================== SUMMARY ====================

total = len(uk)
eligible = uk["eligible_1851"].sum()
matched = uk[uk["eligible_1851"]]["matched"].sum()
unmatched_eligible = eligible - matched

print("\n" + "=" * 80)
print("RESULTS SUMMARY")
print("=" * 80)
print(f"Total parish-RD rows: {total:,}")
print(f"Eligible for 1851 (overlap 1851): {eligible:,}")
print(f"Matched to 1851 geometry: {matched:,} ({matched/eligible*100:.1f}%)")
print(f"Unmatched (eligible): {unmatched_eligible:,} ({unmatched_eligible/eligible*100:.1f}%)")

# Match method breakdown
if matched > 0:
    print("\nMatch method breakdown:")
    method_counts = uk[uk["matched"] & uk["eligible_1851"]]["match_method"].value_counts()
    for method, count in method_counts.items():
        print(f"  {method}: {count:,} ({count/matched*100:.1f}%)")

# ==================== SAVE OUTPUTS ====================

print("\n[6/6] Saving outputs...")
uk.to_csv(OUT_MATCHED, index=False)
print(f"✓ Saved: {OUT_MATCHED}")

unmatched = uk[uk["eligible_1851"] & ~uk["matched"]].copy()
unmatched.to_csv(OUT_UNMATCHED, index=False)
print(f"✓ Saved: {OUT_UNMATCHED} ({len(unmatched):,} rows)")

# District-level summary
district_summary = uk[uk["eligible_1851"]].groupby("district").agg(
    total_eligible=("parish", "size"),
    matched=("matched", "sum"),
    match_rate=("matched", "mean")
).reset_index().sort_values("match_rate")

district_summary.to_csv(OUT_SUMMARY, index=False)
print(f"✓ Saved: {OUT_SUMMARY}")

print("\n" + "=" * 80)
print("COMPARISON TO ORIGINAL MATCHING")
print("=" * 80)
print("Original match rate: 89.0% (14,264 / 15,976)")
print(f"Improved match rate: {matched/eligible*100:.1f}% ({matched:,} / {eligible:,})")
improvement = (matched / eligible) - 0.890
additional = matched - 14264
print(f"Improvement: +{improvement*100:.1f} percentage points")
print(f"Additional parishes matched: {additional:,}")
print("=" * 80)
