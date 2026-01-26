import os
import time
import random
import requests
import pandas as pd
from bs4 import BeautifulSoup

# ------------------ config ------------------
URLS_PATH = "Harmonization/ukbmd_district_urls.csv"

RAW_DIR = "Harmonization/data_raw/ukbmd_table1_raw"
ELIG_DIR = "Harmonization/data_intermediate/ukbmd_1851_eligible"
MASTER_OUT = "Harmonization/data_intermediate/ukbmd_1851_all_districts.csv"
LOG_OUT = "Harmonization/data_intermediate/scrape_log.csv"

REF_YEAR = 1851

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari"
}

# ------------------ utils ------------------
def ensure_dirs():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(ELIG_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(MASTER_OUT), exist_ok=True)

def safe_filename(name: str) -> str:
    # make a filename-safe district identifier
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
        # keep only 5-column rows (parish/county/from/to/comments)
        if len(vals) == 5:
            # drop header row
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

    all_eligible = []
    logs = []

    for i, r in urls.iterrows():
        district = r["district"]
        url = r["url"]
        fn = safe_filename(district)

        raw_path = os.path.join(RAW_DIR, f"{fn}.csv")
        elig_path = os.path.join(ELIG_DIR, f"{fn}_1851.csv")

        # skip if already scraped (idempotent)
        if os.path.exists(elig_path):
            logs.append({"district": district, "url": url, "status": "skipped_exists", "rows_raw": None, "rows_1851": None})
            continue

        try:
            df = scrape_table1(url, district)

            # save raw
            df.to_csv(raw_path, index=False)

            # parse years
            df["from_year"] = df["from_year"].map(parse_year)
            df["to_year"] = df["to_year"].map(parse_year)

            # 1851 eligibility filter
            df_1851 = df[
                (df["from_year"].notna()) &
                (df["from_year"] <= REF_YEAR) &
                ((df["to_year"].isna()) | (df["to_year"] >= REF_YEAR))
            ].copy()

            df_1851.to_csv(elig_path, index=False)
            all_eligible.append(df_1851)

            logs.append({
                "district": district,
                "url": url,
                "status": "ok",
                "rows_raw": len(df),
                "rows_1851": len(df_1851)
            })

        except Exception as e:
            logs.append({
                "district": district,
                "url": url,
                "status": f"error: {type(e).__name__}",
                "rows_raw": None,
                "rows_1851": None
            })

        # be polite to the site
        time.sleep(0.5 + random.random() * 0.75)

        # periodic checkpoint save
        if (i + 1) % 50 == 0:
            pd.DataFrame(logs).to_csv(LOG_OUT, index=False)

    # write logs
    pd.DataFrame(logs).to_csv(LOG_OUT, index=False)

    # combine eligible
    if len(all_eligible) > 0:
        master = pd.concat(all_eligible, ignore_index=True)
    else:
        master = pd.DataFrame(columns=["parish", "county", "from_year", "to_year", "comments", "district", "source_url"])

    master.to_csv(MASTER_OUT, index=False)

    print("Done.")
    print("Eligible rows total:", len(master))
    print("Saved master to:", MASTER_OUT)
    print("Saved log to:", LOG_OUT)

if __name__ == "__main__":
    main()
