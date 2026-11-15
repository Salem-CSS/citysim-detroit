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
FOLLOW_UP_SAMPLE = 60                # residents per group asked the follow-up question after a rerun (a choice)
LEVER_CHANGE = {"location": "different location", "size": "smaller", "hours": "limited hours"}
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
    diag["asked_for_but_not_tried"] = not_tried(said, can, sum(said.values()))
    if not levers:
        return [], "no lever is available for this kind of proposal" + (" (residents asked for community benefits, which the engine cannot model)" if said.get("community benefits") else "")
    return levers, None


def not_tried(said: dict, can: dict, total: int) -> list[str]:
    """What opponents asked for that the engine cannot change, in plain words."""
    out, name = [], {"different location": "location", "smaller": "size", "limited hours": "hours"}
    why = {"location": "this proposal has no single verified site to move", "size": "this kind of proposal has no size setting",
           "hours": "this kind of proposal has no hours setting"}
    for k, n in sorted(said.items(), key=lambda kv: -kv[1]):
        share = round(100 * n / total, 1) if total else 0
        if k == "community benefits":
            out.append(f"community benefits ({share}% of opponents asked): the engine cannot model benefits; this is for the proposer to answer")
        elif k in name and not can[name[k]]:
            out.append(f"{k} ({share}% of opponents asked): {why[name[k]]}")
    return out


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


def adults_near(points: list[tuple[float, float]], blocks: list[list]) -> list[tuple[int, int]]:
    """Adults (2020 census blocks) within a mile and within a quarter mile of each point. Blocks are filed in a grid
    so thousands of lots can be counted quickly."""
    cell, grid = 0.01, {}
    for b in blocks:
        grid.setdefault((int(b[0] // cell), int(b[1] // cell)), []).append(b)
    out = []
    for lon, lat in points:
        k, m, q = math.cos(math.radians(lat)), 0, 0
        cx, cy = int(lon // cell), int(lat // cell)
        for i in range(cx - 3, cx + 4):
            for j in range(cy - 2, cy + 3):
                for b in grid.get((i, j), ()):
                    d = math.sqrt(((b[0] - lon) * k) ** 2 + (b[1] - lat) ** 2) * proximity.M_PER_DEG_LAT
                    if d <= MILE_M:
                        m += b[2]
                        if d <= QUARTER_MILE_M:
                            q += b[2]
        out.append((m, q))
    return out


def location_candidates(spec: dict, index: dict, limit: int = 12, blocks: list[list] | None = None) -> tuple[list[dict], dict]:
    """Land Bank lots in the selected districts, in the same zoning district as the original site, at least half a
    mile apart and half a mile from the original. With `blocks`: lots at least as large as the pool's median lot,
    fewest adults living within a mile first (opposition follows the site, BACKEND_PLAN 15.14). Without: largest first."""
    action = next(a for a in spec["actions"] if _where(a) and _where(a).get("resolved"))
    here = _where(action)["resolved"]
    zone, zdist = zoning_at(here["lon"], here["lat"], index)
    zi = index["zoning"].index(zone) if zone else None
    pool = [s for s in index["sites"] if s[4] in spec["districts"] and s[3] == zi]
    pool.sort(key=lambda s: -s[2])
    order = "largest first"
    if blocks and pool:
        big = pool[:(len(pool) + 1) // 2]                # at least the median lot size
        near = adults_near([(s[0], s[1]) for s in big], blocks)
        pool_ranked = [s for _, s in sorted(zip(near, big), key=lambda t: (t[0][0], t[0][1], -t[1][2]))]
        order = "lots at least as large as the median lot in that pool, fewest adults living within a mile first"
    else:
        pool_ranked = pool
    origin = {"kind": "point", "lon": here["lon"], "lat": here["lat"]}
    chosen = []
    for s in pool_ranked:
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
            "rule": f"Land Bank lots in the selected districts in zoning district {zone}, at least {MIN_SPREAD_MI} miles apart and from the original site, {order}. "
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


# ---------- what residents asked for, and what they did after it was changed ----------
def asked_outcome(asked: list[dict], rows: list[dict], lever: str) -> dict:
    """For each answer to "what one change would make you more supportive": how those residents answered the rerun.
    `asked` is the opponents' seven answers (one per resident); `rows` the rerun's answers. Counts of residents."""
    by = {r["persona_id"]: r["stance"] for r in rows}
    table = {}
    for c in asked:
        t = table.setdefault(c["one_change"], {"change": c["one_change"], "asked_for_it": 0, "answered_rerun": 0, "support": 0, "neutral": 0, "oppose": 0})
        t["asked_for_it"] += 1
        if c["persona_id"] in by:
            t["answered_rerun"] += 1
            t[by[c["persona_id"]]] += 1
    made = LEVER_CHANGE[lever]
    return {"change_made": made, "by_request": sorted(table.values(), key=lambda t: (t["change"] != made, -t["asked_for_it"]))}


def follow_up_targets(asked: list[dict], original: list[dict], rerun: list[dict], lever: str, cap: int = FOLLOW_UP_SAMPLE) -> list[dict]:
    """Who gets the follow-up question after a rerun, nearest to the proposal's new place first, up to `cap` each:
    'asked_for_it': asked for the change that was made, and still oppose;
    'new_opponent': did not oppose the original version, and oppose this one."""
    want = {c["persona_id"]: c["one_change"] for c in asked}
    before = {r["persona_id"]: r for r in original}
    near = lambda r: (r.get("distance_m") is None, r.get("distance_m") or 0, r["persona_id"])
    groups = {"asked_for_it": [], "new_opponent": []}
    for r in sorted((r for r in rerun if r["stance"] == "oppose"), key=near):
        b = before.get(r["persona_id"])
        if b is None:
            continue
        if b["stance"] == "oppose" and want.get(r["persona_id"]) == LEVER_CHANGE[lever]:
            g = "asked_for_it"
        elif b["stance"] != "oppose":
            g = "new_opponent"
        else:
            continue
        if len(groups[g]) < cap:
            groups[g].append({"persona_id": r["persona_id"], "group": g, "before": b["stance"], "before_reason": b.get("reason"),
                              "after_reason": r["reason"], "asked_for": want.get(r["persona_id"]), "distance_m": r.get("distance_m")})
    return groups["asked_for_it"] + groups["new_opponent"]


def follow_up_summary(targets: list[dict], answers: dict, fields: dict) -> dict:
    """Counts per wording and per group, plus sample sentences. `answers`: {variant: [items]}; `fields`: {variant:
    (free-text field, [option fields])}. No model writes this: it is a tally."""
    group = {t["persona_id"]: t["group"] for t in targets}
    out = {"asked": {g: sum(t["group"] == g for t in targets) for g in ("asked_for_it", "new_opponent")}, "wordings": {}}
    for variant, items in answers.items():
        text, options = fields[variant]
        v = {"answered": len(items), "average_characters": round(sum(len(i[text]) for i in items) / len(items)) if items else 0,
             "distinct_sentences": len({i[text].strip().lower() for i in items})}
        for f in options:
            v[f] = {}
            for g in ("asked_for_it", "new_opponent", "all"):
                count = {}
                for i in items:
                    if g == "all" or group.get(i["persona_id"]) == g:
                        count[i[f]] = count.get(i[f], 0) + 1
                v[f][g] = dict(sorted(count.items(), key=lambda kv: -kv[1]))
        v["sentences"] = []
        for g in ("asked_for_it", "new_opponent"):
            v["sentences"] += [{"group": g, "text": i[text]} for i in items if group.get(i["persona_id"]) == g][:4]
        out["wordings"][variant] = v
    return out


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
