"""Output checks for resident responses (SCOPE.md, Implementation rules)."""
from residents.prompt import CONCERNS

def check(item: dict, expected_ids: set[str]) -> str | None:
    """Return None if valid, else the reason."""
    if item.get("persona_id") not in expected_ids:
        return "unknown persona_id"
    s = item.get("support")
    if not isinstance(s, int) or not 1 <= s <= 5:
        return "support not an integer 1-5"
    if item.get("top_concern") not in CONCERNS:
        return "top_concern not in list"
    r = item.get("reaction")
    if not isinstance(r, str) or not r or len(r) >= 200:
        return "reaction missing or 200+ chars"
    return None

def stance(support: int) -> str:
    return "support" if support >= 4 else "neutral" if support == 3 else "oppose"
