"""Hard spending limit for Bedrock calls.

Every model call goes through `converse()`. Before a call it reads what has been spent so far and
refuses when a limit is reached; after a call it adds the call's real cost, computed from the token
counts Bedrock returns and the prices in shared/bedrock_prices.json.

Two limits, both in US dollars, both read from the environment (set by infra/template.yaml):
    MAX_RUN_USD   one run (all resident batches of one POST /runs)
    MAX_DAY_USD   everything in one UTC day for this stack: runs plus POST /scenario calls

Spend is kept in the runs table (RUNS_TABLE) as whole micro-dollars under the keys
`spend#<run_id>` and `spend#day#<YYYY-MM-DD>`. The check happens before each call, so a limit can be
overshot by at most the calls already in flight (10 resident batches at a time).

Without RUNS_TABLE (unit tests, a laptop with no stack) nothing is tracked and nothing is refused.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

PRICES = json.loads((Path(__file__).parent / "bedrock_prices.json").read_text())["models"]


class BudgetError(RuntimeError):
    """A spending limit was reached, a limit is not set, or the model has no sourced price."""


def price(model_id: str) -> dict:
    """Prices for a model id or inference profile id (`us.` / `global.` prefixes are ignored)."""
    base = model_id.split(".", 1)[1] if model_id.split(".", 1)[0] in ("us", "global", "eu", "apac") else model_id
    if base not in PRICES:
        raise BudgetError(f"no sourced price for model {model_id}; add it to shared/bedrock_prices.json")
    return PRICES[base]


def cost_micro_usd(model_id: str, usage: dict) -> int:
    """Cost of one call in micro-dollars, rounded up. `usage` is the Converse response's usage block."""
    p = price(model_id)
    exact = usage.get("inputTokens", 0) * p["input"] + usage.get("outputTokens", 0) * p["output"]  # tokens * $/Mtok = micro-$
    return int(exact) + (exact > int(exact))


def _limit(name: str) -> int:
    raw = os.environ.get(name, "")
    if not raw:
        raise BudgetError(f"{name} is not set; refusing to call a paid model without a limit")
    return int(float(raw) * 1_000_000)


_local = threading.local()


def _table():
    """One table handle per thread, made once: building it for every call cost more time than the model call."""
    import boto3
    name = os.environ["RUNS_TABLE"]
    if getattr(_local, "name", None) != name:
        _local.table, _local.name = boto3.session.Session().resource("dynamodb").Table(name), name
    return _local.table


def _day_key() -> str:
    return "spend#day#" + time.strftime("%Y-%m-%d", time.gmtime())


def _spent(table, key: str) -> int:
    item = table.get_item(Key={"run_id": key}, ConsistentRead=True).get("Item") or {}
    return int(item.get("micro_usd", 0))


def check(run_id: str | None = None, table=None) -> None:
    """Raise BudgetError if the day's or the run's limit is already reached."""
    table = table or _table()
    day = _spent(table, _day_key())
    if day >= _limit("MAX_DAY_USD"):
        raise BudgetError(f"daily spending limit reached (${day / 1e6:.4f} of ${os.environ['MAX_DAY_USD']})")
    if run_id:
        run = _spent(table, f"spend#{run_id}")
        if run >= _limit("MAX_RUN_USD"):
            raise BudgetError(f"run spending limit reached (${run / 1e6:.4f} of ${os.environ['MAX_RUN_USD']})")


def record(micro_usd: int, run_id: str | None = None, table=None) -> None:
    table = table or _table()
    for key in [_day_key()] + ([f"spend#{run_id}"] if run_id else []):
        table.update_item(Key={"run_id": key}, UpdateExpression="ADD micro_usd :c, calls :one",
                          ExpressionAttributeValues={":c": micro_usd, ":one": 1})


def converse(client, run_id: str | None = None, table=None, **kwargs) -> dict:
    """client.converse(**kwargs) behind the spending limit. Use this for every Bedrock call."""
    model_id = kwargs["modelId"]
    if "maxTokens" not in (kwargs.get("inferenceConfig") or {}):
        raise BudgetError("inferenceConfig.maxTokens is required so one call's cost is bounded")
    price(model_id)  # unknown price -> refuse before spending anything
    tracked = table is not None or bool(os.environ.get("RUNS_TABLE"))
    if tracked:
        check(run_id, table)
    resp = client.converse(**kwargs)
    if tracked:
        record(cost_micro_usd(model_id, resp.get("usage", {})), run_id, table)
    return resp
