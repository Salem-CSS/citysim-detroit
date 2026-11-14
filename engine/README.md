# engine/

Traffic engine Lambda: scenario spec in, street loads and per-block impacts out. Owner: Lane B (BUILD.md Steps 5, 11).

```
engine/
  handler.py        Lambda entry; dispatches each action
  trips.py          ITE trip generation + Detroit car-ownership adjustment
  load.py           load = (AADT x K x D) / (lanes x 800)
  actions/          one module per engine action (6)
  tests/            pytest
```

Run tests from repo root: `pip install pytest && python -m pytest engine/tests`.
