import pytest

from shared import budget


class FakeTable:
    def __init__(self):
        self.items = {}

    def get_item(self, Key, ConsistentRead=False):
        item = self.items.get(Key["run_id"])
        return {"Item": dict(item)} if item else {}

    def update_item(self, Key, UpdateExpression, ExpressionAttributeValues):
        item = self.items.setdefault(Key["run_id"], {"micro_usd": 0, "calls": 0})
        item["micro_usd"] += ExpressionAttributeValues[":c"]
        item["calls"] += ExpressionAttributeValues[":one"]


class FakeClient:
    def __init__(self, usage):
        self.usage, self.calls = usage, 0

    def converse(self, **kwargs):
        self.calls += 1
        return {"usage": self.usage}


KW = {"modelId": "us.amazon.nova-lite-v1:0", "inferenceConfig": {"maxTokens": 100}}


def test_cost_uses_listed_prices():
    # 1,000,000 input at $0.06 + 1,000,000 output at $0.24 = $0.30
    assert budget.cost_micro_usd("us.amazon.nova-lite-v1:0", {"inputTokens": 1_000_000, "outputTokens": 1_000_000}) == 300_000
    assert budget.cost_micro_usd("amazon.nova-pro-v1:0", {"inputTokens": 1000, "outputTokens": 1000}) == 4000


def test_unknown_model_is_refused_before_any_call():
    client = FakeClient({})
    with pytest.raises(budget.BudgetError):
        budget.converse(client, table=FakeTable(), modelId="us.made-up-model", inferenceConfig={"maxTokens": 10})
    assert client.calls == 0


def test_max_tokens_is_required():
    with pytest.raises(budget.BudgetError):
        budget.converse(FakeClient({}), table=FakeTable(), modelId="us.amazon.nova-lite-v1:0")


def test_run_limit_stops_further_calls(monkeypatch):
    monkeypatch.setenv("MAX_RUN_USD", "0.50")
    monkeypatch.setenv("MAX_DAY_USD", "10")
    table, client = FakeTable(), FakeClient({"inputTokens": 1_000_000, "outputTokens": 1_000_000})  # $0.30 a call
    budget.converse(client, "run-1", table, **KW)
    budget.converse(client, "run-1", table, **KW)          # $0.60 spent: over the limit now
    with pytest.raises(budget.BudgetError, match="run spending limit"):
        budget.converse(client, "run-1", table, **KW)
    assert client.calls == 2
    budget.converse(client, "run-2", table, **KW)          # another run still has its own allowance


def test_day_limit_covers_all_runs(monkeypatch):
    monkeypatch.setenv("MAX_RUN_USD", "10")
    monkeypatch.setenv("MAX_DAY_USD", "0.50")
    table, client = FakeTable(), FakeClient({"inputTokens": 1_000_000, "outputTokens": 1_000_000})
    budget.converse(client, "run-1", table, **KW)
    budget.converse(client, None, table, **KW)
    with pytest.raises(budget.BudgetError, match="daily spending limit"):
        budget.converse(client, "run-2", table, **KW)


def test_missing_limit_refuses(monkeypatch):
    monkeypatch.delenv("MAX_DAY_USD", raising=False)
    with pytest.raises(budget.BudgetError, match="MAX_DAY_USD is not set"):
        budget.converse(FakeClient({}), "run-1", FakeTable(), **KW)
