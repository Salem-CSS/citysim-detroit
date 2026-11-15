"""Distance from a resident's home block to a verified proposal location. Pure Python, no map library.

    places_of(spec)            -> [{"kind": "point" | "route", "what", "name", ...}] from the spec's verified places
    distance_m(lon, lat, pl)   -> metres from a home point to that place
    lines_for(persona, places) -> the plain lines a resident reads, and the nearest distance in metres

A resident's home point is the interior point of their 2020 census block (data/personas/build.py), not an
address. A route's distance is measured to the straight line between its verified start and end, because the
real path is not known; the line says so.
"""
from __future__ import annotations

import math

M_PER_DEG_LAT = 111_320.0
FT_PER_M = 3.28084


def _xy(lon: float, lat: float, lat0: float) -> tuple[float, float]:
    return lon * M_PER_DEG_LAT * math.cos(math.radians(lat0)), lat * M_PER_DEG_LAT


def distance_m(lon: float, lat: float, place: dict) -> float:
    if place["kind"] == "point":
        px, py = _xy(lon, lat, lat)
        qx, qy = _xy(place["lon"], place["lat"], lat)
        return math.hypot(px - qx, py - qy)
    (ax, ay), (bx, by), (px, py) = _xy(*place["from"], lat), _xy(*place["to"], lat), _xy(lon, lat, lat)
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def how_far(m: float) -> str:
    """'about 400 ft' under a fifth of a mile, else 'about 0.6 miles'."""
    miles = m / 1609.344
    if miles < 0.2:
        return f"about {max(50, int(round(m * FT_PER_M / 50.0)) * 50):,} ft"
    return f"about {miles:.1f} miles"


def places_of(spec: dict) -> list[dict]:
    out = []
    for a in spec.get("actions", []):
        by_id = {c["id"]: c for c in a["constraints"]}
        what = str((by_id.get("what") or {}).get("value") or a.get("title") or "proposal").strip()
        start, end = (by_id.get("from") or {}).get("resolved"), (by_id.get("to") or {}).get("resolved")
        where = (by_id.get("where") or {}).get("resolved")
        if start and end:
            out.append({"kind": "route", "what": what, "name": f"{start['name']} to {end['name']}",
                        "from": [start["lon"], start["lat"]], "to": [end["lon"], end["lat"]]})
        elif where:
            out.append({"kind": "point", "what": what, "name": where["name"], "lon": where["lon"], "lat": where["lat"]})
    return out


def lines_for(persona: dict, places: list[dict]) -> tuple[list[str], float | None]:
    if persona.get("home_lon") is None or not places:
        return [], None
    lines, nearest = [], None
    for pl in places:
        d = distance_m(persona["home_lon"], persona["home_lat"], pl)
        nearest = d if nearest is None else min(nearest, d)
        if pl["kind"] == "point":
            lines.append(f"The proposed {_noun(pl['what'])} would be {how_far(d)} from your home")
        else:
            lines.append(f"Your home is {how_far(d)} from the straight line between the route's start and end ({pl['name']})")
    return lines, nearest


def _noun(what: str) -> str:
    w = what.strip()
    for art in ("a ", "an ", "the "):
        if w.lower().startswith(art):
            return w[len(art):]
    return w
