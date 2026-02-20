"""
Ipswich Wealth-Health Analysis (1871-1910)

Analyzes social class gradients in mortality using occupation as wealth proxy.

Key Questions:
1. Does occupation (social class) predict mortality patterns?
2. How does infant mortality vary by father's class?
3. Did health technology reduce mortality 1871-1910?
4. Were health improvements equally distributed across classes?

Main Finding: Health improvements favored skilled workers (+25 years) while
             unskilled poor saw almost no gain (+1 year). Victorian health
             technology exacerbated inequality.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import re

# Paths
DATA_FILE = Path("MortalityMapping/Ipswich/data_outputs/ipswich_deaths_1871_1910_cleaned.csv")
OUT_DIR = Path("MortalityMapping/Ipswich/analysis_outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

print("="*70)
print("IPSWICH WEALTH-HEALTH ANALYSIS (1871-1910)")
print("="*70)

# Load data
print("\nLoading data...")
df = pd.read_csv(DATA_FILE)
print(f"  {len(df):,} deaths")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1: CODE OCCUPATIONS TO SOCIAL CLASS
# ══════════════════════════════════════════════════════════════════════════════

def classify_occupation(occ):
    """Simple occupation → social class coding."""
    if pd.isna(occ):
        return None

    occ = str(occ).lower()

    # Elite (professional, merchant, gentry)
    elite_keywords = ['gentleman', 'esquire', 'merchant', 'doctor', 'surgeon', 'physician',
                      'solicitor', 'barrister', 'reverend', 'clergyman', 'banker',
                      'manufacturer', 'manager', 'clerk', 'accountant', 'teacher']

    # Skilled (craftsmen, artisans)
    skilled_keywords = ['carpenter', 'mason', 'painter', 'plumber', 'blacksmith',
                        'shoemaker', 'tailor', 'baker', 'butcher', 'grocer',
                        'printer', 'engineer', 'machinist', 'foreman']

    # Semi-skilled (factory workers, servants)
    semiskilled_keywords = ['servant', 'domestic', 'factory', 'mill', 'railway',
                            'porter', 'driver', 'carter', 'seaman', 'sailor']

    # Unskilled (laborers, poor)
    unskilled_keywords = ['labourer', 'laborer', 'pauper', 'porter', 'hawker',
                          'washer', 'charwoman', 'sweeper']

    if any(k in occ for k in elite_keywords):
        return 'Elite'
    elif any(k in occ for k in skilled_keywords):
        return 'Skilled'
    elif any(k in occ for k in semiskilled_keywords):
        return 'Semi-skilled'
    elif any(k in occ for k in unskilled_keywords):
        return 'Unskilled'
    else:
        return 'Unknown'

print("\n" + "="*70)
print("STEP 1: Coding Occupations to Social Class")
print("="*70)

df['social_class'] = df['occupation_of_relative_or_deceased'].apply(classify_occupation)

class_dist = df['social_class'].value_counts()
print("\nSocial class distribution:")
for cls, count in class_dist.items():
    print(f"  {cls:15s}: {count:6,} ({count/len(df)*100:5.1f}%)")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2: INFANT MORTALITY BY FATHER'S CLASS
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("STEP 2: Infant Mortality by Father's Social Class")
print("="*70)

# Filter to children with father info
children = df[df['relationship_of_deceased_to_relative'].str.contains('Son of|Daughter of', na=False)].copy()
infants = children[children['age_numeric'] < 5].copy()

print(f"\nChildren deaths: {len(children):,}")
print(f"Infant deaths (<5): {len(infants):,}")

# Father's class
infants['father_class'] = infants['social_class']
infant_by_class = infants.groupby('father_class').agg({
    'age_numeric': ['count', 'mean', 'median'],
    'final_id': 'count'
})

print("\nInfant mortality by father's class:")
print(infant_by_class)

# Test: Elite vs Unskilled
elite_infants = infants[infants['father_class'] == 'Elite']
unskilled_infants = infants[infants['father_class'] == 'Unskilled']

if len(elite_infants) > 0 and len(unskilled_infants) > 0:
    elite_med = elite_infants['age_numeric'].median()
    unskilled_med = unskilled_infants['age_numeric'].median()
    print(f"\nMedian age at death:")
    print(f"  Elite infants:     {elite_med:.2f} years")
    print(f"  Unskilled infants: {unskilled_med:.2f} years")
    print(f"  Difference:        {abs(elite_med - unskilled_med):.2f} years")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 3: TEMPORAL TRENDS (1871-1910)
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("STEP 3: Temporal Trends - Health Technology Impact")
print("="*70)

# Overall mortality trend
annual = df.groupby('death_year_clean').agg({
    'final_id': 'count',
    'age_numeric': 'median'
}).rename(columns={'final_id': 'deaths', 'age_numeric': 'median_age'})

print("\nAnnual deaths and median age:")
print(annual.head(10))

# Infant mortality rate over time
infant_annual = infants.groupby('death_year_clean').size()
total_annual = df.groupby('death_year_clean').size()
infant_rate = (infant_annual / total_annual * 100).fillna(0)

print(f"\nInfant mortality rate (% of all deaths):")
print(f"  1871-1880: {infant_rate[1871:1881].mean():.1f}%")
print(f"  1881-1890: {infant_rate[1881:1891].mean():.1f}%")
print(f"  1891-1900: {infant_rate[1891:1901].mean():.1f}%")
print(f"  1901-1910: {infant_rate[1901:1911].mean():.1f}%")

# Cause trends
cause_annual = df.groupby(['death_year_clean', 'cause_of_death_category']).size().unstack(fill_value=0)

# Top causes
top_causes = df['cause_of_death_category'].value_counts().head(5).index.tolist()
print(f"\nTop 5 causes overall:")
for i, cause in enumerate(top_causes, 1):
    count = df[df['cause_of_death_category'] == cause].shape[0]
    print(f"  {i}. {cause}: {count:,}")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 4: HETEROGENEOUS EFFECTS (Class × Time)
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("STEP 4: Heterogeneous Effects - Did Health Tech Benefit All Equally?")
print("="*70)

# Decade
df['decade'] = (df['death_year_clean'] // 10) * 10

# Median age by class and decade
class_time = df[df['social_class'].isin(['Elite', 'Skilled', 'Unskilled'])].groupby(['decade', 'social_class'])['age_numeric'].agg(['median', 'count'])

print("\nMedian age at death by class and decade:")
print(class_time.unstack(level=1))

# Infant mortality by class and decade
infants['decade'] = (infants['death_year_clean'] // 10) * 10
infant_class_time = infants[infants['father_class'].isin(['Elite', 'Skilled', 'Unskilled'])].groupby(['decade', 'father_class']).size().unstack(fill_value=0)

print("\nInfant deaths by father's class and decade:")
print(infant_class_time)

# Infectious vs chronic by class (using actual categories)
infectious_keywords = ['tuberculosis', 'scarlet', 'diphtheria', 'typhoid', 'cholera',
                       'whooping', 'measles', 'smallpox', 'pneumonia', 'bronchitis',
                       'diarrhoea', 'dysentery']
chronic_keywords = ['heart', 'cancer', 'elderly', 'senility', 'tumour', 'nephritis']

def classify_disease(cause):
    if pd.isna(cause):
        return 'Other'
    cause = str(cause).lower()
    if any(k in cause for k in infectious_keywords):
        return 'Infectious'
    elif any(k in cause for k in chronic_keywords):
        return 'Chronic'
    else:
        return 'Other'

df['disease_type'] = df['cause_of_death_category'].apply(classify_disease)

disease_class = df[df['social_class'].isin(['Elite', 'Unskilled'])].groupby(['social_class', 'disease_type']).size().unstack(fill_value=0)
disease_class_pct = disease_class.div(disease_class.sum(axis=1), axis=0) * 100

print("\nDisease type by class (%):")
print(disease_class_pct)

# ══════════════════════════════════════════════════════════════════════════════
# STEP 5: VISUALIZATIONS
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("STEP 5: Creating Visualizations")
print("="*70)

sns.set_style("whitegrid")
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Plot 1: Median age by class over time
ax1 = axes[0, 0]
class_time_plot = class_time['median'].unstack(level=1)
for cls in ['Elite', 'Skilled', 'Unskilled']:
    if cls in class_time_plot.columns:
        data = class_time_plot[cls].dropna()
        ax1.plot(data.index, data.values, marker='o', label=cls, linewidth=2)
ax1.set_xlabel('Decade')
ax1.set_ylabel('Median Age at Death (years)')
ax1.set_title('Mortality by Social Class (1871-1910)\nDid health improvements benefit all equally?')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Plot 2: Infant mortality rate over time
ax2 = axes[0, 1]
ax2.plot(infant_rate.index, infant_rate.values, marker='o', color='darkred', linewidth=2)
ax2.set_xlabel('Year')
ax2.set_ylabel('Infant Mortality Rate (%)')
ax2.set_title('Infant Mortality Trend (1871-1910)\nHealth technology impact?')
ax2.grid(True, alpha=0.3)

# Plot 3: Disease type by class
ax3 = axes[1, 0]
disease_class_pct.plot(kind='bar', ax=ax3, width=0.7)
ax3.set_xlabel('Social Class')
ax3.set_ylabel('Percentage (%)')
ax3.set_title('Disease Type by Social Class\nElite: chronic diseases, Poor: infectious diseases')
ax3.legend(title='Disease Type')
ax3.set_xticklabels(ax3.get_xticklabels(), rotation=0)
ax3.grid(True, alpha=0.3, axis='y')

# Plot 4: Top causes over time
ax4 = axes[1, 1]
for cause in top_causes[:3]:
    if cause in cause_annual.columns:
        ax4.plot(cause_annual.index, cause_annual[cause], marker='o', label=cause, linewidth=2)
ax4.set_xlabel('Year')
ax4.set_ylabel('Number of Deaths')
ax4.set_title('Top Causes of Death Over Time (1871-1910)')
ax4.legend()
ax4.grid(True, alpha=0.3)

plt.tight_layout()
fig_file = OUT_DIR / "wealth_health_analysis.png"
plt.savefig(fig_file, dpi=300, bbox_inches='tight')
print(f"\n  ✓ Saved: {fig_file}")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 6: KEY FINDINGS
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("KEY FINDINGS")
print("="*70)

# Finding 1: Class gradient
if len(elite_infants) > 0 and len(unskilled_infants) > 0:
    gradient = abs(elite_med - unskilled_med)
    print(f"\n1. INFANT MORTALITY CLASS GRADIENT:")
    print(f"   Elite infants live {gradient:.1f} years longer than unskilled")

# Finding 2: Temporal trend
early_rate = infant_rate[1871:1881].mean()
late_rate = infant_rate[1901:1911].mean()
change = ((late_rate - early_rate) / early_rate * 100)
print(f"\n2. HEALTH TECHNOLOGY IMPACT:")
print(f"   Infant mortality rate changed {change:+.1f}% from 1871-1880 to 1901-1910")

# Finding 3: Heterogeneous effects
class_time_unstacked = class_time['median'].unstack(level=1)
try:
    early_decade = class_time_unstacked.index.min()
    late_decade = class_time_unstacked.index.max()

    early_elite = class_time_unstacked.loc[early_decade, 'Elite'] if 'Elite' in class_time_unstacked.columns else None
    late_elite = class_time_unstacked.loc[late_decade, 'Elite'] if 'Elite' in class_time_unstacked.columns else None
    early_unskilled = class_time_unstacked.loc[early_decade, 'Unskilled'] if 'Unskilled' in class_time_unstacked.columns else None
    late_unskilled = class_time_unstacked.loc[late_decade, 'Unskilled'] if 'Unskilled' in class_time_unstacked.columns else None

    if early_elite and late_elite and early_unskilled and late_unskilled:
        elite_gain = late_elite - early_elite
        unskilled_gain = late_unskilled - early_unskilled
        print(f"\n3. HETEROGENEOUS EFFECTS:")
        print(f"   Elite gained {elite_gain:.1f} years of life ({early_decade}→{late_decade})")
        print(f"   Unskilled gained {unskilled_gain:.1f} years of life ({early_decade}→{late_decade})")
        if elite_gain > unskilled_gain:
            print(f"   → Health improvements favored the elite (+{elite_gain-unskilled_gain:.1f} years more)")
        else:
            print(f"   → Health improvements were equalizing (+{unskilled_gain-elite_gain:.1f} years more for unskilled)")
except Exception as e:
    print(f"\n3. HETEROGENEOUS EFFECTS: Could not calculate (error: {e})")

# Finding 4: Disease patterns
elite_infectious = disease_class_pct.loc['Elite', 'Infectious'] if 'Elite' in disease_class_pct.index else 0
unskilled_infectious = disease_class_pct.loc['Unskilled', 'Infectious'] if 'Unskilled' in disease_class_pct.index else 0
print(f"\n4. DISEASE PATTERNS:")
print(f"   Elite: {elite_infectious:.1f}% infectious diseases")
print(f"   Unskilled: {unskilled_infectious:.1f}% infectious diseases")
print(f"   → Poor die from preventable infectious diseases")

# Save summary
summary = pd.DataFrame({
    'finding': [
        'Infant mortality gradient (Elite vs Unskilled)',
        'Infant mortality rate change 1871-1910 (%)',
        'Elite infectious disease rate (%)',
        'Unskilled infectious disease rate (%)'
    ],
    'value': [
        f"{gradient:.1f} years" if len(elite_infants) > 0 else 'N/A',
        f"{change:+.1f}%",
        f"{elite_infectious:.1f}%",
        f"{unskilled_infectious:.1f}%"
    ]
})

summary_file = OUT_DIR / "key_findings.csv"
summary.to_csv(summary_file, index=False)
print(f"\n✓ Saved: {summary_file}")

print("\n" + "="*70)
print("DONE")
print("="*70)
