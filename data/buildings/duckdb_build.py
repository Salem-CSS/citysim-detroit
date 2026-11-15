"""Build the Detroit buildings table on a laptop with DuckDB (no AWS account needed).

Same result as athena_build.py + sql/02_bbox.sql + sql/03_clip.sql, for accounts that cannot run
Athena in us-west-2. Reads the public Overture bucket anonymously.

    python -m data.buildings.duckdb_build                      # release from OVERTURE_RELEASE or the default below
    python -m data.buildings.duckdb_build --release 2026-10-21.0

Output: data/processed/buildings/detroit_buildings.parquet with the columns export_mvt.py reads
(building_id, geometry as WKB, building_class, floors, height_m, height_source, lon, lat).
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "processed" / "buildings" / "detroit_buildings.parquet"
DEFAULT_RELEASE = "2026-10-21.0"   # the release athena_build.py was run on (LOG.md, Nov 14)

SQL = """
COPY (
  WITH d AS (
    SELECT geometry AS g
    FROM read_parquet('s3://overturemaps-us-west-2/release/{release}/theme=divisions/type=division_area/*', hive_partitioning=1)
    WHERE subtype = 'locality' AND class = 'land' AND region = 'US-MI' AND names."primary" = 'Detroit'
  ), b AS (
    SELECT id, geometry, height, num_floors, class, ST_Centroid(geometry) AS c
    FROM read_parquet('s3://overturemaps-us-west-2/release/{release}/theme=buildings/type=building/*', hive_partitioning=1)
    WHERE bbox.xmin > -83.29 AND bbox.xmax < -82.91 AND bbox.ymin > 42.25 AND bbox.ymax < 42.46
  )
  SELECT
    b.id AS building_id,
    ST_AsWKB(b.geometry) AS geometry,
    b.class AS building_class,
    b.num_floors AS floors,
    ROUND(COALESCE(b.height, b.num_floors * 3.5,
      CASE WHEN b.class IN ('house','detached','residential','semidetached_house') THEN 7.0
           WHEN b.class IN ('garage','garages','shed') THEN 3.5
           WHEN b.class = 'apartments' THEN 12.0
           ELSE 6.0 END), 1) AS height_m,
    CASE WHEN b.height IS NOT NULL THEN 'overture_height'
         WHEN b.num_floors IS NOT NULL THEN 'overture_floors'
         ELSE concat('default_', COALESCE(b.class, 'other')) END AS height_source,
    ST_X(b.c) AS lon,
    ST_Y(b.c) AS lat
  FROM b, d
  WHERE ST_Contains(d.g, b.c)
) TO '{out}' (FORMAT PARQUET);
"""


def main() -> None:
    import duckdb

    ap = argparse.ArgumentParser()
    ap.add_argument("--release", default=os.environ.get("OVERTURE_RELEASE", DEFAULT_RELEASE))
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")
    con.execute("SET s3_region='us-west-2'; SET s3_access_key_id=''; SET s3_secret_access_key='';")
    n_city = con.execute(SQL.split("), b AS")[0].replace("COPY (\n  WITH d AS (", "SELECT count(*) FROM (").format(release=a.release) + ")").fetchone()[0]
    if n_city != 1:
        raise SystemExit(f"expected exactly one Detroit city polygon in release {a.release}, found {n_city}")
    con.execute(SQL.format(release=a.release, out=a.out.as_posix()))
    rows = con.execute(f"""SELECT count(*), sum(height_source='overture_height'), sum(height_source='overture_floors'),
                           median(height_m), max(height_m) FROM read_parquet('{a.out.as_posix()}')""").fetchone()
    print(f"release {a.release}: {rows[0]:,} buildings; {rows[1]:,} measured height, {rows[2]:,} from floors, "
          f"{rows[0]-rows[1]-rows[2]:,} defaulted; median {rows[3]} m, max {rows[4]} m -> {a.out}")


if __name__ == "__main__":
    main()
