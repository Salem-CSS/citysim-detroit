"""Run pipeline Lambdas (BUILD.md Steps 2 + 8). Thin glue: real work lives in engine/ and residents/.

POST /runs        start_run   -> writes a pending row, starts the state machine, returns {run_id}
                  body {spec, mode}: mode "fast" = 25 residents share a model call, "accurate" = one resident per call
GET  /runs/{id}   get_run     -> the row (status, stage, mode, total, answered, result)
GET  /runs/{id}/answers  get_answers -> each resident's own answer (contracts/run_answers.schema.json)
State machine     engine_step -> plan_batches -> Map(resident_batch, 10 at a time) -> aggregate_step

Until engine/ and residents/ are implemented, each step records `not_implemented` instead of failing,
so the whole path deploys and can be exercised end to end.
"""
from __future__ import annotations

import json
import os
import time
import uuid

CORS = {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"}
BATCH = 25
MODES = {"fast": 25, "accurate": 1}      # residents per model call


def _table():
    import boto3
    return boto3.resource("dynamodb").Table(os.environ["RUNS_TABLE"])


def _resp(code, body):
    return {"statusCode": code, "headers": CORS, "body": json.dumps(body, default=str)}


def _update(run_id, **fields):
    names = {f"#{k}": k for k in fields}
    vals = {f":{k}": (json.loads(json.dumps(v), parse_float=str) if isinstance(v, (dict, list)) else v) for k, v in fields.items()}
    _table().update_item(Key={"run_id": run_id}, UpdateExpression="SET " + ", ".join(f"#{k} = :{k}" for k in fields),
                         ExpressionAttributeNames=names, ExpressionAttributeValues=vals)


# ---------- API ----------
def start_run(event, context=None):
    import boto3
    body = json.loads(event.get("body") or "{}")
    spec = body.get("spec")
    if not spec or not spec.get("actions"):
        return _resp(400, {"error": "spec with at least one action is required"})
    residents = len(spec.get("districts", [])) * int(os.environ.get("PERSONAS_PER_DISTRICT", "500"))
    cap = int(os.environ["MAX_RESIDENTS_PER_RUN"])
    if residents > cap:
        return _resp(400, {"error": f"this run would ask {residents} residents; the limit is {cap}"})
    from agent.handler import check_places
    spec["status"] = "draft"
    spec = check_places(spec)                       # the panel may have edited places and values; re-verify and rebuild the sentence
    if spec["status"] == "needs_info":
        return _resp(400, {"error": "this proposal needs a place before it can run", "questions": spec["questions"], "spec": spec})
    spec["status"] = "confirmed"
    mode = body.get("mode") or default_mode()
    if mode not in MODES:
        return _resp(400, {"error": 'mode must be "fast" or "accurate"'})
    run_id = f"run-{uuid.uuid4().hex[:10]}"
    _table().put_item(Item={"run_id": run_id, "spec_id": spec["spec_id"], "spec_version": spec["version"], "mode": mode,
                            "total": residents, "answered": 0,
                            "status": "running", "stage": "engine", "created": int(time.time())})
    boto3.client("stepfunctions").start_execution(stateMachineArn=os.environ["STATE_MACHINE_ARN"], name=run_id,
                                                  input=json.dumps({"run_id": run_id, "spec": spec, "mode": mode, "started": int(time.time())}))
    return _resp(202, {"run_id": run_id, "mode": mode, "total": residents})


def default_mode() -> str:
    return "fast" if int(os.environ.get("RESIDENTS_PER_CALL", "1")) > 1 else "accurate"


def get_run(event, context=None):
    run_id = (event.get("pathParameters") or {}).get("id")
    item = _table().get_item(Key={"run_id": run_id}).get("Item")
    if not item or str(run_id).startswith(("spend#", "resp#")):
        return _resp(404, {"error": "no such run"})
    if "result_json" in item:                       # stored as text so numbers stay numbers
        item["result"] = json.loads(item.pop("result_json"))
    elif item.get("status") == "running":
        failed = execution_failure(run_id)
        if failed:                                  # the run died inside Step Functions: say so instead of "running" forever
            item.update(status="failed", stage="failed", error=failed)
    return _resp(200, item)


def execution_failure(run_id: str, client=None) -> str | None:
    """None while the run's execution is running or succeeded; else a short reason. Never raises."""
    arn = os.environ.get("STATE_MACHINE_ARN", "")
    if not arn:
        return None
    try:
        import boto3
        client = client or boto3.client("stepfunctions")
        ex = client.describe_execution(executionArn=arn.replace(":stateMachine:", ":execution:") + ":" + run_id)
    except Exception:
        return None
    if ex.get("status") in ("FAILED", "TIMED_OUT", "ABORTED"):
        return f"the run {ex['status'].lower().replace('_', ' ')} on the server" + (f" ({ex['error']})" if ex.get("error") else "")
    return None


def get_answers(event, context=None):
    """Every resident's own answer for a run: what the map colours each figure with and what a click on a person shows.
    Works while the run is still going (the answers stored so far)."""
    run_id = (event.get("pathParameters") or {}).get("id")
    table = _table()
    item = None if str(run_id).startswith(("spend#", "resp#")) else table.get_item(Key={"run_id": run_id}).get("Item")
    if not item:
        return _resp(404, {"error": "no such run"})
    rows = read_rows(table, run_id, int(item.get("batches", 0)))
    keep = ("persona_id", "stance", "reason", "quote", "distance_m")
    return _resp(200, {"run_id": run_id, "status": item.get("status"), "mode": item.get("mode"),
                       "answers": [{k: r[k] for k in keep if r.get(k) is not None} for r in rows]})


def read_rows(table, run_id: str, batches: int) -> list[dict]:
    rows = []
    for n in range(batches):
        item = table.get_item(Key={"run_id": f"resp#{run_id}#{n}"}, ConsistentRead=True).get("Item")
        rows += json.loads(item["rows"]) if item else []
    return rows


# ---------- state machine steps ----------
def engine_step(event, context=None):
    from engine.handler import handler as engine
    out = engine({**event["spec"], "status": "confirmed"})
    status = out["status"]
    _update(event["run_id"], stage="residents", engine_status=status)
    return {**event, "engine": out, "engine_status": status}


def plan_batches(event, context=None):
    """Split the personas for the chosen districts into 25-resident batches (ids only; residents load from S3)."""
    per = int(os.environ.get("PERSONAS_PER_DISTRICT", "500"))
    ids = [f"d{d}-{i:04d}" for d in event["spec"].get("districts", []) for i in range(per)]
    from engine import proximity
    spec = {"spec_id": event["spec"]["spec_id"], "summary": event["spec"]["summary"]}
    places = proximity.places_of(event["spec"])
    computed, lines = False, {}       # per-resident lines are built in the batch from places and street effects
    effects = (event.get("engine") or {}).get("street_effects") or []
    per_call = MODES.get(event.get("mode") or default_mode(), 1)
    batches = [{"run_id": event["run_id"], "batch": n, "spec": spec, "residents_per_call": per_call, "persona_ids": ids[i:i + BATCH], "places": places, "street_effects": effects,
                "impacts_computed": computed, "impact_lines": {p: lines[p] for p in ids[i:i + BATCH] if p in lines}}
               for n, i in enumerate(range(0, len(ids), BATCH))]
    _update(event["run_id"], batches=len(batches), total=len(ids))
    return {**event, "batches": batches}


def resident_batch(event, context=None):
    from residents import batch
    out = batch.main(event)         # answers go to the runs table; only counts come back
    _table().update_item(Key={"run_id": event["run_id"]}, UpdateExpression="ADD answered :n",       # progress for GET /runs/{id}
                         ExpressionAttributeValues={":n": int(out.get("asked", 0))})
    return out


def aggregate_step(event, context=None):
    from residents import aggregate
    run_id, results, table = event["run_id"], event.get("batch_results", []), _table()
    rows = read_rows(table, run_id, len(results))
    stats = {"residents": sum(b.get("asked", 0) for b in results), "retried": sum(b.get("retried", 0) for b in results),
             "bedrock_calls": sum(b.get("calls", 0) for b in results),
             "quotes_requested": sum(b.get("quotes_requested", 0) for b in results),
             "seconds": int(time.time()) - int(event.get("started", time.time()))}
    result = aggregate.main(rows, event["spec"], stats)
    stopped = sorted({b["status"] for b in results if str(b.get("status", "")).startswith("stopped")})
    eng = event.get("engine") or {}
    result["segments"] = eng.get("segments", [])
    for k in ("trips", "transit"):
        if k in eng:
            result[k] = eng[k]
    result["engine_notes"] = eng.get("notes", [])
    result.update(run_id=run_id, status="done", engine_status=event.get("engine_status"),
                  created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    if stopped:
        result["stopped"] = stopped                 # for example the spending limit was reached mid-run
    spend = table.get_item(Key={"run_id": f"spend#{run_id}"}, ConsistentRead=True).get("Item") or {}
    result["run_stats"]["mode"] = event.get("mode") or default_mode()
    result["run_stats"]["model_cost_usd"] = round(int(spend.get("micro_usd", 0)) / 1e6, 4)
    _update(run_id, status="done", stage="done", result_json=json.dumps(result), finished=int(time.time()))
    return {"run_id": run_id, "status": "done"}
