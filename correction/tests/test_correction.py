"""Correction engine: diagnosis, levers, candidates, predictor, and the loop with its caps (no AWS, no model)."""
import copy
import json

import pytest

from correction import core, loop
from engine import proximity
from infra import runs

ORIGIN = (-83.07, 42.33)
DEG_PER_MILE_LAT = core.MILE_M / proximity.M_PER_DEG_LAT


def person(i, miles_north, **kw):
    return {"persona_id": f"d6-{i:04d}", "district": 6, "home_lon": ORIGIN[0], "home_lat": ORIGIN[1] + miles_north * DEG_PER_MILE_LAT,
            "weight": 100.0, "age": 40, "tenure": "owner", "vehicles": 1, **kw}


def people():
    """400 residents on a line running north from the original site: 300 within a mile of it, 100 spread from 1.2 to 20 miles."""
    where = [i / 300 for i in range(300)] + [1.2 + 0.19 * i for i in range(100)]
    return [person(i, m, tenure="renter" if i % 2 else "owner", vehicles=0 if i % 4 == 0 else 1) for i, m in enumerate(where)]


def answer(p, place, far="support"):
    """The synthetic 'model': oppose within a mile of the place, neutral to 3 miles, `far` beyond."""
    d = proximity.distance_m(p["home_lon"], p["home_lat"], place)
    stance = "oppose" if d <= core.MILE_M else "neutral" if d <= 3 * core.MILE_M else far
    return {"persona_id": p["persona_id"], "stance": stance, "reason": "noise" if stance == "oppose" else "none" if stance == "neutral" else "jobs",
            "distance_m": round(d), **{k: p[k] for k in ("district", "weight", "age", "tenure", "vehicles")}}


def spec(lon=ORIGIN[0], lat=ORIGIN[1]):
    return {"spec_id": "s1", "version": 1, "districts": [6], "summary": "Proposal: a venue at Here in District 6.", "actions": [{
        "action_id": "a1", "type": "add_event_surge", "title": "Event venue", "constraints": [
            {"id": "what", "label": "What", "type": "text", "value": "a venue", "source": "from_question"},
            {"id": "where", "label": "Where", "type": "text", "value": "Here", "source": "from_question",
             "resolved": {"name": "Here", "method": "crossing", "lon": lon, "lat": lat, "district": 6}},
            {"id": "seats", "label": "Seats", "type": "number", "value": 2000, "step": 500, "min": 0, "source": "assumed"},
            {"id": "event_time", "label": "Event time", "type": "select", "value": "evening", "source": "assumed",
             "options": [{"value": "evening", "label": "Evening"}, {"value": "afternoon", "label": "Afternoon"}]}]}]}


def index(miles=(0.2, 1, 2, 2.2, 3.5, 6, 8, 12, 15.5, 18)):
    sites = [[ORIGIN[0], round(ORIGIN[1] + m * DEG_PER_MILE_LAT, 5), 5000 + int(m * 100), 0, 6, f"{int(m * 100)} Test St", "A St", "B St", "Hood", "DLBA Owned Lot"] for m in miles]
    sites.append([ORIGIN[0], round(ORIGIN[1] + 9 * DEG_PER_MILE_LAT, 5), 99999, 1, 6, "900 Other Zone", "", "", "", "DLBA Owned Lot"])    # wrong zoning
    sites.append([ORIGIN[0], round(ORIGIN[1] + 15 * DEG_PER_MILE_LAT, 5), 99999, 0, 3, "1500 Other District", "", "", "", "DLBA Owned Lot"])  # wrong district
    return {"zoning": ["B4", "R1"], "sites": sites, "parcels": [[ORIGIN[0], ORIGIN[1], 0], [ORIGIN[0], ORIGIN[1] + 9 * DEG_PER_MILE_LAT, 1]]}


HERE = {"kind": "point", "lon": ORIGIN[0], "lat": ORIGIN[1]}


# ---------- core ----------
def test_targets():
    sp = {"support": 40.0, "neutral": 30.0, "oppose": 30.0}
    assert core.score(sp, "more_support_than_oppose") == 10.0 and core.met(sp, "more_support_than_oppose")
    assert core.score(sp, "majority") == 40.0 and not core.met(sp, "majority") and not core.met(sp, "two_thirds")
    assert core.met({"support": 66.7, "neutral": 0, "oppose": 33.3}, "two_thirds")


