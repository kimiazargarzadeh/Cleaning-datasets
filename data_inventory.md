# Data Inventory — WealthisHealth Project

All data lives in: `/Users/kimik/Ellen Dropbox/Kimia Zargarzadeh/WealthisHealth/`



---

## 1. Mortality Data (1851–1910, by Registration District)

**Source:** UK Data Archive, Study 9034
**Location:** `1851-1910 Age- and Cause-Specific Mortality in E&W/tab/`

### `mort_age_ew_reg_dec.tab`
- **Coverage:** 1850–1910, by **decade**
- **Unit:** Registration District × decade × sex
- **Rows:** 3,780 | **Columns:** 52
- **Key columns:**
  - `decade`, `reg_num`, `reg_dist`, `reg_cnty`
  - `births`, `deaths` (totals)
  - Male deaths by age: `m_0`, `m_1`, `m_2_4`, `m_5_9`, `m_10_14`, `m_15_19`, `m_20_24`, `m_25_34`, `m_35_44`, `m_45_54`, `m_55_64`, `m_65_74`, `m_75_up`
  - Female deaths by age: same structure with `f_` prefix
  - `g_unit` — population size / geographic unit code
- **Link to harmonization:** via `reg_num` / `reg_dist`

### `cause_ew_reg_dec.tab`
- **Coverage:** 1850–1910, by **decade**
- **Unit:** Registration District × decade × cause × sex
- **Rows:** 160,246 | **Columns:** 36
- **Key columns:**
  - `decade`, `reg_num`, `reg_dist`, `reg_cnty`
  - `cause`, `short_cause` — specific cause of death
  - `sex` (M/F)
  - `total`, `males`, `females`
  - Deaths by age: `a_0`, `a_1`, `a_2_4`, `a_5_9` ... `a_75_up`
  - `start_date`, `end_date` (e.g. 1851-01-01 to 1860-12-31)
  - `g_unit` — population size / geographic unit code
- **Documentation:** `mrdoc/pdf/cause_ew_reg_dec_doc.pdf`
- **Link to harmonization:** via `reg_num` / `reg_dist`

---

## 2. FreeBMD Deaths (1858–1990, Annual)

**Location:** `freebmd/Deaths/`

### Cleaned individual-level death records
**Path:** `freebmd/Deaths/cleaned/`
- **Coverage:** 1858–1990, **one CSV per year** (133 files)
- **File naming:** `cleaned_freebmd_deaths_{year}.csv`
- **Unit:** Individual death record × Registration District × quarter
- **Status:** Cloud-only, auto-download on access

### Collapsed / aggregated versions
**Path:** `freebmd/Deaths/collapsed/`

| Subfolder | Aggregation level |
|-----------|-------------------|
| `surname-gender-district/` | surname × gender × district, by year (1858–1990) |
| `surname-gender-yod-qod/` | surname × gender × year × quarter of death |
| `surname-year/` | surname × year |
| `surname-gen/` | surname × gender |

### Other
- `freebmd/Deaths/withboundaries/` — deaths with spatial boundary information attached
- `freebmd/Districts/` — district reference files
- `freebmd/shortnames/` — standardized short district names

---

## 3. FreeBMD Births & Marriages

**Location:** `freebmd/Births/`, `freebmd/Marriages/`
- Coverage unknown (cloud-only, not yet inspected)
- Expected format: similar to deaths (annual CSVs by district)

---

## 4. Shapefiles

**Location:** `shapefiles/`

### 1851 Civil Parishes
**Path:** `shapefiles/1851parishes/`
- `1851EngWalesParishandPlace.shp` (+ .dbf, .prj, .shx, .sbn)
- Full shapefile for **all England & Wales civil parishes in 1851**
- This is the **reference geography** for the harmonization pipeline
- Also available as CSV with WKT geometry in the pipeline repo

### Registration Districts (1851–1911)
**Path:** `shapefiles/Registration-Districts-1851-to-1911/xml/`
- Official RD boundary shapefiles for census years:
  - `ukds_ew1851_regdistricts/`
  - `ukds_ew1861_regdistricts/`
  - `ukds_ew1871_regdistricts/`
  - `ukds_ew1881_regdistricts/`
  - `ukds_ew1891_regdistricts/`
  - `ukds_ew1901_regdistricts/`
  - `ukds_ew1911_regdistricts/`
- Used for **spatial validation** of the 1851 backbone reconstruction
- CRS: EPSG:27700 (British National Grid)

