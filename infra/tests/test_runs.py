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
    for mode, per_call, batches, flight in (("instant", 25, 2, 2), ("fast", 5, 2, 2), ("accurate", 1, 2, 10)):
        out = runs.plan_batches({"run_id": "r1", "spec": SPEC, "mode": mode})
        assert len(out["batches"]) == batches and {b["residents_per_call"] for b in out["batches"]} == {per_call}
        assert out["max_concurrency"] == flight and out["batches"][0]["calls_at_once"] == (5 if mode == "fast" else None)


def test_fast_uses_the_smallest_groups_that_fit_one_minute_of_model_calls():
    assert [runs.per_call_for("fast", n) for n in (500, 1000, 1500, 2000)] == [5, 8, 14, 23]
    for n in (500, 1000, 1500, 2000):                # answer calls plus one quote call per 25 residents stay inside the budget
        k = runs.per_call_for("fast", n)
        assert n / k + n / 25 <= runs.FAST_BUDGET + 1
    assert runs.per_call_for("instant", 2000) == 25 and runs.per_call_for("accurate", 2000) == 1


def test_a_batch_holds_whole_groups(monkeypatch):
    monkeypatch.setenv("PERSONAS_PER_DISTRICT", "500")
    monkeypatch.setattr(runs, "_table", lambda: Table({}))
    out = runs.plan_batches({"run_id": "r1", "spec": {**SPEC, "districts": [5, 6]}, "mode": "fast"})       # 1,000 residents: groups of 8
    sizes = [len(b["persona_ids"]) for b in out["batches"]]
    assert set(sizes[:-1]) == {24} and sum(sizes) == 1000 and out["batches"][0]["calls_at_once"] == 3
    assert out["max_concurrency"] == len(out["batches"])


def test_no_mode_uses_the_stack_default(monkeypatch):
    monkeypatch.setenv("RESIDENTS_PER_CALL", "25")
    assert runs.default_mode() == "instant"
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


def test_a_run_that_died_in_step_functions_is_reported_as_failed(monkeypatch):
    class SF:
        def __init__(self, status):
            self.status = status

        def describe_execution(self, executionArn):
            assert executionArn == "arn:aws:states:us-east-2:1:execution:citysim-x-run:r1"
            return {"status": self.status, "error": "ClientError"}

    monkeypatch.setenv("STATE_MACHINE_ARN", "arn:aws:states:us-east-2:1:stateMachine:citysim-x-run")
    assert runs.execution_failure("r1", SF("RUNNING")) is None and runs.execution_failure("r1", SF("SUCCEEDED")) is None
    assert runs.execution_failure("r1", SF("FAILED")) == "the run failed on the server (ClientError)"
    monkeypatch.delenv("STATE_MACHINE_ARN")
    assert runs.execution_failure("r1", SF("FAILED")) is None
