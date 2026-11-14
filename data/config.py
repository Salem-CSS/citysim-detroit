"""Shared constants for the data pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"            # untouched downloads (gitignored)
INTERIM = ROOT / "interim"    # cleaned, not yet district-tagged
PROCESSED = ROOT / "processed"  # district-tagged GeoParquet, ready for S3

STATE_FIPS = "26"          # Michigan
COUNTY_FIPS = "163"        # Wayne County
DETROIT_PLACE_FIPS = "22000"  # Detroit city (place GEOID 2622000)

# Newest vintages to try first; scripts fall back to older ones if a file is missing.
ACS5_YEARS = [2024, 2023]
PUMS5_YEARS = [2024, 2023]
TIGER_YEARS = [2025, 2024, 2023]
LODES_YEARS = [2023, 2022, 2021]

PERSONA_SEED = 1114
PERSONAS_PER_DISTRICT = 500

# ACS 5-year tract tables used for persona fitting and impact context.
ACS_TABLES = {
    "B01001": "Sex by age",
    "B19001": "Household income",
    "B25003": "Tenure (owner / renter)",
    "B25044": "Tenure by vehicles available",
    "B25009": "Tenure by household size",
    "B08301": "Means of transportation to work",
    "B08303": "Travel time to work",
    "B25038": "Tenure by year householder moved in",
    "B11005": "Households by presence of people under 18",
}

for d in (RAW, INTERIM, PROCESSED):
    d.mkdir(parents=True, exist_ok=True)
