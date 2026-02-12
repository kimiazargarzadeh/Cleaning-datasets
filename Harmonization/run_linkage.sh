#!/bin/bash
# Run deaths linkage analysis

cd "/Users/kimik/Desktop/RA (probate + hospital records)/Cleaning-datasets"

echo "Running deaths → RD coverage linkage..."
/Users/kimik/miniforge3/envs/geo/bin/python Harmonization/batch_match_deaths_to_coverage.py

echo ""
echo "✅ Done! Check outputs:"
echo "  - Harmonization/data_outputs/deaths_linkage_summary/linkage_summary_all_years.csv"
echo "  - Harmonization/data_outputs/deaths_linkage_summary/unlinked_districts_all_years.csv"
