"""The user's own words and place must reach residents unchanged (BACKEND_PLAN.md section 11.1)."""
from agent.handler import build_spec

Q = "What if a strip club opens on Trumbull Ave near Michigan Ave?"


def spec_for(values, question=Q):
    return build_spec({"actions": [{"type": "add_building", "values": values}], "unsupported": [], "confidence": "medium"},
                      question, [6], None)


def test_summary_carries_what_and_where_not_a_preset():
    spec = spec_for({"what": "a strip club", "where": "Trumbull Ave near Michigan Ave"})
    assert spec["summary"] == "Proposal: a strip club at Trumbull Ave near Michigan Ave in District 6."
    assert "homes" not in spec["summary"].lower() and "shops" not in spec["summary"].lower()


def test_numbers_not_in_the_question_are_marked_assumed():
    spec = spec_for({"what": "a strip club", "floors": 3, "retail_sqft": 10000})
    src = {c["id"]: c["source"] for c in spec["actions"][0]["constraints"]}
    assert src["floors"] == "assumed" and src["retail_sqft"] == "assumed"
    assert "floors" not in spec["summary"]          # an assumed value is not read to residents


def test_numbers_in_the_question_stay_from_question():
    spec = spec_for({"what": "an apartment building", "homes": 120, "floors": 6},
                    "Add a 120 unit, 6 floor apartment building on Michigan Ave")
    src = {c["id"]: c["source"] for c in spec["actions"][0]["constraints"]}
    assert src["homes"] == "from_question" and src["floors"] == "from_question"
    assert "apartments: 120" in spec["summary"] or "120" in spec["summary"]


def test_summary_stays_within_contract_length():
    spec = spec_for({"what": "x" * 300, "where": "y" * 300})
    assert len(spec["summary"]) <= 240 and spec["summary"].endswith("in District 6.")
