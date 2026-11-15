"""Correction engine loop (BACKEND_PLAN.md section 15). Event driven: no Lambda waits for a run.

    POST /corrections {run_id, target}   start        -> {correction_id}; the first step runs in the background
    GET  /corrections/{id}               get          -> progress and the report
    step(event)                                        one step of the loop; invoked asynchronously

Steps
    {"correction_id", "start": true}       diagnose the original run, choose levers, build candidates, then start a
                                           repeat of the original proposal (to measure run-to-run spread)
    {"correction_id", "run_id"}            a run this correction started has finished (sent by infra/runs.aggregate_step):
                                           record it, then either stop or start the next rerun

Hard caps, checked here and nowhere else: at most core.MAX_RERUNS reruns per correction; every run is subject to
the run and day spending limits in shared/budget.py, and a run that was stopped by them ends the correction.

State lives in the runs table under `corr#<id>` as one JSON document; the report is that document.
"""
from __future__ import annotations

import json
import os
import time
import uuid

from correction import core
from infra import runs

_index: dict = {}
_blocks: list = []


def _table():
    return runs._table()


def _load_json(key: str, env_file: str) -> dict:
    local = os.environ.get(env_file)
    if local:
        return json.loads(open(local, encoding="utf-8").read())
    import boto3
    return json.loads(boto3.client("s3").get_object(Bucket=os.environ["DATA_BUCKET"], Key=key)["Body"].read())


def site_index() -> dict:
    if not _index:
        _index.update(_load_json("processed/correction/sites.json", "SITES_FILE"))
    return _index


def blocks() -> list:
    if not _blocks:
        _blocks.extend(_load_json("processed/engine/engine_data.json", "ENGINE_DATA_FILE")["blocks"])
    return _blocks


def save(state: dict) -> None:
    state["updated"] = int(time.time())
    _table().put_item(Item={"run_id": f"corr#{state['correction_id']}", "state_json": json.dumps(state)})


def load(cid: str) -> dict | None:
    item = _table().get_item(Key={"run_id": f"corr#{cid}"}, ConsistentRead=True).get("Item")
    return json.loads(item["state_json"]) if item else None


def run_rows(run_id: str) -> tuple[dict, list[dict]]:
    table = _table()
    item = table.get_item(Key={"run_id": run_id}, ConsistentRead=True).get("Item") or {}
    return item, runs.read_rows(table, run_id, int(item.get("batches", 0)))


def personas_for(districts: list[int]) -> dict:
    from residents import batch
    return batch.load_personas(set(districts))


# ---------- API ----------
def start(event, context=None):
    body = json.loads(event.get("body") or "{}")
    run_id, target = body.get("run_id"), body.get("target") or "more_support_than_oppose"
    if target not in core.TARGETS:
        return runs._resp(400, {"error": f"target must be one of {', '.join(core.TARGETS)}"})
    item = _table().get_item(Key={"run_id": str(run_id)}).get("Item") if run_id else None
    if not item or item.get("status") != "done" or "spec_json" not in item:
        return runs._resp(400, {"error": "run_id must be a finished run started after the correction engine was deployed"})
    cid = f"corr-{uuid.uuid4().hex[:10]}"
    save({"correction_id": cid, "status": "running", "stage": "diagnosing", "target": target, "target_text": core.TARGETS[target],
          "original_run_id": run_id, "mode": item.get("mode") or runs.default_mode(), "max_reruns": core.MAX_RERUNS,
          "reruns_used": 0, "attempts": [], "created": int(time.time())})
    invoke({"correction_id": cid, "start": True})
    return runs._resp(202, {"correction_id": cid})


def get(event, context=None):
    state = load((event.get("pathParameters") or {}).get("id") or "")
    return runs._resp(200, state) if state else runs._resp(404, {"error": "no such correction"})


def invoke(payload: dict) -> None:
    import boto3
    boto3.client("lambda").invoke(FunctionName=os.environ["CORRECTION_FUNCTION"], InvocationType="Event", Payload=json.dumps(payload).encode())


# ---------- the loop ----------
def step(event, context=None):
    state = load(event["correction_id"])
    if not state or state["status"] != "running":
        return {"ignored": True}
    try:
        if event.get("start"):
            first_step(state)
        else:
            run_finished(state, event["run_id"])
    except Exception as e:                                   # never leave a correction hanging as "running"
        stop(state, f"stopped by an error: {type(e).__name__}: {e}"[:300])
        raise
    return {"correction_id": state["correction_id"], "status": state["status"], "stage": state.get("stage")}


