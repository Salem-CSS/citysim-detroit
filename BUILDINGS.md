# Buildings: real Detroit outlines and heights

Instructions for building the 3D building layer. Written so a person or a coding assistant can follow it top to bottom. Goal: every building in Detroit with its real outline and height, tagged with council district and parcel, ready for deck.gl.

**Prerequisite:** [DATA_SETUP.md](DATA_SETUP.md) is done (repo cloned, venv active, `.env` filled, `data/raw/` downloaded and synced to S3). This guide uses two of those files: the Detroit city boundary (`data/raw/census/tiger/tl_*_26_place.zip`) and the council districts (`data/raw/detroit/council_districts_2026.geojson`).

**Time:** about 45 minutes, mostly downloads.

**Status (11-14 19:30 ET): the fast path below is done and is the default.** The longer guide after it (SEMCOG merge, parcel/block tags) is optional polish.

## Fast path (done, use this)

Overture alone is enough: inside Detroit city limits it has **335,338 buildings, 95% with a measured (lidar) height**. Everything is scripted:

```bash
pip install boto3 pyarrow shapely
python -m data.buildings.athena_build --bucket citysim-athena-574246332084-usw2   # runs data/buildings/sql/01-04 in Athena (us-west-2), downloads Parquet
#   or, if the tables already exist:  ... --download-only
python -m data.buildings.export_tiles [--districts data/raw/detroit/council_districts_2026.geojson]
#   writes web/prototype/buildings/index.json + t/*.json
open web/prototype/map3d.html   # serve the folder: python -m http.server -d web/prototype
```

| Step | File | What it does |
| --- | --- | --- |
| Tables | `data/buildings/sql/01_tables.sql` | External tables over Overture buildings + divisions (bbox fields are `double`) |
| Box cut | `sql/02_bbox.sql` | 607,306 buildings in a box around Detroit (~93 MB scanned) |
| Clip + heights | `sql/03_clip.sql` | Keep centroids inside the Overture `Detroit` locality polygon (drops Hamtramck, Highland Park, Dearborn, Windsor). Height = Overture height, else floors × 3.5 m, else default by class |
| Check | `sql/04_check.sql` | Expected numbers below |
| Tiles | `data/buildings/export_tiles.py` | 0.01° grid tiles, ~1 m quantized, delta-encoded JSON; optional district tag |
| Map | `web/prototype/map3d.html` | MapLibre + deck.gl extruded buildings, loads only visible tiles, color by height or height source |

Results (Overture release 2026-10-21.0, already built in account 574246332084, table `overture.detroit_buildings`):

| | Count |
| --- | --- |
| Buildings in city limits | 335,338 |
| Measured height (Overture/lidar) | 318,480 (95%) |
| Height from floors | 94 |
| Default height by class | 16,764 |
| Median / max height | 5.1 m / 221.5 m (Renaissance Center) |
| 50 m or taller | 105 |

Overture counts fewer buildings than the city's 419,882 figure in SCOPE.md, mostly garages and sheds missing from the footprint sources. Fine for the map; add SEMCOG (section 4) if you need them.

Tiles are generated data and gitignored (`web/prototype/buildings/`). To show them on the deployed site, either commit them (decision pending, see LOG.md) or host them on S3/CloudFront and open `map3d.html?src=https://<host>/buildings/`.

---

## 0. The plan in one paragraph

Use **Overture Maps buildings** as the base layer: it's free, hosted on AWS as GeoParquet, and many buildings carry a lidar-derived `height`. Fill gaps with **SEMCOG building footprints** (the Southeast Michigan regional planning agency's inventory), then fall back to a sensible default by building type. Clip to Detroit, tag each building with its council district, parcel and census block, and write one file per district for the web map. Detroit is mostly low-rise (SCOPE.md: 397,744 of 419,882 buildings under 2 stories), so the important thing is getting houses right, and both sources cover houses.

```
Overture (S3, us-west-2) ──┐
                           ├─► merge + height fill ─► clip to Detroit ─► tag district / parcel / block ─► per-district files ─► S3 ─► deck.gl
SEMCOG footprints (REST) ──┘
```

Output files:

```
data/processed/buildings/detroit_buildings.parquet        all Detroit buildings, GeoParquet (EPSG:4326)
data/processed/buildings/district_{1..7}.geojson          one per district, for deck.gl GeoJsonLayer
data/processed/buildings/manifest.json                    counts, height sources, release used
```

Each building row has:

