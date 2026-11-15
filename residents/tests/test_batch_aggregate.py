import json

import pytest

from residents import aggregate, batch, prompt

SPEC = {"spec_id": "s1", "version": 2, "summary": "Proposal: a strip club at Trumbull Ave near Michigan Ave in District 6."}


def people(n=4):
    return [{"persona_id": f"d6-{i:04d}", "district": 6, "block_geoid": f"26163521500200{i}", "weight": 100.0 + i, "age": 30 + 10 * i,
             "sex": "female", "tenure": "owner" if i % 2 else "renter", "vehicles": i % 2, "hh_income": 40000, "children": False,
             "commute_mode": "bus", "education": "bachelor's degree", "race": "Black"} for i in range(n)]


class Table:
    def __init__(self):
        self.items = {}

    def get_item(self, Key, ConsistentRead=False):
        i = self.items.get(Key["run_id"])
        return {"Item": dict(i)} if i else {}

    def update_item(self, Key, UpdateExpression, ExpressionAttributeValues):
        i = self.items.setdefault(Key["run_id"], {"micro_usd": 0, "calls": 0})
        i["micro_usd"] += ExpressionAttributeValues[":c"]
        i["calls"] += 1

    def put_item(self, Item):
        self.items[Item["run_id"]] = Item


class Client:
    """Returns the queued replies in order."""
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def converse(self, **kw):
        self.calls.append(kw)
        return {"output": {"message": {"content": [{"text": self.replies.pop(0)}]}}, "usage": {"inputTokens": 1000, "outputTokens": 100}}


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setattr(batch, "MODEL_ID", "us.amazon.nova-lite-v1:0")
    monkeypatch.setattr(batch, "load_personas", lambda districts: {p["persona_id"]: p for p in people()})
    monkeypatch.setattr(prompt, "QUOTE_SHARE", 0.0)
    monkeypatch.setenv("MAX_RUN_USD", "10")
    monkeypatch.setenv("MAX_DAY_USD", "10")


def event(**kw):
    return {"run_id": "r1", "batch": 0, "persona_ids": [p["persona_id"] for p in people()], "spec": SPEC, "impacts_computed": False, **kw}


def answers(ids, stance="oppose", reason="noise"):
    return json.dumps([{"persona_id": i, "stance": stance, "reason": reason} for i in ids])


def test_invalid_answers_are_asked_once_more_then_dropped():
    ids = [p["persona_id"] for p in people()]
    first = json.dumps([{"persona_id": ids[0], "stance": "oppose", "reason": "noise"},
                        {"persona_id": ids[1], "stance": "maybe", "reason": "noise"},          # bad stance
                        {"persona_id": "d6-9999", "stance": "oppose", "reason": "noise"}])     # unknown resident
    client, table = Client("```json\n" + first + "\n```", answers(ids[1:3])), Table()
    stats = batch.main(event(), client=client, table=table)
    assert stats == {"status": "ok", "asked": 4, "retried": 3, "calls": 2, "valid": 3, "dropped": 1, "quotes_requested": 0}
    rows = json.loads(table.items["resp#r1#0"]["rows"])
    assert [r["persona_id"] for r in rows] == ids[:3] and rows[0]["weight"] == 100.0 and rows[0]["tenure"] == "renter"
    assert ids[0] not in client.calls[1]["messages"][0]["content"][0]["text"]                 # retry asks only the missing ones


def test_no_engine_result_means_no_impact_line():
    client = Client(answers([p["persona_id"] for p in people()]))
    batch.main(event(), client=client, table=Table())
    text = client.calls[0]["messages"][0]["content"][0]["text"]
    assert "Personal impact" not in text and "No direct change" not in text and SPEC["summary"] in text


def test_spending_limit_stops_the_batch(monkeypatch):
    monkeypatch.setenv("MAX_RUN_USD", "0")
    client = Client()
    stats = batch.main(event(), client=client, table=Table())
    assert stats["status"].startswith("stopped") and stats["valid"] == 0 and client.calls == []


def test_totals_are_weighted_and_match_the_contract():
    import jsonschema
    rows = [{**p, "stance": s, "reason": r} for p, (s, r) in zip(people(), [("support", "jobs"), ("oppose", "noise"), ("oppose", "safety"), ("neutral", "none")])]
    rows[1]["quote"] = "Too loud."
    res = aggregate.main(rows, SPEC, {"residents": 5, "retried": 1})
    total = sum(p["weight"] for p in people())
    assert res["overall"]["support"] == round(100 * 100.0 / total, 1) and res["overall"]["oppose"] == round(100 * (101 + 102) / total, 1)
    assert res["districts"] == [{"district": 6, "split": {k: res["overall"][k] for k in ("support", "neutral", "oppose")}, "n": 4, "top_reason": "safety"}]
    assert res["run_stats"]["dropped"] == 1 and res["run_stats"]["drop_rate"] == 0.2 and res["run_stats"]["unreliable"] is True
    assert res["quotes"] == [{"persona_id": "d6-0001", "text": "Too loud.", "stance": "oppose", "reason": "noise", "who": "Homeowner, 40, District 6", "district": 6}]
    assert {g["label"]: g["support"] for g in res["groups"]}["No car"] == round(100 * 100.0 / (100 + 102), 1)
    full = {**res, "run_id": "r1", "status": "done"}
    jsonschema.validate(full, json.load(open("contracts/run_result.schema.json")))
