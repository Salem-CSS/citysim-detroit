"""Lambda entry for POST /scenario: plain-English question -> draft scenario spec (v2).

Request : {"question": str, "districts": [int], "spec": <current spec, optional, for follow-ups>}
Response: {"spec": <scenario_spec v2, status "draft">}

How it stays honest
- The model only picks action types and fills constraint values. It calls one tool, `submit_actions`,
  whose input schema is generated from contracts/actions.json, so it can't invent fields.
- Every value is checked here: numbers clamped to min/max, selects must be a listed option. Anything
  invalid falls back to the template default and is marked `assumed` with a note.
- The resident-facing `summary` is rebuilt from the values (contracts.spec.summary_line), never written by the model.
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from contracts.spec import TEMPLATES, new_action, summary_line

MODEL_ID = os.environ.get("AGENT_MODEL_ID", "us.amazon.nova-pro-v1:0")
SYSTEM = (Path(__file__).parent / "system_prompt.md").read_text()
CORS = {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"}


# ---------- tool schema + catalog from the contract ----------
def catalog() -> str:
    """Plain-text list of actions and their fields, generated from contracts/actions.json."""
    lines = []
    for t, a in TEMPLATES.items():
        lines.append(f"- {t} ({a['title']}):")
        for c in a["constraints"]:
            if c["type"] not in ("number", "select"):
                continue
            if c.get("options"):
                opts = "; ".join(f"{json.dumps(o['value'])} = {o['label']}" for o in c["options"])
                lines.append(f"    {c['id']} - {c['label']}. One of: {opts}. Default {json.dumps(c.get('default'))}.")
            else:
                lines.append(f"    {c['id']} - {c['label']} ({c.get('unit', '')}), number {c.get('min')}-{c.get('max')}. Default {c.get('default')}.")
    return "\n".join(lines)


def tool_spec() -> dict:
    return {"toolSpec": {
        "name": "submit_actions",
        "description": "Submit the actions that make up the user's proposal.",
        "inputSchema": {"json": {"type": "object", "properties": {
            "actions": {"type": "array", "items": {"type": "object", "properties": {
                "type": {"type": "string", "enum": list(TEMPLATES)},
                "values": {"type": "object", "description": "field id -> value, only for fields the user stated or clearly implied"}},
                "required": ["type", "values"]}},
            "unsupported": {"type": "array", "items": {"type": "string"}, "description": "Parts of the question no action covers"},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]}},
            "required": ["actions", "unsupported", "confidence"]}}}}


# ---------- validation ----------
def clean_values(action_type: str, raw: dict) -> tuple[dict, list[str]]:
    """Keep only valid values; return (values, notes)."""
    t = {c["id"]: c for c in TEMPLATES[action_type]["constraints"]}
    out, notes = {}, []
    for k, v in (raw or {}).items():
        c = t.get(k)
        if c is None:
            notes.append(f"ignored unknown field {k}")
            continue
        if isinstance(v, dict) and "value" in v:   # the model sometimes wraps a value as {value, source}
            v = v["value"]
        if c.get("options"):
            allowed = [o["value"] for o in c["options"]]
            if v in allowed:
                out[k] = v
            elif str(v) in map(str, allowed):
                out[k] = allowed[[str(a) for a in allowed].index(str(v))]
            else:
                notes.append(f"{c['label']}: '{v}' isn't an option, kept the default")
        elif c["type"] == "number":
            try:
                x = float(v)
            except (TypeError, ValueError):
                notes.append(f"{c['label']}: '{v}' isn't a number, kept the default")
                continue
            lo, hi = c.get("min", x), c.get("max", x)
            if x < lo or x > hi:
                notes.append(f"{c['label']}: {v} is outside {lo}-{hi}, clamped")
            x = min(max(x, lo), hi)
            out[k] = int(x) if float(x).is_integer() else x
    return out, notes


def build_spec(tool_input: dict, question: str, districts: list[int], parent: dict | None) -> dict:
    actions, notes = [], []
    for a in tool_input.get("actions", []):
        t = a.get("type")
        if t not in TEMPLATES:
            notes.append(f"unknown action {t}")
            continue
        vals, n = clean_values(t, a.get("values", {}))
        notes += n
        act = new_action(t, vals)
        if parent:                       # follow-up: values the user gave this time are 'edited'
            for c in act["constraints"]:
                if c["source"] == "from_question":
                    c["source"] = "edited"
        actions.append(act)
    spec = {
        "spec_id": parent["spec_id"] if parent else f"spec-{uuid.uuid4().hex[:10]}",
        "version": (parent["version"] + 1) if parent else 1,
        "parent_spec_id": parent["spec_id"] if parent else None,
        "status": "draft",
        "prompt": question,
        "districts": districts,
        "confidence": tool_input.get("confidence", "medium") if actions else "low",
        "actions": actions,
        "unsupported": list(tool_input.get("unsupported", [])) + notes,
    }
    spec["summary"] = summary_line(spec) if actions else ""
    return spec


# ---------- Bedrock ----------
def ask_model(question: str, parent: dict | None, client=None) -> dict:
    from shared import budget
    from shared.aws import bedrock_runtime
    client = client or bedrock_runtime()      # may borrow a role in another account (BEDROCK_ROLE_ARN)
    user = question if not parent else (
        f"Current proposal (edit it, keep what the user doesn't change):\n{json.dumps(parent['actions'])}\n\nFollow-up: {question}")
    resp = budget.converse(            # refuses when the daily spending limit is reached
        client,
        modelId=MODEL_ID,
        system=[{"text": SYSTEM + "\n\nActions and their fields (use these ids and option values exactly):\n" + catalog()
                 + "\n\nCall submit_actions exactly once. Fill only values the user stated or clearly implied; the rest get defaults."}],
        messages=[{"role": "user", "content": [{"text": user}]}],
        toolConfig={"tools": [tool_spec()], "toolChoice": {"tool": {"name": "submit_actions"}}},
        inferenceConfig={"temperature": 0, "maxTokens": 1500},
    )
    for block in resp["output"]["message"]["content"]:
        if "toolUse" in block:
            return block["toolUse"]["input"]
    return {"actions": [], "unsupported": ["The model didn't return a proposal."], "confidence": "low"}


def handler(event, context=None, client=None):
    try:
        body = json.loads(event.get("body") or "{}") if isinstance(event, dict) and "body" in event else event
        question = (body.get("question") or "").strip()
        if not question:
            return {"statusCode": 400, "headers": CORS, "body": json.dumps({"error": "question is required"})}
        districts = [int(d) for d in body.get("districts", [])][:4]
        parent = body.get("spec")
        spec = build_spec(ask_model(question, parent, client), question, districts, parent)
        return {"statusCode": 200, "headers": CORS, "body": json.dumps({"spec": spec})}
    except Exception as e:  # surface the reason to the UI instead of a bare 502
        return {"statusCode": 500, "headers": CORS, "body": json.dumps({"error": f"{type(e).__name__}: {e}"})}