def test_diagnosis_finds_local_opposition_and_counts_what_opponents_asked_for():
    rows = [answer(p, HERE) for p in people()]
    changes = [{"persona_id": r["persona_id"], "one_change": "different location", "reaction": "Too close."} for r in rows[:15]] + \
              [{"persona_id": "x", "one_change": "smaller", "reaction": "Too big."}] * 5
    d = core.diagnose(rows, changes)
    assert d["opposition_is_local"] and d["within_1_mile"]["oppose"] == 100.0 and d["beyond_1_mile"]["oppose"] == 0.0
    assert [b["label"] for b in d["bands"]] == [b[0] for b in core.BANDS] and sum(b["n"] for b in d["bands"]) == 400
    assert d["opponents_asked"]["one_change"][0] == {"change": "different location", "count": 15, "share": 75.0}
    assert d["opponent_reasons"][0] == {"reason": "noise", "share": 100.0} and not d["target_met"]
    assert any("concentrated near the site" in s for s in d["sentences"])


def test_opposition_that_does_not_depend_on_distance_is_not_local():
    rows = [{**answer(p, HERE), "stance": "oppose" if i % 2 else "support", "reason": "noise"} for i, p in enumerate(people())]
    assert not core.diagnose(rows)["opposition_is_local"]


def test_levers_follow_what_opponents_asked_for():
    rows = [answer(p, HERE) for p in people()]
    said = lambda *pairs: [{"persona_id": "x", "one_change": k, "reaction": "r"} for k, n in pairs for _ in range(n)]
    assert core.choose_levers(core.diagnose(rows, said(("smaller", 9), ("different location", 3))), spec())[0] == ["size", "location", "hours"]
    assert core.choose_levers(core.diagnose(rows, said(("different location", 9), ("limited hours", 3))), spec())[0] == ["location", "hours", "size"]
    assert core.choose_levers(core.diagnose(rows, None), spec())[0] == ["location", "size", "hours"]
    d = core.diagnose(rows, said(("community benefits", 6), ("different location", 4)))
    assert core.choose_levers(d, spec())[0] == ["location", "size", "hours"] and d["levers_asked_for"] == ["location"] and d["asked_for_but_not_tried"][0].startswith("community benefits (60.0% of opponents asked)")
    no_hours = spec(); no_hours["actions"][0]["type"] = "add_building"
    d = core.diagnose(rows, said(("limited hours", 7), ("different location", 3)))
    assert core.choose_levers(d, no_hours)[0] == ["location", "size"] and "no hours setting" in d["asked_for_but_not_tried"][0]
    flat = [{**r, "stance": "oppose" if i % 2 else "support"} for i, r in enumerate(rows)]
    levers, why = core.choose_levers(core.diagnose(flat, said(("nothing", 9), ("smaller", 1))), spec())
    assert levers == [] and "not fixable" in why
    happy = [{**r, "stance": "support"} for r in rows]
    assert core.choose_levers(core.diagnose(happy), spec()) == ([], "no correction needed: the target is already met")


def test_location_candidates_are_real_lots_same_zoning_same_districts_and_spread_out():
    cands, note = core.location_candidates(spec(), index())
    assert note["original_zoning"] == "B4" and note["lots_in_pool"] == 10
    names = [c["name"] for c in cands]
    assert "20 Test St, between A St and B St" not in names           # 0.2 miles: too close to the original
    assert not any("Other" in n for n in names)                         # wrong zoning district, wrong council district
    assert ("200 Test St, between A St and B St" in names) != ("220 Test St, between A St and B St" in names)   # 0.2 miles apart: only one
    for a in cands:
        for b in cands:
            if a is not b:
                assert proximity.distance_m(a["lon"], a["lat"], {"kind": "point", "lon": b["lon"], "lat": b["lat"]}) >= 0.5 * core.MILE_M - 1


def test_setting_candidates_use_only_values_the_action_allows():
    size = core.setting_candidates(spec(), "size")
    assert [c["value"] for c in size] == [1500, 1000, 500] and all(c["constraint_id"] == "seats" for c in size)
    hours = core.setting_candidates(spec(), "hours")
    assert [c["value"] for c in hours] == ["afternoon"]


