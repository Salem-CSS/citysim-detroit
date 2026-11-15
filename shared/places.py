"""Verify a place the user typed against real map data (BACKEND_PLAN.md 11.2). Never guesses.

    resolve("Michigan and Trumbull", [6]) ->
        {"status": "ok", "name": "Michigan Ave & Trumbull", "method": "crossing", "lon": ..., "lat": ..., "district": 6, "in_selected": True}
    resolve("Woodward and 5th", [5]) ->
        {"status": "no_crossing", "message": "...", "alternatives": [...]}

Order: coordinates (map pick) -> two streets -> street address -> landmark (Amazon Location place search, Detroit only).
The index comes from data/places/build_index.py (city road layer + official council districts).
Statuses: ok | empty | unknown_street | no_crossing | no_address | ambiguous | not_found | error.
"""
from __future__ import annotations

import difflib
import json
import os
import re

DETROIT_BBOX = [-83.29, 42.25, -82.91, 42.46]
PLACE_SEARCH_MICRO_USD = 500          # $0.50 per 1,000 Search Text requests, Core tier, us-east-2 (AWS Price List API, Nov 14 2026)
_TYPES = {"st", "street", "ave", "avenue", "av", "rd", "road", "blvd", "boulevard", "dr", "drive", "hwy", "highway", "pl", "place",
          "ct", "court", "fwy", "freeway", "ln", "lane", "pkwy", "parkway", "ter", "terrace", "cir", "circle", "way", "service", "drv"}
_DIRS = {"e", "w", "n", "s", "east", "west", "north", "south"}
_WORDS = {"first": "1st", "second": "2nd", "third": "3rd", "fourth": "4th", "fifth": "5th", "sixth": "6th", "seventh": "7th",
          "eighth": "8th", "ninth": "9th", "tenth": "10th", "eleventh": "11th", "twelfth": "12th", "mile": "mile"}
_index = None


def norm_street(name: str) -> str:
    """'W Grand River Ave' -> 'grand river'. Direction prefixes and street types are dropped."""
    words = [_WORDS.get(w, w) for w in re.sub(r"[^a-z0-9 ]", " ", name.lower()).split()]
    while words and words[0] in _DIRS and len(words) > 1:
        words = words[1:]
    while words and words[-1] in _TYPES | _DIRS and len(words) > 1:
        words = words[:-1]
    return " ".join(words)


def load(index: dict | None = None) -> dict:
    global _index
    if index is not None:
        _index = index
    if _index is None:
        local = os.environ.get("PLACES_FILE")
        if local:
            _index = json.loads(open(local, encoding="utf-8").read())
        else:
            import boto3
            body = boto3.client("s3").get_object(Bucket=os.environ["DATA_BUCKET"], Key="processed/places/places.json")["Body"].read()
            _index = json.loads(body)
    return _index


def district_of(lon: float, lat: float, index: dict | None = None) -> int | None:
    """Council district holding the point (ray casting on the simplified official polygons), or None."""
    for d, polys in load(index)["districts"].items():
        for ring in polys:
            inside, j = False, len(ring) - 1
            for i in range(len(ring)):
                xi, yi, xj, yj = ring[i][0], ring[i][1], ring[j][0], ring[j][1]
                if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                    inside = not inside
                j = i
            if inside:
                return int(d)
    return None


def _ok(name, method, lon, lat, districts, index):
    d = district_of(lon, lat, index)
    return {"status": "ok", "name": name, "method": method, "lon": round(lon, 6), "lat": round(lat, 6), "district": d,
            "in_selected": d in [int(x) for x in districts] if districts else d is not None}


def _close(name: str, pool, n=3) -> list[str]:
    return difflib.get_close_matches(name, list(pool), n=n, cutoff=0.6)


def _crossing(a_raw: str, b_raw: str, districts, idx) -> dict:
    a, b = norm_street(a_raw), norm_street(b_raw)
    streets = idx["streets"]
    for raw, key in ((a_raw, a), (b_raw, b)):
        if key not in streets:
            alts = [streets[k] for k in _close(key, streets)]
            return {"status": "unknown_street", "message": f"There is no street named \"{raw.strip()}\" on the city's road map.", "alternatives": alts}
    pt = idx["crossings"].get("|".join(sorted((a, b))))
    if pt:
        return _ok(f"{streets[a]} & {streets[b]}", "crossing", pt[0], pt[1], districts, idx)
    # Real alternatives from the map: the crossings on the first street that lie nearest the second street.
    def crossings_of(key):
        out = {}
        for k, pt in idx["crossings"].items():
            x, y = k.split("|")
            if key in (x, y):
                out[y if x == key else x] = pt
        return out
    on_a, on_b = crossings_of(a), crossings_of(b)
    near = sorted(on_a, key=lambda k: min(((on_a[k][0] - q[0]) * 0.74) ** 2 + (on_a[k][1] - q[1]) ** 2 for q in on_b.values())) if on_b else []
    alts = [f"{streets[a]} & {streets[k]}" for k in near[:3]]
    return {"status": "no_crossing", "message": f"{streets[a]} and {streets[b]} are both real streets, but they do not cross.", "alternatives": alts}


def _address(number: int, street_raw: str, districts, idx) -> dict:
    key = norm_street(street_raw)
    if key not in idx["streets"]:
        return {"status": "unknown_street", "message": f"There is no street named \"{street_raw.strip()}\" on the city's road map.",
                "alternatives": [idx["streets"][k] for k in _close(key, idx["streets"])]}
    for lo, hi, x1, y1, x2, y2 in idx["ranges"].get(key, []):
        if lo <= number <= hi:
            t = (number - lo) / (hi - lo) if hi > lo else 0.5
            return _ok(f"{number} {idx['streets'][key]}", "address", x1 + t * (x2 - x1), y1 + t * (y2 - y1), districts, idx)
    return {"status": "no_address", "message": f"{idx['streets'][key]} is a real street, but number {number} is outside its address ranges.", "alternatives": []}


