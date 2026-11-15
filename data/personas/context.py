"""Neighborhood facts around each resident's home block (BACKEND_PLAN.md 7.1, Tier 2).

    python -m data.personas.context          # after data.personas.build

Adds to every persona row a `context` list of plain lines plus the numbers behind them. Every fact is a count
or a distance for the area around the home block's interior point, taken from a public dataset. None is a
record about a person. "Nearby" means within a quarter mile (402 m) in a straight line.

Sources (data/raw/, all listed in manifest.json unless noted):
  neighborhoods.geojson            City of Detroit neighborhoods
  crime_incidents_2026.geojson     Detroit Police reported incidents, 2026 to date
  dlba_owned_properties.geojson    Detroit Land Bank inventory (lots = statuses containing "Lot")
  liquor_licenses.geojson          state liquor licenses in Detroit, status Active
  city_parks.geojson, schools.geojson
  ddot_stop_ridership.geojson      bus stops with route and boardings (ridership period not stated by the city)
  traffic_volumes_2024.geojson     2024 traffic counts (num_aadt)
  improve_detroit_311.geojson      311 requests, last 12 months of the file
  ../cdc_places_wayne_tracts.json  CDC PLACES 2023 tract estimates (fetched from data.cdc.gov, not in manifest)
"""
from __future__ import annotations

import json
import time
from collections import Counter

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from data.config import PROCESSED, RAW
from engine.proximity import how_far

DET = RAW / "detroit"
OUT = PROCESSED / "personas"
NEAR_M = 402.0
CRS_M = 26917                      # UTM 17N, metres


