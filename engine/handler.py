"""Lambda entry point: scenario spec in, segments + per-block impacts out (BUILD.md Steps 5, 11).

Contract in:  contracts/scenario_spec.schema.json
Contract out: run_result.segments / trips / blocks (sentiment fields are filled by residents/)
"""
import importlib, json

def handler(event, context=None):
    spec = event if isinstance(event, dict) and "actions" in event else json.loads(event["body"])
    results = []
    for action in spec["actions"]:
        mod = importlib.import_module(f"engine.actions.{action['type']}")
        results.append(mod.run(action, ctx=None))
    # TODO: sum segment deltas across actions, compute load before/after, build per-block impacts
    return {"spec_id": spec["spec_id"], "actions": results}
