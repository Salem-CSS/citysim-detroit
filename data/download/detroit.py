"""City of Detroit open data, read straight from the city's ArcGIS feature services.

    python -m data.download.detroit
    python -m data.download.detroit --only traffic_volumes roads

Every layer is paged in full and its row count checked against the service (see _arcgis.py).
Census tracts are not downloaded here: TIGER (census.py) already covers them.
If a layer has moved, find it at https://services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/services
and update LAYERS.
"""
import argparse
import re
from data.config import RAW
from data.download._arcgis import fetch_layer, _get
from data.download._http import fetch

SERVICES = "https://services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/services"
OUT = RAW / "detroit"

# name -> (service/layer path, columns dropped on download)
LAYERS = {
    "council_districts_2026": ("city_council_districts_2026/FeatureServer/0", ()),
    "roads": ("City_of_Detroit_Roads/FeatureServer/0", ()),
    "neighborhoods": ("Current_City_of_Detroit_Neighborhoods/FeatureServer/0", ()),
    "ddot_routes": ("DDOT_Bus_Routes_202509/FeatureServer/0", ()),
    "ddot_stop_ridership": ("BusStopAmenitiesForArcGIS/FeatureServer/0", ()),
    "zoning": ("Zoning_1/FeatureServer/0", ()),
    # parcel_file_current is the copy the city edits daily; the catalog's Parcels_Current is stale.
    # Taxpayer names and mailing addresses are personal data the project does not need.
    "parcels": ("parcel_file_current/FeatureServer/0",
                ("taxpayer_1", "taxpayer_2", "taxpayer_address", "taxpayer_city", "taxpayer_state", "taxpayer_zip_code")),
    "building_footprints": ("Detroit_Building_Footprints_(Public_Safety)/FeatureServer/0", ()),
    "improve_detroit_311": ("improve_detroit/FeatureServer/0", ()),
}
TRAFFIC_SERVICE = "yearly_traffic_volume_layers/FeatureServer"
GTFS_URL = "https://www.detroitmi.gov/Portals/0/docs/deptoftransportation/pdfs/ddot_gtfs.zip"


def traffic_volumes():
    """The service has one layer per count year. Take the newest, found by its name, not its position."""
    layers = _get(f"{SERVICES}/{TRAFFIC_SERVICE}", {"f": "json"})["layers"]
    by_year = {}
    for lyr in layers:
        m = re.fullmatch(r"(\d{4}) Traffic Volumes", lyr["name"])
        if m:
            by_year[int(m.group(1))] = lyr["id"]
    if not by_year:
        raise RuntimeError(f"no '<year> Traffic Volumes' layer in {TRAFFIC_SERVICE}: {[l['name'] for l in layers]}")
    year = max(by_year)
    fetch_layer(f"{SERVICES}/{TRAFFIC_SERVICE}/{by_year[year]}", OUT / f"traffic_volumes_{year}.geojson", count_year=year)


def gtfs():
    fetch(GTFS_URL, RAW / "ddot" / "ddot_gtfs.zip")


def main(only: list[str] | None = None):
    jobs = {name: (lambda p=path, d=drop, n=name: fetch_layer(f"{SERVICES}/{p}", OUT / f"{n}.geojson", drop_fields=d))
            for name, (path, drop) in LAYERS.items()}
    big_311 = jobs.pop("improve_detroit_311")   # 765,000 rows and nice-to-have: run it last
    jobs = {"traffic_volumes": traffic_volumes, **jobs, "gtfs": gtfs, "improve_detroit_311": big_311}
    unknown = [n for n in (only or []) if n not in jobs]
    if unknown:
        raise SystemExit(f"unknown dataset(s) {unknown}; choose from {list(jobs)}")
    failed = []
    for name, job in jobs.items():
        if only and name not in only:
            continue
        print(name)
        try:
            job()
        except Exception as e:
            failed.append(name)
            print(f"  FAILED {name}: {e}")
    print("done ->", OUT)
    if failed:
        raise SystemExit(f"FAILED: {', '.join(failed)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="+", help="download just these datasets")
    main(ap.parse_args().only)
