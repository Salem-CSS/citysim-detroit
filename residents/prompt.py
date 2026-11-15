"""Resident prompt (SCOPE.md, Public sentiment model). Batched 25 personas per Bedrock call."""
CONCERNS = ["traffic", "noise", "safety", "privacy", "rent", "jobs", "access", "none"]

SYSTEM = (
    "You answer as Detroit residents. For each resident, reply as that person would, "
    "based only on their traits and their computed personal impact. Return JSON only."
)

def persona_line(p: dict) -> str:
    car = "no car" if p["vehicles"] == 0 else f"{p['vehicles']} car(s)"
    return (f"[{p['persona_id']}] {p['age']}-year-old {p['sex']}, {p['tenure']}"
            f"{', ' + str(p['years_in_home']) + ' years in home' if p.get('years_in_home') else ''}, {car}, "
            f"commute: {p.get('commute_mode', 'unknown')}, household income ${p['hh_income']:,}, District {p['district']}.")

def build(personas: list[dict], scenario_summary: str, impacts: dict[str, list[str]]) -> str:
    lines = [f"Proposed change: {scenario_summary}", "", "Residents:"]
    for p in personas:
        lines.append(persona_line(p))
        lines.append("  Your personal impact: " + "; ".join(impacts.get(p["persona_id"], ["no direct change"])))
    lines += ["", "Reply with a JSON array, one object per resident:",
              '{"persona_id": "...", "support": 1-5, "top_concern": one of ' + str(CONCERNS) + ', "reaction": "one sentence"}']
    return "\n".join(lines)
