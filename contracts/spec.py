"""Helpers shared by agent/, engine/ and residents/ for the v2 scenario spec.

    from contracts.spec import new_action, values, summary_line
"""
import json, re, uuid
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

PLACE_IDS = {"site", "hub", "street", "route"}          # constraints that name a preset place
PLACE_WORDS = {"from", "between", "on", "at", "near", "along", "above", "over", "in", "by", "across", "next", "behind"}


_COORDS = re.compile(r"\s*\(?\s*-?\d{1,3}\.\d+\s*,\s*-?\d{1,3}\.\d+\s*\)?\s*$")


def _place(v) -> str:
    """Residents read the place name, never raw map coordinates."""
    t = str(v or "").strip()
    bare = _COORDS.sub("", t).strip(" ,")
    return bare if bare or not t else "a point on the map"


def summary_line(spec: dict) -> str:
    """Neutral one-sentence summary. Residents are asked about this, not the raw prompt.

    It leads with what the user asked for and where, in the user's own terms (the `what` and `where`
    text constraints), then lists only the settings the user stated or edited. Defaults the agent
    assumed are engine inputs; they are not read to residents as if the user had proposed them."""
    parts = []
    for a in spec["actions"]:
        by_id = {c["id"]: c for c in a["constraints"]}
        what = str((by_id.get("what") or {}).get("value") or "").strip()
        where = _place((by_id.get("where") or {}).get("value"))
        start = _place((by_id.get("from") or {}).get("value"))
        end = _place((by_id.get("to") or {}).get("value"))
        if start and end:
            where = f"from {start} to {end}"
        joined = where if where.lower().split(" ")[0] in PLACE_WORDS else f"at {where}"
        head = (what or a["title"]) + (f" {joined}" if where else "")
        skip = {"what", "where", "from", "to"} | (PLACE_IDS if where else set())   # the user's own place replaces a preset place
        stated = [c for c in a["constraints"] if c["id"] not in skip and c.get("show", "panel") == "panel"
                  and c.get("source") in ("from_question", "edited") and c.get("type") in ("number", "select")]
        details = ", ".join(f"{c['label'].lower()}: {label_of(c)}" for c in stated)
        parts.append(head + (f" ({details})" if details else ""))
    d = spec.get("districts", [])
    where_d = f" in District{'s' if len(d) > 1 else ''} {', '.join(map(str, d))}" if d else ""
    body = "Proposal: " + "; plus ".join(parts)
    return body[:240 - len(where_d) - 1] + where_d + "."

def apply_edit(spec: dict, action_id: str, constraint_id: str, value) -> dict:
    """User edited a block: set value, mark source='edited'. Caller bumps version on Ask again."""
    for a in spec["actions"]:
        if a["action_id"] == action_id:
            for c in a["constraints"]:
                if c["id"] == constraint_id:
                    c["value"], c["source"] = value, "edited"
    spec["summary"] = summary_line(spec)
    return spec
