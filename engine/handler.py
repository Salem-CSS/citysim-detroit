"""Traffic engine: confirmed scenario spec in, sourced numbers out. No AI, no invented values.

    handler(spec, data=None) -> {"status", "trips", "segments", "street_effects", "transit", "notes"}

What it computes today (BACKEND_PLAN.md section 8), and nothing more:

add_building, when the user stated the number of homes (or a grocery with its floor area):
  1. Trips = size x the published rate in data/ite_rates.csv (daily and evening peak).
  2. Detroit adjustment: x (1 - share of households with no vehicle in the site's census tract, ACS B25044).
  3. The counted street nearest the verified site gets all of the adjusted trips. This is an upper bound for
     that street and is labelled as an assumption: trips are not yet spread over the network.
  4. Load before and after = (vehicles a day x K x D) / (lanes per direction x capacity), with the planning
     assumptions K 0.09, D 0.55, capacity 800 vehicles per lane per hour. These three are unsourced defaults,
     reported in `notes`.
  Any other use (no rate in the table, or homes not stated) returns no trips and says why.

change_transit, for a route with a verified start and end:
  adults living within a quarter mile of the straight line between them (2020 Census block counts) and the
  existing DDOT stops within that band. No ridership or traffic forecast: there is no sourced method yet.

Other action types return a note that they are not computed.
"""
from __future__ import annotations

import json
import math
import os

from engine import proximity
from engine.trips import detroit_adjust, generate

K_FACTOR, D_FACTOR, LANE_CAPACITY = 0.09, 0.55, 800
QUARTER_MILE_M = 402.0
_data = None


def load(data: dict | None = None) -> dict:
    global _data
    if data is not None:
        _data = data
    if _data is None:
        local = os.environ.get("ENGINE_DATA_FILE")
        if local:
            _data = json.loads(open(local, encoding="utf-8").read())
        else:
            import boto3
            body = boto3.client("s3").get_object(Bucket=os.environ["DATA_BUCKET"], Key="processed/engine/engine_data.json")["Body"].read()
            _data = json.loads(body)
    return _data


def _dist_to_lines(lon: float, lat: float, lines: list) -> float:
    best = math.inf
    for line in lines:
        for a, b in zip(line, line[1:]):
            best = min(best, proximity.distance_m(lon, lat, {"kind": "route", "from": a, "to": b}))
    return best


def nearest_segment(lon: float, lat: float, data: dict) -> tuple[dict, float]:
    """The counted street at the site. A corner site touches two streets: of the counted segments within 40 m of
    the nearest one, the busiest is used."""
    dists = [(_dist_to_lines(lon, lat, s["coords"]), s) for s in data["segments"]]
    nearest = min(d for d, _ in dists)
    d, seg = max((x for x in dists if x[0] <= nearest + 40), key=lambda x: x[1]["aadt"])
    return seg, d


def tract_of(lon: float, lat: float, data: dict) -> dict:
    """Census tract of the block whose interior point is nearest the site."""
    b = min(data["blocks"], key=lambda r: ((r[0] - lon) * 0.74) ** 2 + (r[1] - lat) ** 2)
    return data["tracts"][b[3]]


def load_ratio(aadt: float, lanes_per_direction: float) -> float:
    return round(aadt * K_FACTOR * D_FACTOR / (lanes_per_direction * LANE_CAPACITY), 2)


def _c(action: dict, cid: str) -> dict:
    return next((c for c in action["constraints"] if c["id"] == cid), {})


def _stated(c: dict) -> bool:
    return c.get("source") in ("from_question", "edited") and c.get("value") not in (None, "", 0)


