"""Build the place index the scenario step uses to verify locations (BACKEND_PLAN.md 11.2).

    python -m data.places.build_index

From the city road layer (data/raw/detroit/roads.geojson):
  streets        normalised name -> display name
  crossings      "a|b" (names sorted) -> [lon, lat] where the two streets share a node
  ranges         normalised name -> [[low, high, lon1, lat1, lon2, lat2], ...] address ranges per segment
From the official council districts: simplified polygons, so a point can be placed in a district
without a map library at run time.

Output: data/processed/places/places.json (uploaded to s3://<bucket>/processed/places/places.json).
"""
from __future__ import annotations

import json
from collections import defaultdict

from shapely.geometry import shape

from data.config import PROCESSED, RAW
from shared.places import norm_street

OUT = PROCESSED / "places" / "places.json"
SKIP_TYPES = {"RAMP", "TURN"}


def main() -> None:
    feats = json.loads((RAW / "detroit" / "roads.geojson").read_text())["features"]
    streets, ranges = {}, defaultdict(list)
    nodes = defaultdict(set)                       # rounded endpoint -> street names meeting there
    for f in feats:
        p, g = f["properties"], f["geometry"]
        if not g or (p.get("FETYPE") or "").strip() in SKIP_TYPES:
            continue
        key = norm_street(p.get("RDNAME") or "")
        if not key:
            continue
        streets.setdefault(key, " ".join((p.get("RDNAME") or "").split()))
        lines = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"]
        for line in lines:
            for lon, lat in (line[0][:2], line[-1][:2]):
                nodes[(round(lon, 5), round(lat, 5))].add(key)
            for lo, hi in ((p.get("FRADDL"), p.get("TOADDL")), (p.get("FRADDR"), p.get("TOADDR"))):
                if lo and hi:
                    a, b = sorted((int(lo), int(hi)))
                    first, last = (line[0], line[-1]) if int(lo) <= int(hi) else (line[-1], line[0])
                    ranges[key].append([a, b, round(first[0], 6), round(first[1], 6), round(last[0], 6), round(last[1], 6)])
    pts = defaultdict(list)
    for (lon, lat), names in nodes.items():
        names = sorted(names)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                pts[f"{a}|{b}"].append((lon, lat))
    crossings = {}
    for k, ps in pts.items():                      # several meeting points: keep the one nearest their middle
        mx, my = sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps)
        crossings[k] = list(min(ps, key=lambda p: (p[0] - mx) ** 2 + (p[1] - my) ** 2))
    districts = {}
    for f in json.loads((RAW / "detroit" / "council_districts_2026.geojson").read_text())["features"]:
        g = shape(f["geometry"]).buffer(0).simplify(0.0001)
        polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
        districts[str(int(f["properties"]["district_number"]))] = [[[round(x, 5), round(y, 5)] for x, y in p.exterior.coords] for p in polys]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"source": "City of Detroit road layer (City_of_Detroit_Roads) and 2026 council districts",
                               "streets": streets, "crossings": crossings, "ranges": ranges, "districts": districts},
                              separators=(",", ":")))
    print(f"{len(streets):,} streets, {len(crossings):,} crossings, {sum(len(v) for v in ranges.values()):,} address ranges, "
          f"{len(districts)} districts -> {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
