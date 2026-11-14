# data/clean

One script per dataset: read `data/raw/...`, clean, spatial-join a `district` column from `council_districts_2026`, write GeoParquet to `data/processed/`, log row counts to `data/manifest.json` (BUILD.md Step 3).
