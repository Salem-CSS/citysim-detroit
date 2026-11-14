# data/

Download, clean and district-tag every dataset, then build the AI residents. Owner: Lane A (BUILD.md Steps 3, 4, 13).

## Get the raw files

The download scripts need normal internet access (census.gov, lehd.ces.census.gov, detroitdata.org). Run them on a laptop:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r data/requirements.txt
cp .env.example .env            # add your free CENSUS_API_KEY
python -m data.download.all     # or run census / lodes / detroit one at a time
```

Everything lands in `data/raw/` (gitignored). Re-running skips files you already have. Then upload: `aws s3 sync data/raw s3://$DATA_BUCKET/raw/`.

## What gets downloaded

| Source | Files | Used for |
| --- | --- | --- |
| TIGER/Line | MI tracts, block groups, 2020 blocks, places | Tract and block geometry; Detroit boundary |
| ACS 5-year (API) | 9 tract tables for Wayne County (`config.ACS_TABLES`) | IPF control totals for personas |
| 2020 Census PL (API) | Block population, Wayne County | Assigning each persona a home block |
| Census relationship file | 2020 tract to 2020 PUMA | Which PUMS records cover Detroit |
| ACS PUMS 5-year | Michigan person + household CSVs | Seed records for AI residents |
| LODES 8 | MI OD, RAC, WAC, block crosswalk | Where residents work; trip distribution |
| Detroit Open Data | 2026 council districts, parcels, zoning, traffic volumes, 311, 2020 tracts | District tagging, sites, AADT |

Scripts try the newest vintage first and fall back to older ones if a file isn't published yet.

## Layout

```
data/
  config.py              constants: FIPS codes, vintages, seed, ACS tables
  download/              census.py, lodes.py, detroit.py, all.py
  clean/                 one cleaner per dataset (TODO)
  personas/build.py      IPF + persona draw (TODO)
  ite_rates.csv          ITE trip rates, typed by hand; grow to 25-40 codes
  calibration_targets.json  DMACS checks + drone poll bounds
  raw/ interim/ processed/  gitignored
```
