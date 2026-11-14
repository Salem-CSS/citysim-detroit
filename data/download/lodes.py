"""LEHD LODES 8 for Michigan: where residents work (OD), plus RAC/WAC and the block crosswalk.

    python -m data.download.lodes
"""
from data.config import RAW, LODES_YEARS
from data.download._http import fetch, first_available

BASE = "https://lehd.ces.census.gov/data/lodes/LODES8/mi"
OUT = RAW / "lodes"

def main():
    od = first_available([f"{BASE}/od/mi_od_main_JT00_{y}.csv.gz" for y in LODES_YEARS])
    year = od.rsplit("_", 1)[1].split(".")[0]
    print(f"LODES 8 Michigan, year {year}")
    fetch(od, OUT / od.rsplit("/", 1)[1])
    fetch(f"{BASE}/od/mi_od_aux_JT00_{year}.csv.gz", OUT / f"mi_od_aux_JT00_{year}.csv.gz")   # jobs held out of state
    fetch(f"{BASE}/rac/mi_rac_S000_JT00_{year}.csv.gz", OUT / f"mi_rac_S000_JT00_{year}.csv.gz")
    fetch(f"{BASE}/wac/mi_wac_S000_JT00_{year}.csv.gz", OUT / f"mi_wac_S000_JT00_{year}.csv.gz")
    fetch(f"{BASE}/mi_xwalk.csv.gz", OUT / "mi_xwalk.csv.gz")
    print("done ->", OUT)

if __name__ == "__main__":
    main()
