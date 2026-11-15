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
    base = (f"{p['age']}-year-old {p['sex']}, {p['tenure']}{yrs}, {car}, commute: {p.get('commute_mode', 'unknown')}, "
            f"household income ${p['hh_income']:,}{kids}, lives in District {p['district']}")
    return base + census_details(p)


def census_details(p: dict) -> str:
    """More facts from the same census record (BACKEND_PLAN.md 7.1, Tier 1). Fixed order; a fact is listed only
    when the record has it. Set PERSONA_CARD=base to leave these out (for the calibration comparison)."""
    if os.environ.get("PERSONA_CARD", "tier1") == "base" or "education" not in p:
        return ""
    bits = []
    if p.get("race"):
        bits.append(p["race"] + (", Hispanic" if p.get("hispanic") else ""))
    if p.get("move_in_band"):
        bits.append(f"moved in {p['move_in_band']} ago" if "months" in p["move_in_band"] or "years" in p["move_in_band"] else p["move_in_band"])
    if p.get("building_type"):
        bits.append(f"lives in a {p['building_type']}")
    bits.append(p["education"])
    if p.get("employment"):
        bits.append(p["employment"])
    if p.get("housing_cost_pct_income") is not None:
        bits.append(f"housing costs {p['housing_cost_pct_income']}% of income")
    if p.get("poverty_ratio_pct") is not None and p["poverty_ratio_pct"] < 100:
        bits.append("income below the poverty line")
    for key, text in (("snap", "receives food assistance"), ("disability", "has a disability"),
                      ("difficulty_walking", "has difficulty walking"), ("someone_65_plus_at_home", "someone 65 or older at home"),
                      ("born_abroad", "born outside the US"), ("veteran", "veteran")):
        if p.get(key):
            bits.append(text)
    if p.get("home_language") and p["home_language"] != "English only":
        bits.append(f"{p['home_language']} spoken at home")
    if p.get("internet_at_home") is False:
        bits.append("no internet at home")
    return "; " + "; ".join(bits)

# Stance step used by batch.py. It never mentions quotes: in a 500-resident trial on Nov 14 every resident marked
# "quote: yes" answered support and nobody else did, so the quote marker was steering the stance. Quotes are now
# asked for in a second call (build_quotes), after the stance is fixed.
SYSTEM_STANCE = (
    "You simulate Detroit residents reacting to a proposed change in their city. "
    "Answer separately for each resident, as that specific person would, based only on their traits and their personal impact. "
    "For each resident give: stance (support, neutral or oppose) and the single main reason from the allowed list. "
    "Do not invent facts or numbers beyond what is given. Return a JSON array only."
)
SYSTEM_QUOTES = (
    "You write what Detroit residents would say about a proposed change in their city. Each resident's stance and main "
    "reason are already decided and must not change. For each resident write one short first-person sentence in their own "
    "voice, under 200 characters, consistent with that stance and reason. Do not invent facts or numbers beyond what is "
    "given. Return a JSON array only."
)


def build_quotes(personas: list[dict], answers: dict[str, dict], spec: dict) -> str:
    """Second call: one sentence from each sampled resident, given the stance and reason they already gave."""
    lines = [f"Proposed change: {spec['summary']}", "", "Residents:"]
    for p in personas:
        a = answers[p["persona_id"]]
        lines.append(f"- [{p['persona_id']}] {persona_line(p)}")
        lines.append(f"  stance: {a['stance']}; main reason: {a['reason']}")
    lines += ["", "Reply with a JSON array, one object per resident, in the same order:", '{"persona_id": "...", "quote": "..."}']
    return "\n".join(lines)


def build(personas: list[dict], spec: dict, impact_lines: dict[str, list[str]] | None, quotes: bool = True) -> tuple[str, dict[str, bool]]:
    """Returns (user_message, quote_flags). `spec` must be the CONFIRMED scenario spec.
    impact_lines=None means no engine result exists for this proposal: the impact line is left out and the
    model is told so, rather than telling residents there is "no change" that was never computed."""
    flags = {p["persona_id"]: wants_quote(p["persona_id"], spec["spec_id"]) for p in personas}
    lines = [f"Proposed change: {spec['summary']}", "", "Residents:"]
    for p in personas:
        pid = p["persona_id"]
        lines.append(f"- [{pid}] {persona_line(p)}")
        if impact_lines is not None:
            lines.append("  Personal impact: " + "; ".join(impact_lines.get(pid, ["No direct change near your home"])))
        if quotes:
            lines.append(f"  quote: {'yes' if flags[pid] else 'no'}")
    if impact_lines is None:
        lines += ["", "No personal impact figures have been calculated for this proposal. Each resident reacts to the "
                      "proposal itself, as described above, as that person would."]
    lines += ["",
              f"Allowed stances: {', '.join(STANCES)}",
              f"Allowed reasons: {', '.join(REASONS)} (use 'none' only with neutral)",
              "Reply with a JSON array, one object per resident, in the same order:",
              '{"persona_id": "...", "stance": "...", "reason": "..."}' + ('  plus "quote": "..." ONLY when quote is yes' if quotes else "")]
    return "\n".join(lines), flags

CALIBRATION_TEMPLATE = (
    "Statement: \"{statement}\"\n"
    "For this calibration question, stance means: support = agree, neutral = neither, oppose = disagree. "
    "Reason: pick the closest from the allowed list, or none."
)
