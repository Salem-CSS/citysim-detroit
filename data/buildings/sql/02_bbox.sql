-- Cheap first cut: everything whose bbox falls in a box around Detroit (~93 MB scanned).
DROP TABLE IF EXISTS overture.detroit_bbox_buildings;

CREATE TABLE overture.detroit_bbox_buildings
WITH (format = 'PARQUET', external_location = 's3://{bucket}/detroit_bbox_buildings_{run}/') AS
SELECT id, geometry, height, num_floors, class
FROM overture.buildings
WHERE type = 'building'
  AND bbox.xmin > -83.29 AND bbox.xmax < -82.91
  AND bbox.ymin > 42.25  AND bbox.ymax < 42.46;