def test_apply_candidate_changes_one_thing_and_never_the_what():
    base = spec()
    cand = core.location_candidates(base, index())[0][0]
    new = core.apply_candidate(base, cand)
    by = {c["id"]: c for c in new["actions"][0]["constraints"]}
    assert by["what"] == {c["id"]: c for c in base["actions"][0]["constraints"]}["what"]
    assert by["where"]["value"].startswith(cand["name"]) and by["where"]["source"] == "edited" and f"{cand['lat']:.5f}" in by["where"]["value"]
    assert by["seats"]["value"] == 2000 and new["version"] == 2 and base["version"] == 1
    smaller = core.apply_candidate(base, core.setting_candidates(base, "size")[1])
    assert {c["id"]: c for c in smaller["actions"][0]["constraints"]}["seats"]["value"] == 1000


def test_predictor_recovers_the_pattern_and_prefers_emptier_places():
    ppl = people()
    pred = core.Predictor([[answer(p, HERE) for p in ppl]])
    same = pred.predict(HERE, ppl)
    actual = core.split([answer(p, HERE) for p in ppl])
    assert abs(same["oppose"] - actual["oppose"]) < 0.2 and abs(same["support"] - actual["support"]) < 0.2
    edge = {"kind": "point", "lon": ORIGIN[0], "lat": ORIGIN[1] - 2 * DEG_PER_MILE_LAT}      # 2 miles south: nobody within a mile
    assert pred.predict(edge, ppl)["oppose"] == 0.0 and pred.predict(edge, ppl)["opposed_within_quarter_mile"] == 0.0


def test_who_lives_near():
    blocks = [[ORIGIN[0], ORIGIN[1], 120, 150], [ORIGIN[0], ORIGIN[1] + 0.5 * DEG_PER_MILE_LAT, 300, 400], [ORIGIN[0], ORIGIN[1] + 5 * DEG_PER_MILE_LAT, 999, 999]]
    prof = core.near_profile(HERE, people(), blocks)
    assert prof["adults_within_quarter_mile"] == 120 and prof["adults_within_1_mile"] == 420
    assert prof["simulated_residents_within_1_mile"] == 300 and prof["renters_pct"] == 50.0 and prof["no_car_pct"] == 25.0


# ---------- the loop ----------
class Table:
    def __init__(self):
        self.items = {}

    def get_item(self, Key, **kw):
        return {"Item": copy.deepcopy(self.items[Key["run_id"]])} if Key["run_id"] in self.items else {}

    def put_item(self, Item):
        self.items[Item["run_id"]] = copy.deepcopy(Item)


@pytest.fixture
def world(monkeypatch):
    table, ppl, started = Table(), people(), []
    monkeypatch.setattr(runs, "_table", lambda: table)
    monkeypatch.setattr(loop, "personas_for", lambda districts: {p["persona_id"]: p for p in ppl})
    monkeypatch.setattr(loop, "site_index", lambda: index())
    monkeypatch.setattr(loop, "blocks", lambda: [[p["home_lon"], p["home_lat"], 10, 12] for p in ppl])
    monkeypatch.setattr(loop, "invoke", lambda payload: None)

    def fake_launch(sp, mode=None, correction_id=None, stopped=None):
        """A finished run: every resident answers by the synthetic rule for wherever the proposal now is."""
        sp = copy.deepcopy(sp)
        where = next(c for c in sp["actions"][0]["constraints"] if c["id"] == "where")
        if "resolved" not in where or "(" in str(where["value"]):
            import re
            m = re.search(r"\((-?\d+\.\d+), (-?\d+\.\d+)\)\s*$", str(where["value"]))
            if m:
                where["resolved"] = {"name": where["value"].split(" (")[0], "lon": float(m.group(2)), "lat": float(m.group(1)), "district": 6}
        place = {"kind": "point", "lon": where["resolved"]["lon"], "lat": where["resolved"]["lat"]}
        seats = next(c for c in sp["actions"][0]["constraints"] if c["id"] == "seats")["value"]
        run_id = f"run-{len(started)}"
        rows = [answer(p, place, world_state.get("far", "support")) for p in ppl]
        if world_state.get("size_matters") and seats <= 1000:
            rows = [{**r, "stance": "support"} for r in rows]
        sp["summary"] = f"Proposal: a venue at {where['resolved']['name']} in District 6."
        table.items[run_id] = {"run_id": run_id, "status": "done", "mode": mode or "fast", "batches": 1, "spec_json": json.dumps(sp),
                               "result_json": json.dumps({"run_stats": {"model_cost_usd": 0.05, "seconds": 20}, **({"stopped": [world_state["stop"]]} if world_state.get("stop") and len(started) >= 2 else {})})}
        table.items[f"resp#{run_id}#0"] = {"rows": json.dumps(rows)}
        started.append((run_id, sp, correction_id))
        return 202, {"run_id": run_id, "mode": mode or "fast", "total": len(ppl)}

    world_state = {}
    monkeypatch.setattr(runs, "launch", fake_launch)
    fake_launch(spec(), "fast")                       # the user's original run: run-0
    return {"table": table, "started": started, "state": world_state, "people": ppl}


