"""Helpers shared by agent/, engine/ and residents/ for the v2 scenario spec.

    from contracts.spec import new_action, values, summary_line
"""
import json, uuid
from pathlib import Path

ACTIONS = json.loads((Path(__file__).parent / "actions.json").read_text())
TEMPLATES = {a["type"]: a for a in ACTIONS["actions"]}
REASONS = ACTIONS["reasons"]
STANCES = ACTIONS["stances"]

def new_action(action_type: str, from_question: dict | None = None) -> dict:
    """Build an action with every constraint from its template.
    Values in from_question get source='from_question'; the rest get the default and source='assumed'."""
    t = TEMPLATES[action_type]
    from_question = from_question or {}
    cons = []
    for c in t["constraints"]:
        c2 = {k: v for k, v in c.items() if k not in ("default", "engine_hint")}
        c2.setdefault("show", "panel")
        if c["id"] in from_question:
            c2["value"], c2["source"] = from_question[c["id"]], "from_question"
        else:
            c2["value"], c2["source"] = c["default"], "assumed"
        cons.append(c2)
    return {"action_id": f"{action_type}-{uuid.uuid4().hex[:6]}", "type": action_type, "title": t["title"], "constraints": cons}

def values(action: dict) -> dict:
    """{constraint_id: value} for the engine."""
    return {c["id"]: c["value"] for c in action["constraints"]}

def label_of(constraint: dict) -> str:
    """Human label for the current value (uses option labels for selects)."""
    v = constraint["value"]
    for o in constraint.get("options", []):
        if o["value"] == v:
            return o["label"]
    unit = constraint.get("unit")
    return f"{v} {unit}" if unit and v is not None else str(v)

def summary_line(spec: dict) -> str:
    """Neutral one-sentence summary rebuilt from constraint values. Residents are asked about this, not the raw prompt."""
    parts = []
    for a in spec["actions"]:
        shown = [c for c in a["constraints"] if c.get("show", "panel") == "panel"]
        details = ", ".join(f"{c['label'].lower()}: {label_of(c)}" for c in shown)
        parts.append(f"{a['title']} ({details})")
    d = spec.get("districts", [])
    where = f" in District{'s' if len(d) > 1 else ''} {', '.join(map(str, d))}" if d else ""
    return ("Proposal: " + "; plus ".join(parts) + where + ".")[:240]

def apply_edit(spec: dict, action_id: str, constraint_id: str, value) -> dict:
    """User edited a block: set value, mark source='edited'. Caller bumps version on Ask again."""
    for a in spec["actions"]:
        if a["action_id"] == action_id:
            for c in a["constraints"]:
                if c["id"] == constraint_id:
                    c["value"], c["source"] = value, "edited"
    spec["summary"] = summary_line(spec)
    return spec
