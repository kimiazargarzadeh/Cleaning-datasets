"""
Visualize deaths linkage and coverage trends over time
"""
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

SUMMARY = Path("Harmonization/data_outputs/deaths_linkage_summary/linkage_summary_all_years.csv")
OUT_DIR = Path("Harmonization/data_outputs/deaths_linkage_summary")

print("Loading linkage summary...")
df = pd.read_csv(SUMMARY)
print(f"Years available: {df['year'].min()}-{df['year'].max()} ({len(df)} years)")

# Create visualization
fig, axes = plt.subplots(3, 1, figsize=(12, 10))
fig.suptitle("FreeBMD Deaths → RD Coverage: Temporal Trends", fontsize=16, fontweight='bold')

# Plot 1: Link rate over time
ax1 = axes[0]
ax1.plot(df['year'], df['link_rate'] * 100, 'o-', linewidth=2, markersize=8, color='#2E86AB')
ax1.axhline(y=90, color='green', linestyle='--', alpha=0.5, label='90% threshold')
ax1.set_ylabel('Link Rate (%)', fontsize=12, fontweight='bold')
ax1.set_title('A) Deaths Successfully Matched to RD Coverage', fontsize=12, loc='left')
ax1.grid(True, alpha=0.3)
ax1.set_ylim([0, 105])
ax1.legend()

# Plot 2: Usable 1851 backbone rate (of linked deaths)
ax2 = axes[1]
ax2.plot(df['year'], df['usable_rate_of_linked'] * 100, 'o-', linewidth=2, markersize=8, color='#A23B72')
ax2.axhline(y=80, color='orange', linestyle='--', alpha=0.5, label='80% threshold')
ax2.axhline(y=50, color='red', linestyle='--', alpha=0.5, label='50% threshold')
ax2.set_ylabel('Usable 1851 Backbone (%)', fontsize=12, fontweight='bold')
ax2.set_title('B) Linked Deaths with Usable 1851 Parish Geography', fontsize=12, loc='left')
ax2.grid(True, alpha=0.3)
ax2.set_ylim([0, 105])
ax2.legend()

# Plot 3: Absolute counts
ax3 = axes[2]
ax3.plot(df['year'], df['usable_1851_backbone'] / 1000, 'o-', linewidth=2, markersize=8,
         color='green', label='Usable (with 1851 geometry)')
ax3.plot(df['year'], df['non_usable_1851_backbone'] / 1000, 'o-', linewidth=2, markersize=8,
         color='red', label='Non-usable (imputed centroids)')
ax3.set_xlabel('Year', fontsize=12, fontweight='bold')
ax3.set_ylabel('Deaths (thousands)', fontsize=12, fontweight='bold')
ax3.set_title('C) Absolute Death Counts by Coverage Quality', fontsize=12, loc='left')
ax3.grid(True, alpha=0.3)
ax3.legend()

plt.tight_layout()
plt.savefig(OUT_DIR / "coverage_trends.png", dpi=300, bbox_inches='tight')
print(f"✓ Saved: {OUT_DIR / 'coverage_trends.png'}")

# Summary statistics table
print("\n" + "=" * 80)
print("SUMMARY BY YEAR")
print("=" * 80)
print(df[['year', 'total_deaths', 'link_rate', 'usable_rate_of_linked',
          'median_matched_share']].to_string(index=False))

print("\n" + "=" * 80)
print("KEY FINDINGS:")
print("=" * 80)

# Check for critical decline
early_years = df[df['year'] < 1920]['usable_rate_of_linked'].mean()
late_years = df[df['year'] >= 1935]['usable_rate_of_linked'].mean()

if len(df[df['year'] >= 1935]) > 0:
    decline = early_years - late_years
    print(f"Average usable rate 1850s-1910s: {early_years*100:.1f}%")
    print(f"Average usable rate 1935+: {late_years*100:.1f}%")
    print(f"Decline: {decline*100:.1f} percentage points")

    if late_years < 0.7:
        print("\n⚠️  SIGNIFICANT COVERAGE LOSS post-1935!")
        print("   → Recommendation: Consider RD-LGD crosswalk for 1935+ period")
    elif late_years < 0.8:
        print("\n⚠️  MODERATE COVERAGE LOSS post-1935")
        print("   → Recommendation: Assess if acceptable for your analysis")
    else:
        print("\n✅ COVERAGE REMAINS GOOD post-1935")
        print("   → Current 1851 backbone approach is sufficient")
else:
    print("⚠️  No post-1935 data available yet. Download more years to assess decline.")

print("=" * 80)
