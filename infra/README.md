# infra/

AWS stack (BUILD.md Step 2). Pick SAM or CDK in the first hour and stick with it.

Resources
- S3 `citysim-data-<account>`: raw/, processed/, personas/
- DynamoDB: `scenarios` (pk spec_id), `runs` (pk spec_id, sk run_id), `calibration` (pk seed#prompt_version)
- Lambdas: `engine`, `residents_batch`, `aggregate`, `chat`
- Step Functions: engine -> inline Map (concurrency 10) over 25-persona batches -> aggregate -> DynamoDB
- HTTP API: POST /scenario, POST /run, GET /run/{id}, POST /chat (CORS: Amplify domain + localhost)
- Amplify Hosting for web/

Lambda size: osmnx/geopandas don't fit a zip Lambda. Precompute routes offline or use a container image.
