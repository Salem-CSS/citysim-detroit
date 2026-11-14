"""Strands tools for the scenario agent (BUILD.md Step 10). Each returns plain data; none invent numbers."""
from contracts.spec import new_action as _new_action, summary_line, TEMPLATES

def list_actions() -> list[dict]:
    """Action types and their constraint ids/labels, so the model knows what it can fill."""
    return [{"type": t, "title": a["title"], "constraints": [{"id": c["id"], "label": c["label"], "type": c["type"],
             "options": [o["value"] for o in c.get("options", [])]} for c in a["constraints"]]} for t, a in TEMPLATES.items()]

def new_action(action_type: str, from_question: dict) -> dict:
    """Build an action with all its constraints; values from the question are marked from_question, the rest assumed."""
    return _new_action(action_type, from_question)

def make_summary(spec: dict) -> str:
    """Neutral one-sentence summary from constraint values (what residents are asked about)."""
    return summary_line(spec)

def geocode(place: str) -> dict:
    """Amazon Location: place name -> {lat, lon, label}."""
    raise NotImplementedError

def find_parcels(lat: float, lon: float, radius_m: int = 100) -> list[dict]:
    raise NotImplementedError

def lookup_trip_rate(land_use: str) -> dict:
    """Nearest ITE code from data/ite_rates.csv, with a confidence flag."""
    raise NotImplementedError
