# Contracts

Shared formats every lane builds against (BUILD.md Step 1). Change a schema only with the matching fixture update, and log it in LOG.md.

## The question framework (v2)

```
typed question
  └─ agent ──► scenario_spec (status: draft)        actions[] → constraints[]  = left-panel blocks
                 └─ user edits blocks, Ask residents ──► scenario_spec (status: confirmed, version n)
                       └─ engine ──► impacts         per-block numbers → each resident's impact lines (templates, no AI)
                             └─ residents ──► resident_response   stance (support/neutral/oppose) + reason (+ quote for ~10%)
                                   └─ aggregate ──► run_result    what the right panel shows
```

| File | Written by | Read by |
| --- | --- | --- |
| `actions.json` | humans (one source of truth) | agent, engine, web (block rendering) |
| `scenario_spec.schema.json` | `agent/` → edited in `web/` | `engine/`, `residents/` (summary only) |
| `impacts.schema.json` | `engine/` | `residents/` |
| `resident_response.schema.json` | Bedrock (via `residents/`) | `residents/aggregate` |
| `run_result.schema.json` | `engine/` + `residents/` | `web/` |
| `persona.schema.json` | `data/personas` | `residents/` |
| `spec.py` | helpers: `new_action`, `values`, `summary_line`, `apply_edit` | agent, engine, residents |

Rules
- Residents never see the raw `prompt`, only the confirmed spec's neutral `summary` and their own impact lines.
- Residents answer only `stance` and one `reason`. Quotes come from a fixed ~10% sample (`residents/prompt.wants_quote`).
- The engines produce every number; the AI never does.

```
pip install jsonschema
python contracts/validate.py scenario_spec fixtures/scenario_spec.drone.json
```
