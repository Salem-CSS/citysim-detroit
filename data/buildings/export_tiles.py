"""Turn the clipped Detroit buildings Parquet into small JSON tiles for the 3D map.

    python -m data.buildings.export_tiles                       # default in/out
    python -m data.buildings.export_tiles --districts data/raw/detroit/council_districts_2026.geojson

Input : data/processed/buildings/*.parquet  (from athena_build.py)
Output: web/prototype/buildings/index.json + t/<ix>_<iy>.json  (read by map3d.html)

Tile format (kept tiny so ~335k buildings load fast):
  {"o": [lon0, lat0], "b": [[h, s, d, x, y, dx, dy, dx, dy, ...], ...]}
  h  height in metres (1 decimal)
  s  height source: 0 Overture height (lidar), 1 floors x 3.5 m, 2 default by class
  d  council district number (0 if no district file was given)
  x,y first vertex in Q-degree units from the tile origin, then deltas (outer ring only)
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IN_DIR = ROOT / "data" / "processed" / "buildings"
OUT_DIR = ROOT / "web" / "prototype" / "buildings"

LON0, LAT0 = -83.29, 42.25        # SW corner of the Detroit bbox used in sql/02_bbox.sql
TILE = 0.01                       # degrees (~0.8 km x 1.1 km)
Q = 1e-5                          # coordinate step in degrees (~0.8-1.1 m)
SIMPLIFY = 5e-6                   # degrees (~0.5 m)
SOURCE_CODE = {"overture_height": 0, "overture_floors": 1}
ATTRIBUTION = "Buildings: Overture Maps Foundation (ODbL), incl. OpenStreetMap contributors, Microsoft, Google"


def tile_of(lon: float, lat: float) -> tuple[int, int]:
    return math.floor((lon - LON0) / TILE), math.floor((lat - LAT0) / TILE)


def encode_ring(coords, ox: float, oy: float) -> list[int]:
    """Quantize a ring to Q steps from the tile origin, delta-encode, drop repeats + closing point."""
    pts: list[tuple[int, int]] = []
    for lon, lat in coords:
        p = (round((lon - ox) / Q), round((lat - oy) / Q))
        if not pts or p != pts[-1]:
            pts.append(p)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    if len(pts) < 3:
        return []
    out = [pts[0][0], pts[0][1]]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        out += [bx - ax, by - ay]
    return out


def decode_ring(enc: list[int], ox: float, oy: float) -> list[tuple[float, float]]:
    """Inverse of encode_ring (used by tests; map3d.html does the same in JS)."""
    x, y = enc[0], enc[1]
    pts = [(ox + x * Q, oy + y * Q)]
    for i in range(2, len(enc), 2):
        x += enc[i]
        y += enc[i + 1]
        pts.append((ox + x * Q, oy + y * Q))
    return pts


def load_districts(path: Path | None, prop: str):
    if not path:
        return None
    from shapely.geometry import shape
    from shapely.strtree import STRtree

    feats = json.loads(Path(path).read_text())["features"]
    geoms, ids = [], []
    for f in feats:
        geoms.append(shape(f["geometry"]))
        ids.append(int(str(f["properties"][prop]).strip().split()[-1]))
    return STRtree(geoms), geoms, ids


def district_of(index, lon: float, lat: float) -> int:
    if index is None:
        return 0
    from shapely.geometry import Point

    tree, geoms, ids = index
    p = Point(lon, lat)
    for i in tree.query(p):
        if geoms[i].contains(p):
            return ids[i]
    return 0


def read_rows(in_dir: Path):
    import pyarrow.parquet as pq

    files = sorted(in_dir.glob("*.parquet"))
    if not files:
        raise SystemExit(f"no Parquet in {in_dir}; run python -m data.buildings.athena_build first")
    cols = ["geometry", "height_m", "height_source", "lon", "lat"]
    for f in files:
        t = pq.read_table(f, columns=cols)
        yield from zip(*(t.column(c).to_pylist() for c in cols))


def export(rows, out_dir: Path, districts=None) -> dict:
    from shapely import wkb
    from shapely.geometry import MultiPolygon, Polygon

    tiles: dict[tuple[int, int], list] = defaultdict(list)
    stats = {"buildings": 0, "parts": 0, "skipped": 0, "by_source": [0, 0, 0], "max_m": 0.0,
             "tall_50m": 0, "by_district": defaultdict(int)}

    for geom_b, h, src, lon, lat in rows:
        try:
            g = wkb.loads(bytes(geom_b))
        except Exception:
            stats["skipped"] += 1
            continue
        parts = list(g.geoms) if isinstance(g, MultiPolygon) else [g] if isinstance(g, Polygon) else []
        ix, iy = tile_of(lon, lat)
        ox, oy = LON0 + ix * TILE, LAT0 + iy * TILE
        s = SOURCE_CODE.get(src, 2)
        d = district_of(districts, lon, lat)
        wrote = False
        for p in parts:
            ring = encode_ring(p.simplify(SIMPLIFY, preserve_topology=True).exterior.coords, ox, oy)
            if ring:
                tiles[(ix, iy)].append([round(float(h), 1), s, d, *ring])
                stats["parts"] += 1
                wrote = True
        if not wrote:
            stats["skipped"] += 1
            continue
        stats["buildings"] += 1
        stats["by_source"][s] += 1
        stats["by_district"][d] += 1
        stats["max_m"] = max(stats["max_m"], float(h))
        stats["tall_50m"] += float(h) >= 50

    (out_dir / "t").mkdir(parents=True, exist_ok=True)
    for old in (out_dir / "t").glob("*.json"):
        old.unlink()
    total_bytes = 0
    for (ix, iy), recs in tiles.items():
        body = json.dumps({"o": [round(LON0 + ix * TILE, 6), round(LAT0 + iy * TILE, 6)], "b": recs},
                          separators=(",", ":"))
        (out_dir / "t" / f"{ix}_{iy}.json").write_text(body)
        total_bytes += len(body)

    stats["by_district"] = dict(sorted(stats["by_district"].items()))
    index = {
        "version": 1,
        "origin": [LON0, LAT0],
        "tile": TILE,
        "q": Q,
        "tiles": {f"{ix}_{iy}": len(r) for (ix, iy), r in sorted(tiles.items())},
        "stats": {**stats, "bytes": total_bytes},
        "sources": ["Overture height", "Floors x 3.5 m", "Default by class"],
        "attribution": ATTRIBUTION,
    }
    (out_dir / "index.json").write_text(json.dumps(index, indent=1))
    return index


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_dir", type=Path, default=IN_DIR)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--districts", type=Path, help="council districts GeoJSON (optional)")
    ap.add_argument("--district-prop", default="district", help="property holding the district number")
    a = ap.parse_args()
    idx = export(read_rows(a.in_dir), a.out, load_districts(a.districts, a.district_prop))
    s = idx["stats"]
    print(f"{s['buildings']:,} buildings in {len(idx['tiles'])} tiles, {s['bytes'] / 1e6:.1f} MB "
          f"(lidar {s['by_source'][0]:,}, floors {s['by_source'][1]:,}, default {s['by_source'][2]:,}, "
          f"max {s['max_m']} m) -> {a.out}")


if __name__ == "__main__":
    main()