def drive(world, changes, target="more_support_than_oppose", limit=20):
    state = {"correction_id": "c1", "status": "running", "stage": "diagnosing", "target": target, "target_text": core.TARGETS[target],
             "original_run_id": "run-0", "mode": "fast", "max_reruns": core.MAX_RERUNS, "reruns_used": 0, "attempts": [], "created": 0}
    loop.save(state)
    loop.first_step(state, ask=lambda *a, **k: changes)
    steps = 0
    while loop.load("c1")["status"] == "running" and steps < limit:
        state = loop.load("c1")
        loop.run_finished(state, state["waiting"]["run_id"])
        steps += 1
    return loop.load("c1")


def nobody_supports(world):
    """Residents far from the site are neutral, not supportive, in the original run and in every rerun."""
    world["state"]["far"] = "neutral"
    world["table"].items["resp#run-0#0"] = {"rows": json.dumps([answer(p, HERE, "neutral") for p in world["people"]])}


def said(k, n=20):
    return [{"persona_id": "x", "one_change": k, "reaction": "r"}] * n


def test_loop_moves_the_site_and_stops_when_the_target_is_reached(world):
    out = drive(world, said("different location"))
    assert out["status"] == "done" and out["stop_reason"] == "target reached"
    assert out["original"]["split"]["oppose"] == 75.0 and out["original"]["score"] < 0
    assert out["levers"][0] == "location" and out["spread_pts"] == 0.0
    last = out["attempts"][-1]
    assert last["lever"] == "location" and last["meets_target"] and last["split"]["support"] > last["split"]["oppose"]
    assert last["predicted"] is not None and last["who_lives_near"]["adults_within_1_mile"] >= 0 and last["site"]["zoning"] == "B4"
    assert out["best"]["rerun"] == last["rerun"] and "Best of" in out["limits"][0]
    assert world["started"][1][2] == "c1" and len(world["started"]) == 2 + len(out["attempts"])      # original, repeat, reruns
    assert "spec" not in out and "candidates" not in out


def test_loop_never_exceeds_five_reruns(world, monkeypatch):
    nobody_supports(world)                            # the target cannot be reached
    hopeful = lambda self, place, ppl: {"support": 0.0 if abs(place["lat"] - ORIGIN[1]) < 1e-9 else 60.0, "neutral": 30.0, "oppose": 10.0, "opposed_within_quarter_mile": 0.0}
    monkeypatch.setattr(core.Predictor, "predict", hopeful)
    out = drive(world, said("different location"), target="majority")           # the predictor is (wrongly) hopeful about every other site
    assert out["status"] == "done" and out["stop_reason"] == "5 reruns used"
    assert len(out["attempts"]) == core.MAX_RERUNS == 5 and out["reruns_used"] == 5
    assert len(world["started"]) == 2 + 5 and all(not a["meets_target"] for a in out["attempts"])
    assert out["best"]["label"] == "your original proposal"


def test_loop_stops_early_when_no_site_is_predicted_to_do_better(world):
    nobody_supports(world)
    out = drive(world, said("different location"), target="majority")
    levers = [x["lever"] for x in out["attempts"]]
    assert 1 <= levers.count("location") < 5 and len(levers) <= 5          # the site search ends early ...
    assert levers[levers.count("location"):] and "location" not in levers[levers.count("location"):]      # ... and the other levers get their turn


def test_loop_tries_size_when_opponents_ask_for_smaller(world):
    world["state"]["size_matters"] = True
    out = drive(world, said("smaller"))
    assert out["levers"][0] == "size" and out["stop_reason"] == "target reached"
    assert [a["lever"] for a in out["attempts"]] == ["size", "size"] and "1,000" in out["attempts"][-1]["label"]


