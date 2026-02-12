"""
Deep dive into remaining unmatched parishes after improvements
Look for additional safe patterns to fix
"""
import pandas as pd
import re
from collections import Counter

unmatched = pd.read_csv("Harmonization/data_outputs/parish_rd_allyears_unmatched_IMPROVED.csv")
parishes_1851 = pd.read_csv("Harmonization/1851EngWalesParishandPlace.csv")

print("=" * 80)
print(f"REMAINING UNMATCHED: {len(unmatched):,} parishes")
print("=" * 80)

# Create normalized lookup for fuzzy checking
par_norm = {}
for _, row in parishes_1851.iterrows():
    key = row['PLA'].lower().strip().replace(' ', '')
    par_norm[key] = row['PLA']

# Pattern analysis
patterns = {
    "has_&": [],
    "has_saint_vs_st": [],
    "very_short_name": [],
    "number_in_name": [],
    "near_miss_1_char": [],
    "near_miss_2_char": [],
}

print("\nChecking for patterns...")

for idx, row in unmatched.iterrows():
    parish = str(row['parish'])
    parish_clean = parish.lower().strip().replace(' ', '')

    # & in name
    if '&' in parish:
        patterns["has_&"].append(parish)

    # Saint vs St issues
    if 'saint' in parish.lower() or ' st ' in parish.lower() or parish.lower().startswith('st '):
        patterns["has_saint_vs_st"].append(parish)

    # Very short names (might be abbreviations)
    if len(parish_clean) <= 4:
        patterns["very_short_name"].append(parish)

    # Has numbers
    if any(c.isdigit() for c in parish):
        patterns["number_in_name"].append(parish)

    # Near misses (1-2 char difference)
    # Check if there's a 1851 parish with very similar name
    for norm_key, orig_name in par_norm.items():
        if abs(len(parish_clean) - len(norm_key)) <= 2:
            # Count differences
            if len(parish_clean) == len(norm_key):
                diff_count = sum(1 for a, b in zip(parish_clean, norm_key) if a != b)
                if diff_count == 1:
                    patterns["near_miss_1_char"].append((parish, orig_name, parish_clean, norm_key))
                    break
                elif diff_count == 2:
                    patterns["near_miss_2_char"].append((parish, orig_name, parish_clean, norm_key))
                    break

print("\n" + "=" * 80)
print("PATTERN ANALYSIS")
print("=" * 80)

for pattern, examples in patterns.items():
    if pattern in ["near_miss_1_char", "near_miss_2_char"]:
        if len(examples) > 0:
            print(f"\n{pattern}: {len(examples)} cases")
            print("  Examples (UKBMD → 1851 candidate):")
            for ukbmd, p1851, uk_norm, p_norm in examples[:10]:
                print(f"    '{ukbmd}' → '{p1851}'")
                print(f"      ('{uk_norm}' vs '{p_norm}')")
    else:
        if len(examples) > 0:
            print(f"\n{pattern}: {len(examples)} cases")
            print(f"  Examples: {', '.join(examples[:10])}")

# Most common unmatched (by frequency)
print("\n" + "=" * 80)
print("MOST FREQUENT UNMATCHED PARISHES")
print("=" * 80)
freq = unmatched['parish'].value_counts().head(20)
for parish, count in freq.items():
    print(f"  {parish}: {count} times")

# Sample manual inspection
print("\n" + "=" * 80)
print("SAMPLE FOR MANUAL INSPECTION (first 30 unique)")
print("=" * 80)
sample = unmatched['parish'].unique()[:30]
for i, parish in enumerate(sample, 1):
    parish_norm = parish.lower().strip().replace(' ', '')
    # Find closest 1851 match by prefix
    prefix = parish_norm[:4] if len(parish_norm) >= 4 else parish_norm
    candidates = [p for key, p in par_norm.items() if key.startswith(prefix)][:3]

    print(f"{i}. '{parish}'")
    if candidates:
        print(f"     → Candidates: {', '.join(candidates)}")

print("\n" + "=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)
print("Review the near_miss_1_char and near_miss_2_char cases above.")
print("These might be legitimate matches (Welsh spelling variants, typos).")
print("But they require manual verification to avoid false positives.")
print("=" * 80)
