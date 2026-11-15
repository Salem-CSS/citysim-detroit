"""Correction engine, the parts with no AWS in them (BACKEND_PLAN.md section 15).

    diagnose(rows, changes)            why residents said no: where, who, and what they say would change their mind
    choose_levers(diag, spec)          which settings are worth changing, in order
    location_candidates(spec, index)   real alternative sites (Land Bank lots in the same zoning district)
    setting_candidates(spec, lever)    smaller sizes / other hours the proposal type already offers
    Predictor(rows_by_place)           predicted split for a candidate site, from the residents' own answers so far
    apply_candidate(spec, cand)        the proposal with that one thing changed
    near_profile(place, personas, blocks)   who lives near a site

Every number comes from the run's stored answers, the persona files, the block file or the site index. Where a
threshold is a convention or a choice it is named below and reported with the result.
"""
from __future__ import annotations

import copy
import math

from engine import proximity

QUARTER_MILE_M, MILE_M = 402.0, 1609.344
BANDS = (("Within a quarter mile", 0, QUARTER_MILE_M), ("A quarter mile to a mile", QUARTER_MILE_M, MILE_M),
         ("1 to 3 miles", MILE_M, 3 * MILE_M), ("More than 3 miles", 3 * MILE_M, float("inf")))
TARGETS = {"more_support_than_oppose": "more residents support than oppose",
           "majority": "more than half of residents support",
           "two_thirds": "at least two thirds of residents support"}
MAX_RERUNS = 5                       # hard cap, enforced by correction/loop.py on the server
MIN_SPREAD_MI = 0.5                  # candidate sites are at least this far apart and from the original site (a choice)
MIN_CELL = 5                         # a predictor cell with fewer residents falls back to the wider group (a choice)
Z = 1.96                             # two-sided 95% for "differs from": the usual convention
SIZE_IDS = {"add_drone_route": "flights_per_day", "add_building": "homes", "add_event_surge": "seats", "change_transit": "buses_per_hour"}
HOURS_IDS = {"add_drone_route": "flying_hours", "add_event_surge": "event_time"}
GROUPS = (("Renters", lambda r: r["tenure"] == "renter"), ("Homeowners", lambda r: r["tenure"] == "owner"),
          ("Under 35", lambda r: r["age"] < 35), ("35 to 64", lambda r: 35 <= r["age"] < 65), ("65 and over", lambda r: r["age"] >= 65),
          ("No car", lambda r: r["vehicles"] == 0), ("Has a car", lambda r: r["vehicles"] > 0))


# ---------- splits and targets ----------
def split(rows: list[dict]) -> dict:
    total = sum(r["weight"] for r in rows)
    if not total:
        return {"support": 0.0, "neutral": 0.0, "oppose": 0.0, "n": 0}
    share = lambda s: round(100 * sum(r["weight"] for r in rows if r["stance"] == s) / total, 1)
    return {"support": share("support"), "neutral": share("neutral"), "oppose": share("oppose"), "n": len(rows)}


def score(sp: dict, target: str) -> float:
    """The number a target is judged on, in percentage points."""
    return round(sp["support"] - sp["oppose"], 1) if target == "more_support_than_oppose" else sp["support"]


def met(sp: dict, target: str) -> bool:
    if target == "more_support_than_oppose":
        return sp["support"] > sp["oppose"]
    return sp["support"] > 50 if target == "majority" else sp["support"] >= 66.7


def band_of(d: float | None) -> str | None:
    if d is None:
        return None
    return next(label for label, lo, hi in BANDS if lo <= d < hi or (hi == float("inf") and d >= lo))


