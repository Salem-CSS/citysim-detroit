import json

from agent import handler as h


class FakeBedrock:
    def __init__(self, tool_input):
        self.tool_input, self.calls = tool_input, []

    def converse(self, **kw):
        self.calls.append(kw)
        return {"output": {"message": {"content": [{"toolUse": {"name": "submit_actions", "input": self.tool_input}}]}}}


def call(tool_input, **body):
    fake = FakeBedrock(tool_input)
    body.setdefault("question", "What if we expand the Newlab drone route to 200 flights a day?")
    res = h.handler({"body": json.dumps(body)}, client=fake)
    return res, json.loads(res["body"]), fake


def test_drone_question_fills_from_question_and_assumes_rest():
    res, out, fake = call({"actions": [{"type": "add_drone_route", "values": {"hub": "newlab", "flights_per_day": 200}}],
                           "unsupported": [], "confidence": "high"}, districts=[5, 6])
    assert res["statusCode"] == 200
    spec = out["spec"]
    a = spec["actions"][0]
    src = {c["id"]: (c["value"], c["source"]) for c in a["constraints"]}
    assert src["flights_per_day"] == (200, "from_question") and src["hub"] == ("newlab", "from_question")
    assert src["altitude_ft"][1] == "assumed"
    assert spec["status"] == "draft" and spec["districts"] == [5, 6] and spec["summary"].startswith("Proposal: Drone")
    assert "add_drone_route" in fake.calls[0]["system"][0]["text"]          # catalog sent to the model


def test_bad_values_fall_back_with_notes():
    _, out, _ = call({"actions": [{"type": "add_building", "values": {"homes": 99999, "site": "mars", "bogus": 1}}],
                      "unsupported": [], "confidence": "medium"}, question="Build 99999 homes on Mars")
    spec = out["spec"]
    vals = {c["id"]: c for c in spec["actions"][0]["constraints"]}
    assert vals["homes"]["value"] == 2000 and vals["site"]["source"] == "assumed"
    assert any("clamped" in n for n in spec["unsupported"]) and any("isn't an option" in n for n in spec["unsupported"])


def test_followup_bumps_version_and_marks_edited():
    _, first, _ = call({"actions": [{"type": "add_drone_route", "values": {"flights_per_day": 200}}], "unsupported": [], "confidence": "high"})
    _, out, fake = call({"actions": [{"type": "add_drone_route", "values": {"flights_per_day": 200, "flying_hours": "8-20"}}],
                         "unsupported": [], "confidence": "high"}, question="only fly 8 to 8", spec=first["spec"])
    spec = out["spec"]
    assert spec["version"] == 2 and spec["parent_spec_id"] == first["spec"]["spec_id"]
    assert {c["id"]: c["source"] for c in spec["actions"][0]["constraints"]}["flying_hours"] == "edited"
    assert "Current proposal" in fake.calls[0]["messages"][0]["content"][0]["text"]


def test_missing_question_is_400():
    res = h.handler({"body": "{}"}, client=FakeBedrock({}))
    assert res["statusCode"] == 400


def test_spec_validates_against_contract():
    from contracts.validate import validate
    _, out, _ = call({"actions": [{"type": "modify_road", "values": {"street": "vernor_w", "lanes_removed": 1}}],
                      "unsupported": [], "confidence": "medium"}, question="road diet on Vernor", districts=[6])
    assert validate("scenario_spec", out["spec"]) == []


def test_wrapped_value_is_unwrapped():
    from agent.handler import clean_values
    vals, notes = clean_values("add_drone_route", {"flights_per_day": {"value": 150, "source": "from_question"}})
    assert vals == {"flights_per_day": 150} and notes == []
