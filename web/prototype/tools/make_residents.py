"""Write geo/residents.geojson: the simulated residents the map draws and the person card shows.

    python web/prototype/tools/make_residents.py

Source: data/processed/personas/district_{1..7}.json, built by data/personas/build.py from census data (PUMS
2020-2024 records fitted to each district's ACS tables, placed on a census block). The same files are in S3 under
personas/ and are what the backend asks. Each feature carries the persona_id the backend uses, so an answer from
GET /runs/{id}/answers can be matched to the figure on the map. No field here is invented or defaulted: a value the
persona file does not have is left out.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "data" / "processed" / "personas"
OUT = Path(__file__).resolve().parents[1] / "geo" / "residents.geojson"
FIELDS = ("age", "sex", "hh_income", "tenure", "years_in_home", "move_in_band", "hh_size", "children", "vehicles",
          "commute_mode", "commute_minutes", "employment", "education", "building_type")

features = []
for d in range(1, 8):
    for p in json.loads((SRC / f"district_{d}.json").read_text(encoding="utf-8")):
        props = {"persona_id": p["persona_id"], "d": p["district"]}
        props.update({k: p[k] for k in FIELDS if p.get(k) is not None})
        props["weight"] = round(p["weight"], 1)          # census weight: adults this resident stands for (district profiles)
        for line in p.get("context") or []:
            if line.startswith("Neighborhood: "):
                props["neighborhood"] = line[len("Neighborhood: "):]
        features.append({"type": "Feature", "properties": props,
                         "geometry": {"type": "Point", "coordinates": [round(p["home_lon"], 6), round(p["home_lat"], 6)]}})
OUT.write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")), encoding="utf-8")
print(len(features), "residents ->", OUT, f"({OUT.stat().st_size / 1e6:.2f} MB)")