def points(path, keep=(), where=None) -> gpd.GeoDataFrame:
    """Read a line-per-feature GeoJSON of points without loading it as one object."""
    xs, ys, rows = [], [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip().lstrip(",")
            if not line.startswith('{"type":"Feature"'):
                continue
            ft = json.loads(line)
            p, g = ft["properties"], ft.get("geometry")
            lon, lat = (g["coordinates"][:2] if g and g["type"] == "Point" else (p.get("longitude"), p.get("latitude")))
            if lon is None or lat is None or (where and not where(p)):
                continue
            xs.append(lon); ys.append(lat); rows.append({k: p.get(k) for k in keep})
    return gpd.GeoDataFrame(rows, geometry=gpd.points_from_xy(xs, ys), crs=4326).to_crs(CRS_M)


def count_near(homes_xy: np.ndarray, pts: gpd.GeoDataFrame, label_col: str | None = None, top: int = 2):
    """For each home: how many points lie within NEAR_M, and the most common labels among them."""
    xy = np.column_stack([pts.geometry.x.to_numpy(), pts.geometry.y.to_numpy()])
    labels = pts[label_col].fillna("").astype(str).str.strip().to_numpy() if label_col else None
    counts, tops = [], []
    for hx, hy in homes_xy:
        near = (xy[:, 0] - hx) ** 2 + (xy[:, 1] - hy) ** 2 <= NEAR_M ** 2
        counts.append(int(near.sum()))
        tops.append([k for k, _ in Counter(labels[near]).most_common(top) if k] if label_col else [])
    return counts, tops


def nearest(homes: gpd.GeoDataFrame, other: gpd.GeoDataFrame, cols: list[str]) -> pd.DataFrame:
    j = gpd.sjoin_nearest(homes, other[cols + ["geometry"]], how="left", distance_col="dist_m")
    return j[~j.index.duplicated()][cols + ["dist_m"]]


def main() -> None:
    people = {d: json.loads((OUT / f"district_{d}.json").read_text()) for d in range(1, 8)}
    blocks = {p["block_geoid"]: (p["home_lon"], p["home_lat"]) for rows in people.values() for p in rows}
    ids = sorted(blocks)
    homes = gpd.GeoDataFrame({"block": ids}, geometry=[Point(blocks[b]) for b in ids], crs=4326).to_crs(CRS_M)
    xy = np.column_stack([homes.geometry.x.to_numpy(), homes.geometry.y.to_numpy()])
    print(f"{len(ids):,} home blocks")

    hoods = gpd.read_file(DET / "neighborhoods.geojson")[["nhood_name", "geometry"]].to_crs(CRS_M)
    hood = gpd.sjoin(homes, hoods, how="left", predicate="within")
    hood = hood[~hood.index.duplicated()].nhood_name

    crime = points(DET / "crime_incidents_2026.geojson", keep=("offense_category",))
    crime_n, crime_top = count_near(xy, crime, "offense_category")
    lots = points(DET / "dlba_owned_properties.geojson", keep=("inventory_status_socrata",),
                  where=lambda p: "Lot" in (p.get("inventory_status_socrata") or ""))
    lots_n, _ = count_near(xy, lots)
    liquor = points(DET / "liquor_licenses.geojson", where=lambda p: p.get("status") == "Active")
    liquor_n, _ = count_near(xy, liquor)
    cutoff = None
    with open(DET / "improve_detroit_311.geojson", encoding="utf-8") as f:           # newest request date in the file
        newest = max((json.loads(l.strip().lstrip(","))["properties"].get("created_at") or 0)
                     for l in f if l.lstrip(",").startswith('{"type":"Feature"'))
    cutoff = newest - 365 * 86400 * 1000
    req = points(DET / "improve_detroit_311.geojson", keep=("request_type",), where=lambda p: (p.get("created_at") or 0) >= cutoff)
    req_n, req_top = count_near(xy, req, "request_type")
    print(f"crime {len(crime):,}, land bank lots {len(lots):,}, active liquor licenses {len(liquor):,}, 311 in last 12 months {len(req):,}")

    parks = gpd.read_file(DET / "city_parks.geojson")[["park_name", "geometry"]].to_crs(CRS_M)
    schools = gpd.read_file(DET / "schools.geojson")[["ENTITY_NAME", "geometry"]].to_crs(CRS_M)
    stops = gpd.read_file(DET / "ddot_stop_ridership.geojson")[["Location", "Route_Name", "Route_Numb", "Boardings", "geometry"]].to_crs(CRS_M)
    counts = gpd.read_file(DET / "traffic_volumes_2024.geojson")[["street_name", "num_aadt", "geometry"]].to_crs(CRS_M)
    park, school, stop, road = (nearest(homes, parks, ["park_name"]), nearest(homes, schools, ["ENTITY_NAME"]),
                                nearest(homes, stops, ["Location", "Route_Name", "Route_Numb", "Boardings"]),
                                nearest(homes, counts, ["street_name", "num_aadt"]))

    cdc = {}
    for r in json.loads((RAW / "cdc_places_wayne_tracts.json").read_text()):
        if r["measureid"] == "GHLTH" and r.get("data_value"):
            cdc[r["locationname"]] = float(r["data_value"])

    ctx = {}
    for i, b in enumerate(ids):
        lines = []
        if isinstance(hood.iloc[i], str):
            lines.append(f"Neighborhood: {hood.iloc[i]}")
        lines.append(f"Crimes reported within a quarter mile of home in 2026 so far: {crime_n[i]}"
                     + (f" (most common: {', '.join(t.lower() for t in crime_top[i])})" if crime_top[i] else ""))
        lines.append(f"Vacant Land Bank lots within a quarter mile: {lots_n[i]}")
        lines.append(f"Places licensed to sell alcohol within a quarter mile: {liquor_n[i]}")
        lines.append(f"Nearest park: {park.park_name.iloc[i]}, {how_far(park.dist_m.iloc[i])} away")
        lines.append(f"Nearest school: {str(school.ENTITY_NAME.iloc[i]).strip()}, {how_far(school.dist_m.iloc[i])} away")
        lines.append(f"Nearest bus stop: {how_far(stop.dist_m.iloc[i])} away, route {str(stop.Route_Numb.iloc[i]).strip()} {str(stop.Route_Name.iloc[i]).strip()}")
        lines.append(f"Nearest street with a traffic count: {str(road.street_name.iloc[i]).strip()}, {int(road.num_aadt.iloc[i]):,} vehicles a day, {how_far(road.dist_m.iloc[i])} away")
        if req_top[i]:
            lines.append(f"Most common 311 requests within a quarter mile in the past year: {', '.join(t.lower() for t in req_top[i])}")
        if b[:11] in cdc:
            lines.append(f"In your census tract, {cdc[b[:11]]:.0f}% of adults report fair or poor health (CDC, 2023)")
        ctx[b] = {"context": lines, "neighborhood": hood.iloc[i] if isinstance(hood.iloc[i], str) else None,
                  "crimes_quarter_mile_2026": crime_n[i], "landbank_lots_quarter_mile": lots_n[i],
                  "liquor_licenses_quarter_mile": liquor_n[i], "park_m": round(float(park.dist_m.iloc[i])),
                  "school_m": round(float(school.dist_m.iloc[i])), "bus_stop_m": round(float(stop.dist_m.iloc[i])),
                  "requests_311_quarter_mile_year": req_n[i]}

    for d, rows in people.items():
        for p in rows:
            p.update(ctx[p["block_geoid"]])
        (OUT / f"district_{d}.json").write_text(json.dumps(rows))
        df = pd.DataFrame(rows)
        df["years_in_home"] = pd.array([None] * len(df), dtype="Int64")
        df.to_parquet(OUT / f"district_{d}.parquet", index=False)
    crimes = np.array(crime_n)
    summary = {"built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "home_blocks": len(ids), "near_m": NEAR_M,
               "crimes_quarter_mile": {"min": int(crimes.min()), "median": int(np.median(crimes)), "max": int(crimes.max())},
               "blocks_without_neighborhood": int(sum(not isinstance(h, str) for h in hood)),
               "blocks_without_cdc_tract": int(sum(b[:11] not in cdc for b in ids)),
               "requests_311_window": "365 days up to the newest request in the file"}
    (OUT / "context_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary))
    print("\n".join(people[6][0]["context"]))


if __name__ == "__main__":
    main()
