"""Download every Census file CitySim needs for Detroit's council districts.

    python -m data.download.census          # from repo root
    python -m data.download.census --skip-pums

Writes to data/raw/census/. Safe to re-run: existing files are skipped.

What it gets
  TIGER/Line   Michigan tracts, block groups, 2020 blocks, places (Detroit boundary)
  ACS 5-year   tract tables for Wayne County (see config.ACS_TABLES)
  Decennial    2020 block population (P1) for Wayne County, for home-block assignment
  Rel. file    2020 tract -> 2020 PUMA, to find Detroit's PUMAs
  PUMS 5-year  Michigan person + household records (seed for AI residents)
"""
import argparse, csv, io, json, os
import requests
from dotenv import load_dotenv
from data.config import RAW, STATE_FIPS, COUNTY_FIPS, ACS5_YEARS, PUMS5_YEARS, TIGER_YEARS, ACS_TABLES, DETROIT_PUMAS_FALLBACK
from data.download._http import fetch, first_available, UA

load_dotenv()
OUT = RAW / "census"
KEY = os.getenv("CENSUS_API_KEY", "")

def tiger():
    print("TIGER/Line")
    layers = {
        "TRACT": "tl_{y}_26_tract.zip",
        "BG": "tl_{y}_26_bg.zip",
        "TABBLOCK20": "tl_{y}_26_tabblock20.zip",
        "PLACE": "tl_{y}_26_place.zip",
    }
    for folder, name in layers.items():
        url = first_available([f"https://www2.census.gov/geo/tiger/TIGER{y}/{folder}/{name.format(y=y)}" for y in TIGER_YEARS])
        fetch(url, OUT / "tiger" / url.rsplit("/", 1)[1])

def api_get(url: str, params: dict) -> list[list[str]]:
    if KEY:
        params = {**params, "key": KEY}
    r = requests.get(url, params=params, headers=UA, timeout=120)
    r.raise_for_status()
    return r.json()

def acs():
    print("ACS 5-year tract tables (Wayne County)")
    year = None
    for y in ACS5_YEARS:
        try:
            requests.get(f"https://api.census.gov/data/{y}/acs/acs5", headers=UA, timeout=30).raise_for_status()
            year = y; break
        except requests.RequestException:
            continue
    if not year:
        raise RuntimeError("no ACS 5-year vintage reachable")
    for table, label in ACS_TABLES.items():
        dest = OUT / "acs" / f"acs5_{year}_{table}_tract_wayne.csv"
        if dest.exists():
            print(f"  have  {dest.name}"); continue
        rows = api_get(f"https://api.census.gov/data/{year}/acs/acs5",
                       {"get": f"NAME,group({table})", "for": "tract:*", "in": f"state:{STATE_FIPS} county:{COUNTY_FIPS}"})
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", newline="") as f:
            csv.writer(f).writerows(rows)
        print(f"  got   {dest.name}  ({len(rows)-1} tracts) {label}")
    # variable labels, so column codes are readable later
    fetch(f"https://api.census.gov/data/{year}/acs/acs5/variables.json", OUT / "acs" / f"acs5_{year}_variables.json")

def block_population():
    print("2020 block population (P1, Wayne County)")
    dest = OUT / "decennial" / "dec2020_pl_P1_blocks_wayne.csv"
    if dest.exists():
        print(f"  have  {dest.name}"); return
    rows = api_get("https://api.census.gov/data/2020/dec/pl",
                   {"get": "P1_001N", "for": "block:*", "in": f"state:{STATE_FIPS} county:{COUNTY_FIPS} tract:*"})
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", newline="") as f:
        csv.writer(f).writerows(rows)
    print(f"  got   {dest.name}  ({len(rows)-1} blocks)")

def detroit_pumas() -> list[str]:
    print("2020 tract -> PUMA relationship")
    p = fetch("https://www2.census.gov/geo/docs/maps-data/data/rel2020/2020_Census_Tract_to_2020_PUMA.txt",
              OUT / "rel" / "2020_Census_Tract_to_2020_PUMA.txt")
    return sorted({r["PUMA5CE"] for r in csv.DictReader(open(p, encoding="utf-8-sig"))
                   if r["STATEFP"] == STATE_FIPS and r["COUNTYFP"] == COUNTY_FIPS})

def pums():
    print("PUMS 5-year Michigan (person + household)")
    for kind in ("p", "h"):
        url = first_available([f"https://www2.census.gov/programs-surveys/acs/data/pums/{y}/5-Year/csv_{kind}mi.zip" for y in PUMS5_YEARS])
        year = url.split("/pums/")[1].split("/")[0]
        fetch(url, OUT / "pums" / f"pums5_{year}_csv_{kind}mi.zip")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-pums", action="store_true", help="PUMS zips are large (~100+ MB each)")
    ap.add_argument("--skip-blocks", action="store_true", help="statewide 2020 block shapefile is large")
    a = ap.parse_args()
    tiger()
    acs()
    block_population()
    try:
        wayne = detroit_pumas()
        print(f"  Wayne County PUMAs: {', '.join(wayne)}  (Detroit's are the ones whose tracts fall in the city; data/personas filters by tract)")
    except Exception as e:
        print(f"  relationship file failed ({e}); fallback Detroit PUMAs {DETROIT_PUMAS_FALLBACK}")
    if not a.skip_pums:
        pums()
    print("done ->", OUT)

if __name__ == "__main__":
    main()
