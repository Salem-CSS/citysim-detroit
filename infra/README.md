# infra/

AWS SAM stack for the backend. Setup, access and deploys: [../AWS_ACCESS.md](../AWS_ACCESS.md).

- `template.yaml`: HTTP API (`POST /scenario`, `POST /runs`, `GET /runs/{id}`), Lambdas, DynamoDB runs table, Step Functions run pipeline (engine -> inline Map over 25-resident batches, concurrency 10 -> aggregate). One stack per Stage.
- `runs.py`: run-pipeline glue that calls engine/ and residents/.
- `deploy.sh <stage>`: packages agent/, contracts/, engine/, residents/ and runs `sam deploy`.

Heavy GIS libs (osmnx/geopandas) don't fit a zip Lambda: precompute routes offline or switch that function to a container image.
