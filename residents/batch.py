"""Ask one batch of residents (25) about a confirmed proposal with one Bedrock call.

    main(event) -> {"status", "asked", "valid", "retried", "dropped", "calls", "quotes_requested"}

event: {"run_id", "batch", "persona_ids", "spec": {"spec_id", "summary"}, "impacts_computed": bool,
        "impact_lines": {persona_id: [line, ...]}}

- Residents come from s3://$DATA_BUCKET/personas/district_{n}.json (data/personas/build.py).
- Every model call goes through shared.budget.converse (hard spending limit) and shared.aws.bedrock_runtime.
- Each answer is checked with validate.check; residents with a missing or invalid answer are asked once more
  in a smaller call; anyone still invalid is dropped and counted.
- Valid answers are stored in the runs table under `resp#<run_id>#<batch>`, each with the resident traits
  that aggregate.py needs. Only counts go back through Step Functions (its payload limit is 256 KB).
"""
from __future__ import annotations

import json
import os
import re
import time

from residents import prompt, validate

MODEL_ID = os.environ.get("RESIDENT_MODEL_ID", "")
MAX_TOKENS_PER_RESIDENT = 110          # stance + reason is about 30 output tokens; a quote adds about 50
KEEP = ("district", "block_geoid", "weight", "age", "tenure", "vehicles")   # traits aggregate.py groups by
_personas: dict[int, dict] = {}


class BatchError(RuntimeError):
    pass


def load_personas(districts: set[int]) -> dict[str, dict]:
    import boto3

    local = os.environ.get("PERSONAS_DIR")
    out = {}
    for d in sorted(districts):
        if d not in _personas:
            if local:
                rows = json.loads(open(os.path.join(local, f"district_{d}.json"), encoding="utf-8").read())
            else:
                body = boto3.client("s3").get_object(Bucket=os.environ["DATA_BUCKET"], Key=f"personas/district_{d}.json")["Body"].read()
                rows = json.loads(body)
            _personas[d] = {r["persona_id"]: r for r in rows}
        out.update(_personas[d])
    return out


def parse(text: str) -> list:
    """The model is asked for a JSON array only; tolerate a code fence or stray text around it."""
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return []
    return data if isinstance(data, list) else []


def ask(client, run_id, personas: list[dict], spec: dict, impact_lines: dict, table=None) -> tuple[dict, dict]:
    """One model call. Returns ({persona_id: valid answer}, quote flags)."""
    from shared import budget

    message, flags = prompt.build(personas, spec, impact_lines, quotes=False)
    for attempt in range(4):
        try:
            resp = budget.converse(client, run_id, table, modelId=MODEL_ID, system=[{"text": prompt.SYSTEM_STANCE}],
                                   messages=[{"role": "user", "content": [{"text": message}]}],
                                   inferenceConfig={"maxTokens": 200 + MAX_TOKENS_PER_RESIDENT * len(personas)})
            break
        except Exception as e:                       # throttling: wait and retry; anything else is raised
            if "Throttling" not in type(e).__name__ and "Throttling" not in str(e) or attempt == 3:
                raise
            time.sleep(2 ** attempt)
    text = "".join(b.get("text", "") for b in resp["output"]["message"]["content"])
    ids, good = set(flags), {}
    for item in parse(text):
        pid = item.get("persona_id") if isinstance(item, dict) else None
        if pid in ids and pid not in good and validate.check(item, ids, False) is None:
            good[pid] = item
    return good, flags


def ask_quotes(client, run_id, personas: list[dict], answers: dict, spec: dict, table=None) -> dict:
    """Second call, after stances are fixed: one sentence from each sampled resident. Returns {persona_id: quote}.
    A missing or over-long quote just leaves that resident without one; it never drops their answer."""
    from shared import budget

    resp = budget.converse(client, run_id, table, modelId=MODEL_ID, system=[{"text": prompt.SYSTEM_QUOTES}],
                           messages=[{"role": "user", "content": [{"text": prompt.build_quotes(personas, answers, spec)}]}],
                           inferenceConfig={"maxTokens": 200 + MAX_TOKENS_PER_RESIDENT * len(personas)})
    text = "".join(b.get("text", "") for b in resp["output"]["message"]["content"])
    ids, out = {p["persona_id"] for p in personas}, {}
    for item in parse(text):
        if isinstance(item, dict) and item.get("persona_id") in ids and isinstance(item.get("quote"), str):
            q = " ".join(item["quote"].split())
            if 0 < len(q) <= 200:
                out[item["persona_id"]] = q
    return out


def main(event: dict, context=None, client=None, table=None) -> dict:
    from shared import budget
    from shared.aws import bedrock_runtime

    if not MODEL_ID:
        raise BatchError("RESIDENT_MODEL_ID is not set")
    ids = event["persona_ids"]
    people = load_personas({int(i[1:].split("-")[0]) for i in ids})
    missing = [i for i in ids if i not in people]
    if missing:
        raise BatchError(f"{len(missing)} persona ids are not in the persona files, e.g. {missing[0]}")
    personas = [people[i] for i in ids]
    # No engine result for this proposal: leave the impact line out (prompt.build says so to the model).
    # Never tell a resident there is "no change" that was not computed.
    lines = (event.get("impact_lines") or {}) if event.get("impacts_computed") else None
    client = client or bedrock_runtime()
    stats = {"status": "ok", "asked": len(ids), "retried": 0, "calls": 0}
    try:
        good, flags = ask(client, event["run_id"], personas, event["spec"], lines, table)
        stats["calls"] += 1
        again = [p for p in personas if p["persona_id"] not in good]
        if again:
            stats["retried"] = len(again)
            more, _ = ask(client, event["run_id"], again, event["spec"], lines, table)
            stats["calls"] += 1
            good.update(more)
        quoted = [p for p in personas if flags[p["persona_id"]] and p["persona_id"] in good]
        if quoted:
            for pid, q in ask_quotes(client, event["run_id"], quoted, good, event["spec"], table).items():
                good[pid]["quote"] = q
            stats["calls"] += 1
    except budget.BudgetError as e:
        return {**stats, "status": f"stopped: {e}", "valid": 0, "dropped": len(ids), "quotes_requested": 0}
    rows = [{**good[i], **{k: people[i][k] for k in KEEP}} for i in ids if i in good]
    stats.update(valid=len(rows), dropped=len(ids) - len(rows), quotes_requested=sum(flags.values()))
    store(event["run_id"], event["batch"], rows, table)
    return stats


def store(run_id: str, batch: int, rows: list[dict], table=None) -> None:
    if table is None:
        import boto3
        table = boto3.resource("dynamodb").Table(os.environ["RUNS_TABLE"])
    table.put_item(Item={"run_id": f"resp#{run_id}#{batch}", "rows": json.dumps(rows)})