def _differs(p1: float, n1: int, p2: float, n2: int) -> bool:
    """Two shares (0-100) differ by more than sampling alone would explain (two-proportion test, 95%)."""
    if n1 < MIN_CELL or n2 < MIN_CELL:
        return False
    a, b = p1 / 100, p2 / 100
    pooled = (a * n1 + b * n2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    return se > 0 and abs(a - b) / se > Z


# ---------- diagnosis ----------
def diagnose(rows: list[dict], changes: list[dict] | None = None, target: str = "more_support_than_oppose") -> dict:
    """rows: the run's stored answers (stance, reason, distance_m, age, tenure, vehicles, district, weight).
    changes: answers of sampled opponents to the seven questions (correction/ask.py), or None if not asked."""
    overall = split(rows)
    with_d = [r for r in rows if r.get("distance_m") is not None]
    bands = [{"label": label, **split([r for r in with_d if band_of(r["distance_m"]) == label])} for label, _, _ in BANDS]
    bands = [b for b in bands if b["n"]]
    near, far = [r for r in with_d if r["distance_m"] <= MILE_M], [r for r in with_d if r["distance_m"] > MILE_M]
    sn, sf = split(near), split(far)
    local = _differs(sn["oppose"], sn["n"], sf["oppose"], sf["n"]) and sn["oppose"] > sf["oppose"]
    groups = []
    for label, keep in GROUPS:
        g, rest = [r for r in rows if keep(r)], [r for r in rows if not keep(r)]
        sg, sr = split(g), split(rest)
        if g:
            groups.append({"label": label, **sg, "oppose_elsewhere": sr["oppose"],
                           "stands_out": _differs(sg["oppose"], sg["n"], sr["oppose"], sr["n"]) and sg["oppose"] > sr["oppose"]})
    opp = [r for r in rows if r["stance"] == "oppose"]
    total_opp = sum(r["weight"] for r in opp) or 1
    reasons = {}
    for r in opp:
        reasons[r["reason"]] = reasons.get(r["reason"], 0) + r["weight"]
    reasons = [{"reason": k, "share": round(100 * v / total_opp, 1)} for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])]
    asked = None
    if changes:
        count = {}
        for c in changes:
            count[c["one_change"]] = count.get(c["one_change"], 0) + 1
        asked = {"asked": len(changes),
                 "one_change": [{"change": k, "count": v, "share": round(100 * v / len(changes), 1)} for k, v in sorted(count.items(), key=lambda kv: -kv[1])],
                 "sentences": [c["reaction"] for c in changes[:6]]}
    diag = {"overall": overall, "target": target, "target_text": TARGETS[target], "target_met": met(overall, target),
            "has_place": bool(with_d), "bands": bands, "within_1_mile": sn, "beyond_1_mile": sf, "opposition_is_local": local,
            "groups": groups, "opponent_reasons": reasons, "opponents_asked": asked}
    diag["sentences"] = sentences(diag)
    return diag


def sentences(d: dict) -> list[str]:
    """Plain sentences built from the tables by template. No model writes these."""
    o, out = d["overall"], []
    out.append(f"{o['support']}% support, {o['neutral']}% neutral and {o['oppose']}% oppose ({o['n']:,} residents).")
    if d["has_place"] and d["within_1_mile"]["n"] and d["beyond_1_mile"]["n"]:
        a, b = d["within_1_mile"], d["beyond_1_mile"]
        out.append(f"Within a mile of the site {a['oppose']}% oppose ({a['n']:,} residents); farther away {b['oppose']}% oppose ({b['n']:,}). "
                   + ("Opposition is concentrated near the site, so where it goes matters." if d["opposition_is_local"]
                      else "Opposition does not clearly depend on distance, so moving it may not help."))
    stand = [g for g in d["groups"] if g["stands_out"]]
    if stand:
        out.append("Groups that oppose more than everyone else: " + "; ".join(f"{g['label'].lower()} ({g['oppose']}% against {g['oppose_elsewhere']}%)" for g in stand) + ".")
    if d["opponent_reasons"]:
        r = d["opponent_reasons"][0]
        out.append(f"The main reason opponents give is {r['reason']} ({r['share']}% of opponents).")
    if d["opponents_asked"]:
        top = d["opponents_asked"]["one_change"][0]
        out.append(f"Asked what one change would make them more supportive, {top['share']}% of {d['opponents_asked']['asked']} opponents said \"{top['change']}\".")
    return out


# ---------- levers ----------
def choose_levers(diag: dict, spec: dict) -> tuple[list[str], str | None]:
    """Ordered levers to try, and a reason when there is nothing to try. One lever is changed per rerun."""
    if diag["target_met"]:
        return [], "no correction needed: the target is already met"
    types = [a["type"] for a in spec["actions"]]
    can = {"location": diag["has_place"] and any(_where(a) is not None and _where(a).get("resolved") for a in spec["actions"]),
           "size": any(t in SIZE_IDS for t in types), "hours": any(t in HOURS_IDS for t in types)}
    said = {c["change"]: c["count"] for c in (diag["opponents_asked"] or {}).get("one_change", [])}
    name = {"different location": "location", "smaller": "size", "limited hours": "hours"}
    order = [name[k] for k, _ in sorted(said.items(), key=lambda kv: -kv[1]) if k in name]
    if said and max(said, key=said.get) == "nothing" and not diag["opposition_is_local"]:
        return [], "not fixable by changing the proposal: most opponents asked said nothing would change their mind, and opposition does not depend on distance"
    if not said:                                    # opponents were not asked: fall back on what the data shows
        order = ["location"] if diag["opposition_is_local"] else []
        order += ["size", "hours"]
    if "location" in order and not diag["opposition_is_local"]:
        order = [l for l in order if l != "location"] + ["location"]      # still tried, but last
    levers = [l for l in dict.fromkeys(order) if can[l]]
    if not levers:
        return [], "no lever is available for this kind of proposal" + (" (residents asked for community benefits, which the engine cannot model)" if said.get("community benefits") else "")
    return levers, None


