"""Turn the clipped Detroit buildings Parquet into Mapbox Vector Tiles for the 3D map.

    python -m data.buildings.export_mvt --districts web/prototype/geo/districts.geojson

Input : data/processed/buildings/*.parquet            (from athena_build.py)
Output: web/prototype/tiles/{z}/{x}/{y}.pbf  z10-14 (overzoomed past 14; z14 grid is ~0.45 m)    (layer "buildings")
        web/prototype/tiles/index.json                 (zooms, bounds, counts)
        web/prototype/geo/residents_demo.geojson       (demo resident dots, ~1 in 120 homes)

Why vector tiles: MapLibre draws them with its native `fill-extrusion` layer. Triangulation runs in
web workers (not the main thread), only tiles in view load, and low zooms carry only big/tall
buildings, so the zoomed-out city view stays light.

Feature properties: h = height m (1 decimal), s = height source (0 Overture/lidar, 1 floors x 3.5 m,
2 default by class), d = council district (0 if none / no district file).
"""
from __future__ import annotations

import argparse
import json
import math
import random
import shutil
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
IN_DIR = ROOT / "data" / "processed" / "buildings"
OUT_DIR = ROOT / "web" / "prototype" / "tiles"
RESIDENTS_OUT = ROOT / "web" / "prototype" / "geo" / "residents_demo.geojson"

EXTENT, BUFFER = 4096, 64
R = 6378137.0
WORLD = 2 * math.pi * R
MINZOOM, MAXZOOM = 10, 14
# keep a building at zoom z if footprint >= area m2 OR height >= h  (None = keep all)
KEEP = {10: (2000, 25), 11: (800, 12), 12: (150, 8), 13: (80, 6), 14: None}
SIMPLIFY_PX = {10: 2.0, 11: 2.0, 12: 1.5, 13: 1.5, 14: 0.0}   # Douglas-Peucker tolerance in tile pixels (of 4096)
SOURCE_CODE = {"overture_height": 0, "overture_floors": 1}
ATTRIBUTION = "Buildings: Overture Maps Foundation (ODbL), incl. OpenStreetMap contributors, Microsoft, Google"


def merc(lon, lat):
    x = np.radians(lon) * R
    y = np.log(np.tan(np.pi / 4 + np.radians(lat) / 2)) * R
    return x, y


