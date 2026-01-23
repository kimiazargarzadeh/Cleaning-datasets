import pandas as pd

# Load both files (original from Sheet 2)
original = pd.read_excel('hospital-records.xlsx', sheet_name='Hospital - Union Catalogue')
filled = pd.read_excel('hospitals_missing_town_filled.xlsx')

# --- CHECK MISSING BEFORE ---
print("=== BEFORE FILLING ===")
print(f"Missing Towns: {original['Town'].isna().sum()} / {len(original)}")
print(f"Missing Post Codes: {original['Post Code'].isna().sum()} / {len(original)}")
print()

# --- CORRECT COLUMN NAMES (based on your output) ---
HOSPITAL_COL = 'HOSPITAL'       # same in both files
TOWN_COL = 'Town'
POSTCODE_COL = 'Post Code'
EXCEL_ROW_COL = 'excel_row'

# Track what we fill
filled_by_row = {'town': 0, 'postcode': 0}
filled_by_name = {'town': 0, 'postcode': 0}

# --- METHOD 1: Match by Excel row index (most reliable) ---
print("Using Excel row matching...")
for _, row in filled.iterrows():
    # Excel row to pandas index (subtract 2: 1 for header, 1 for 0-indexing)
    idx = int(row[EXCEL_ROW_COL]) - 2
    
    if 0 <= idx < len(original):
        if pd.isna(original.loc[idx, TOWN_COL]) and pd.notna(row[TOWN_COL]):
            original.loc[idx, TOWN_COL] = row[TOWN_COL]
            filled_by_row['town'] += 1
        if pd.isna(original.loc[idx, POSTCODE_COL]) and pd.notna(row[POSTCODE_COL]):
            original.loc[idx, POSTCODE_COL] = row[POSTCODE_COL]
            filled_by_row['postcode'] += 1

print(f"Filled via row index - Towns: {filled_by_row['town']}, Post Codes: {filled_by_row['postcode']}")

# --- METHOD 2: Fill remaining gaps by hospital name matching ---
print("Checking for remaining gaps via hospital name matching...")

# Create lookups from filled file (only rows with actual values)
town_lookup = filled.dropna(subset=[TOWN_COL]).set_index(HOSPITAL_COL)[TOWN_COL].to_dict()
postcode_lookup = filled.dropna(subset=[POSTCODE_COL]).set_index(HOSPITAL_COL)[POSTCODE_COL].to_dict()

for idx, row in original.iterrows():
    hospital = row[HOSPITAL_COL]
    
    if pd.isna(row[TOWN_COL]) and hospital in town_lookup:
        original.loc[idx, TOWN_COL] = town_lookup[hospital]
        filled_by_name['town'] += 1
    
    if pd.isna(row[POSTCODE_COL]) and hospital in postcode_lookup:
        original.loc[idx, POSTCODE_COL] = postcode_lookup[hospital]
        filled_by_name['postcode'] += 1

print(f"Filled via name match - Towns: {filled_by_name['town']}, Post Codes: {filled_by_name['postcode']}")

# --- FINAL SUMMARY ---
print("\n=== FINAL SUMMARY ===")
print(f"Total filled - Towns: {filled_by_row['town'] + filled_by_name['town']}")
print(f"Total filled - Post Codes: {filled_by_row['postcode'] + filled_by_name['postcode']}")
print(f"Still missing - Towns: {original[TOWN_COL].isna().sum()}")
print(f"Still missing - Post Codes: {original[POSTCODE_COL].isna().sum()}")

# Save updated file
original.to_excel('hospitalrecords_updated.xlsx', index=False)
print("\nSaved to 'hospitalrecords_updated.xlsx'")