def _where(action: dict) -> dict | None:
    return next((c for c in action["constraints"] if c["id"] == "where"), None)


def _constraint(action: dict, cid: str) -> dict | None:
    return next((c for c in action["constraints"] if c["id"] == cid), None)


# ---------- candidates ----------
def zoning_at(lon: float, lat: float, index: dict) -> tuple[str | None, float]:
    """Zoning district of the parcel nearest to a point, and how far that parcel's centre is (metres)."""
    best, bd = None, float("inf")
    k = math.cos(math.radians(lat))
    for plon, plat, zi in index["parcels"]:
        d = (plon - lon) ** 2 * k * k + (plat - lat) ** 2
        if d < bd:
            best, bd = zi, d
    return (index["zoning"][best] if best is not None else None), math.sqrt(bd) * proximity.M_PER_DEG_LAT


def site_name(s: list) -> str:
    """The place as residents read it: the lot's address and cross streets, nothing else."""
    return s[5] + (f", between {s[6]} and {s[7]}" if s[6] and s[7] else "")


def location_candidates(spec: dict, index: dict, limit: int = 12) -> tuple[list[dict], dict]:
    """Land Bank lots in the selected districts, in the same zoning district as the original site, at least half a
    mile apart and half a mile from the original. Largest lots first."""
    action = next(a for a in spec["actions"] if _where(a) and _where(a).get("resolved"))
    here = _where(action)["resolved"]
    zone, zdist = zoning_at(here["lon"], here["lat"], index)
    zi = index["zoning"].index(zone) if zone else None
    pool = [s for s in index["sites"] if s[4] in spec["districts"] and s[3] == zi]
    pool.sort(key=lambda s: -s[2])
    origin = {"kind": "point", "lon": here["lon"], "lat": here["lat"]}
    chosen = []
    for s in pool:
        if proximity.distance_m(s[0], s[1], origin) < MIN_SPREAD_MI * MILE_M:
            continue
        if any(proximity.distance_m(s[0], s[1], {"kind": "point", "lon": c["lon"], "lat": c["lat"]}) < MIN_SPREAD_MI * MILE_M for c in chosen):
            continue
        chosen.append({"lever": "location", "action_id": action["action_id"], "lon": s[0], "lat": s[1], "lot_sqft": s[2], "district": s[4],
                       "name": site_name(s), "neighborhood": s[8], "zoning": zone,
                       "label": f"Move it to the Land Bank lot at {site_name(s)}" + (f", {s[8]}" if s[8] else "") + f" (District {s[4]})"})
        if len(chosen) == limit:
            break
    note = {"original_zoning": zone, "nearest_parcel_m": round(zdist), "lots_in_pool": len(pool),
            "rule": f"Land Bank lots in the selected districts in zoning district {zone}, at least {MIN_SPREAD_MI} miles apart and from the original site, largest first. "
                    "Same zoning district as your site; whether the use is permitted there was not checked."}
    return chosen, note


def setting_candidates(spec: dict, lever: str) -> list[dict]:
    """Smaller sizes (three quarters, half, a quarter of the current value, on the setting's own step) or the other
    hours the action offers. Only values the action type already allows."""
    out = []
    for a in spec["actions"]:
        cid = (SIZE_IDS if lever == "size" else HOURS_IDS).get(a["type"])
        c = _constraint(a, cid) if cid else None
        if not c:
            continue
        if lever == "size":
            step, lo, cur = c.get("step") or 1, c.get("min") or 0, float(c["value"] or 0)
            seen = set()
            for f in (0.75, 0.5, 0.25):
                v = max(lo, round(cur * f / step) * step)
                v = int(v) if float(v).is_integer() else v
                if v != cur and v > 0 and v not in seen:
                    seen.add(v)
                    out.append({"lever": "size", "action_id": a["action_id"], "constraint_id": cid, "value": v,
                                "label": f"Make it smaller: {c['label'].lower()} {v:,} instead of {int(cur) if cur.is_integer() else cur:,}"})
        else:
            for o in c.get("options", []):
                if o["value"] != c["value"]:
                    out.append({"lever": "hours", "action_id": a["action_id"], "constraint_id": cid, "value": o["value"],
                                "label": f"Change {c['label'].lower()} to {o['label']}"})
    return out


def apply_candidate(spec: dict, cand: dict) -> dict:
    """A copy of the proposal with only that one thing changed. The `what` text is never touched."""
    new = copy.deepcopy(spec)
    for key in ("status", "questions"):
        new.pop(key, None)
    action = next(a for a in new["actions"] if a["action_id"] == cand["action_id"])
    if cand["lever"] == "location":
        c = _where(action)
        c["value"], c["source"] = f"{cand['name']} ({cand['lat']:.5f}, {cand['lon']:.5f})", "edited"
    else:
        c = _constraint(action, cand["constraint_id"])
        c["value"], c["source"] = cand["value"], "edited"
    new["version"] = int(new.get("version", 1)) + 1
    return new


