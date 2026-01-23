import pandas as pd

# =========================
# CONFIG
# =========================
FILE_PATH = "hospital-records.xlsx"
SHEET_NAME = "Hospital - Union Catalogue"
HEADER_ROW_EXCEL = 1
CUTOFF_YEAR = 1959  # Modern UK postcodes start ~1959

# =========================
# LOAD DATA
# =========================
df = pd.read_excel(FILE_PATH, sheet_name=SHEET_NAME, header=HEADER_ROW_EXCEL - 1)
df['excel_row'] = df.index + HEADER_ROW_EXCEL + 1

# =========================
# CLEAN CLOSURE DATE
# =========================
# Combine exact and approximate closure dates
df['Closure'] = df['Closure Date'].combine_first(df['Closure Date Approximate'])
df['Closure'] = pd.to_numeric(df['Closure'], errors='coerce')
# Treat 0 or negative values as missing
df.loc[df['Closure'] <= 0, 'Closure'] = pd.NA

# =========================
# CLOSED-BEFORE-POSTCODE HOSPITALS
# =========================
closed_before_postcode = df.loc[df['Closure'].notna() & (df['Closure'] < CUTOFF_YEAR)]

# Split into missing vs filled Post Codes
closed_missing_postcode = closed_before_postcode.loc[
    closed_before_postcode['Post Code'].isna() | (closed_before_postcode['Post Code'] == '')
]

closed_with_postcode = closed_before_postcode.loc[
    closed_before_postcode['Post Code'].notna() & (closed_before_postcode['Post Code'] != '')
]

# =========================
# GENERAL MISSING LOCATION (all hospitals)
# =========================
missing_postcode = df['Post Code'].isna() | (df['Post Code'] == '')
missing_town = df['Town'].isna() | (df['Town'] == '')
missing_both = missing_postcode & missing_town

print("===== GENERAL MISSING LOCATION =====")
print("Missing Post Code:", missing_postcode.sum())
print("Missing Town:", missing_town.sum())
print("Missing BOTH Town and Post Code:", missing_both.sum())

# =========================
# EXPORT RESULTS
# =========================
closed_missing_postcode.to_excel("closed_before_postcode_missing.xlsx", index=False)
closed_with_postcode.to_excel("closed_before_postcode_filled.xlsx", index=False)

# Optional: save general missing info with flags
df['missing_postcode'] = missing_postcode
df['missing_town'] = missing_town
df['missing_both'] = missing_both
df.to_excel("all_hospitals_missing_location_flags.xlsx", index=False)

print("\nSaved all files:")
print("- closed_before_postcode_missing.xlsx")
print("- closed_before_postcode_filled.xlsx")
print("- all_hospitals_missing_location_flags.xlsx")


# Filter hospitals closed before 1959 and missing Post Code
closed_missing_postcode = closed_before_postcode.loc[
    closed_before_postcode['Post Code'].isna() | (closed_before_postcode['Post Code'] == '')
]

# Among these, filter those that do NOT have Town
no_town = closed_missing_postcode['Town'].isna() | (closed_missing_postcode['Town'] == '')

# Get Excel row numbers
excel_rows_no_town = closed_missing_postcode.loc[no_town, 'excel_row'].tolist()

print("Excel rows of closed-before-1959 hospitals missing Post Code AND missing Town:")
print(excel_rows_no_town)

# Optional: export to Excel
pd.DataFrame({'excel_row': excel_rows_no_town}).to_excel(
    "closed_missing_postcode_no_town.xlsx", index=False
)

# =========================
# HOSPITALS MISSING TOWN IN GENERAL
# =========================
hospitals_missing_town = df.loc[missing_town, ['excel_row', 'HOSPITAL', 'Town', 'Post Code']]

print("\nSample of hospitals missing Town (general):")
print(hospitals_missing_town.head(10))

# Optional: export full list
hospitals_missing_town.to_excel("hospitals_missing_town.xlsx", index=False)
print("\nSaved: hospitals_missing_town.xlsx")
