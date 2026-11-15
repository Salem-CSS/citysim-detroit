"""Run pipeline Lambdas (BUILD.md Steps 2 + 8). Thin glue: real work lives in engine/ and residents/.

POST /runs        start_run   -> writes a pending row, starts the state machine, returns {run_id}
GET  /runs/{id}   get_run     -> the row (status, stage, result)
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
    spec["status"] = "confirmed"
    run_id = f"run-{uuid.uuid4().hex[:10]}"
    _table().put_item(Item={"run_id": run_id, "spec_id": spec["spec_id"], "spec_version": spec["version"],
                            "status": "running", "stage": "engine", "created": int(time.time())})
    boto3.client("stepfunctions").start_execution(stateMachineArn=os.environ["STATE_MACHINE_ARN"], name=run_id,
                                                  input=json.dumps({"run_id": run_id, "spec": spec}))
    return _resp(202, {"run_id": run_id})


def get_run(event, context=None):
    run_id = (event.get("pathParameters") or {}).get("id")
    item = _table().get_item(Key={"run_id": run_id}).get("Item")
    return _resp(200, item) if item else _resp(404, {"error": "no such run"})


# ---------- state machine steps ----------
def engine_step(event, context=None):
    from engine.handler import handler as engine
    try:
        impacts, status = engine(event["spec"]), "ok"
    except NotImplementedError as e:
        impacts, status = {"lines": {}}, f"not_implemented: {e}"
    _update(event["run_id"], stage="residents", engine_status=status)
    return {**event, "impacts": impacts, "engine_status": status}


def plan_batches(event, context=None):
    """Split the personas for the chosen districts into 25-resident batches (ids only; residents load from S3)."""
    per = int(os.environ.get("PERSONAS_PER_DISTRICT", "500"))
    ids = [f"d{d}-{i:04d}" for d in event["spec"].get("districts", []) for i in range(per)]
    batches = [{"run_id": event["run_id"], "spec_id": event["spec"]["spec_id"], "persona_ids": ids[i:i + BATCH]}
               for i in range(0, len(ids), BATCH)]
    return {**event, "batches": batches}


def resident_batch(event, context=None):
    from residents import batch
    try:
        return {"responses": batch.main(event), "status": "ok"}
    except NotImplementedError as e:
        return {"responses": [], "status": f"not_implemented: {e}"}


def aggregate_step(event, context=None):
    from residents import aggregate
    responses = [r for b in event.get("batch_results", []) for r in b.get("responses", [])]
    try:
        result, status = aggregate.main(responses, event["spec"]), "done"
    except NotImplementedError as e:
        result, status = {"note": "aggregate not implemented yet", "responses": len(responses)}, f"done_stub: {e}"
    _update(event["run_id"], status=status, stage="done", result=result, finished=int(time.time()))
    return {"run_id": event["run_id"], "status": status}
