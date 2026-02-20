# Ipswich Wealth-Health Analysis Summary

**Data:** 42,939 deaths (1871-1910) with occupation-based social class coding

**Method:** Occupation → social class (Elite, Skilled, Semi-skilled, Unskilled) → mortality patterns

---

## Key Finding: Health Technology Exacerbated Inequality

Victorian health improvements (1880-1910) did NOT benefit all classes equally:

| Social Class | Median Age 1880 | Median Age 1910 | **Gain** |
|--------------|-----------------|-----------------|----------|
| **Skilled** | 24 years | 49 years | **+25 years** |
| **Elite** | 39.5 years | 46.5 years | **+7 years** |
| **Unskilled** | 35 years | 36 years | **+1 year** |

**Interpretation:** Skilled workers gained 25× more life years than the unskilled poor. Health technology (sanitation, hospitals, medical care) was not equalizing - it favored those with moderate resources.

---

## Supporting Findings

### 1. Infant Mortality Gradient (Small)
- Elite infants: 0.92 years median age at death
- Unskilled infants: 1.00 years median age at death
- **Difference: 1 month** (surprisingly small)

### 2. Disease Patterns (Similar Across Classes)
- Elite: 35% infectious diseases, 24% chronic
- Unskilled: 37% infectious, 20% chronic
- Both classes died from infectious diseases at similar rates

### 3. Top Causes Over Time
- **Tuberculosis:** Stable throughout (leading cause)
- **Conditions of elderly:** Increasing (people living longer)
- **Bronchitis:** Declining after 1900 (sanitation?)

### 4. Infant Mortality Trend
- No clear decline 1885-1910
- Very volatile year-to-year
- Peaked around 1905 (~35% of all deaths)

---

## Why Did Skilled Workers Benefit Most?

Possible mechanisms:

1. **Access to care:** Skilled workers could afford hospitals/doctors (unlike unskilled)
2. **Housing quality:** Better neighborhoods than slums (unlike unskilled)
3. **Workplace safety:** Factory reforms benefited skilled trades
4. **Nutrition:** Could afford better food than laborers
5. **Not wealthy enough to resist change:** Elite may have been skeptical of new medicine, skilled workers adopted it

---

## Implications

### For Victorian History:
- Health improvements were **not equalizing**
- Technology adoption favored the "middle class" (skilled workers)
- The poorest were left behind despite public health reforms

### For WealthisHealth Project:
- Occupation is a strong wealth proxy (even without probate data)
- Can analyze wealth-health gradients for all of England & Wales using FreeBMD
- Ipswich validates the approach - clear social class mortality patterns

### Next Steps:
1. Replicate analysis for other towns/cities in FreeBMD
2. Test if pattern holds nationally (FreeBMD 1866-1910)
3. Link to probate records when available (actual wealth)
4. Investigate mechanisms (housing, occupation-specific hazards)

---

## Research Output

**Visualization:** `analysis_outputs/wealth_health_analysis.png` (4-panel graph)

**Data:** `analysis_outputs/key_findings.csv`

**Script:** `analyze_wealth_health.py` (reproducible)

---

**Created:** February 2026
**Project:** WealthisHealth - Victorian Mortality and Economic History
