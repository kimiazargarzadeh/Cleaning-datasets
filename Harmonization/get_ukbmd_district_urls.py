import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin

url = "https://www.freebmd.org.uk/district-list.html"
BASE = "https://www.ukbmd.org.uk/"

headers = {"User-Agent": "Mozilla/5.0"}

html = requests.get(url, headers=headers, timeout=30).text
soup = BeautifulSoup(html, "html.parser")

districts = []
for a in soup.find_all("a", href=True):
    href = a["href"].strip()
    if "reg/districts/" in href and href.endswith(".html"):
        name = a.get_text(strip=True)
        full_url = urljoin(BASE, href)   # ✅ robust
        districts.append({"district": name, "url": full_url})

df = pd.DataFrame(districts).drop_duplicates()
print("Districts found:", len(df))
print(df.head())

df.to_csv("Harmonization/ukbmd_district_urls.csv", index=False)
