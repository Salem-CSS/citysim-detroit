from contracts.spec import new_action, summary_line, apply_edit, values
from residents.prompt import build, wants_quote
from residents.validate import check

def spec():
    s = {"spec_id": "t1", "version": 1, "status": "confirmed", "prompt": "raw words", "summary": "",
         "districts": [6], "confidence": "medium", "actions": [new_action("add_drone_route", {"flights_per_day": 200})]}
    s["summary"] = summary_line(s); return s

def test_sources_and_values():
    a = spec()["actions"][0]
    src = {c["id"]: c["source"] for c in a["constraints"]}
    assert src["flights_per_day"] == "from_question" and src["altitude_ft"] == "assumed"
    assert values(a)["flights_per_day"] == 200

def test_edit_marks_edited_and_updates_summary():
    s = spec(); aid = s["actions"][0]["action_id"]
    apply_edit(s, aid, "altitude_ft", 400)
    c = next(c for c in s["actions"][0]["constraints"] if c["id"] == "altitude_ft")
    assert c["source"] == "edited" and "400 ft" in s["summary"]

def test_prompt_uses_summary_not_raw_prompt():
    s = spec(); p = {"persona_id": "d6-0001", "age": 62, "sex": "female", "tenure": "owner", "vehicles": 1, "hh_income": 34000, "district": 6}
    msg, flags = build([p], s, {"d6-0001": ["A drone route passes about 200 ft from your home"]})
    assert "raw words" not in msg and s["summary"] in msg and "200 ft from your home" in msg

def test_validate():
    ids = {"a"}
    assert check({"persona_id": "a", "stance": "support", "reason": "access"}, ids, False) is None
    assert check({"persona_id": "a", "stance": "maybe", "reason": "noise"}, ids, False)
    assert check({"persona_id": "a", "stance": "oppose", "reason": "none"}, ids, False)
    assert check({"persona_id": "a", "stance": "neutral", "reason": "noise"}, ids, True)  # quote required
    item = {"persona_id": "a", "stance": "neutral", "reason": "noise", "quote": "x"}
    assert check(item, ids, False) is None and "quote" not in item

def test_quote_share_about_ten_percent():
    n = sum(wants_quote(f"d6-{i:04d}", "spec") for i in range(2000))
    assert 140 < n < 260
