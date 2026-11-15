import json

import pyarrow as pa
import pyarrow.parquet as pq
from shapely.geometry import MultiPolygon, Polygon, box

from data.buildings import export_tiles as et
from data.buildings.athena_build import statements


def _rows():
    rencen = box(-83.0400, 42.3290, -83.0390, 42.3298)            # downtown, tall
    house = Polygon([(-83.1500, 42.4000), (-83.14988, 42.4000), (-83.14988, 42.40009),
                     (-83.1500, 42.40009)])
    duo = MultiPolygon([box(-83.10, 42.35, -83.0999, 42.3501), box(-83.0998, 42.35, -83.0997, 42.3501)])
    return [
        (rencen.wkb, 221.5, "overture_height", -83.0395, 42.3294),
        (house.wkb, 7.0, "default_house", -83.14994, 42.400045),
        (duo.wkb, 10.5, "overture_floors", -83.09985, 42.35005),
        (b"not wkb", 5.0, "overture_height", -83.0, 42.3),
    ]


def test_ring_roundtrip():
    ox, oy = -83.04, 42.32
    ring = [(-83.0400, 42.3290), (-83.0390, 42.3290), (-83.0390, 42.3298), (-83.0400, 42.3298), (-83.0400, 42.3290)]
    enc = et.encode_ring(ring, ox, oy)
    assert len(enc) == 8                                   # 4 points, closing point dropped
    for (a, b), (c, d) in zip(et.decode_ring(enc, ox, oy), ring):
        assert abs(a - c) < et.Q and abs(b - d) < et.Q


def test_degenerate_ring_dropped():
    assert et.encode_ring([(-83.0, 42.3), (-83.0, 42.3), (-83.0, 42.3)], -83.0, 42.3) == []


def test_export(tmp_path):
    idx = et.export(_rows(), tmp_path)
    s = idx["stats"]
    assert s["buildings"] == 3 and s["parts"] == 4 and s["skipped"] == 1
    assert s["by_source"] == [1, 1, 1]
    assert s["max_m"] == 221.5 and s["tall_50m"] == 1
    assert sum(idx["tiles"].values()) == 4
    key = "%d_%d" % et.tile_of(-83.0395, 42.3294)
    tile = json.loads((tmp_path / "t" / f"{key}.json").read_text())
    h, src, d, *ring = tile["b"][0]
    assert (h, src, d) == (221.5, 0, 0)
    xs = [p[0] for p in et.decode_ring(ring, *tile["o"])]
    assert abs(min(xs) - -83.0400) < 2e-5 and abs(max(xs) - -83.0390) < 2e-5


def test_districts(tmp_path):
    gj = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"district": "District 6"},
         "geometry": box(-83.05, 42.32, -83.03, 42.34).__geo_interface__}]}
    p = tmp_path / "d.geojson"
    p.write_text(json.dumps(gj))
    idx = et.export(_rows(), tmp_path / "out", et.load_districts(p, "district"))
    assert idx["stats"]["by_district"] == {0: 2, 6: 1}


def test_read_rows(tmp_path):
    rows = _rows()[:2]
    cols = list(zip(*rows))
    pq.write_table(pa.table({"geometry": list(cols[0]), "height_m": list(cols[1]),
                             "height_source": list(cols[2]), "lon": list(cols[3]), "lat": list(cols[4])}),
                   tmp_path / "x.parquet")
    assert len(list(et.read_rows(tmp_path))) == 2


def test_sql_statements():
    from pathlib import Path
    sql = (Path(et.__file__).parent / "sql" / "03_clip.sql").read_text()
    st = statements(sql, bucket="b", run="r")
    assert len(st) == 2 and st[0].startswith("DROP")
    assert "s3://b/detroit_buildings_r/" in st[1] and "{" not in st[1]
