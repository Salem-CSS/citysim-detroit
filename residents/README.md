# residents/

AI residents: Bedrock batch runner, output validation, aggregation, calibration. Owner: Lane C (BUILD.md Steps 7, 9).

```
residents/
  prompt.py      prompt template, 25 personas per call
  validate.py    schema checks on each response; support -> stance
  batch.py       Bedrock calls + retry (TODO)
  aggregate.py   weighted splits, worries, groups, quotes (TODO)
  calibrate.py   DMACS checks (TODO)
```
