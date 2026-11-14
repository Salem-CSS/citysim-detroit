"""Download every Census file CitySim needs for Detroit's council districts.

    python -m data.download.census          # from repo root
    python -m data.download.census --skip-pums
    python -m data.download.census --skip-api   # files only (TIGER, PUMS); no API key needed

Writes to data/raw/census/. Safe to re-run: existing files are skipped.

What it gets
  TIGER/Line   Michigan tracts, block groups, 2020 blocks, places (Detroit boundary)
  ACS 5-year   tract tables for Wayne County (see config.ACS_TABLES)
  Decennial    2020 block population, total (P1) and 18 and over (P3), for Wayne County
  Rel. file    2020 tract -> 2020 PUMA; Detroit's PUMAs are derived from it and written to
               data/interim/detroit_pumas.json
  PUMS 5-year  Michigan person + household records (seed for AI residents)
"""
import argparse, csv, json, os
import requests
from dotenv import load_dotenv
from data.config import RAW, INTERIM, STATE_FIPS, COUNTY_FIPS, DETROIT_PLACE_FIPS, ACS5_YEARS, PUMS5_YEARS, TIGER_YEARS, ACS_TABLES
from data.download._http import fetch, first_available, record, UA

load_dotenv()
OUT = RAW / "census"
KEY = os.getenv("CENSUS_API_KEY", "").strip()

def require_key():
    """The Census API refuses requests without a key (it answers with a "Missing Key" web page)."""
    if not KEY:
        raise SystemExit(
            "CENSUS_API_KEY is not set. The Census API no longer answers without one.\n"
            "Get a free key at https://api.census.gov/data/key_signup.html and put it in .env "
            "(CENSUS_API_KEY=...).\nTo download only the files that need no key, run with --skip-api.")

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
    require_key()
    r = requests.get(url, params={**params, "key": KEY}, headers=UA, timeout=300)
    r.raise_for_status()
    try:
        return r.json()
    except ValueError:
        raise RuntimeError(f"Census API did not return data for {url} (is the key valid and activated?): {r.text[:120]!r}")

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
        record(dest, f"https://api.census.gov/data/{year}/acs/acs5?get=group({table})", rows=len(rows) - 1, vintage=f"ACS 5-year {year}")
        print(f"  got   {dest.name}  ({len(rows)-1} tracts) {label}")
    # variable labels, so column codes are readable later
    fetch(f"https://api.census.gov/data/{year}/acs/acs5/variables.json", OUT / "acs" / f"acs5_{year}_variables.json")

def block_population():
    print("2020 block population: total (P1_001N) and 18 and over (P3_001N), Wayne County")
    dest = OUT / "decennial" / "dec2020_pl_P1_P3_blocks_wayne.csv"
    if dest.exists():
        print(f"  have  {dest.name}"); return
    rows = api_get("https://api.census.gov/data/2020/dec/pl",
                   {"get": "P1_001N,P3_001N", "for": "block:*", "in": f"state:{STATE_FIPS} county:{COUNTY_FIPS} tract:*"})
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", newline="") as f:
        csv.writer(f).writerows(rows)
    record(dest, "https://api.census.gov/data/2020/dec/pl?get=P1_001N,P3_001N", rows=len(rows) - 1, vintage="2020 Census PL 94-171")
    print(f"  got   {dest.name}  ({len(rows)-1} blocks)")