def building(action: dict, data: dict) -> dict:
    what = str(_c(action, "what").get("value") or "building").strip()
    site = _c(action, "where").get("resolved")
    homes, ground, sqft = _c(action, "homes"), _c(action, "ground_floor"), _c(action, "retail_sqft")
    parts = []
    if _stated(homes):
        parts.append((221, float(homes["value"]), f"{int(homes['value'])} homes"))
    if ground.get("value") == "grocery" and _stated(ground) and _stated(sqft):
        parts.append((850, float(sqft["value"]) / 1000.0, f"{int(sqft['value']):,} sq ft grocery"))
    if not parts:
        return {"notes": [f"No traffic was computed for {what}: there is no published trip rate for this use in the rate table "
                          f"(it has mid-rise housing and supermarkets), or the number of homes was not stated."]}
    if not site:
        return {"notes": [f"No traffic was computed for {what}: its location has not been verified."]}
    raw = pm = 0.0
    for code, size, _ in parts:
        g = generate(code, size)
        raw, pm = raw + g["daily_raw"], pm + g["pm_peak"]
    tract = tract_of(site["lon"], site["lat"], data)
    adjusted = detroit_adjust(raw, tract["zero_car_share"])
    seg, dist = nearest_segment(site["lon"], site["lat"], data)
    # through lanes per direction: half the counted lanes on a two-way street, rounded down (an odd lane is a turn lane)
    lanes_dir = (max(1, seg["lanes"] // 2) if seg["two_way"] else seg["lanes"]) if seg.get("lanes") else None
    name = f"{seg['street']} ({seg['from']} to {seg['to']})"
    row = {"segment_id": seg["id"], "name": name, "counted": True, "aadt_before": seg["aadt"], "aadt_after": round(seg["aadt"] + adjusted),
           "lanes": seg.get("lanes")}
    notes = [f"Trips: {' + '.join(p[2] for p in parts)} at the published rates in data/ite_rates.csv = {raw:,.0f} vehicle trips a day "
             f"({pm:,.0f} in the evening peak hour).",
             f"Detroit adjustment: {tract['zero_car_share']:.0%} of households in the site's census tract ({tract['geoid']}) have no "
             f"vehicle (ACS 2024), so {adjusted:,.0f} trips a day are counted as car trips.",
             f"Assumption: all of those trips are placed on the nearest counted street, {name}, {proximity.how_far(dist)} from the site. "
             f"This is an upper bound for that street; trips are not yet spread over the network."]
    if lanes_dir:
        row["load_before"], row["load_after"] = load_ratio(seg["aadt"], lanes_dir), load_ratio(seg["aadt"] + adjusted, lanes_dir)
        notes.append(f"Load = vehicles a day x {K_FACTOR} x {D_FACTOR} / ({lanes_dir} through lanes per direction x {LANE_CAPACITY}). "
                     f"The three factors are standard planning assumptions, not measured values.")
    else:
        row["load_before"] = row["load_after"] = 0.0
        notes.append("Load could not be computed: the count has no lane number.")
    return {"trips": {"daily_raw": round(raw), "daily_adjusted": round(adjusted), "pm_peak": round(pm)}, "segments": [row], "notes": notes,
            "street_effects": [{"name": seg["street"], "added_daily": round(adjusted), "coords": seg["coords"]}]}


def transit(action: dict, data: dict) -> dict:
    start, end = _c(action, "from").get("resolved"), _c(action, "to").get("resolved")
    if not (start and end):
        return {"notes": ["Nothing was computed for the bus service: it needs a verified start and end."]}
    line = {"kind": "route", "from": [start["lon"], start["lat"]], "to": [end["lon"], end["lat"]]}
    adults = sum(b[2] for b in data["blocks"] if proximity.distance_m(b[0], b[1], line) <= QUARTER_MILE_M)
    near = [s for s in data["stops"] if proximity.distance_m(s[0], s[1], line) <= QUARTER_MILE_M]
    routes = sorted({f"{s[2]} {s[3]}".strip() for s in near})
    length = proximity.distance_m(start["lon"], start["lat"], {"kind": "point", "lon": end["lon"], "lat": end["lat"]})
    return {"transit": {"from": start["name"], "to": end["name"], "straight_line_miles": round(length / 1609.344, 2),
                        "adults_within_quarter_mile": int(adults), "existing_stops_within_quarter_mile": len(near),
                        "existing_routes_within_quarter_mile": routes},
            "notes": [f"{adults:,} adults live within a quarter mile of the straight line from {start['name']} to {end['name']} "
                      f"(2020 Census block counts). {len(near)} existing DDOT stops on {len(routes)} routes are already within that band.",
                      "No ridership or traffic change was computed for the bus service: there is no sourced method for a new route yet. "
                      "The real path will differ from a straight line."]}


def handler(event, context=None, data: dict | None = None) -> dict:
    spec = event if isinstance(event, dict) and "actions" in event else json.loads(event["body"])
    if spec.get("status") != "confirmed":
        raise ValueError("engine only runs confirmed specs")
    out = {"spec_id": spec["spec_id"], "spec_version": spec.get("version", 1), "segments": [], "street_effects": [], "notes": []}
    for action in spec["actions"]:
        if action["type"] == "add_building":
            r = building(action, load(data))
        elif action["type"] == "change_transit":
            r = transit(action, load(data))
        else:
            r = {"notes": [f"No traffic was computed for {action.get('title', action['type'])}: this type is not built in the engine yet."]}
        out["segments"] += r.get("segments", [])
        out["street_effects"] += r.get("street_effects", [])
        out["notes"] += r.get("notes", [])
        for k in ("trips", "transit"):
            if k in r:
                out[k] = r[k]
    out["status"] = "computed" if (out["segments"] or "transit" in out) else "nothing_computed"
    return out
