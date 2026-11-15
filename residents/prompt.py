"""Resident prompt, v2 framework (SCOPE.md, Public sentiment model).

Residents answer ONLY: stance (support / neutral / oppose) + one reason from a fixed list.
About 1 in 10 residents (picked deterministically) also give a one-sentence quote.
They see the confirmed spec's neutral `summary` and their own computed impact lines, never the raw prompt.
Batched 25 residents per Bedrock call.
"""
import hashlib
import os
from contracts.spec import REASONS, STANCES

# Share of residents who also give a one-sentence quote. A deploy setting (QuoteShare in infra/template.yaml):
# 0.10 = 1 in 10, 0.5 = half, 1 = everyone. More quotes cost more output tokens per run.
QUOTE_SHARE = min(1.0, max(0.0, float(os.environ.get("QUOTE_SHARE", "0.10"))))

SYSTEM = (
    "You simulate Detroit residents reacting to a proposed change in their city. "
    "Answer separately for each resident, as that specific person would, based only on their traits and their personal impact. "
    "For each resident give: stance (support, neutral or oppose) and the single main reason from the allowed list. "
    "Only residents marked 'quote: yes' also give one short first-person sentence in their own voice. "
    "Do not invent facts or numbers beyond what is given. Return a JSON array only."
)

def wants_quote(persona_id: str, spec_id: str) -> bool:
    """Deterministic ~10% sample, stable across retries of the same spec."""
    h = int(hashlib.sha1(f"{spec_id}:{persona_id}".encode()).hexdigest()[:8], 16)
    return (h % 1000) < QUOTE_SHARE * 1000

def persona_line(p: dict) -> str:
    car = "no car" if p["vehicles"] == 0 else f"{p['vehicles']} car{'s' if p['vehicles'] > 1 else ''}"
    yrs = f", {p['years_in_home']} years in their home" if p.get("years_in_home") else ""
    kids = ", children at home" if p.get("children") else ""
    return (f"{p['age']}-year-old {p['sex']}, {p['tenure']}{yrs}, {car}, commute: {p.get('commute_mode', 'unknown')}, "
            f"household income ${p['hh_income']:,}{kids}, lives in District {p['district']}")

def build(personas: list[dict], spec: dict, impact_lines: dict[str, list[str]]) -> tuple[str, dict[str, bool]]:
    """Returns (user_message, quote_flags). `spec` must be the CONFIRMED scenario spec."""
    flags = {p["persona_id"]: wants_quote(p["persona_id"], spec["spec_id"]) for p in personas}
    lines = [f"Proposed change: {spec['summary']}", "", "Residents:"]
    for p in personas:
        pid = p["persona_id"]
        lines.append(f"- [{pid}] {persona_line(p)}")
        lines.append("  Personal impact: " + "; ".join(impact_lines.get(pid, ["No direct change near your home"])))
        lines.append(f"  quote: {'yes' if flags[pid] else 'no'}")
    lines += ["",
              f"Allowed stances: {', '.join(STANCES)}",
              f"Allowed reasons: {', '.join(REASONS)} (use 'none' only with neutral)",
              "Reply with a JSON array, one object per resident, in the same order:",
              '{"persona_id": "...", "stance": "...", "reason": "..."}  plus "quote": "..." ONLY when quote is yes']
    return "\n".join(lines), flags

CALIBRATION_TEMPLATE = (
    "Statement: \"{statement}\"\n"
    "For this calibration question, stance means: support = agree, neutral = neither, oppose = disagree. "
    "Reason: pick the closest from the allowed list, or none."
)
