# Fixtures

Hand-made sample data matching `contracts/` so every lane can build before real data lands. Values are **not real results**.

| File | Contract | Pipeline step |
| --- | --- | --- |
| `scenario_spec.drone.json` | scenario_spec (v2) | Question → standard spec with constraints (left-panel blocks) |
| `impacts.drone.json` | impacts | Engine → per-block impacts → each resident's impact lines |
| `resident_responses.drone.json` | resident_response | What residents return: stance + reason (+ quote for the sample) |
| `run_result.drone.json` | run_result | Totals the frontend shows |

Validate any of them: `python contracts/validate.py <contract> <file>` (for the responses array, validate each item).

Still to add (BUILD.md Step 1): ~50 District 6 street segments, ~20 parcels, ~100 personas.
