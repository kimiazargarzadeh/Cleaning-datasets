import os
import time
import random
import requests
import pandas as pd
from bs4 import BeautifulSoup

# ------------------ config ------------------
URLS_PATH = "Harmonization/ukbmd_district_urls.csv"

RAW_DIR = "Harmonization/data_raw/ukbmd_table1_raw"

# NEW: store all-years per-district files (optional but useful)
ALLYEARS_DIR = "Harmonization/data_intermediate/ukbmd_all_years_by_district"

# keep your 1851 subset directory if you still want it
ELIG_DIR = "Harmonization/data_intermediate/ukbmd_1851_eligible"

# NEW: master outputs
MASTER_ALL_OUT = "Harmonization/data_intermediate/ukbmd_all_districts_all_years.csv"
MASTER_1851_OUT = "Harmonization/data_intermediate/ukbmd_1851_all_districts.csv"

LOG_OUT = "Harmonization/data_intermediate/scrape_log.csv"

REF_YEAR = 1851

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari"
}

# ------------------ utils ------------------
def ensure_dirs():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(ALLYEARS_DIR, exist_ok=True)
    os.makedirs(ELIG_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(MASTER_ALL_OUT), exist_ok=True)

def safe_filename(name: str) -> str:
    keep = []
    for ch in str(name):
        if ch.isalnum() or ch in ("-", "_"):
            keep.append(ch)
        elif ch.isspace():
            keep.append("_")
    fn = "".join(keep).strip("_")
    return fn or "unknown"

def parse_year(x):
    x = str(x).strip()
    return int(x) if x.isdigit() else None

def scrape_table1(url: str, district: str) -> pd.DataFrame:
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    tables = soup.find_all("table")
    target = None
    for t in tables:
        txt = t.get_text(" ", strip=True).lower()
        if "civil parish" in txt and "county" in txt and "from" in txt and "to" in txt:
            target = t
            break

    if target is None:
        return pd.DataFrame(columns=["parish", "county", "from_year", "to_year", "comments", "district", "source_url"])

    rows = []
    for tr in target.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        vals = [c.get_text(" ", strip=True) for c in cells]
        if len(vals) == 5:
            if vals[0].strip().lower().startswith("civil parish"):
                continue
            rows.append(vals)

    df = pd.DataFrame(rows, columns=["parish", "county", "from_year", "to_year", "comments"])
    df["district"] = district
    df["source_url"] = url
    return df

# ------------------ main ------------------
def main():
    ensure_dirs()

    urls = pd.read_csv(URLS_PATH)
    if len(urls) == 0:
        raise ValueError(f"No districts found in {URLS_PATH}")

    all_years_rows = []
    all_1851_rows = []
    logs = []

    for i, r in urls.iterrows():
        district = r["district"]
        url = r["url"]
        fn = safe_filename(district)

        raw_path = os.path.join(RAW_DIR, f"{fn}.csv")
        all_years_path = os.path.join(ALLYEARS_DIR, f"{fn}_all_years.csv")
        elig_path = os.path.join(ELIG_DIR, f"{fn}_1851.csv")

        # idempotent: if we've already saved the all-years file, skip scraping
        if os.path.exists(all_years_path):
            logs.append({"district": district, "url": url, "status": "skipped_exists", "rows_raw": None, "rows_all_years": None, "rows_1851": None})
            continue

        try:
            df = scrape_table1(url, district)

            # save raw scrape (as-is)
            df.to_csv(raw_path, index=False)

            # parse years
            df["from_year"] = df["from_year"].map(parse_year)
            df["to_year"] = df["to_year"].map(parse_year)

            # save all-years per district (cleaned years)
            df.to_csv(all_years_path, index=False)
            all_years_rows.append(df)

            # 1851 eligibility filter (optional subset)
            df_1851 = df[
                (df["from_year"].notna()) &
                (df["from_year"] <= REF_YEAR) &
                ((df["to_year"].isna()) | (df["to_year"] >= REF_YEAR))
            ].copy()

            df_1851.to_csv(elig_path, index=False)
            all_1851_rows.append(df_1851)

            logs.append({
                "district": district,
                "url": url,
                "status": "ok",
                "rows_raw": len(df),
                "rows_all_years": len(df),
                "rows_1851": len(df_1851)
            })

        except Exception as e:
            logs.append({
                "district": district,
                "url": url,
                "status": f"error: {type(e).__name__}: {e}",
                "rows_raw": None,
                "rows_all_years": None,
                "rows_1851": None
            })

        # be polite to the site
        time.sleep(0.5 + random.random() * 0.75)

        # periodic checkpoint save
        if (i + 1) % 50 == 0:
            pd.DataFrame(logs).to_csv(LOG_OUT, index=False)

    # write logs
    pd.DataFrame(logs).to_csv(LOG_OUT, index=False)

    # combine all-years
    if len(all_years_rows) > 0:
        master_all = pd.concat(all_years_rows, ignore_index=True)
    else:
        master_all = pd.DataFrame(columns=["parish", "county", "from_year", "to_year", "comments", "district", "source_url"])

    master_all.to_csv(MASTER_ALL_OUT, index=False)

    # combine 1851 subset (optional)
    if len(all_1851_rows) > 0:
        master_1851 = pd.concat(all_1851_rows, ignore_index=True)
    else:
        master_1851 = pd.DataFrame(columns=["parish", "county", "from_year", "to_year", "comments", "district", "source_url"])

    master_1851.to_csv(MASTER_1851_OUT, index=False)

    print("Done.")
    print("All-years rows total:", len(master_all))
    print("Saved all-years master to:", MASTER_ALL_OUT)
    print("1851-eligible rows total:", len(master_1851))
    print("Saved 1851 master to:", MASTER_1851_OUT)
    print("Saved log to:", LOG_OUT)

if __name__ == "__main__":
    main()
