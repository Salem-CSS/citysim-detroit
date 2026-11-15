"""Run glue: the Fast / Accurate mode reaches every batch, and GET /runs/{id}/answers returns each resident's answer."""
import json

from contracts.validate import validate
from infra import runs


class Table:
    def __init__(self, items):
        self.items = items

    def get_item(self, Key, **kw):
        return {"Item": dict(self.items[Key["run_id"]])} if Key["run_id"] in self.items else {}

    def update_item(self, Key, **kw):
        self.items.setdefault(Key["run_id"], {"run_id": Key["run_id"]})


SPEC = {"spec_id": "s1", "version": 1, "summary": "Proposal: a test.", "districts": [6], "actions": []}


def test_mode_sets_residents_per_call(monkeypatch):
    monkeypatch.setenv("PERSONAS_PER_DISTRICT", "50")
    monkeypatch.setattr(runs, "_table", lambda: Table({}))
    for mode, per_call in (("fast", 25), ("accurate", 1)):
        out = runs.plan_batches({"run_id": "r1", "spec": SPEC, "mode": mode})
        assert len(out["batches"]) == 2 and {b["residents_per_call"] for b in out["batches"]} == {per_call}


def test_no_mode_uses_the_stack_default(monkeypatch):
    monkeypatch.setenv("RESIDENTS_PER_CALL", "25")
    assert runs.default_mode() == "fast"
    monkeypatch.setenv("RESIDENTS_PER_CALL", "1")
    assert runs.default_mode() == "accurate"


def test_answers_endpoint_matches_the_contract(monkeypatch):
    rows = [{"persona_id": "d6-0000", "stance": "oppose", "reason": "noise", "quote": "Too loud.", "distance_m": 310, "weight": 100.0, "age": 40},
            {"persona_id": "d6-0001", "stance": "support", "reason": "jobs", "weight": 90.0, "age": 30}]
    table = Table({"r1": {"run_id": "r1", "status": "done", "mode": "accurate", "batches": 2},
                   "resp#r1#0": {"rows": json.dumps(rows[:1])}, "resp#r1#1": {"rows": json.dumps(rows[1:])}})
    monkeypatch.setattr(runs, "_table", lambda: table)
    resp = runs.get_answers({"pathParameters": {"id": "r1"}})
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 200 and validate("run_answers", body) == []
    assert body["answers"] == [{"persona_id": "d6-0000", "stance": "oppose", "reason": "noise", "quote": "Too loud.", "distance_m": 310},
                               {"persona_id": "d6-0001", "stance": "support", "reason": "jobs"}]
    assert runs.get_answers({"pathParameters": {"id": "resp#r1#0"}})["statusCode"] == 404
    assert runs.get_answers({"pathParameters": {"id": "nope"}})["statusCode"] == 404