def detroit_pumas() -> list[str]:
    """Detroit's 2020 PUMAs: the PUMAs of the Wayne County tracts that lie in the Detroit place boundary.

    A tract counts as Detroit when more than half its area is inside the city polygon (TIGER place
    2622000). Tracts that only touch the city line are not counted; any tract split by the line is printed.
    Needs the TIGER tract and place files, so tiger() must have run. Writes data/interim/detroit_pumas.json.
    """
    import geopandas as gpd
    print("Detroit PUMAs (2020 definitions) from tracts inside the city boundary")
    rel_url = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/2020_Census_Tract_to_2020_PUMA.txt"
    rel = fetch(rel_url, OUT / "rel" / "2020_Census_Tract_to_2020_PUMA.txt")
    tract_zip = sorted((OUT / "tiger").glob("tl_*_26_tract.zip"))[-1]
    place_zip = sorted((OUT / "tiger").glob("tl_*_26_place.zip"))[-1]
    place = gpd.read_file(place_zip)
    city = place[place["GEOID"] == STATE_FIPS + DETROIT_PLACE_FIPS]
    if len(city) != 1:
        raise RuntimeError(f"expected one Detroit place polygon in {place_zip.name}, found {len(city)}")
    tracts = gpd.read_file(tract_zip)
    tracts = tracts[tracts["COUNTYFP"] == COUNTY_FIPS].to_crs(26917)   # UTM 17N, metres
    city_shape = city.to_crs(26917).geometry.iloc[0]
    share = tracts.geometry.intersection(city_shape).area / tracts.geometry.area
    split = tracts[(share > 0.01) & (share < 0.99)]
    for geoid, sh in zip(split["GEOID"], share[split.index]):
        print(f"  tract {geoid} is split by the city line: {sh:.0%} inside Detroit")
    detroit_tracts = set(tracts[share > 0.5]["TRACTCE"])
    puma_of = {r["TRACTCE"]: r["PUMA5CE"] for r in csv.DictReader(open(rel, encoding="utf-8-sig"))
               if r["STATEFP"] == STATE_FIPS and r["COUNTYFP"] == COUNTY_FIPS}
    unmatched = detroit_tracts - set(puma_of)
    if unmatched:
        raise RuntimeError(f"{len(unmatched)} Detroit tracts are missing from the tract-to-PUMA file: {sorted(unmatched)[:5]}")
    pumas = sorted({puma_of[t] for t in detroit_tracts})
    tracts_per_puma = {p: sum(1 for t in detroit_tracts if puma_of[t] == p) for p in pumas}
    all_per_puma = {p: sum(1 for v in puma_of.values() if v == p) for p in pumas}
    out = INTERIM / "detroit_pumas.json"
    out.write_text(json.dumps({
        "pumas": pumas, "puma_vintage": "2020", "detroit_tracts": len(detroit_tracts),
        "detroit_tracts_per_puma": tracts_per_puma, "all_tracts_per_puma": all_per_puma,
        "rule": "Wayne County tract with more than half its area inside TIGER place 2622000",
        "sources": [rel_url, tract_zip.name, place_zip.name]}, indent=1))
    print(f"  {len(detroit_tracts)} Detroit tracts -> PUMAs {', '.join(pumas)}  ({out.name})")
    for p in pumas:
        if tracts_per_puma[p] != all_per_puma[p]:
            print(f"  note: PUMA {p} also covers {all_per_puma[p] - tracts_per_puma[p]} tract(s) outside Detroit")
    return pumas

def pums():
    print("PUMS 5-year Michigan (person + household)")
    for kind in ("p", "h"):
        url = first_available([f"https://www2.census.gov/programs-surveys/acs/data/pums/{y}/5-Year/csv_{kind}mi.zip" for y in PUMS5_YEARS])
        year = url.split("/pums/")[1].split("/")[0]
        fetch(url, OUT / "pums" / f"pums5_{year}_csv_{kind}mi.zip")

def main(argv: list[str] | None = None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-pums", action="store_true", help="PUMS zips are large (30-70 MB each)")
    ap.add_argument("--skip-api", action="store_true", help="skip the ACS and block-population API calls (the only steps that need CENSUS_API_KEY)")
    a = ap.parse_args(argv)
    if not a.skip_api:
        require_key()   # fail before any download, not halfway through
    tiger()
    detroit_pumas()
    if not a.skip_api:
        acs()
        block_population()
    if not a.skip_pums:
        pums()
    print("done ->", OUT)

if __name__ == "__main__":
    main()
