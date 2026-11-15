"""Seven-question resident questionnaire, PARKED for the second engine (the correction engine).

Not used by the first engine. The first engine asks each resident only for a stance and a reason
(residents/prompt.py, contracts/resident_response.schema.json).

What the correction engine is for (agreed Nov 14, 2026; not built yet):
after a first-engine run, find out why residents said no and propose a changed version of the
request that gets a better support-to-oppose ratio. It tallies these seven answers, and also reads
the answers against who the residents are (for example no car, housing status) and where they are
(for example one area opposed while the rest supported, and that area has a blocked street), so the
questions support the diagnosis but are not the whole of it.

The wording and options below were agreed on Nov 14, 2026 (BACKEND_PLAN.md section 9.1). Changing
any of them means bumping PROMPT_VERSION. No contract or fixture carries these fields yet: the four
new answers (top_benefit, daily_life, speak_likelihood, one_change) need a schema of their own
when the correction engine is built.
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

# Forced tool for Bedrock Converse (Nova does not support structured outputs; the array is wrapped in an object).
TOOL_NAME = "submit_correction_answers"
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

def question_lines() -> list[str]:
    out = []
    for i, (field, text, options) in enumerate(QUESTIONS, 1):
        out.append(f"{i}. {text}" + (f" Options: {', '.join(options)}." if options else "") + f" -> {field}")
    return out

def check(item: dict, expected_ids: set[str]) -> str | None:
    """Return None if valid, else the reason. Every one of the seven answers must be present and in range."""
    if item.get("persona_id") not in expected_ids:
        return "unknown persona_id"
    s = item.get("support")
    if isinstance(s, bool) or not isinstance(s, int) or not 1 <= s <= 5:
        return "support not an integer 1-5"
    for field, options in ENUM_FIELDS.items():
        if item.get(field) not in options:
            return f"{field} not in list"
    r = item.get("reaction")
    if not isinstance(r, str) or not r or len(r) >= 200:
        return "reaction missing or 200+ chars"
    return None