### Local/Urban Districts (1911–1971) ⭐ Key for post-1930s coverage
**Path:** `shapefiles/LAD-Districts-1911-to-1971/shp/`
- LGD boundary shapefiles for:
  - `ukds_ew1911_lgdistricts2/`
  - `ukds_ew1921_lgdistricts2/`
  - `ukds_ew1931_lgdistricts2/`
  - `ukds_ew1951_lgdistricts2/`
  - `ukds_ew1961_lgdistricts2/`
  - `ukds_ew1971_lgdistricts2/`
- **Critical for Option B** (RD → LGD crosswalk to extend spatial coverage post-1930s)

### Parliamentary Constituencies (1832–2010)
**Path:** `shapefiles/Parliamentary Constituencies1832-1885/` and `1885-2010/`
- Available for: England, Wales, Scotland, Northern Ireland
- Boundary years: 1832, 1885, 1918, 1922, 1945, 1950, 1955, 1974, 1983, 1997, 2005, 2010
- Also includes joined versions and centroids

---

## 5. UKDA-5413 — Ipswich & MSA Data

**Location:** `UKDA-5413-tab/tab/`
- `births_msa.tab` — births data for Metropolitan Statistical Areas
- `deaths_msa.tab` — deaths data for Metropolitan Statistical Areas
- **Ipswich-specific census & vital records:**
  - `ipswich_1871_census_mse.tab`
  - `ipswich_1871_msa.tab`
  - `ipswich_1881_census_mse.tab` / `ipswich_1881_msa.tab`
  - `ipswich_1891_census_mse.tab` / `ipswich_1891_msa.tab`
  - `ipswich_1901_msa_1.tab` / `ipswich_1901_msa_2.tab`
  - `ipswich_births_1871_1892_mse.tab` / `ipswich_births_1892_1910_mse.tab`
  - `ipswich_deaths_1871_1910_mse.tab`
  - `ipswich_east_1901_census_mse.tab` / `ipswich_west_1901_census_mse.tab`

---

## 6. Municipal Borough Financial Accounts (1872–1910)

**Location:** `Municipal Borough and Urban Sanitary Authority Financial Accounts, 1872-1910/`
- `data/allAccountsMBsOnly_19041910.xlsx` — full accounts 1904–1910
- `data/MBs_undertakings1906-1910.xlsx` — municipal undertakings 1906–1910
- `Variable_definitions.xlsx` — codebook
- **Unit:** Municipal Borough × year
- **Contents:** Local government financial records (expenditure, revenues, public utilities)

---

## 7. Aidt-Davenport Research Data

**Location:** `aidt-davenport/`
- Stata `.dta` files for regression analysis (figures & tables from a related paper)
- **Original data:** `dta/original data/` — LTR (Long-Term Returns) datasets
- **Working data:** `dta/working data/` — cleaned regression-ready files
  - `LTR 10 regression decennial_rd_crude.dta` — decennial RD-level crude mortality regressions
  - `LTR 5 regression.dta`, `loans 5 regression.dta`
- **Output:** `output/figures/`, `output/tables/`
- **Code:** `do/` — Stata do-files

---

## Summary Table

| Dataset | Coverage | Unit | Format | Key Use |
|---------|----------|------|--------|---------|
| `mort_age_ew_reg_dec` | 1851–1910 | RD × decade | .tab | Age-specific mortality analysis |
| `cause_ew_reg_dec` | 1851–1910 | RD × decade × cause | .tab | Cause-specific mortality analysis |
| FreeBMD Deaths (cleaned) | **1858–1990** | Individual × RD × year | .csv | Full death linkage |
| FreeBMD Deaths (collapsed) | 1858–1990 | Surname × RD × year | .csv | Surname-based analysis |
| 1851 Parish shapefile | 1851 | Parish polygon | .shp | Reference geography |
| RD shapefiles | 1851–1911 | RD polygon | .shp | Spatial validation |
| LGD shapefiles | **1911–1971** | LGD polygon | .shp | Post-1930s coverage (Option B) |
| Parliamentary Constituencies | 1832–2010 | Constituency polygon | .shp | Political geography |
| UKDA-5413 (Ipswich/MSA) | 1871–1910 | MSA/individual | .tab | Case study / MSA analysis |
| Municipal Borough accounts | 1872–1910 | Borough × year | .xlsx | Public finance / health spending |
| Aidt-Davenport data | Various | RD × decade | .dta | Related regression analysis |

---

## Notes on Access

- Files marked **cloud-only** live in Dropbox Smart Sync — they auto-download when accessed by a script
- Do **not** bulk-download all FreeBMD files at once (133 files × ~50MB = ~6GB)
- Process year-by-year using `batch_match_deaths_to_coverage.py` which reads one file at a time
- Dropbox path root: `/Users/kimik/Ellen Dropbox/Kimia Zargarzadeh/WealthisHealth/`

---

*Last updated: February 2026*
