"""
Deep dive: Find more safe matching patterns in remaining unmatched
"""
import pandas as pd
import re
from collections import defaultdict

unmatched = pd.read_csv("Harmonization/data_outputs/parish_rd_allyears_unmatched_IMPROVED.csv")
parishes_1851 = pd.read_csv("Harmonization/1851EngWalesParishandPlace.csv")

print("=" * 80)
print(f"DEEP DIVE: {len(unmatched):,} remaining unmatched")
print("=" * 80)

# Normalize 1851 parishes for lookup
par_lookup = {}
for _, row in parishes_1851.iterrows():
    key = row['PLA'].lower().strip().replace(' ', '')
    par_lookup[key] = row['PLA']

# Look for specific patterns
print("\n[1] Looking for EXACT matches with minor differences...")
print("-" * 80)

exact_with_typo = []
for idx, row in unmatched.head(100).iterrows():  # Sample first 100
    parish = str(row['parish'])
    parish_norm = parish.lower().strip().replace(' ', '')

    # Try finding in 1851 with very small edits
    for key_1851, orig_1851 in par_lookup.items():
        # Same length, 1 char diff
        if len(parish_norm) == len(key_1851):
            diffs = sum(1 for a, b in zip(parish_norm, key_1851) if a != b)
            if diffs == 1:
                exact_with_typo.append({
                    'ukbmd': parish,
                    '1851': orig_1851,
                    'ukbmd_norm': parish_norm,
                    '1851_norm': key_1851,
                    'diff_chars': [(i, a, b) for i, (a, b) in enumerate(zip(parish_norm, key_1851)) if a != b]
                })
                break

if exact_with_typo:
    print(f"\nFound {len(exact_with_typo)} cases with 1 character difference:")
    for item in exact_with_typo[:15]:
        pos, char_uk, char_1851 = item['diff_chars'][0]
        print(f"  '{item['ukbmd']}' → '{item['1851']}'")
        print(f"    Position {pos}: '{char_uk}' vs '{char_1851}'")

# Analyze character substitution patterns
print("\n[2] Character substitution patterns in 1-char differences:")
print("-" * 80)
char_subs = defaultdict(int)
for item in exact_with_typo:
    pos, char_uk, char_1851 = item['diff_chars'][0]
    char_subs[(char_uk, char_1851)] += 1

print("Most common character substitutions:")
for (c1, c2), count in sorted(char_subs.items(), key=lambda x: -x[1])[:20]:
    print(f"  '{c1}' ↔ '{c2}': {count} times")

# Look for "St." vs "Saint" issues
print("\n[3] Saint/St variations:")
print("-" * 80)
saint_cases = []
for idx, row in unmatched.iterrows():
    parish = str(row['parish']).lower()
    if 'saint' in parish or parish.startswith('st ') or ' st ' in parish:
        saint_cases.append(row['parish'])

print(f"Found {len(saint_cases)} parishes with Saint/St")
print("Sample:", ', '.join(saint_cases[:15]))

# Generic/ambiguous names
print("\n[4] Very generic names (likely ambiguous):")
print("-" * 80)
generic_patterns = []
for idx, row in unmatched.iterrows():
    parish = str(row['parish']).lower().strip()
    # Check if it's just a generic descriptor
    if parish in ['birmingham', 'manchester', 'liverpool', 'london']:
        generic_patterns.append(row['parish'])
    elif parish.startswith('st ') and len(parish.split()) <= 3:
        generic_patterns.append(row['parish'])

print(f"Found {len(generic_patterns)} generic/ambiguous names")
print("Examples:", ', '.join(list(set(generic_patterns))[:20]))

# Check for partial name matches
print("\n[5] Potential partial matches (UKBMD is substring of 1851):")
print("-" * 80)
substring_matches = []
for idx, row in unmatched.head(50).iterrows():
    parish = str(row['parish'])
    parish_norm = parish.lower().strip().replace(' ', '')

    if len(parish_norm) < 5:  # Skip very short
        continue

    for key_1851, orig_1851 in par_lookup.items():
        # Is UKBMD parish a substring of 1851?
        if parish_norm in key_1851 and len(key_1851) > len(parish_norm):
            substring_matches.append({
                'ukbmd': parish,
                '1851': orig_1851,
                'ukbmd_len': len(parish_norm),
                '1851_len': len(key_1851)
            })
            break

if substring_matches:
    print(f"Found {len(substring_matches)} potential substring matches:")
    for item in substring_matches[:15]:
        print(f"  '{item['ukbmd']}' ⊂ '{item['1851']}'")

# Look for number suffixes
print("\n[6] Parishes with numbers (might be divisions):")
print("-" * 80)
number_cases = [row['parish'] for _, row in unmatched.iterrows() if any(c.isdigit() for c in str(row['parish']))]
print(f"Found {len(number_cases)} with numbers")
print("Examples:", ', '.join(number_cases[:20]))

# Check for obvious candidates
print("\n[7] Manual spot-check (UKBMD → likely 1851 candidates):")
print("-" * 80)
spot_check = [
    'Dihewid', 'Ceulanymaesmawr', 'Clarach', 'Sutton Courtenay',
    'Sambourne', 'Draycott Moor', 'Binsted', 'Melchet Park'
]

for ukbmd_name in spot_check:
    if ukbmd_name not in unmatched['parish'].values:
        continue

    ukbmd_norm = ukbmd_name.lower().strip().replace(' ', '')
    # Find closest 1851 matches
    candidates = []
    for key_1851, orig_1851 in par_lookup.items():
        if key_1851.startswith(ukbmd_norm[:4]):
            # Calculate rough distance
            if len(key_1851) == len(ukbmd_norm):
                dist = sum(1 for a, b in zip(ukbmd_norm, key_1851) if a != b)
                candidates.append((orig_1851, dist))

    candidates.sort(key=lambda x: x[1])
    if candidates:
        print(f"\n'{ukbmd_name}':")
        for cand, dist in candidates[:3]:
            print(f"  → {cand} (distance: {dist})")

print("\n" + "=" * 80)
print("SUMMARY OF POTENTIAL IMPROVEMENTS")
print("=" * 80)
print(f"1. One-char differences (manual review): {len(exact_with_typo)} cases")
print(f"2. Saint/St ambiguous names: {len(saint_cases)} cases (likely can't fix)")
print(f"3. Generic names: {len(generic_patterns)} cases (too ambiguous)")
print(f"4. Substring matches: {len(substring_matches)} cases (need verification)")
print("\nRecommendation: The remaining unmatched are mostly:")
print("  - Genuinely ambiguous (St. John, St. Thomas)")
print("  - Missing from 1851 (post-1851 creations)")
print("  - Require manual expert verification")
print("=" * 80)
