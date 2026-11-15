"""Build the small data file the traffic engine reads in Lambda (no map library at run time).

    python -m data.engine_data

Output: data/processed/engine/engine_data.json (uploaded to s3://<bucket>/processed/engine/engine_data.json)
  blocks    [lon, lat, adults, tract index] for every 2020 block inside a council district (interior point, P3 adults)
  tracts    [{geoid, zero_car_share}]  share of households with no vehicle, ACS 2024 B25044
  segments  2024 traffic counts: id, street, from, to, aadt, lanes, speed, coords (simplified to ~10 m)
  stops     [lon, lat, route number, route name] for DDOT stops
"""
from __future__ import annotations

import json

import geopandas as gpd

from data.config import PROCESSED, RAW
from data.personas.build import acs, blocks_with_districts

OUT = PROCESSED / "engine" / "engine_data.json"


def main() -> None:
    b = blocks_with_districts().dropna(subset=["district"])
    veh = acs("B25044")
    share = ((veh["B25044_003E"] + veh["B25044_010E"]) / veh["B25044_001E"]).dropna()
    geoids = sorted(set(b.tract) & set(share.index))
    idx = {g: i for i, g in enumerate(geoids)}
    blocks = [[round(r.lon, 5), round(r.lat, 5), int(r.adults), idx[r.tract]] for r in b.itertuples() if r.tract in idx]
    tracts = [{"geoid": g, "zero_car_share": round(float(share[g]), 4)} for g in geoids]

    seg = gpd.read_file(RAW / "detroit" / "traffic_volumes_2024.geojson")
    seg["geometry"] = seg.geometry.to_crs(26917).simplify(10).to_crs(4326)
    segments = []
    for r in seg.itertuples():
        lines = [r.geometry] if r.geometry.geom_type == "LineString" else list(r.geometry.geoms)
        segments.append({"id": r.route_location_id, "street": " ".join(str(r.street_name).split()), "from": r.from_description,
                         "to": r.to_description, "aadt": int(r.num_aadt), "lanes": int(r.num_lanes) if r.num_lanes == r.num_lanes else None,
                         "two_way": str(r.facility_type).startswith("2"), "speed": r.posted_speed,
                         "coords": [[[round(x, 5), round(y, 5)] for x, y in ln.coords] for ln in lines]})
    stops = gpd.read_file(RAW / "detroit" / "ddot_stop_ridership.geojson")
    stop_rows = [[round(g.x, 5), round(g.y, 5), str(n).strip(), str(m).strip()] for g, n, m in zip(stops.geometry, stops.Route_Numb, stops.Route_Name)]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"sources": {"blocks": "2020 Census P3 (adults) by block, TIGER 2025 interior points, 2026 council districts",
                                           "tracts": "ACS 2024 5-year B25044", "segments": "City of Detroit 2024 traffic volumes (num_aadt)",
                                           "stops": "DDOT bus stop layer (BusStopAmenitiesForArcGIS)"},
                               "blocks": blocks, "tracts": tracts, "segments": segments, "stops": stop_rows}, separators=(",", ":")))
    print(f"{len(blocks):,} blocks, {len(tracts)} tracts, {len(segments):,} counted segments, {len(stop_rows):,} stops -> "
          f"{OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
