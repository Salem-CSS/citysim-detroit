# Contracts

The shared JSON formats every lane builds against (BUILD.md Step 1). Change a schema only with the matching fixture update, and tell the other lanes.

| Schema | Written by | Read by |
| --- | --- | --- |
| `scenario_spec.schema.json` | `agent/` (from a typed proposal) | `engine/`, `residents/`, `web/` confirmation card |
| `run_result.schema.json` | `engine/` + `residents/` | `web/` results panel and map |
| `persona.schema.json` | `data/personas` | `residents/` |

`run_result` includes everything the prototype (`web/prototype/index.html`) shows: overall split, worries, support by group, per-district split, quotes, street loads, per-block popover data, calibration and run stats.

```
pip install jsonschema
python contracts/validate.py run_result fixtures/run_result.drone.json
```
