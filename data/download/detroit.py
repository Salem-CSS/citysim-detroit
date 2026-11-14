"""City of Detroit open data via the detroitdata.org CKAN API.

    python -m data.download.detroit

Each dataset is looked up by its CKAN id; the first GeoJSON (or CSV) resource is saved.
If an id has changed, search https://detroitdata.org and update DATASETS.
"""
import requests
from data.config import RAW
from data.download._http import fetch, UA

CKAN = "https://detroitdata.org/api/3/action/package_show"
OUT = RAW / "detroit"
DATASETS = {
    "council_districts_2026": "detroit-city-council-districts-2026",
    "parcels": "parcels",
    "zoning": "zoning",
    "traffic_volumes": "traffic-volumes",
    "improve_detroit_311": "improve-detroit-issues1",
    "census_tracts_2020": "detroit-2020-census-tracts-zipcodes",
}
PREFER = ["GeoJSON", "geojson", "CSV", "csv", "ZIP", "Shapefile"]

def main():
    for name, ckan_id in DATASETS.items():
        try:
            pkg = requests.get(CKAN, params={"id": ckan_id}, headers=UA, timeout=60).json()["result"]
            res = sorted(pkg["resources"], key=lambda r: PREFER.index(r.get("format")) if r.get("format") in PREFER else 99)[0]
            ext = {"geojson": "geojson", "csv": "csv", "zip": "zip", "shapefile": "zip"}.get(res.get("format", "").lower(), "dat")
            fetch(res["url"], OUT / f"{name}.{ext}")
        except Exception as e:
            print(f"  FAILED {name} ({ckan_id}): {e}")
    print("done ->", OUT)

if __name__ == "__main__":
    main()
