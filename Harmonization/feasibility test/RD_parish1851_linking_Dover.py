import pandas as pd
import re

df = pd.read_csv("Harmonization/1851EngWalesParishandPlace.csv")

def clean_name(s):
    s = str(s).lower().strip()
    s = re.sub(r"[^\w\s,]", "", s)     # keep comma for splitting
    s = re.sub(r"\s+", " ", s)

    # normalize saint/st consistently
    s = s.replace(" st ", " saint ")
    if s.startswith("st "):
        s = s.replace("st ", "saint ", 1)

    return s.strip()

# 1) clean full PLA
df["parish_clean_full"] = df["PLA"].map(clean_name)

# 2) clean "tail" part after comma: e.g. "dover, saint james..." -> "saint james..."
df["parish_clean_tail"] = df["parish_clean_full"].str.split(",", n=1).str[-1].str.strip()

# build a set of all acceptable keys in parish data
parish_keys = set(df["parish_clean_full"]).union(set(df["parish_clean_tail"]))

ukbmd_parishes_1851 = [
    "Alkham","Buckland","Capel-le-Ferne","Charlton","Coldred","Denton",
    "Dover Castle","East Cliffe","East Langdon","Guston","Hougham","Lydden",
    "Oxney","Poulton","Sibertswold","St. James the Apostle",
    "St. Margaret's at Cliffe","St. Mary the Virgin","Temple Ewell",
    "West Cliffe","West Langdon","Whitfield","Wootton"
]

uk = pd.Series(ukbmd_parishes_1851)
uk_clean = uk.map(clean_name).str.replace(",", "", regex=False).str.strip()  # UKBMD no comma needed

matched = uk_clean.isin(parish_keys)

result = pd.DataFrame({
    "ukbmd_parish": ukbmd_parishes_1851,
    "matched_in_1851": matched
})

print(result)
print("Match rate:", matched.mean())
print("Unmatched:", result.loc[~matched, "ukbmd_parish"].tolist())