def first_step(state: dict, ask=None) -> None:
    from correction import ask as ask_mod
    from engine import proximity

    item, rows = run_rows(state["original_run_id"])
    spec = json.loads(item["spec_json"])
    state["spec"], state["proposal"] = spec, spec["summary"]
    people = personas_for(spec["districts"])
    places = proximity.places_of(spec)
    quick = core.diagnose(rows, None, state["target"])
    changes = None
    if not quick["target_met"] and any(r["stance"] == "oppose" for r in rows):
        per_call = runs.MODES.get(state["mode"], 1)
        fn = ask or (lambda *args: ask_mod.ask_opponents(*args, at_once=8 if per_call == 1 else 2))
        changes = fn(rows, people, spec, places, f"{state['correction_id']}-ask", per_call)
    diag = core.diagnose(rows, changes, state["target"])
    state["diagnosis"] = diag
    state["original"] = {"run_id": state["original_run_id"], "split": diag["overall"], "score": core.score(diag["overall"], state["target"]),
                         "bands": diag["bands"]}
    if places and places[0]["kind"] == "point":
        state["original"]["who_lives_near"] = core.near_profile(places[0], list(people.values()), blocks())
    levers, why = core.choose_levers(diag, spec)
    if not levers:
        return stop(state, why)
    state["levers"], state["lever_at"], state["candidates"] = levers, 0, []
    build_candidates(state, people)
    if not state["candidates"]:
        return stop(state, "no real alternative was found to try (no Land Bank lot in the same zoning district far enough away, and no other setting to change)")
    state["stage"] = "measuring run-to-run variation"
    save(state)
    launch(state, spec, "repeat", None)


def build_candidates(state: dict, people: dict) -> None:
    """Fill state['candidates'] for the current lever; move on to the next lever if it has none."""
    spec = state["spec"]
    while state["lever_at"] < len(state["levers"]):
        lever = state["levers"][state["lever_at"]]
        if lever == "location":
            cands, note = core.location_candidates(spec, site_index())
            state["site_rule"] = note
            for c in cands:
                c["who_lives_near"] = core.near_profile({"kind": "point", "lon": c["lon"], "lat": c["lat"]}, list(people.values()), blocks())
        else:
            cands = core.setting_candidates(spec, lever)
        tried = {a["label"] for a in state["attempts"]}
        cands = [c for c in cands if c["label"] not in tried]
        if cands:
            state["lever"], state["candidates"] = lever, cands
            return
        state["lever_at"] += 1
    state["candidates"] = []


def launch(state: dict, spec: dict, kind: str, cand: dict | None) -> None:
    """Start one run of `spec` for this correction. The run reports back through infra/runs.aggregate_step."""
    code, body = runs.launch(spec, state["mode"], correction_id=state["correction_id"])
    if code != 202:
        return stop(state, f"a rerun could not start: {body.get('error')}"
                    + ("; " + "; ".join(q["text"] for q in body.get("questions", [])) if body.get("questions") else ""))
    state["waiting"] = {"run_id": body["run_id"], "kind": kind, "candidate": cand}
    state["stage"] = "measuring run-to-run variation" if kind == "repeat" else f"rerun {state['reruns_used']} of at most {state['max_reruns']}"
    save(state)


def all_rows(state: dict) -> list[list[dict]]:
    """Answers from every run of this correction that has a place: the predictor's evidence."""
    ids = [state["original_run_id"]] + ([state["repeat"]["run_id"]] if state.get("repeat") else []) + [a["run_id"] for a in state["attempts"]]
    return [run_rows(i)[1] for i in ids]


def rank(state: dict, people: dict) -> None:
    """Predicted split for every untried location candidate, best first. Settings levers have no predictor: they
    keep their order (smallest change first)."""
    if state["lever"] != "location":
        return
    trait_name, trait = core.strongest_trait(state["diagnosis"])
    pred = core.Predictor(all_rows(state), trait)
    plist = list(people.values())
    for c in state["candidates"]:
        c["predicted"] = pred.predict({"kind": "point", "lon": c["lon"], "lat": c["lat"]}, plist)
        c["predicted_score"] = core.score(c["predicted"], state["target"])
    state["candidates"].sort(key=lambda c: (-c["predicted_score"], c["predicted"]["opposed_within_quarter_mile"]))
    state["predictor"] = {"cells": "distance band" + (f" x {trait_name}" if trait_name else ""),
                          "answers_used": pred.all[3], "min_answers_per_cell": core.MIN_CELL}


