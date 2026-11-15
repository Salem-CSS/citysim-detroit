-- Expect (release 2026-10-21.0): n 335,338 · overture_height 318,480 · floors 94 ·
-- defaulted 16,764 · median ~5.1 m · max 221.5 m (Renaissance Center) · 105 at 50 m+
SELECT count(*) AS n,
       count_if(height_source = 'overture_height') AS lidar,
       count_if(height_source = 'overture_floors') AS floors,
       count_if(height_source LIKE 'default%') AS defaulted,
       approx_percentile(height_m, 0.5) AS median_m,
       max(height_m) AS max_m,
       count_if(height_m >= 50) AS tall
FROM overture.detroit_buildings;