def test_loop_stops_when_the_spending_limit_stops_a_run(world):
    world["state"]["stop"] = "stopped: daily spending limit reached"
    nobody_supports(world)
    out = drive(world, said("different location"), target="majority")
    assert out["status"] == "done" and out["stop_reason"].startswith("spending limit reached") and len(out["attempts"]) == 0


def test_loop_does_nothing_when_residents_already_agree(world):
    world["table"].items["resp#run-0#0"] = {"rows": json.dumps([{**answer(p, HERE), "stance": "support"} for p in world["people"]])}
    out = drive(world, None)
    assert out["stop_reason"] == "no correction needed: the target is already met" and len(world["started"]) == 1


def test_report_matches_the_contract(world):
    from contracts.validate import validate
    assert validate("correction_result", drive(world, said("different location"))) == []
    assert validate("correction_result", json.load(open("fixtures/correction_result.busgarage.json", encoding="utf-8"))) == []


# ---------- what residents asked for, the follow-up question, and sites with few neighbours ----------
def test_sites_with_the_fewest_adults_within_a_mile_come_first():
    blocks = [[ORIGIN[0], ORIGIN[1] + m * DEG_PER_MILE_LAT, n] for m, n in ((6, 900), (8, 50), (12, 400), (15.5, 0), (18, 10))]
    assert core.adults_near([(ORIGIN[0], ORIGIN[1] + 6.2 * DEG_PER_MILE_LAT)], blocks) == [(900, 900)]
    assert core.adults_near([(ORIGIN[0], ORIGIN[1] + 6.5 * DEG_PER_MILE_LAT)], blocks) == [(900, 0)]
    cands, note = core.location_candidates(spec(), index(), blocks=blocks)
    assert [c["name"].split(" ")[0] for c in cands] == ["1550", "1800", "800", "1200", "600"]      # the five largest lots, emptiest first
    assert "fewest adults living within a mile first" in note["rule"]


def test_what_those_who_asked_for_a_change_did_after_it_was_made():
    asked = [{"persona_id": f"p{i}", "one_change": "limited hours" if i < 6 else "different location"} for i in range(10)]
    rerun = [{"persona_id": f"p{i}", "stance": "oppose" if i < 5 else "neutral", "reason": "noise", "distance_m": 100 * i} for i in range(9)]
    out = core.asked_outcome(asked, rerun, "hours")
    assert out["change_made"] == "limited hours"
    assert out["by_request"][0] == {"change": "limited hours", "asked_for_it": 6, "answered_rerun": 6, "support": 0, "neutral": 1, "oppose": 5}
    assert out["by_request"][1] == {"change": "different location", "asked_for_it": 4, "answered_rerun": 3, "support": 0, "neutral": 3, "oppose": 0}


def test_follow_up_goes_to_those_who_got_what_they_asked_for_and_to_new_opponents():
    asked = [{"persona_id": "a", "one_change": "limited hours"}, {"persona_id": "b", "one_change": "different location"}, {"persona_id": "c", "one_change": "limited hours"}]
    row = lambda i, s, d=500: {"persona_id": i, "stance": s, "reason": "noise", "distance_m": d}
    original = [row("a", "oppose"), row("b", "oppose"), row("c", "oppose"), row("d", "neutral"), row("e", "support")]
    rerun = [row("a", "oppose", 900), row("b", "oppose"), row("c", "neutral"), row("d", "oppose", 300), row("e", "oppose", 200), row("z", "oppose")]
    t = core.follow_up_targets(asked, original, rerun, "hours")
    assert [(x["persona_id"], x["group"]) for x in t] == [("a", "asked_for_it"), ("e", "new_opponent"), ("d", "new_opponent")]
    assert t[0]["asked_for"] == "limited hours" and t[1]["before"] == "support"
    assert len(core.follow_up_targets(asked, original, rerun, "hours", cap=1)) == 2
    answers = {"change": [{"persona_id": "a", "why": "Still loud.", "would_change": "nothing"}, {"persona_id": "d", "why": "Now it is near me.", "would_change": "different location"}]}
    s = core.follow_up_summary(t, answers, {"change": ("why", ["would_change"])})
    assert s["asked"] == {"asked_for_it": 1, "new_opponent": 2} and s["wordings"]["change"]["answered"] == 2
    assert s["wordings"]["change"]["would_change"]["asked_for_it"] == {"nothing": 1} and s["wordings"]["change"]["distinct_sentences"] == 2
    assert s["wordings"]["change"]["sentences"][0] == {"group": "asked_for_it", "text": "Still loud."}


