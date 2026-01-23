import pandas as pd

# Load your data
df = pd.read_excel('hospital-records.xlsx', sheet_name='Hospital - Union Catalogue')

print("=== COUNTING DUPLICATE HOSPITAL RECORDS ===\n")

# Count exact duplicates based on different combinations
print("1. EXACT NAME + FOUNDATION DATE + TOWN:")
duplicates_name_date_town = df.groupby(['HOSPITAL', 'Foundation Date', 'Town']).size().reset_index(name='Count')
duplicates_name_date_town = duplicates_name_date_town[duplicates_name_date_town['Count'] > 1].sort_values('Count', ascending=False)
print(f"Found {len(duplicates_name_date_town)} groups with duplicates")
if len(duplicates_name_date_town) > 0:
    print(duplicates_name_date_town.to_string(index=False))
    print()

print("\n2. EXACT NAME + FOUNDATION DATE + POSTCODE:")
duplicates_name_date_postcode = df.groupby(['HOSPITAL', 'Foundation Date', 'Post Code']).size().reset_index(name='Count')
duplicates_name_date_postcode = duplicates_name_date_postcode[duplicates_name_date_postcode['Count'] > 1].sort_values('Count', ascending=False)
print(f"Found {len(duplicates_name_date_postcode)} groups with duplicates")
if len(duplicates_name_date_postcode) > 0:
    print(duplicates_name_date_postcode.to_string(index=False))
    print()

print("\n3. EXACT NAME + FOUNDATION DATE + TOWN + POSTCODE:")
duplicates_all = df.groupby(['HOSPITAL', 'Foundation Date', 'Town', 'Post Code']).size().reset_index(name='Count')
duplicates_all = duplicates_all[duplicates_all['Count'] > 1].sort_values('Count', ascending=False)
print(f"Found {len(duplicates_all)} groups with duplicates")
if len(duplicates_all) > 0:
    print(duplicates_all.to_string(index=False))
    print()

print("\n4. EXACT NAME + FOUNDATION DATE (regardless of location):")
duplicates_name_date = df.groupby(['HOSPITAL', 'Foundation Date']).size().reset_index(name='Count')
duplicates_name_date = duplicates_name_date[duplicates_name_date['Count'] > 1].sort_values('Count', ascending=False)
print(f"Found {len(duplicates_name_date)} groups with duplicates")
if len(duplicates_name_date) > 0:
    print(duplicates_name_date.head(20).to_string(index=False))
    print()

# Summary
print("\n=== SUMMARY ===")
print(f"Total records: {len(df)}")
print(f"Records with same Name+Date+Town: {duplicates_name_date_town['Count'].sum() if len(duplicates_name_date_town) > 0 else 0}")
print(f"Records with same Name+Date+Postcode: {duplicates_name_date_postcode['Count'].sum() if len(duplicates_name_date_postcode) > 0 else 0}")
print(f"Records with same Name+Date+Town+Postcode: {duplicates_all['Count'].sum() if len(duplicates_all) > 0 else 0}")
print(f"Records with same Name+Date (any location): {duplicates_name_date['Count'].sum() if len(duplicates_name_date) > 0 else 0}")

# Save detailed duplicates to Excel for review
if len(duplicates_name_date) > 0:
    # Get full details of records with same name and foundation date
    duplicate_hospitals = duplicates_name_date[duplicates_name_date['Count'] > 1]['HOSPITAL'].tolist()
    duplicate_dates = duplicates_name_date[duplicates_name_date['Count'] > 1]['Foundation Date'].tolist()
    
    detailed_duplicates = df[df.apply(lambda x: (x['HOSPITAL'], x['Foundation Date']) in zip(duplicate_hospitals, duplicate_dates), axis=1)]
    detailed_duplicates = detailed_duplicates.sort_values(['HOSPITAL', 'Foundation Date', 'Town'])
    
    detailed_duplicates.to_excel('duplicate_hospitals_detailed.xlsx', index=False)
    print(f"\nDetailed duplicate records saved to 'duplicate_hospitals_detailed.xlsx'")