# residents/

AI residents: Bedrock batch runner, response checks, aggregation, calibration. Owner: Lane C (BUILD.md Steps 7, 9).

**Answer format (v2):** each resident returns only `stance` (support / neutral / oppose) and one `reason` from the fixed list. About 1 in 10 (picked by `wants_quote`) also return a one-sentence `quote`. They are asked about the confirmed spec's neutral `summary` plus their own impact lines from `contracts/impacts.schema.json`, never the raw prompt.

```
residents/
  prompt.py      SYSTEM + build(personas, spec, impact_lines) -> (message, quote_flags); 25 per call
  validate.py    check(item, ids, wants_quote) against contracts/resident_response.schema.json
  batch.py       Bedrock calls + retry once for failed residents (TODO)
  aggregate.py   weighted support/neutral/oppose, reasons, groups, quotes (TODO)
  calibrate.py   DMACS statements, support=agree (TODO)
  tests/         python -m pytest residents/tests
```