def test_follow_up_wordings_and_their_checks():
    from correction import ask
    ppl = {p["persona_id"]: {**p, "sex": "F", "hh_income": 30000, "years_in_home": 5, "hh_size": 2, "children": 0, "commute_mode": "car",
                             "employment": "employed", "education": "hs", "building_type": "single"} for p in people()[:2]}
    t = [{"persona_id": "d6-0000", "group": "asked_for_it", "before": "oppose", "before_reason": "noise", "after_reason": "noise", "asked_for": "limited hours"}]
    text = ask.follow_up_message("stance", t, ppl, spec(), proximity.places_of(spec()), "Change event time to Afternoon")
    assert "What was changed from the original version: Change event time to Afternoon" in text and "said: limited hours" in text
    assert "-> explanation" in text and "-> scope" in text and "-> acceptable_version" in text
    ok = {"persona_id": "d6-0000", "explanation": "I object to the noise.", "scope": "only near my home", "acceptable_version": "yes"}
    assert ask.check_follow_up("stance", ok, {"d6-0000"}) is None
    assert ask.check_follow_up("stance", {**ok, "scope": "maybe"}, {"d6-0000"}) == "scope not in list"
    assert ask.check_follow_up("stance", {**ok, "explanation": "x" * 500}, {"d6-0000"}) == "explanation missing or too long"
    assert ask.check_follow_up("change", {"persona_id": "d6-0000", "why": "Too loud.", "would_change": "nothing"}, {"d6-0000"}) is None
    assert ask.check_follow_up("change", {"persona_id": "nope", "why": "Too loud.", "would_change": "nothing"}, {"d6-0000"}) == "unknown persona_id"


def test_loop_saves_each_opponents_answers_and_asks_the_follow_up_after_a_rerun(world):
    nobody_supports(world)
    rows = json.loads(world["table"].items["resp#run-0#0"]["rows"])
    changes = [{"persona_id": r["persona_id"], "one_change": "different location", "reaction": "Too close."} for r in rows if r["stance"] == "oppose"][:40]
    calls = []

    def fake(variant, targets, people, sp, places, change, run_id, per_call):
        calls.append((variant, len(targets), change))
        if variant == "change":
            return [{"persona_id": t["persona_id"], "why": "It is near me now.", "would_change": "nothing"} for t in targets]
        return [{"persona_id": t["persona_id"], "explanation": "I do not want it near homes.", "scope": "only near my home", "acceptable_version": "yes"} for t in targets]

    state = {"correction_id": "c1", "status": "running", "stage": "diagnosing", "target": "majority", "target_text": core.TARGETS["majority"],
             "original_run_id": "run-0", "mode": "fast", "max_reruns": core.MAX_RERUNS, "reruns_used": 0, "attempts": [], "created": 0, "follow_up": "both"}
    loop.save(state)
    loop.first_step(state, ask=lambda *a, **k: changes)
    assert len(loop.load_extra("c1", "asked")) == 40
    for _ in range(10):
        state = loop.load("c1")
        if state["status"] != "running":
            break
        loop.run_finished(state, state["waiting"]["run_id"], ask=fake)
    out = loop.load("c1")
    a = out["attempts"][0]
    assert a["asked_then"]["change_made"] == "different location" and a["asked_then"]["by_request"][0]["asked_for_it"] == 40
    assert a["asked_then"]["by_request"][0]["oppose"] == 0            # the site moved away from everyone who asked
    assert a["follow_up"]["asked"]["asked_for_it"] == 0 and a["follow_up"]["asked"]["new_opponent"] > 0
    assert set(a["follow_up"]["wordings"]) == {"change", "stance"} and a["follow_up"]["wordings"]["stance"]["scope"]["all"] == {"only near my home": a["follow_up"]["asked"]["new_opponent"]}
    assert {c[0] for c in calls} == {"change", "stance"} and calls[0][2].startswith("Move it to the Land Bank lot")
    saved = loop.load_extra("c1", "followup#1")
    assert len(saved["targets"]) == a["follow_up"]["asked"]["new_opponent"] and set(saved["answers"]) == {"change", "stance"}
    got = json.loads(loop.get({"pathParameters": {"id": "c1"}, "queryStringParameters": {"answers": "1"}})["body"])
    assert len(got["asked_answers"]) == 40 and "1" in got["follow_up_answers"]
    from contracts.validate import validate
    assert validate("correction_result", out) == []
