# CitySim Detroit

Forecasts **traffic load** and **public sentiment** for proposed changes in Detroit neighborhoods: housing, drone delivery, road diets, bus changes and more. Pick up to 4 of Detroit's 7 City Council districts, place a scenario on a realistic 3D map, and see street-by-street load plus support and opposition from 500 census-based AI residents per district.

Built for the BuilderWars Hackathon (Nov 14–15, 2026, Newlab Detroit), AWS track.

- **Team log (read first, write last):** [LOG.md](LOG.md)
- **Full project scope:** [SCOPE.md](SCOPE.md)
- **Step-by-step build guide:** [BUILD.md](BUILD.md)
- **Data setup (AWS owner does this first):** [DATA_SETUP.md](DATA_SETUP.md)
- **3D buildings (after data setup):** [BUILDINGS.md](BUILDINGS.md)
- **Stack:** Next.js + deck.gl, API Gateway, Lambda, Step Functions, Amazon Bedrock (Nova 2 Lite), Strands Agents, DynamoDB, S3 + Athena

All data comes from public sources listed in the scope.

## Repo layout

```
contracts/   JSON schemas shared by every lane (scenario spec, run result, persona)
fixtures/    sample data matching the schemas, for building before real data lands
data/        download scripts (census, LODES, Detroit open data), cleaning, personas
engine/      traffic engine Lambda: actions -> trips -> streets -> load
residents/   Bedrock batch runner, response checks, aggregation, calibration
agent/       Strands scenario-chat agent
infra/       AWS stack
web/         Next.js + deck.gl app; web/prototype/ is the design reference
demo/        demo prompts and cached runs
```

**Get the data:** follow [DATA_SETUP.md](DATA_SETUP.md) (download, then upload to S3).
