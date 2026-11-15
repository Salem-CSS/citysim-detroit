-- Clip to Detroit city limits (Overture locality polygon; drops Hamtramck,
-- Highland Park, Dearborn, Windsor) and fill in a height for every building.
-- Height order: Overture height (mostly lidar) > floors x 3.5 m > default by class.
DROP TABLE IF EXISTS overture.detroit_buildings;

CREATE TABLE overture.detroit_buildings
WITH (format = 'PARQUET', external_location = 's3://{bucket}/detroit_buildings_{run}/') AS
WITH d AS (
  SELECT ST_GeomFromBinary(geometry) AS g FROM overture.division_areas
  WHERE type = 'division_area' AND subtype = 'locality' AND class = 'land'
    AND region = 'US-MI' AND names.primary = 'Detroit'
), b AS (
  SELECT *, ST_Centroid(ST_GeomFromBinary(geometry)) AS c FROM overture.detroit_bbox_buildings
)
SELECT
  b.id AS building_id,
  b.geometry,
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
FROM b CROSS JOIN d
WHERE ST_Contains(d.g, b.c);
