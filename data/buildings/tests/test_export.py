import json
from pathlib import Path

import mapbox_vector_tile
import pyarrow as pa
from shapely.geometry import MultiPolygon, Polygon, box

from data.buildings import export_mvt as em
from data.buildings.athena_build import statements


def _table():
    rencen = box(-83.0400, 42.3290, -83.0390, 42.3298)                     # big + tall: kept at every zoom
    house = box(-83.15000, 42.40000, -83.14988, 42.40009)                   # ~100 m2, 7 m: only z13+
    duo = MultiPolygon([box(-83.10, 42.35, -83.0999, 42.3501), box(-83.0998, 42.35, -83.0997, 42.3501)])
    rows = [(rencen.wkb, 221.5, "overture_height", -83.0395, 42.3294),
            (house.wkb, 7.0, "default_house", -83.14994, 42.400045),
            (duo.wkb, 10.5, "overture_floors", -83.09985, 42.35005),
            (b"not wkb", 5.0, "overture_height", -83.0, 42.3)]
    cols = list(zip(*rows))
    return pa.table({"geometry": list(cols[0]), "height_m": list(cols[1]), "height_source": list(cols[2]),
                     "lon": list(cols[3]), "lat": list(cols[4])})


def _districts(tmp_path):
    gj = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"district": "District 6"},
         "geometry": box(-83.05, 42.32, -83.03, 42.34).__geo_interface__}]}
    p = tmp_path / "d.geojson"
    p.write_text(json.dumps(gj))
    return em.load_districts(p, "district")


def _decode(path):
    return mapbox_vector_tile.decode(path.read_bytes())["buildings"]["features"]


def test_tile_range_known_tile():
    x, y = em.merc(-83.0395, 42.3294)
    x0, x1, y0, y1 = em.tile_range(float(x), float(y), float(x), float(y), 14)
    assert (x0, y0) == (x1, y1) == (4412, 6061)        # Renaissance Center at z14


def test_keep_rules():
    assert em.keep_at(10, 5000, 5) and em.keep_at(10, 10, 40) and not em.keep_at(10, 100, 7)
    assert em.keep_at(14, 1, 1)


def test_export(tmp_path):
    out, res = tmp_path / "tiles", tmp_path / "res.geojson"
    idx = em.export(_table(), out, _districts(tmp_path), res)
    st = idx["stats"]
    assert st["buildings"] == 3 and st["by_source"] == [1, 1, 1] and st["max_m"] == 221.5
    assert st["by_district"] == {0: 2, 6: 1}
    assert st["features_per_zoom"][10] == 1 and st["features_per_zoom"][14] == 3
    feats = _decode(out / "14" / "4412" / "6061.pbf")
    assert feats[0]["properties"] == {"h": 221.5, "s": 0, "d": 6}
    assert json.loads((out / "index.json").read_text())["layer"] == "buildings"
    assert res.exists()


def test_sql_statements():
    sql = (Path(em.__file__).parent / "sql" / "03_clip.sql").read_text()
    st = statements(sql, bucket="b", run="r")
    assert len(st) == 2 and st[0].startswith("DROP")
    assert "s3://b/detroit_buildings_r/" in st[1] and "{" not in st[1]