def run_finished(state: dict, run_id: str) -> None:
    waiting = state.get("waiting") or {}
    if waiting.get("run_id") != run_id:
        return
    item, rows = run_rows(run_id)
    result = json.loads(item.get("result_json") or "{}")
    sp = core.split(rows)
    people = personas_for(state["spec"]["districts"])
    state.pop("waiting", None)
    if result.get("stopped"):
        return stop(state, "spending limit reached: " + "; ".join(result["stopped"]))
    best = best_so_far(state)
    if waiting["kind"] == "repeat":
        base = state["original"]["split"]
        state["repeat"] = {"run_id": run_id, "split": sp, "score": core.score(sp, state["target"])}
        state["spread_pts"] = round(abs(core.score(sp, state["target"]) - core.score(base, state["target"])), 1)
        state["spread_note"] = ("The unchanged proposal was run twice. The two runs differ by this many points on the target measure; "
                                "a changed version only counts as better if it beats the best so far by more than that."
                                + (" In Fast mode two identical runs give nearly identical answers, so this understates how much "
                                   "a result can move when the proposal changes; use Accurate mode for a firmer comparison." if state["mode"] == "fast" else ""))
    else:
        cand = waiting["candidate"]
        sc = core.score(sp, state["target"])
        diag = core.diagnose(rows, None, state["target"])
        attempt = {"rerun": state["reruns_used"], "run_id": run_id, "lever": cand["lever"], "label": cand["label"],
                   "proposal": json.loads(item["spec_json"])["summary"], "split": sp, "score": sc,
                   "change_vs_original": round(sc - state["original"]["score"], 1), "bands": diag["bands"],
                   "predicted": cand.get("predicted"), "predicted_score": cand.get("predicted_score"),
                   "who_lives_near": cand.get("who_lives_near"), "site": {k: cand[k] for k in ("name", "neighborhood", "district", "zoning", "lot_sqft", "lon", "lat") if k in cand},
                   "beats_best_beyond_spread": sc - best["score"] > state["spread_pts"], "meets_target": core.met(sp, state["target"]),
                   "cost_usd": (result.get("run_stats") or {}).get("model_cost_usd"), "seconds": (result.get("run_stats") or {}).get("seconds")}
        state["attempts"].append(attempt)
        if attempt["meets_target"]:
            return stop(state, "target reached")
    if state["reruns_used"] >= state["max_reruns"]:
        return stop(state, f"{state['max_reruns']} reruns used")
    next_rerun(state, people)


def best_so_far(state: dict) -> dict:
    """The original, or the best rerun that beat what came before it by more than the spread."""
    best = {"label": "your original proposal", "score": state["original"]["score"], "split": state["original"]["split"], "rerun": 0}
    for a in state["attempts"]:
        if a["beats_best_beyond_spread"] and a["score"] > best["score"]:
            best = {"label": a["label"], "score": a["score"], "split": a["split"], "rerun": a["rerun"], "proposal": a["proposal"]}
    return best


def next_rerun(state: dict, people: dict) -> None:
    tried = {a["label"] for a in state["attempts"]}
    state["candidates"] = [c for c in state["candidates"] if c["label"] not in tried]
    if not state["candidates"]:
        state["lever_at"] += 1
        build_candidates(state, people)
        if not state["candidates"]:
            return stop(state, "every alternative found has been tried")
    rank(state, people)
    cand = state["candidates"][0]
    best = best_so_far(state)
    if state["lever"] == "location" and state["attempts"] and cand["predicted_score"] <= best["score"]:
        state["lever_at"] += 1                           # no remaining site is predicted to beat the best: try the next lever
        build_candidates(state, people)
        if not state["candidates"]:
            return stop(state, "no remaining candidate is predicted to beat the best so far")
        rank(state, people)
        cand = state["candidates"][0]
    state["reruns_used"] += 1
    launch(state, core.apply_candidate(state["spec"], cand), "rerun", cand)


def stop(state: dict, reason: str) -> None:
    state.update(status="done", stage="done", stop_reason=reason)
    state.pop("waiting", None)
    if "original" in state:
        state["best"] = best_so_far(state)
        state["limits"] = [f"Best of {len(state['attempts'])} version{'s' if len(state['attempts']) != 1 else ''} tried, not the best possible.",
                           "A forecast from simulated residents, not a poll.",
                           "Candidate sites share the original site's zoning district; whether the use is permitted there was not checked.",
                           "Moving a proposal changes who lives near it: compare 'who lives near' for each site before choosing one."]
    state["candidates_left"] = [{k: c.get(k) for k in ("label", "predicted", "predicted_score", "who_lives_near")} for c in state.get("candidates", [])][:8]
    state.pop("candidates", None)
    state.pop("spec", None)
    save(state)
