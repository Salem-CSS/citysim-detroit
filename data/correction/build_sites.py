"""Build the candidate-site index the correction engine draws alternative locations from.

    python data/correction/build_sites.py            # -> data/processed/correction/sites.json
    aws s3 cp data/processed/correction/sites.json s3://$DATA_BUCKET/processed/correction/sites.json

Sources (data/raw/detroit, downloaded by data/download/detroit.py):
  dlba_owned_properties.geojson   Detroit Land Bank inventory; lots = statuses containing "Lot"
  parcels.geojson                 City parcel file: address, zoning district, lot area, cross streets
  council_districts_2026.geojson  official districts

Output:
  zoning   list of zoning district codes
  sites    one row per Land Bank lot that is also in the parcel file:
           [lon, lat, lot_sqft, zoning index, district, address, cross street 1, cross street 2, neighborhood, status]
  parcels  [lon, lat, zoning index] for every parcel with a zoning district. Used only to read the zoning district
           of the parcel nearest to a proposal's original site.

Nothing here says a use is permitted on a lot: the index carries the zoning district only.
"""
import json
from pathlib import Path

import geopandas as gpd
import pyogrio

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "detroit"
OUT = ROOT / "data" / "processed" / "correction" / "sites.json"


def main():
    cols = ["parcel_id", "address", "zoning_district", "total_square_footage", "cross_street_1", "cross_street_2", "neighborhood"]
    parcels = pyogrio.read_dataframe(RAW / "parcels.geojson", columns=cols)
    parcels = parcels[parcels.geometry.notna()].copy()
    pts = parcels.geometry.representative_point()
    parcels["lon"], parcels["lat"] = pts.x.round(5), pts.y.round(5)
    parcels["zoning_district"] = parcels["zoning_district"].fillna("").str.strip()
    zoned = parcels[parcels["zoning_district"] != ""]
    codes = sorted(zoned["zoning_district"].unique())
    zi = {c: i for i, c in enumerate(codes)}

    dlba = pyogrio.read_dataframe(RAW / "dlba_owned_properties.geojson", columns=["parcel_id", "inventory_status_socrata"])
    lots = dlba[dlba["inventory_status_socrata"].fillna("").str.contains("Lot")][["parcel_id", "inventory_status_socrata"]].drop_duplicates("parcel_id")
    sites = zoned.merge(lots, on="parcel_id", how="inner")
    sites = sites[sites["total_square_footage"].fillna(0) > 0]
    districts = gpd.read_file(RAW / "council_districts_2026.geojson")
    dcol = "district_number"
    g = gpd.GeoDataFrame(sites, geometry=gpd.points_from_xy(sites["lon"], sites["lat"]), crs=districts.crs)
    g = gpd.sjoin(g, districts[[dcol, "geometry"]], how="inner", predicate="within")
    g["d"] = g[dcol].astype(str).str.extract(r"(\d+)")[0].astype(int)

    text = lambda v: v.strip() if isinstance(v, str) else ""          # a missing value is NaN, not None
    rows = [[r.lon, r.lat, int(r.total_square_footage), zi[r.zoning_district], int(r.d), text(r.address).title(),
             text(r.cross_street_1), text(r.cross_street_2), text(r.neighborhood), text(r.inventory_status_socrata)]
            for r in g.itertuples() if text(r.address)]
    par = [[r.lon, r.lat, zi[r.zoning_district]] for r in zoned.itertuples()]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "sources": {"sites": "Detroit Land Bank Authority owned properties (lots), joined to the City of Detroit parcel file by parcel id",
                    "parcels": "City of Detroit parcel file (zoning_district, total_square_footage)",
                    "districts": "City of Detroit council districts 2026"},
        "zoning": codes, "sites": rows, "parcels": par}, separators=(",", ":")), encoding="utf-8")
    print(f"{len(rows):,} Land Bank lots, {len(par):,} zoned parcels, {len(codes)} zoning districts -> {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")
    by = {}
    for r in rows:
        by[r[4]] = by.get(r[4], 0) + 1
    print("lots by district:", dict(sorted(by.items())))


if __name__ == "__main__":
    main()
