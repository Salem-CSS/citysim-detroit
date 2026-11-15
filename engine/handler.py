"""Lambda entry point: confirmed scenario spec (v2) in, segments + impacts out (BUILD.md Steps 5, 11).

Contract in:  contracts/scenario_spec.schema.json (status must be "confirmed")
Contract out: run_result.segments / trips, and contracts/impacts.schema.json (blocks + persona_impacts.lines)
"""
import importlib, json
from contracts.spec import values

def handler(event, context=None):
    spec = event if isinstance(event, dict) and "actions" in event else json.loads(event["body"])
    if spec.get("status") != "confirmed":
        raise ValueError("engine only runs confirmed specs")
    results = []
    for action in spec["actions"]:
        mod = importlib.import_module(f"engine.actions.{action['type']}")
        results.append(mod.run(values(action), ctx=None))
    # TODO: sum segment deltas, compute load before/after, build impacts.blocks,
    #       then persona_impacts.lines with impact_lines.py templates (no AI).
    return {"spec_id": spec["spec_id"], "spec_version": spec["version"], "actions": results}
