import requests
from bs4 import BeautifulSoup
import pandas as pd

url = "https://www.ukbmd.org.uk/reg/districts/dover.html"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

resp = requests.get(url, headers=headers, timeout=30)
print("Status:", resp.status_code)
print("Final URL:", resp.url)
print("First 300 chars:\n", resp.text[:300])

soup = BeautifulSoup(resp.text, "html.parser")
tables = soup.find_all("table")
print("Tables found:", len(tables))

# also print the page title (helps identify if you got redirected)
title = soup.find("title")
print("Title:", title.get_text(strip=True) if title else None)

# Try each table and pick the one that contains the expected header
target = None
for t in tables:
    text = t.get_text(" ", strip=True).lower()
    if "civil parish" in text and "county" in text and "from" in text and "to" in text:
        target = t
        break

if target is None:
    raise ValueError("Could not find Table 1 (civil parish list).")

rows = []
for tr in target.find_all("tr"):
    cells = tr.find_all(["td", "th"])  # <-- important fix
    vals = [c.get_text(" ", strip=True) for c in cells]
    if len(vals) == 5 and vals[0].lower() != "civil parish":
        rows.append(vals)

df = pd.DataFrame(rows, columns=["parish", "county", "from_year", "to_year", "comments"])
df["district"] = "Dover"
df["source_url"] = url

print(df.head())
print("Rows:", len(df))

# 1) Drop the captured header row (where parish starts with "Civil Parish")
df = df[~df["parish"].str.contains("Civil Parish", case=False, na=False)].copy()

# 2) Parse years safely
def parse_year(x):
    x = str(x).strip()
    return int(x) if x.isdigit() else None

df["from_year"] = df["from_year"].map(parse_year)
df["to_year"] = df["to_year"].map(parse_year)

# 3) Filter to parishes that exist in 1851: From <= 1851 <= To (or To is missing)
df_1851 = df[(df["from_year"].notna()) & (df["from_year"] <= 1851) & ((df["to_year"].isna()) | (df["to_year"] >= 1851))].copy()

print("\nCleaned rows (all Table 1 parishes):", len(df))
print("Eligible rows for 1851:", len(df_1851))
print(df_1851[["parish", "county", "from_year", "to_year"]].head(15))

# Save both
df.to_csv("ukbmd_table1_dover_all.csv", index=False)
df_1851.to_csv("ukbmd_table1_dover_1851_eligible.csv", index=False)


