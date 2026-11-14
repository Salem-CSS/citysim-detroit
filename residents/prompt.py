"""Resident prompt and questionnaire (BACKEND_PLAN.md section 9.1). Batched 25 personas per Bedrock call.

One fixed set of seven questions, identical wording and answer options for every resident on every
proposal (agreed Nov 14, 2026). Changing any wording or option means bumping PROMPT_VERSION and
rerunning calibration.
"""
PROMPT_VERSION = "q7-2026-11-14"

CONCERNS = ["traffic", "noise", "safety", "privacy", "rent", "jobs", "access", "none"]
BENEFITS = ["jobs", "housing", "convenience", "safety", "less traffic", "none"]
DAILY_LIFE = ["better", "worse", "no different"]
SPEAK = ["not likely", "somewhat", "very"]
CHANGES = ["smaller", "different location", "limited hours", "community benefits", "nothing"]

# (answer field, question as asked, answer options or None for a 1-5 scale / free text)
QUESTIONS = [
    ("support", "Do you support or oppose this proposal? (1 strongly oppose to 5 strongly support)", None),
    ("top_concern", "What worries you most about it?", CONCERNS),
    ("top_benefit", "What is the biggest benefit to you, if any?", BENEFITS),
    ("daily_life", "Would it make daily life for your household better, worse or no different?", DAILY_LIFE),
    ("speak_likelihood", "How likely are you to speak at a public meeting about it?", SPEAK),
    ("one_change", "What one change would make you more supportive?", CHANGES),
    ("reaction", "Say what you think in one sentence (under 200 characters).", None),
]
ENUM_FIELDS = {field: options for field, _, options in QUESTIONS if options}

SYSTEM = (
    "You answer as Detroit residents. For each resident, reply as that person would, "
    "based only on their traits and their computed personal impact. "
    "Answer every question for every resident using only the listed answer options."
)

# Forced tool for Bedrock Converse (Nova does not support structured outputs; the array is wrapped in an object).
TOOL_NAME = "submit_reactions"
TOOL_SCHEMA = {
    "type": "object",
    "required": ["items"],
    "properties": {"items": {"type": "array", "items": {
        "type": "object",
        "required": ["persona_id"] + [field for field, _, _ in QUESTIONS],
        "properties": {
            "persona_id": {"type": "string"},
            "support": {"type": "integer", "minimum": 1, "maximum": 5},
            **{field: {"type": "string", "enum": options} for field, options in ENUM_FIELDS.items()},
            "reaction": {"type": "string", "maxLength": 199},
        },
    }}},
}

def persona_line(p: dict) -> str:
    car = "no car" if p["vehicles"] == 0 else f"{p['vehicles']} car(s)"
    return (f"[{p['persona_id']}] {p['age']}-year-old {p['sex']}, {p['tenure']}"
            f"{', ' + str(p['years_in_home']) + ' years in home' if p.get('years_in_home') else ''}, {car}, "
            f"commute: {p.get('commute_mode', 'unknown')}, household income ${p['hh_income']:,}, District {p['district']}.")

def question_lines() -> list[str]:
    out = []
    for i, (field, text, options) in enumerate(QUESTIONS, 1):
        out.append(f"{i}. {text}" + (f" Options: {', '.join(options)}." if options else "") + f" -> {field}")
    return out

def build(personas: list[dict], scenario_summary: str, impacts: dict[str, list[str]]) -> str:
    lines = [f"Proposed change: {scenario_summary}", "", "Residents:"]
    for p in personas:
        lines.append(persona_line(p))
        lines.append("  Your personal impact: " + "; ".join(impacts.get(p["persona_id"], ["no direct change"])))
    lines += ["", "Each resident answers these questions:"] + question_lines()
    lines += ["", f"Call {TOOL_NAME} once with one item per resident, each carrying that resident's persona_id."]
    return "\n".join(lines)