VAGUE = {"the", "at", "and", "of", "my", "our", "your", "this", "that", "here", "there", "near", "nearby", "neighborhood", "street",
         "block", "area", "house", "home", "corner", "city", "town", "downtown", "somewhere", "detroit", "district"}


def _landmark(text: str, districts, idx, client=None) -> dict:
    if not [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) >= 3 and w not in VAGUE]:
        return {"status": "not_found", "message": f"\"{text}\" is not a specific place.", "alternatives": []}
    try:
        if client is None:
            import boto3
            client = boto3.client("geo-places", region_name=os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-2")
        items = client.search_text(QueryText=text, Filter={"BoundingBox": DETROIT_BBOX}, MaxResults=5).get("ResultItems", [])
    except Exception as e:                                    # no permission, no network: say so, do not guess
        return {"status": "error", "message": f"Could not look up \"{text}\" ({type(e).__name__}).", "alternatives": []}
    _count_search()
    items = [i for i in items if i.get("PlaceType") != "Street" and district_of(i["Position"][0], i["Position"][1], idx)]
    if not items:
        return {"status": "not_found", "message": f"Could not find \"{text}\" in Detroit.", "alternatives": []}
    label = lambda i: i["Title"] + (", " + i["Address"]["Label"].split(",")[0] if i.get("Address", {}).get("Label") and i["Address"]["Label"].split(",")[0] != i["Title"] else "")
    generic = {"the", "at", "and", "of", "hotel", "center", "centre", "plaza", "building", "park", "detroit", "new", "old"}
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) >= 3 and w not in generic]
    named = [i for i in items if words and all(w in i["Title"].lower() for w in words)]
    if not named:                                              # nothing carries the user's own words: suggest, never pick
        return {"status": "not_found", "message": f"Could not find \"{text}\" in Detroit.", "alternatives": [label(i) for i in items[:3]]}
    items = named
    exact = [i for i in items if i["Title"].lower() == text.strip().lower()]
    pick = exact[0] if len(exact) == 1 else items[0] if len(items) == 1 else None
    if pick is None and len({i["Title"].lower() for i in items}) == 1 and _spread_m(items) < 250:
        pick = items[0]                                        # the same place listed more than once
    if pick is None:
        return {"status": "ambiguous", "message": f"\"{text}\" matches more than one place.", "alternatives": [label(i) for i in items[:4]]}
    return _ok(label(pick), "place search", pick["Position"][0], pick["Position"][1], districts, idx)


def _spread_m(items) -> float:
    xs, ys = [i["Position"][0] for i in items], [i["Position"][1] for i in items]
    return max((max(xs) - min(xs)) * 82000, (max(ys) - min(ys)) * 111000)


def _count_search() -> None:
    """Add the search's price to the day's spend when a runs table is configured."""
    if os.environ.get("RUNS_TABLE"):
        try:
            from shared import budget
            budget.record(PLACE_SEARCH_MICRO_USD)
        except Exception:
            pass


COORDS = re.compile(r"\(?\s*(-?\d{1,3}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)\s*\)?\s*$")


def split_coords(text: str):
    """'Michigan Ave & Trumbull St (42.33120, -83.06710)' -> ('Michigan Ave & Trumbull St', lon, lat).
    Accepts lat,lon or lon,lat; returns (text, None, None) when there is no Detroit-area pair at the end."""
    m = COORDS.search(text or "")
    if not m:
        return text, None, None
    a, b = float(m.group(1)), float(m.group(2))
    lat, lon = (a, b) if 41 < a < 43 else (b, a)
    if not (41 < lat < 43 and -84 < lon < -82):
        return text, None, None
    return text[:m.start()].strip(" ,"), lon, lat


def resolve(text: str, districts=None, index: dict | None = None, client=None) -> dict:
    idx = load(index)
    text = " ".join((text or "").split())
    if not text:
        return {"status": "empty", "message": "No place was given.", "alternatives": []}
    label, lon, lat = split_coords(text)
    if lon is not None:                              # picked on the map or typed as coordinates: the point is exact
        return _ok(label or f"Point at {lat:.5f}, {lon:.5f}", "coordinates", lon, lat, districts, idx)
    core = re.sub(r"^(the )?(corner|intersection) of ", "", text, flags=re.I)
    core = re.sub(r"^(at|on|near|by|in) ", "", core, flags=re.I)
    m = re.match(r"^(.+?)\s+(?:and|&|at|near|@|\+)\s+(.+)$", core, flags=re.I)
    if m:
        known = [norm_street(g) in idx["streets"] for g in m.groups()]
        short = all(len(g.split()) <= 4 for g in m.groups())
        if all(known) or (any(known) and short):       # two streets, or one real street and something street-like
            return _crossing(m.group(1), m.group(2), districts, idx)
    a = re.match(r"^(\d{1,5})\s+(.+)$", core)
    if a and not re.match(r"^\d+(st|nd|rd|th)\b", core, flags=re.I):
        street = re.split(r",", a.group(2))[0]
        if norm_street(street) in idx["streets"] or len(street.split()) <= 4:
            r = _address(int(a.group(1)), street, districts, idx)
            if r["status"] != "unknown_street":
                return r
    return _landmark(core, districts, idx, client)