def tile_range(minx, miny, maxx, maxy, z):
    """Mercator-metre bbox -> inclusive tile x/y range at zoom z (y counted from the top)."""
    size = WORLD / 2 ** z
    x0 = int((minx + WORLD / 2) // size)
    x1 = int((maxx + WORLD / 2) // size)
    y0 = int((WORLD / 2 - maxy) // size)
    y1 = int((WORLD / 2 - miny) // size)
    return x0, x1, y0, y1


def keep_at(z: int, area_m2: float, h: float) -> bool:
    rule = KEEP[z]
    return rule is None or area_m2 >= rule[0] or h >= rule[1]


def load_districts(path: Path | None, prop: str):
    if not path:
        return None
    from shapely.geometry import shape
    from shapely.strtree import STRtree

    feats = json.loads(Path(path).read_text())["features"]
    geoms = [shape(f["geometry"]) for f in feats]
    ids = [int(str(f["properties"][prop]).strip().split()[-1]) for f in feats]
    return STRtree(geoms), geoms, ids


def districts_for(index, lons, lats) -> np.ndarray:
    if index is None:
        return np.zeros(len(lons), dtype=int)
    import shapely

    tree, geoms, ids = index
    pts = shapely.points(lons, lats)
    out = np.zeros(len(lons), dtype=int)
    pi, gi = tree.query(pts, predicate="within")
    out[pi] = np.array(ids)[gi]
    return out


def read_table(in_dir: Path):
    import pyarrow as pa
    import pyarrow.parquet as pq

    files = sorted(in_dir.glob("*.parquet"))
    if not files:
        raise SystemExit(f"no Parquet in {in_dir}; run python -m data.buildings.athena_build first")
    cols = ["geometry", "height_m", "height_source", "lon", "lat"]
    return pa.concat_tables(pq.read_table(f, columns=cols) for f in files)


def build_features(table, districts=None):
    """Parquet table -> (mercator polygons, heights, sources, districts, lon, lat, area m2)."""
    import shapely

    geoms = shapely.from_wkb(table.column("geometry").to_pylist(), on_invalid="ignore")
    lon = np.asarray(table.column("lon").to_pylist(), dtype=float)
    lat = np.asarray(table.column("lat").to_pylist(), dtype=float)
    h = np.round(np.asarray(table.column("height_m").to_pylist(), dtype=float), 1)
    s = np.array([SOURCE_CODE.get(v, 2) for v in table.column("height_source").to_pylist()])
    ok = ~shapely.is_missing(geoms) & np.isin(shapely.get_type_id(geoms), [3, 6])  # Polygon, MultiPolygon
    geoms, lon, lat, h, s = geoms[ok], lon[ok], lat[ok], h[ok], s[ok]
    mg = shapely.transform(geoms, lambda c: np.column_stack(merc(c[:, 0], c[:, 1])))
    # mercator area -> true area: scale by cos(lat)^2
    area = shapely.area(mg) * np.cos(np.radians(lat)) ** 2
    d = districts_for(districts, lon, lat)
    return mg, h, s, d, lon, lat, area


def encode_tile(z, tx, ty, items, mg, h, s, d):
    import mapbox_vector_tile
    import shapely
    from shapely.geometry import box

    size = WORLD / 2 ** z
    x0 = tx * size - WORLD / 2
    ytop = WORLD / 2 - ty * size
    k = EXTENT / size
    sub = shapely.transform(mg[items], lambda c: np.column_stack(((c[:, 0] - x0) * k, (ytop - c[:, 1]) * k)))
    clip = box(-BUFFER, -BUFFER, EXTENT + BUFFER, EXTENT + BUFFER)
    b = shapely.bounds(sub)
    inside = (b[:, 0] >= -BUFFER) & (b[:, 1] >= -BUFFER) & (b[:, 2] <= EXTENT + BUFFER) & (b[:, 3] <= EXTENT + BUFFER)
    tol = SIMPLIFY_PX.get(z, 0.0)
    feats = []
    for j, i in enumerate(items):
        g = sub[j] if inside[j] else sub[j].intersection(clip)
        if tol:
            g = g.simplify(tol, preserve_topology=True)
        if g.is_empty or g.area < 0.5:
            continue
        feats.append({"geometry": g, "properties": {"h": float(h[i]), "s": int(s[i]), "d": int(d[i])}})
    if not feats:
        return None
    return mapbox_vector_tile.encode([{"name": "buildings", "features": feats}],
                                     default_options={"y_coord_down": True, "extents": EXTENT})


def export(table, out_dir: Path, districts=None, residents_out: Path | None = None,
           minzoom=MINZOOM, maxzoom=MAXZOOM) -> dict:
    import shapely

    mg, h, s, d, lon, lat, area = build_features(table, districts)
    bounds = shapely.bounds(mg)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    tiles_per_zoom, bytes_total, feats_per_zoom = {}, 0, {}
    for z in range(minzoom, maxzoom + 1):
        groups: dict[tuple[int, int], list[int]] = defaultdict(list)
        keep = [i for i in range(len(mg)) if keep_at(z, area[i], h[i])]
        for i in keep:
            x0, x1, y0, y1 = tile_range(*bounds[i], z)
            for tx in range(x0, x1 + 1):
                for ty in range(y0, y1 + 1):
                    groups[(tx, ty)].append(i)
        n = 0
        for (tx, ty), items in groups.items():
            data = encode_tile(z, tx, ty, items, mg, h, s, d)
            if data is None:
                continue
            p = out_dir / str(z) / str(tx) / f"{ty}.pbf"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            n += 1
            bytes_total += len(data)
        tiles_per_zoom[z], feats_per_zoom[z] = n, len(keep)

    stats = {"buildings": int(len(mg)), "by_source": [int((s == k).sum()) for k in range(3)],
             "max_m": float(h.max()) if len(h) else 0.0, "tall_50m": int((h >= 50).sum()),
             "by_district": {int(k): int(v) for k, v in zip(*np.unique(d, return_counts=True))},
             "tiles": tiles_per_zoom, "features_per_zoom": feats_per_zoom, "bytes": bytes_total}
    index = {"version": 2, "format": "mvt", "layer": "buildings", "minzoom": minzoom, "maxzoom": maxzoom,
             "bounds": [round(float(lon.min()), 5), round(float(lat.min()), 5), round(float(lon.max()), 5), round(float(lat.max()), 5)],
             "stats": stats, "sources": ["Overture height", "Floors x 3.5 m", "Default by class"], "attribution": ATTRIBUTION}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.json").write_text(json.dumps(index, indent=1))

    if residents_out:                       # demo dots on rooftops of homes; the real ones come from a run
        rng = random.Random(1114)
        homes = [i for i in range(len(mg)) if d[i] and h[i] < 12]
        pick = sorted(rng.sample(homes, min(len(homes), max(1, len(homes) // 120))))
        fc = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {"d": int(d[i]), "u": round(rng.random(), 3), "h": float(h[i])},
             "geometry": {"type": "Point", "coordinates": [round(float(lon[i]), 6), round(float(lat[i]), 6)]}} for i in pick]}
        residents_out.parent.mkdir(parents=True, exist_ok=True)
        residents_out.write_text(json.dumps(fc, separators=(",", ":")))
        index["residents_demo"] = len(pick)
    return index


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_dir", type=Path, default=IN_DIR)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--districts", type=Path, help="council districts GeoJSON (optional)")
    ap.add_argument("--district-prop", default="district", help="property holding the district number")
    ap.add_argument("--no-residents", action="store_true", help="skip geo/residents_demo.geojson")
    a = ap.parse_args()
    idx = export(read_table(a.in_dir), a.out, load_districts(a.districts, a.district_prop),
                 None if a.no_residents else RESIDENTS_OUT)
    st = idx["stats"]
    print(f"{st['buildings']:,} buildings -> {sum(st['tiles'].values())} tiles z{idx['minzoom']}-{idx['maxzoom']}, "
          f"{st['bytes'] / 1e6:.1f} MB; per zoom {st['tiles']}; residents demo {idx.get('residents_demo', 0)}")


if __name__ == "__main__":
    main()
