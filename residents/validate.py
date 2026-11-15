"""Output checks for resident responses (contracts/resident_response.schema.json)."""
from contracts.spec import REASONS, STANCES

def check(item: dict, expected_ids: set[str], wants_quote: bool) -> str | None:
    """Return None if valid, else why. Strips a quote that wasn't asked for (does not fail)."""
    if not isinstance(item, dict):
        return "not an object"
    if item.get("persona_id") not in expected_ids:
        return "unknown persona_id"
    if item.get("stance") not in STANCES:
        return "stance not support/neutral/oppose"
    if item.get("reason") not in REASONS:
        return "reason not in list"
    if item["reason"] == "none" and item["stance"] != "neutral":
        return "reason 'none' only allowed with neutral"
    q = item.get("quote")
    if wants_quote:
        if not isinstance(q, str) or not q.strip() or len(q) > 200:
            return "quote missing or over 200 chars"
    elif q is not None:
        item.pop("quote")
    extra = set(item) - {"persona_id", "stance", "reason", "quote"}
    for k in extra:
        item.pop(k)
    return None
