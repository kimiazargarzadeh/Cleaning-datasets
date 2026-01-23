import pandas as pd

# Load the UPDATED data (after filling missing Town & Post Code)
df = pd.read_excel('hospitalrecords_updated.xlsx')

print("=== DUPLICATE ANALYSIS ===\n")
print(f"Total records: {len(df)}\n")

# =============================================================================
# STEP 1: COUNT DUPLICATES BY DIFFERENT CRITERIA
# =============================================================================

criteria = {
    'Exact duplicates (all columns)': df.duplicated().sum(),
    'Same HOSPITAL name only': df.duplicated(subset=['HOSPITAL']).sum(),
    'Same HOSPITAL + Town': df.duplicated(subset=['HOSPITAL', 'Town']).sum(),
    'Same HOSPITAL + Foundation Date': df.duplicated(subset=['HOSPITAL', 'Foundation Date']).sum(),
    'Same HOSPITAL + Town + Foundation Date': df.duplicated(subset=['HOSPITAL', 'Town', 'Foundation Date']).sum(),
    'Same HOSPITAL + Town + Post Code': df.duplicated(subset=['HOSPITAL', 'Town', 'Post Code']).sum(),
}

print("Duplicate counts by criteria:")
for name, count in criteria.items():
    print(f"  {name}: {count}")

# =============================================================================
# STEP 2: SHOW EXAMPLES OF DUPLICATES
# =============================================================================

print("\n=== EXAMPLE DUPLICATES (by HOSPITAL + Town + Foundation Date) ===\n")
dupe_cols = ['HOSPITAL', 'Town', 'Foundation Date']
dupes = df[df.duplicated(subset=dupe_cols, keep=False)].sort_values(dupe_cols)

if len(dupes) > 0:
    print(dupes[['HOSPITAL', 'Town', 'Post Code', 'Foundation Date', 'Closure Date']].head(30).to_string())
    dupes.to_excel('duplicate_hospitals_review.xlsx', index=False)
    print(f"\nFull duplicate list saved to 'duplicate_hospitals_review.xlsx' for review")
else:
    print("No duplicates found with this criteria!")

# =============================================================================
# STEP 3: CLEANING STRATEGY
# =============================================================================

print("\n=== CLEANING OPTIONS ===")
print("""
Choose your deduplication strategy:
  A) Keep FIRST occurrence (default pandas behavior)
  B) Keep row with MOST COMPLETE DATA (fewer NaN values)
  C) Keep LAST occurrence
  
Recommended: Option B - keeps the most informative record
""")

# --- OPTION A: Keep first ---
def clean_keep_first(data, subset_cols):
    return data.drop_duplicates(subset=subset_cols, keep='first')

# --- OPTION B: Keep most complete row (RECOMMENDED) ---
def clean_keep_most_complete(data, subset_cols):
    # Count non-null values per row
    data = data.copy()
    data['_completeness'] = data.notna().sum(axis=1)
    # Sort by subset cols + completeness (descending), then drop dupes keeping first
    data = data.sort_values(subset_cols + ['_completeness'], ascending=[True]*len(subset_cols) + [False])
    data = data.drop_duplicates(subset=subset_cols, keep='first')
    data = data.drop(columns=['_completeness'])
    return data

# --- OPTION C: Keep last ---
def clean_keep_last(data, subset_cols):
    return data.drop_duplicates(subset=subset_cols, keep='last')

# =============================================================================
# STEP 4: APPLY CLEANING (using Option B)
# =============================================================================

# Define what makes a duplicate - adjust this based on your needs!
DUPLICATE_CRITERIA = ['HOSPITAL', 'Town', 'Foundation Date']

print(f"\nCleaning using criteria: {DUPLICATE_CRITERIA}")
print(f"Strategy: Keep row with most complete data")
print(f"Safeguard: Only dedupe if Town AND Foundation Date are both filled\n")

# Split data: rows WITH complete criteria vs rows MISSING Town or Foundation Date
has_complete_criteria = df['Town'].notna() & df['Foundation Date'].notna()

df_complete = df[has_complete_criteria].copy()      # Can be deduped safely
df_incomplete = df[~has_complete_criteria].copy()   # Keep as-is (don't risk merging different hospitals)

print(f"Rows with Town + Foundation Date filled: {len(df_complete)}")
print(f"Rows missing Town or Foundation Date: {len(df_incomplete)} (kept as-is)\n")

# Only dedupe the complete rows
df_complete_cleaned = clean_keep_most_complete(df_complete, DUPLICATE_CRITERIA)

# Combine back together
df_cleaned = pd.concat([df_complete_cleaned, df_incomplete], ignore_index=True)

print(f"Before cleaning: {len(df)} rows")
print(f"After cleaning:  {len(df_cleaned)} rows")
print(f"Removed:         {len(df) - len(df_cleaned)} duplicates")

# =============================================================================
# STEP 5: SAVE CLEANED DATA
# =============================================================================

df_cleaned.to_excel('hospital_records_cleaned.xlsx', index=False)
print(f"\nCleaned data saved to 'hospital_records_cleaned.xlsx'")

# Quick verification
print("\n=== VERIFICATION ===")
remaining_dupes = df_cleaned.duplicated(subset=DUPLICATE_CRITERIA).sum()
print(f"Remaining duplicates after cleaning: {remaining_dupes}")