"""Turn resident answers into the run result (contracts/run_result.schema.json).

    main(rows, spec, stats) -> run_result fields

`rows` are valid answers from batch.py, each carrying the resident's census weight and traits.
Every share is weighted by `weight` (the resident's post-stratification weight to district adults), so a
district counts in proportion to its adult population. Shares are percentages rounded to one decimal.

Not produced here because the traffic engine supplies them: `segments` (empty until then), `trips`,
the `exposure` group and `in_noise_band`. `calibration` is null until residents/calibrate.py has run.
"""
from __future__ import annotations

import random
from collections import defaultdict

from contracts.spec import REASONS

STANCES = ("support", "neutral", "oppose")
BOOTSTRAP_DRAWS = 200
BOOTSTRAP_SEED = 1114
UNRELIABLE_DROP_RATE = 0.10          # run_stats.unreliable when more than 1 in 10 residents gave no valid answer


def pct(part: float, whole: float) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


def split(rows: list[dict]) -> dict:
    total = sum(r["weight"] for r in rows)
    return {s: pct(sum(r["weight"] for r in rows if r["stance"] == s), total) for s in STANCES}


def top_reason(rows: list[dict]) -> str:
    """Most common reason by weight, leaving out 'none'; 'none' if nobody gave another."""
    w = defaultdict(float)
    for r in rows:
        if r["reason"] != "none":
            w[r["reason"]] += r["weight"]
    return max(w, key=w.get) if w else "none"


def support_range(rows: list[dict]) -> list[float]:
    """5th-95th percentile of weighted support over bootstrap resamples drawn within each district.
    This is sampling spread only, not model error."""
    by_d = defaultdict(list)
    for r in rows:
        by_d[r["district"]].append(r)
    rng, vals = random.Random(BOOTSTRAP_SEED), []
    for _ in range(BOOTSTRAP_DRAWS):
        sup = tot = 0.0
        for group in by_d.values():
            for r in rng.choices(group, k=len(group)):
                tot += r["weight"]
                sup += r["weight"] if r["stance"] == "support" else 0.0
        vals.append(100 * sup / tot if tot else 0.0)
    vals.sort()
    return [round(vals[int(0.05 * (len(vals) - 1))], 1), round(vals[int(0.95 * (len(vals) - 1))], 1)]


def who(r: dict) -> str:
    return f"{'Homeowner' if r['tenure'] == 'owner' else 'Renter'}, {r['age']}, District {r['district']}"


def main(rows: list[dict], spec: dict, stats: dict | None = None) -> dict:
    stats = dict(stats or {})
    asked = stats.get("residents", len(rows))
    dropped = asked - len(rows)
    stats.update(residents=asked, valid=len(rows), dropped=dropped, drop_rate=round(dropped / asked, 4) if asked else 0.0,
                 retried=stats.get("retried", 0))
    stats["unreliable"] = stats["drop_rate"] > UNRELIABLE_DROP_RATE
    result = {"spec_id": spec["spec_id"], "spec_version": spec.get("version", 1), "segments": [], "calibration": None,
              "run_stats": stats}
    if not rows:
        return {**result, "overall": {"support": 0.0, "neutral": 0.0, "oppose": 0.0}, "districts": [], "reasons": [],
                "groups": [], "quotes": [], "blocks": []}

    overall = split(rows)
    overall["support_range"] = support_range(rows)

    districts = []
    for d in sorted({r["district"] for r in rows}):
        g = [r for r in rows if r["district"] == d]
        districts.append({"district": d, "split": split(g), "n": len(g), "top_reason": top_reason(g)})

    total = sum(r["weight"] for r in rows)
    opp = [r for r in rows if r["stance"] == "oppose"]
    opp_total = sum(r["weight"] for r in opp)
    reasons = [{"reason": k, "share": pct(sum(r["weight"] for r in rows if r["reason"] == k), total),
                "share_among_oppose": pct(sum(r["weight"] for r in opp if r["reason"] == k), opp_total)} for k in REASONS]
    reasons = sorted((x for x in reasons if x["share"] > 0), key=lambda x: -x["share"])

    def group(dimension, label, keep):
        g = [r for r in rows if keep(r)]
        return {"dimension": dimension, "label": label, "support": split(g)["support"], "n": len(g)} if g else None

    groups = [g for g in (
        group("tenure", "Renters", lambda r: r["tenure"] == "renter"),
        group("tenure", "Homeowners", lambda r: r["tenure"] == "owner"),
        group("age", "Under 35", lambda r: r["age"] < 35),
        group("age", "35 to 64", lambda r: 35 <= r["age"] < 65),
        group("age", "65 and over", lambda r: r["age"] >= 65),
        group("vehicles", "No car", lambda r: r["vehicles"] == 0),
        group("vehicles", "Has a car", lambda r: r["vehicles"] > 0),
        group("exposure", "Within a quarter mile", lambda r: r.get("distance_m") is not None and r["distance_m"] <= 402),
        group("exposure", "A quarter mile to a mile", lambda r: r.get("distance_m") is not None and 402 < r["distance_m"] <= 1609),
        group("exposure", "More than a mile away", lambda r: r.get("distance_m") is not None and r["distance_m"] > 1609),
    ) if g]

    quotes = [{"persona_id": r["persona_id"], "text": r["quote"], "stance": r["stance"], "reason": r["reason"],
               "who": who(r), "district": r["district"]} for r in rows if r.get("quote")]

    by_block = defaultdict(list)
    for r in rows:
        by_block[r["block_geoid"]].append(r)
    blocks = [{"block_geoid": b, "support": split(g)["support"], "n": len(g), "top_reason": top_reason(g)}
              for b, g in sorted(by_block.items())]

    return {**result, "overall": overall, "districts": districts, "reasons": reasons, "groups": groups,
            "quotes": quotes, "blocks": blocks}