| Field | Type | Meaning |
| --- | --- | --- |
| `building_id` | string | Overture id, or `semcog-<BUILDING_ID>` for SEMCOG-only buildings |
| `height_m` | float | Height in meters used for extrusion |
| `height_source` | string | `overture_height`, `overture_floors`, `semcog_stories`, or `default_<class>` |
| `floors` | int or null | Number of floors if known |
| `building_class` | string or null | e.g. `house`, `apartments`, `commercial` |
| `district` | int | Council district 1–7 (2026 map) |
| `parcel_id` | string or null | Detroit parcel number (from parcels layer) |
| `block_geoid` | string or null | 2020 census block (links to AI residents) |
| `geometry` | polygon | Footprint |

---

## 1. Install extra packages

```bash
pip install duckdb>=1.1 geopandas pyogrio shapely pyarrow requests
```

(Add `duckdb>=1.1` to `data/requirements.txt` if it isn't there.)

## 2. Find the current Overture release

Overture publishes a new release about once a month and **removes old ones**, so never hardcode an old release.

```bash
aws s3 ls --no-sign-request s3://overturemaps-us-west-2/release/
```

Pick the newest folder (format `YYYY-MM-DD.N`, e.g. `2026-10-21.0`) and put it in `.env`:

```
OVERTURE_RELEASE=2026-10-21.0
```

Buildings live at:

```
s3://overturemaps-us-west-2/release/$OVERTURE_RELEASE/theme=buildings/type=building/*
```

## 3. Extract Detroit buildings from Overture

Two options. **Do Option A** (it's the AWS story for judges). Use Option B if Athena gives you trouble; it gives the same result.

Detroit's bounding box (slightly padded), used to pre-filter before the exact clip:

```
west -83.29, east -82.91, south 42.25, north 42.46
```

### Option A: Amazon Athena (reads Overture in place on S3)

Overture's bucket is in **us-west-2**, so Athena must run in **us-west-2**.

1. Create a results bucket in us-west-2 (Athena needs one in the same region):

   ```bash
   ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
   aws s3 mb s3://citysim-athena-$ACCOUNT-usw2 --region us-west-2
   ```

2. Open the Athena console, switch region to **US West (Oregon)**, set the query result location to `s3://citysim-athena-<ACCOUNT>-usw2/results/`.

3. Create a database and the Overture table (replace `RELEASE`):

   ```sql
   CREATE DATABASE IF NOT EXISTS overture;

   CREATE EXTERNAL TABLE IF NOT EXISTS overture.buildings (
     id          string,
     geometry    binary,
     bbox        struct<xmin:double, xmax:double, ymin:double, ymax:double>,   -- must be double, float gives HIVE_BAD_DATA
     height      double,
     num_floors  int,
     class       string,
     subtype     string,
     sources     array<struct<dataset:string, record_id:string>>
   )
   PARTITIONED BY (type string)
   STORED AS PARQUET
   LOCATION 's3://overturemaps-us-west-2/release/RELEASE/theme=buildings/';

   MSCK REPAIR TABLE overture.buildings;
   ```

   Parquet columns are matched by name, so listing only the columns we need is fine. If a column errors, run `SELECT * FROM overture.buildings LIMIT 5` to see the real schema and adjust.

4. Write Detroit's buildings out as Parquet (CTAS):

   ```sql
   CREATE TABLE overture.detroit_buildings
   WITH (format = 'PARQUET', external_location = 's3://citysim-athena-ACCOUNT-usw2/detroit_buildings/')
   AS
   SELECT id, geometry, height, num_floors, class, subtype,
          sources[1].dataset AS primary_source
   FROM overture.buildings
   WHERE type = 'building'
     AND bbox.xmin > -83.29 AND bbox.xmax < -82.91
     AND bbox.ymin > 42.25  AND bbox.ymax < 42.46;
   ```

5. Copy the result down:

   ```bash
   aws s3 sync s3://citysim-athena-$ACCOUNT-usw2/detroit_buildings/ data/raw/buildings/overture/
   ```

Expect a few hundred thousand rows. Note the row count for the manifest.

### Option B: DuckDB (no AWS account needed, reads the public bucket directly)

```python
# data/buildings/overture_duckdb.py
import os, duckdb
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
REL = os.environ["OVERTURE_RELEASE"]
out = Path("data/raw/buildings/overture"); out.mkdir(parents=True, exist_ok=True)

con = duckdb.connect()
con.sql("INSTALL spatial; LOAD spatial; INSTALL httpfs; LOAD httpfs; SET s3_region='us-west-2';")
con.sql(f"""
COPY (
  SELECT id, geometry, height, num_floors, class, subtype,
         sources[1].dataset AS primary_source
  FROM read_parquet('s3://overturemaps-us-west-2/release/{REL}/theme=buildings/type=building/*', hive_partitioning=1)
  WHERE bbox.xmin > -83.29 AND bbox.xmax < -82.91
    AND bbox.ymin > 42.25  AND bbox.ymax < 42.46
) TO '{out}/detroit_buildings.parquet' (FORMAT PARQUET);
""")
print(con.sql(f"SELECT count(*), count(height), count(num_floors) FROM '{out}/detroit_buildings.parquet'").fetchall())
```

Run with `python data/buildings/overture_duckdb.py`. It scans the bbox column remotely, so it takes several minutes.

## 4. Download SEMCOG footprints for Detroit

SEMCOG publishes footprints on its ArcGIS server. Find the newest layer:

```bash
curl -s "https://gis.semcog.org/server/rest/services/Hosted?f=pjson" | python -m json.tool | grep -i building
```

Look for `Building_Footprints__2024` first. If it isn't listed, use `Building_Footprints__2020`, which is confirmed to exist at:

```
https://gis.semcog.org/server/rest/services/Hosted/Building_Footprints__2020/FeatureServer/60
```

Open the layer URL with `?f=pjson` and check the `fields` list. Things to know (from SEMCOG's documentation for the 2020 layer):

- Each footprint has `BUILDING_ID`, `PARCEL_ID`, `BUILD_TYPE` and `SOURCE`.
- **Filter `DEMOLISHED IS NULL`** to keep only standing buildings.
- SEMCOG keeps most building attributes on a separate **Building Points** layer (`https://gis.semcog.org/server/rest/services/Hosted/Building_Points/FeatureServer`); footprints carry only a subset. If the footprint layer has no stories or height field, pull stories from Building Points and join on `BUILDING_ID`.
- The server returns at most 2,000 features per request, so page with `resultOffset`.

```python
# data/buildings/semcog.py
import json, requests, geopandas as gpd
from pathlib import Path

LAYER = "https://gis.semcog.org/server/rest/services/Hosted/Building_Footprints__2020/FeatureServer/60"  # swap to 2024 if found
BBOX = "-83.29,42.25,-82.91,42.46"
out = Path("data/raw/buildings/semcog"); out.mkdir(parents=True, exist_ok=True)

def page(offset):
    r = requests.get(f"{LAYER}/query", params={
        "where": "DEMOLISHED IS NULL", "geometry": BBOX, "geometryType": "esriGeometryEnvelope",
        "inSR": 4326, "spatialRel": "esriSpatialRelIntersects", "outFields": "*", "outSR": 4326,
        "f": "geojson", "resultOffset": offset, "resultRecordCount": 2000}, timeout=120)
    r.raise_for_status(); return r.json()["features"]

feats, off = [], 0
while True:
    batch = page(off); feats += batch; off += len(batch)
    print(off, end="\r")
    if len(batch) < 2000: break
gdf = gpd.GeoDataFrame.from_features(feats, crs=4326)
gdf.to_parquet(out / "semcog_footprints_detroit.parquet")
print("\nSEMCOG footprints:", len(gdf), "fields:", list(gdf.columns))
```

If the `where` clause errors, the field name differs: check the layer's `fields` and fix it. Then, if needed, fetch Building Points the same way and keep `BUILDING_ID` plus the stories/floors field.

## 5. Merge, fill heights, clip and tag

Height fill order (first one available wins). Record which one was used in `height_source`:

1. Overture `height` (meters, mostly from USGS lidar)
2. Overture `num_floors × 3.5 m`
3. SEMCOG stories `× 3.5 m` (matched by footprint centroid falling inside the SEMCOG polygon)
4. Default by class: house 7 m, garage/shed 3.5 m, apartments 12 m, commercial 6 m, anything else 6 m

Also add any SEMCOG footprint that has **no** Overture building overlapping it, as `semcog-<BUILDING_ID>`.

```python
# data/buildings/build.py
import json, glob, geopandas as gpd, pandas as pd
from pathlib import Path
from shapely import wkb

RAW, OUT = Path("data/raw"), Path("data/processed/buildings"); OUT.mkdir(parents=True, exist_ok=True)
FLOOR_M = 3.5
DEFAULTS = {"house": 7, "detached": 7, "garage": 3.5, "shed": 3.5, "apartments": 12, "commercial": 6, "retail": 6}

# --- load Overture
ov = pd.concat([pd.read_parquet(f) for f in glob.glob(str(RAW / "buildings/overture/*"))], ignore_index=True)
ov["geometry"] = ov["geometry"].apply(lambda b: wkb.loads(bytes(b)))
ov = gpd.GeoDataFrame(ov, geometry="geometry", crs=4326)

# --- clip to Detroit city limits (TIGER place 2622000)
place = gpd.read_file(glob.glob(str(RAW / "census/tiger/tl_*_26_place.zip"))[0])
detroit = place[place["GEOID"] == "2622000"].to_crs(4326).geometry.iloc[0]
ov = ov[ov.geometry.representative_point().within(detroit)].copy()

# --- SEMCOG stories via centroid-in-polygon
se = gpd.read_parquet(RAW / "buildings/semcog/semcog_footprints_detroit.parquet").to_crs(4326)
story_col = next((c for c in se.columns if c.lower() in ("stories", "num_stories", "floors", "story")), None)
pts = ov.copy(); pts["geometry"] = ov.geometry.representative_point()
j = gpd.sjoin(pts, se[[c for c in [story_col, "BUILDING_ID", "geometry"] if c]], how="left", predicate="within")
j = j[~j.index.duplicated()]

def fill(row):
    if pd.notna(row.get("height")) and row["height"] > 0: return row["height"], "overture_height"
    if pd.notna(row.get("num_floors")) and row["num_floors"] > 0: return row["num_floors"] * FLOOR_M, "overture_floors"
    if story_col and pd.notna(row.get(story_col)) and row[story_col] > 0: return row[story_col] * FLOOR_M, "semcog_stories"
    c = (row.get("class") or "other")
    return DEFAULTS.get(c, 6), f"default_{c}"

hs = j.apply(fill, axis=1, result_type="expand")
ov["height_m"], ov["height_source"] = hs[0].round(1), hs[1]
ov["floors"] = ov["num_floors"].fillna(j[story_col]) if story_col else ov["num_floors"]
ov = ov.rename(columns={"id": "building_id", "class": "building_class"})

# --- SEMCOG-only buildings (no Overture overlap)
hit = set(j["BUILDING_ID"].dropna())
extra = se[~se["BUILDING_ID"].isin(hit) & se.geometry.representative_point().within(detroit)].copy()
extra["building_id"] = "semcog-" + extra["BUILDING_ID"].astype(str)
extra["floors"] = extra[story_col] if story_col else None
extra["height_m"] = (extra["floors"].fillna(2) * FLOOR_M).round(1) if story_col else 7.0
extra["height_source"] = "semcog_stories" if story_col else "default_semcog"
extra["building_class"] = None
b = pd.concat([ov[["building_id", "height_m", "height_source", "floors", "building_class", "geometry"]],
               extra[["building_id", "height_m", "height_source", "floors", "building_class", "geometry"]]], ignore_index=True)
b = gpd.GeoDataFrame(b, geometry="geometry", crs=4326)

# --- tag district, parcel, census block (by representative point)
rp = b.copy(); rp["geometry"] = b.geometry.representative_point()
dist = gpd.read_file(RAW / "detroit/council_districts_2026.geojson").to_crs(4326)
dcol = next(c for c in dist.columns if "district" in c.lower())   # check the real column name once
b["district"] = gpd.sjoin(rp, dist[[dcol, "geometry"]], how="left", predicate="within").groupby(level=0)[dcol].first().astype("Int64")

par_files = glob.glob(str(RAW / "detroit/parcels.*"))
if par_files:
    par = gpd.read_file(par_files[0]).to_crs(4326)
    pcol = next(c for c in par.columns if c.lower() in ("parcel_number", "parcel_num", "parcelno", "parcel_id", "pnum"))
    b["parcel_id"] = gpd.sjoin(rp, par[[pcol, "geometry"]], how="left", predicate="within").groupby(level=0)[pcol].first()

blk = gpd.read_file(glob.glob(str(RAW / "census/tiger/tl_*_26_tabblock20.zip"))[0], where="COUNTYFP20 = '163'").to_crs(4326)
b["block_geoid"] = gpd.sjoin(rp, blk[["GEOID20", "geometry"]], how="left", predicate="within").groupby(level=0)["GEOID20"].first()

# --- write
b.to_parquet(OUT / "detroit_buildings.parquet")
for d in range(1, 8):
    sub = b[b["district"] == d].copy()
    sub["geometry"] = sub.geometry.simplify(0.000005, preserve_topology=True)   # ~0.5 m, shrinks files
    sub.to_file(OUT / f"district_{d}.geojson", driver="GeoJSON", COORDINATE_PRECISION=6)
manifest = {
    "total": int(len(b)),
    "by_district": {int(k): int(v) for k, v in b["district"].value_counts().sort_index().items()},
    "height_source": b["height_source"].value_counts().to_dict(),
    "overture_release": __import__("os").environ.get("OVERTURE_RELEASE"),
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
print(json.dumps(manifest, indent=2))
```

Run: `python data/buildings/build.py`. Column names in the Detroit layers (district, parcel) are guessed by pattern. If a `next(...)` call fails, print `dist.columns` / `par.columns` and set the name explicitly.

## 6. Check the result

Run these and post the answers in the team chat:

| Check | What good looks like |
| --- | --- |
| Total buildings | Hundreds of thousands. SCOPE.md cites ~420,000 (a 2016 count); fewer now is expected after demolitions |
| Every building has a district | `b["district"].isna().sum()` is near 0 (a few on the city edge are OK) |
| Height sources | `overture_height` + `overture_floors` + `semcog_stories` should be most rows; if `default_*` is over half, heights are mostly guesses: say so in the demo |
| Median height | Single digits of meters (houses) |
| Tallest building | The Renaissance Center, roughly 220 m |
| Michigan Central Station (Corktown) | Roughly 70 m |
| Spot check | Open `district_6.geojson` in https://geojson.io or QGIS and check Corktown looks right |

## 7. Upload

```bash
aws s3 sync data/processed/buildings s3://citysim-data-$ACCOUNT/processed/buildings/
```

The web app loads `district_{n}.geojson` for the districts the user picks. For the hackathon, serve them from S3 (or copy the 4 demo districts into `web/public/buildings/`). If a district file is over ~30 MB, convert to vector tiles later with tippecanoe; not needed for the demo.

## 8. Draw it in deck.gl

```ts
import { GeoJsonLayer } from '@deck.gl/layers';

new GeoJsonLayer({
  id: `buildings-d${district}`,
  data: `/buildings/district_${district}.geojson`,
  extruded: true,
  wireframe: false,
  getElevation: f => f.properties.height_m,
  getFillColor: f => colorForImpact(f.properties.building_id),   // neutral by default; tint buildings in the noise zone or near the site
  material: { ambient: 0.35, diffuse: 0.6, shininess: 20 },
  pickable: true,
  onClick: ({ object }) => openBlockCard(object.properties.block_geoid, object.properties.parcel_id),
  updateTriggers: { getFillColor: [runId] },
});
```

Match the colors in `web/prototype/index.html` (cream buildings on a green ground; residents as dots on top). Use `ScatterplotLayer` for residents and `PathLayer` for streets colored by load.

## Attribution (required)

Overture buildings include OpenStreetMap data under the ODbL. Show this in the map corner:

> © OpenStreetMap contributors, Overture Maps Foundation · Building footprints: SEMCOG

## Troubleshooting

| Problem | Fix |
| --- | --- |
| Athena: `HIVE_METASTORE_ERROR` or no rows | Region isn't us-west-2, or partitions not loaded: run `MSCK REPAIR TABLE overture.buildings` |
| Athena: path not found | The release was removed. List releases again (Step 2) and recreate the table |
| Athena: column type mismatch | Run `SELECT * ... LIMIT 5`, fix the column type in `CREATE EXTERNAL TABLE` |
| DuckDB: very slow | Normal for the first run (remote scan). Make sure the `bbox` filter is in the query |
| SEMCOG `where` error | Field name differs; read the layer's `fields` (`?f=pjson`) |
| SEMCOG returns 0 features | Wrong layer number or bbox; open `.../FeatureServer?f=pjson` and pick the polygon layer |
| District column not found | `print(dist.columns)` and set `dcol` by hand |
| GeoJSON too big for the browser | Raise the `simplify` tolerance, or drop buildings under 15 m² |

## Optional: photorealistic view (stretch)

Google Photorealistic 3D Tiles in deck.gl give a textured city with CitySim layers on top. They need a Google Maps API key and cost money per use, and Detroit coverage isn't confirmed. Skip unless everything else is done.
