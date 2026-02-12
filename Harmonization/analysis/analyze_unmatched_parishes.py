"""
Analyze patterns in unmatched parishes to improve matching
"""
import pandas as pd
import re
from collections import Counter

# Load unmatched parishes
unmatched = pd.read_csv("Harmonization/data_outputs/parish_rd_1851_unmatched.csv")
parishes_1851 = pd.read_csv("Harmonization/1851EngWalesParishandPlace.csv")

print("=" * 80)
print("UNMATCHED PARISH ANALYSIS")
print("=" * 80)
print(f"Total unmatched: {len(unmatched):,}")
print(f"Total 1851 parishes available: {len(parishes_1851):,}")

# Pattern detection
patterns = {
    "has_with": [],
    "has_on": [],
    "has_nigh": [],
    "has_special_chars": [],
    "starts_lower_upper": [],
    "has_ampersand": [],
    "very_long_name": [],
    "welsh_double_l": [],
}

for idx, row in unmatched.iterrows():
    parish = str(row['parish']).lower()

    if ' with ' in parish or parish.startswith('with '):
        patterns["has_with"].append(row['parish'])
    if ' on ' in parish or ' on the ' in parish:
        patterns["has_on"].append(row['parish'])
    if ' nigh ' in parish:
        patterns["has_nigh"].append(row['parish'])
    if any(c in parish for c in ['ô', 'â', 'ê', 'î', 'û', 'ŵ', 'ŷ']):
        patterns["has_special_chars"].append(row['parish'])
    if parish.startswith('lower ') or parish.startswith('upper '):
        patterns["starts_lower_upper"].append(row['parish'])
    if '&' in row['parish']:
        patterns["has_ampersand"].append(row['parish'])
    if len(parish) > 40:
        patterns["very_long_name"].append(row['parish'])
    if 'llan' in parish and 'll' in parish:
        patterns["welsh_double_l"].append(row['parish'])

print("\n" + "=" * 80)
print("PATTERN BREAKDOWN")
print("=" * 80)
for pattern, examples in patterns.items():
    if len(examples) > 0:
        print(f"\n{pattern}: {len(examples)} parishes")
        print(f"  Examples: {', '.join(examples[:5])}")

# Most common unmatched by district
print("\n" + "=" * 80)
print("DISTRICTS WITH MOST UNMATCHED PARISHES")
print("=" * 80)
district_counts = unmatched['district'].value_counts().head(10)
for dist, count in district_counts.items():
    print(f"  {dist}: {count} unmatched")

# Check for near-matches using simple Levenshtein-like approach
print("\n" + "=" * 80)
print("POTENTIAL NEAR-MATCHES (sample)")
print("=" * 80)

# Normalize 1851 parish names for comparison
parishes_1851['normalized'] = parishes_1851['PLA'].str.lower().str.strip()

# Sample 20 unmatched and check if there are very close matches
sample_unmatched = unmatched.head(20)
for idx, row in sample_unmatched.iterrows():
    uk_name = row['uk_key']  # already normalized

    # Find 1851 parishes that start with same first 5 characters
    if len(uk_name) >= 5:
        prefix = uk_name[:5]
        candidates = parishes_1851[parishes_1851['normalized'].str.startswith(prefix)]['PLA'].tolist()

        if len(candidates) > 0:
            print(f"\n  UKBMD: '{row['parish']}'")
            print(f"    Normalized: '{uk_name}'")
            print(f"    Potential 1851 matches: {candidates[:3]}")

print("\n" + "=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)
print("1. Handle 'with' variants: Try matching without 'with' clause")
print("   Example: 'Appleton with Eaton' → try 'Appleton'")
print("")
print("2. Handle 'on/on the' variants: Try with and without")
print("   Example: 'Bidford on Avon' → try 'Bidford'")
print("")
print("3. Remove Welsh accents: Normalize ô→o, â→a, etc.")
print("   Example: 'Rhôstie' → 'Rhostie'")
print("")
print("4. Handle 'nigh' (near): Try both with/without")
print("   Example: 'Llangattock nigh Usk' → try 'Llangattock'")
print("")
print("5. Handle Lower/Upper prefixes: Try stripping them")
print("   Example: 'Lower Cwmyoy' → try 'Cwmyoy'")
print("")
print("6. Implement fuzzy matching (Levenshtein distance ≤ 2) for remaining")
print("=" * 80)