# ---------- predictor ----------
class Predictor:
    """Predicted support / neutral / oppose for a proposal moved to another place, from the residents' own answers.

    Every stored answer is filed under (distance band at the time, trait group). For a candidate place each resident's
    distance to it gives their band; their predicted answer is the weighted share of each stance in that cell. A cell
    with fewer than MIN_CELL answers falls back to the band alone, then to everyone."""

    def __init__(self, runs: list[list[dict]], trait=None):
        self.trait = trait or (lambda r: "all")
        self.cells, self.band, self.all = {}, {}, [0.0, 0.0, 0.0, 0]
        for rows in runs:
            for r in rows:
                if r.get("distance_m") is None:
                    continue
                b = band_of(r["distance_m"])
                for store, key in ((self.cells, (b, self.trait(r))), (self.band, b)):
                    cell = store.setdefault(key, [0.0, 0.0, 0.0, 0])
                    cell[("support", "neutral", "oppose").index(r["stance"])] += r["weight"]
                    cell[3] += 1
                self.all[("support", "neutral", "oppose").index(r["stance"])] += r["weight"]
                self.all[3] += 1

    def _probs(self, band: str, trait) -> list[float]:
        for cell in (self.cells.get((band, trait)), self.band.get(band), self.all):
            if cell and cell[3] >= MIN_CELL and sum(cell[:3]):
                t = sum(cell[:3])
                return [c / t for c in cell[:3]]
        return [0.0, 1.0, 0.0]

    def predict(self, place: dict, people: list[dict]) -> dict:
        """people: rows or personas with home_lon/home_lat (or lon/lat), weight and the trait fields."""
        tot, acc, near_opp = 0.0, [0.0, 0.0, 0.0], 0.0
        for p in people:
            d = proximity.distance_m(p["home_lon"], p["home_lat"], place)
            pr = self._probs(band_of(d), self.trait(p))
            for i in range(3):
                acc[i] += p["weight"] * pr[i]
            tot += p["weight"]
            if d <= QUARTER_MILE_M:
                near_opp += p["weight"] * pr[2]
        if not tot:
            return {"support": 0.0, "neutral": 0.0, "oppose": 0.0, "opposed_within_quarter_mile": 0.0}
        return {"support": round(100 * acc[0] / tot, 1), "neutral": round(100 * acc[1] / tot, 1), "oppose": round(100 * acc[2] / tot, 1),
                "opposed_within_quarter_mile": round(100 * near_opp / tot, 2)}


def strongest_trait(diag: dict):
    """The trait whose groups differ most on opposition, used to split the predictor's cells. None if none stands out."""
    by = {"Renters": "tenure", "Homeowners": "tenure", "Under 35": "age", "35 to 64": "age", "65 and over": "age", "No car": "vehicles", "Has a car": "vehicles"}
    stand = [g for g in diag["groups"] if g["stands_out"]]
    if not stand:
        return None, None
    g = max(stand, key=lambda g: g["oppose"] - g["oppose_elsewhere"])
    kind = by[g["label"]]
    fn = {"tenure": lambda r: r["tenure"], "vehicles": lambda r: "none" if r["vehicles"] == 0 else "has",
          "age": lambda r: "u35" if r["age"] < 35 else "35-64" if r["age"] < 65 else "65+"}[kind]
    return kind, fn


# ---------- who lives near a site ----------
def near_profile(place: dict, personas: list[dict], blocks: list[list]) -> dict:
    """Adults within a quarter mile and a mile (2020 census blocks), and the make-up of the simulated residents
    within a mile (census-built personas; n is given because it can be small)."""
    q = m = 0
    for b in blocks:
        d = proximity.distance_m(b[0], b[1], place)
        if d <= MILE_M:
            m += b[2]
            if d <= QUARTER_MILE_M:
                q += b[2]
    near = [p for p in personas if proximity.distance_m(p["home_lon"], p["home_lat"], place) <= MILE_M]
    tot = sum(p["weight"] for p in near)
    share = (lambda keep: round(100 * sum(p["weight"] for p in near if keep(p)) / tot, 1)) if tot else (lambda keep: None)
    return {"adults_within_quarter_mile": q, "adults_within_1_mile": m, "simulated_residents_within_1_mile": len(near),
            "renters_pct": share(lambda p: p["tenure"] == "renter"), "no_car_pct": share(lambda p: p["vehicles"] == 0),
            "age_65_plus_pct": share(lambda p: p["age"] >= 65)}
