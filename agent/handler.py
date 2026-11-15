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
import re
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
            if c["type"] == "text":
                lines.append(f"    {c['id']} - {c['label']} (short text). {c.get('note', '')}")
                continue
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
        if c is None:                    # the model added a field the action does not have: drop it silently
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
        elif c["type"] == "text":
            text = " ".join(str(v).split())[:120]
            if text:
                out[k] = text
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


def _number_in(value, question: str) -> bool:
    """True if the number appears in the question as digits (1,200 and 1200 both count)."""
    found = set()
    for x in re.findall(r"[0-9][0-9,]*[.]?[0-9]*", question):
        try:
            found.add(float(x.replace(",", "")))
        except ValueError:
            pass
    try:
        return float(value) in found
    except (TypeError, ValueError):
        return False


def _option_in(constraint: dict, question: str) -> bool:
    """True if the chosen option is named in the question: its number, or a word of its label (4+ letters)."""
    value = constraint["value"]
    label = next((o["label"] for o in constraint.get("options", []) if o["value"] == value), str(value))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _number_in(value, question)
    q = question.lower()
    numbers = re.findall(r"[0-9]+", label)
    if numbers:                                   # "7 AM to 9 PM": every number in the label must be in the question
        return all(_number_in(n, question) for n in numbers)
    words = [w for w in re.findall(r"[a-z]{4,}", label.lower()) if w not in ("with", "from", "that", "none")]
    return any(w in q or w.rstrip("s") in q for w in words)


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
        raw = a.get("values") or {}
        said = (question + " " + " ".join(str(c.get("value") or "") for x in (parent or {}).get("actions", []) for c in x["constraints"]
                                          if c["id"] in ("where", "from", "to"))).lower()
        what = next((str(c["value"]).lower() for c in act["constraints"] if c["id"] == "what"), "")
        for c in act["constraints"]:     # a place the user never named is not a place: clear it so the user is asked
            if c["id"] in ("where", "from", "to") and c["value"]:
                words = [w for w in re.findall(r"[a-z0-9]+", str(c["value"]).lower()) if len(w) >= 3 and w not in ("the", "and", "near", "from")]
                if str(c["value"]).lower() == what or not any(w in said for w in words):
                    c["value"], c["source"] = "", "assumed"
        for c in act["constraints"]:     # a value that is not in the question was not stated by the user
            if parent or c["source"] != "from_question" or c["type"] not in ("number", "select"):
                continue                 # (follow-ups are checked against the earlier spec, not the short follow-up text)
            given = raw.get(c["id"])
            given = given["value"] if isinstance(given, dict) and "value" in given else given
            stated = _number_in(given, question) if c["type"] == "number" else _option_in(c, question)
            if not stated:
                c["source"] = "assumed"
                c["note"] = "Not stated in the question; filled in by the assistant."
        if parent:                       # follow-up: a value that changed is 'edited'; an unchanged one keeps its earlier source
            before = {c["id"]: c for x in parent.get("actions", []) if x.get("type") == t for c in x["constraints"]}
            for c in act["constraints"]:
                old = before.get(c["id"])
                if old is not None and str(old.get("value")) == str(c["value"]):
                    c["source"] = old.get("source", c["source"])
                elif c["source"] == "from_question":
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
    return check_places(spec)


ROUTE_TYPES = ("add_drone_route", "change_transit")
ASK = {"where": "Where should this go? Tap the pin to pick it on the map, or give two cross streets, an address, a landmark or coordinates.",
       "from": "Where does the route start? Tap the pin to pick it on the map, or give two cross streets, an address, a landmark or coordinates.",
       "to": "Where does the route end? Tap the pin to pick it on the map, or give two cross streets, an address, a landmark or coordinates."}


def check_places(spec: dict, resolve=None) -> dict:
    """Verify every place the proposal needs (BACKEND_PLAN.md 11.2). A route needs a start and an end; anything else
    needs one place. If a place is missing, not found, ambiguous or outside the selected districts, the spec comes back
    as needs_info with a question. Nothing is guessed. Skipped when no place index is configured (unit tests)."""
    if resolve is None:
        if not (os.environ.get("PLACES_FILE") or os.environ.get("DATA_BUCKET")):
            return spec
        from shared.places import resolve
    questions = []
    for a in spec["actions"]:
        by_id = {c["id"]: c for c in a["constraints"]}
        if a["type"] in ROUTE_TYPES and not (by_id["from"]["value"] or by_id["to"]["value"]) and " to " in str(by_id["where"]["value"]):
            parts = re.split(r"\s+to\s+", re.sub(r"^from\s+", "", str(by_id["where"]["value"]), flags=re.I), maxsplit=1)
            by_id["from"]["value"], by_id["to"]["value"] = parts[0].strip(), parts[1].strip()
            by_id["from"]["source"] = by_id["to"]["source"] = by_id["where"]["source"]
        for cid in (("from", "to") if a["type"] in ROUTE_TYPES else ("where",)):
            c = by_id[cid]
            c.pop("resolved", None)
            qid, text = f"{a['action_id']}.{cid}", str(c["value"] or "").strip()
            if not text:
                questions.append({"id": qid, "label": c["label"], "text": ASK[cid], "options": []})
                continue
            r = resolve(text, spec.get("districts"))
            if r["status"] == "ok" and r["in_selected"]:
                c["resolved"] = {k: r[k] for k in ("name", "method", "lon", "lat", "district")}
            elif r["status"] == "ok":
                where = f"District {r['district']}" if r["district"] else "outside Detroit's council districts"
                questions.append({"id": qid, "label": c["label"], "options": [],
                                  "text": f"{r['name']} is in {where}, which is not one of the districts you selected. "
                                          f"Select that district or give another place."})
            else:
                more = " Which did you mean?" if r.get("alternatives") else " Tap the pin to pick it on the map, or give two cross streets, an address, a landmark or coordinates."
                questions.append({"id": qid, "label": c["label"], "text": r["message"] + more, "options": r.get("alternatives", [])})
    if questions:
        spec["status"], spec["questions"] = "needs_info", questions
    else:
        spec.pop("questions", None)
    spec["summary"] = summary_line(spec) if spec["actions"] else ""
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
                 + "\n\nCall submit_actions exactly once. Fill only values the user stated or clearly implied; the rest get defaults."
                 + " Always fill `what` and `where` for every action. `what` is the thing the user proposed, in their own terms and kept specific (for example 'a strip club', 'a 24-hour gas station', 'a new bus route'), as a short neutral noun phrase. Never generalise it to a broader category. `where` is the place the user named (street, cross streets, landmark, from-to); leave it out if they named none. For a route (drone route, bus service) also fill `from` and `to` with the start and end places the user named, and leave either out if the user did not name it; never invent a start or an end. If the specific use or place has no matching option in a select field, leave that field out: do not pick the nearest option and do not list the use under `unsupported`. `unsupported` is only for parts of the question that none of the action types can represent."}],
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
