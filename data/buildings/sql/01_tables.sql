-- Run in Athena, region us-west-2 (same region as the Overture bucket).
-- {release} is filled in by athena_build.py (default 2026-10-21.0).
CREATE DATABASE IF NOT EXISTS overture;

CREATE EXTERNAL TABLE IF NOT EXISTS overture.buildings (
  id string, geometry binary,
  bbox struct<xmin:double,xmax:double,ymin:double,ymax:double>,
  height double, num_floors int, class string, subtype string
) PARTITIONED BY (type string) STORED AS PARQUET
LOCATION 's3://overturemaps-us-west-2/release/{release}/theme=buildings/';

MSCK REPAIR TABLE overture.buildings;

CREATE EXTERNAL TABLE IF NOT EXISTS overture.division_areas (
  id string, geometry binary, subtype string, class string,
  names struct<primary:string>, country string, region string
) PARTITIONED BY (type string) STORED AS PARQUET
LOCATION 's3://overturemaps-us-west-2/release/{release}/theme=divisions/';

MSCK REPAIR TABLE overture.division_areas;
