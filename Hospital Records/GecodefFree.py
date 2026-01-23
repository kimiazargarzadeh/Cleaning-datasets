import pandas as pd
import requests
import time
from typing import Optional, Tuple

# =============================================================================
# STEP 1: FILL MISSING TOWN & POST CODE
# =============================================================================

# Load the CLEANED data (already filled + deduplicated)
df = pd.read_excel('hospital_records_cleaned.xlsx')

print("=== DATA SUMMARY ===")
print(f"Total rows: {len(df)}")
print(f"Missing Towns: {df['Town'].isna().sum()}")
print(f"Missing Post Codes: {df['Post Code'].isna().sum()}")

# =============================================================================
# STEP 2: GEOCODING FUNCTIONS
# =============================================================================

def geocode_postcode(postcode) -> Optional[Tuple[float, float]]:
    """Geocode UK postcode using Postcodes.io (free, no rate limit)"""
    if pd.isna(postcode):
        return None
    postcode = str(postcode).strip()
    if postcode == "" or postcode.lower() == "nan":
        return None
    try:
        url = f"https://api.postcodes.io/postcodes/{postcode}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200 and resp.json()['status'] == 200:
            data = resp.json()['result']
            return (data['latitude'], data['longitude'])
    except Exception as e:
        pass  # Silent fail, will try town next
    return None

def geocode_town(town) -> Optional[Tuple[float, float]]:
    """Geocode town using Nominatim (rate-limited to 1 req/sec)"""
    if pd.isna(town):
        return None
    town = str(town).strip()
    if town == "" or town.lower() == "nan":
        return None
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {'q': f"{town}, United Kingdom", 'format': 'json', 'limit': 1}
        headers = {'User-Agent': 'HospitalGeocoder/1.0'}
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        if resp.status_code == 200 and len(resp.json()) > 0:
            data = resp.json()[0]
            return (float(data['lat']), float(data['lon']))
    except Exception as e:
        pass
    finally:
        time.sleep(1)  # Nominatim rate limit
    return None

def geocode_hospital(row):
    """Try postcode first, fallback to town"""
    coords = geocode_postcode(row.get('Post Code'))
    if coords:
        return {'latitude': coords[0], 'longitude': coords[1], 'geocode_source': 'postcode'}
    
    coords = geocode_town(row.get('Town'))
    if coords:
        return {'latitude': coords[0], 'longitude': coords[1], 'geocode_source': 'town'}
    
    return {'latitude': None, 'longitude': None, 'geocode_source': 'failed'}

# =============================================================================
# STEP 3: GEOCODE ALL DATA (with progress saves)
# =============================================================================

print("\n=== GEOCODING FULL DATASET ===")
print(f"Total rows: {len(df)}")
print("This may take a while... saving progress every 100 rows.\n")

# Initialize columns
df['latitude'] = None
df['longitude'] = None
df['geocode_source'] = None

start_time = time.time()
success_count = 0
failed_list = []

for idx, row in df.iterrows():
    result = geocode_hospital(row)
    
    df.loc[idx, 'latitude'] = result['latitude']
    df.loc[idx, 'longitude'] = result['longitude']
    df.loc[idx, 'geocode_source'] = result['geocode_source']
    
    if result['geocode_source'] != 'failed':
        success_count += 1
    else:
        failed_list.append({'idx': idx, 'hospital': row['HOSPITAL'], 'town': row['Town'], 'postcode': row['Post Code']})
    
    # Progress update every 50 rows
    if (idx + 1) % 50 == 0:
        elapsed = time.time() - start_time
        rate = (idx + 1) / elapsed
        remaining = (len(df) - idx - 1) / rate
        print(f"Progress: {idx + 1}/{len(df)} | Success: {success_count} | "
              f"Elapsed: {elapsed/60:.1f}min | Remaining: {remaining/60:.1f}min")
    
    # Auto-save every 100 rows
    if (idx + 1) % 100 == 0:
        df.to_excel('hospital_records_geocoded_PARTIAL.xlsx', index=False)

# =============================================================================
# FINAL SAVE & SUMMARY
# =============================================================================

df.to_excel('hospital_records_geocoded.xlsx', index=False)

# Save failed rows for review
if failed_list:
    failed_df = pd.DataFrame(failed_list)
    failed_df.to_excel('geocoding_failures.xlsx', index=False)

print("\n=== FINAL SUMMARY ===")
print(f"Total rows: {len(df)}")
print(f"Geocoded successfully: {success_count} ({100*success_count/len(df):.1f}%)")
print(f"Failed: {len(failed_list)}")
print(f"\nBy source:")
print(df['geocode_source'].value_counts())
print(f"\nSaved to: 'hospital_records_geocoded.xlsx'")
if failed_list:
    print(f"Failed rows saved to: 'geocoding_failures.xlsx'")