# CitySim Detroit — Step-by-Step Build Guide

How to build CitySim from an empty repo to a working demo by Sunday 11:30 AM. Written so each step can be handed to an AI coding agent as-is. [SCOPE.md](SCOPE.md) has the full scope: the what and why. This file covers the order and the definition of done.

## Ground rules for every agent

1. **Contracts first.** Nothing gets built until `contracts/` exists (Step 1). Every module reads and writes those schemas. Never change a schema without updating the fixtures and telling the other lanes.
2. **Stay in your folder.** One agent per lane, one folder per lane (see layout). Don't edit another lane's folder.
3. **Engines produce numbers, AI never does.** The chat agent and the resident model never invent traffic counts, trip rates or poll results. Every number traces back to a dataset or the ITE table.
4. **Build against fixtures.** Each lane works on `fixtures/` data until the real pipeline output exists. Then swap it in.
5. **Commit small and often** to `main`, with clear messages. The repo must show the work was done during the 24 hours.
6. **A step is done when its "Done when" check passes.** Not when the code is written.
7. **Secrets never go in git.** Use `.env` (gitignored) locally and SSM Parameter Store or Lambda env vars on AWS.

## Repo layout

```
contracts/      JSON schemas: scenario spec, run result, persona row (Step 1)
fixtures/       Small sample data for one district, used by every lane until real data lands
data/           Download, clean, clip, district-tag and persona pipelines (Python)
engine/         Traffic engine Lambda: actions → trips → streets → load (Python)
residents/      Bedrock batch runner, output validation, calibration (Python)
agent/          Strands scenario-chat agent and its tools (Python)
infra/          AWS stack: API Gateway, Lambdas, Step Functions, DynamoDB, S3 (CDK or SAM)
web/            Next.js + deck.gl frontend
demo/           3 demo prompts, cached results, backup video notes
```

## Lanes

| Lane | Folders | Steps |
| --- | --- | --- |
| A: Data | `data/` | 3, 4, 13 |
| B: Engine | `engine/` | 5, 11 |
| C: Residents | `residents/` | 7, 9 |
| D: Agent + infra | `agent/`, `infra/` | 2, 8, 10 |
| E: Web | `web/` | 6, 12, 14 |

Run 3–4 agents at a time at most. You are the reviewer, so more than that means unreviewed code.

---

## Step 0 — Accounts and access (human, 3:30–4:00 PM)

Agents can't do this part. Do it while Step 1 runs.

- [ ] AWS account in **us-east-1**, billing working, credits applied
- [ ] Bedrock model access: **Nova 2 Lite** (residents) and a stronger model for the chat agent (Nova Pro or Claude)
- [ ] Service Quotas: check Nova requests per minute. You need about 80 calls per 2,000-resident run
- [ ] Census API key (free): https://api.census.gov/data/key_signup.html
- [ ] AWS CLI configured locally (`aws sts get-caller-identity` works)
- [ ] Start the big downloads now in a browser: PUMS Michigan, LODES 8 Michigan, Detroit parcels

**Done when:** `aws bedrock-runtime converse` returns a reply from Nova 2 Lite.

---

## Step 1 — Contracts and fixtures (Lane D, 4:00–4:20 PM)

Write the shared formats that every other lane builds against.

**Create:**
- `contracts/scenario_spec.schema.json`: `actions[]` (each with `type` from the 6 actions plus its parameters), `districts[]`, `assumptions[]`, `confidence` (low / medium / high), `prompt`, `spec_id`
- `contracts/run_result.schema.json`: `spec_id`, `segments[]` (segment id, geometry ref, AADT before/after, lanes, load before/after, color), `districts[]` (support / neutral / oppose %, range, top concerns, 5 sample quotes), `calibration` (per-check error, average error), `run_stats` (valid, retried, dropped, drop rate), `cached` flag
- `contracts/persona.schema.json`: persona id, district, home block, age, sex, income, tenure, years in home, vehicles, commute mode/time, household size, children, work tract
- `fixtures/`: about 50 street segments, 20 parcels and 100 personas for District 6 (Corktown/Southwest), plus one complete `run_result` example. Hand-made values are fine.
- A small validator script: `python contracts/validate.py <schema> <file>`

**Done when:** every fixture passes the validator.

---

## Step 2 — Hello-world AWS stack (Lane D, 4:20–5:30 PM)

Prove the whole AWS path works before any real logic exists, so infrastructure problems show up now and not at 3 AM.

**Create in `infra/`:**
- S3 bucket `citysim-data-<account>`
- DynamoDB tables: `scenarios` (pk `spec_id`), `runs` (pk `spec_id`, sk `run_id`), `calibration` (pk `seed#prompt_version`)
- Lambda `engine` (Python 3.12) that returns the fixture `run_result`
- Lambda `residents_batch` that sends one 25-persona batch to Nova 2 Lite and returns the JSON
- Step Functions state machine: `engine` → **inline Map** over batches → `residents_batch` → aggregate → write to DynamoDB
- API Gateway HTTP API: `POST /scenario`, `POST /run`, `GET /run/{id}`, `POST /chat`, with CORS open to the Amplify domain and localhost

**Lambda size warning:** osmnx and geopandas don't fit in a zip Lambda. Either precompute routes in Step 5 and ship only pandas, numpy and a pickle, or use a container image Lambda. Decide now.

**Done when:** `curl -X POST <api>/run` with a fixture spec starts an execution that writes a result to DynamoDB, using real Bedrock output for one batch.

---

## Step 3 — Data pipeline (Lane A, 4:00–8:00 PM)

Download, clean and district-tag the datasets. Write everything to S3 as GeoParquet under `s3://citysim-data/<dataset>/`.

**Priority order** (stop and move on if one is slow):
1. Council districts 2026 (boundaries for tagging)
2. Traffic volumes (AADT): segments, lanes, speed limit
3. OSM road network via `osmnx` for Detroit
4. Parcels + zoning
5. Census ACS tract tables (age, income, tenure, vehicles, household size, commute mode) + TIGER tracts and block groups
6. Building footprints: Overture via Athena (`SELECT ... FROM overture buildings WHERE bbox intersects Detroit`) or SEMCOG
7. DDOT GTFS
8. LODES 8 Michigan (OD + WAC + RAC)
9. Crashes, 311 (nice to have)
10. DMACS summary percentages, typed into `data/calibration_targets.json`
11. ITE trip rate table, **25–40 land-use codes**, typed into `data/ite_rates.csv` (`code, name, unit, daily_rate, pm_peak_rate, source_url`)

**Each dataset gets:** a download script, a clean step, a `district` column from a spatial join, and a row count logged to `data/manifest.json`.

**Done when:** `data/manifest.json` lists every loaded dataset with row counts, and AADT segments join to OSM edges for at least 90% of counted segments in District 6.

---

## Step 4 — Personas (Lane A, 6:00–9:00 PM)

**Do:**
- Pull PUMS person and household records for the Detroit PUMAs
- Fit to each district's tract totals with `ipfn` on 5 controls: age band, income band, tenure, vehicles (0 / 1 / 2+), household size
- Draw 500 per district with `SEED=1114`. Assign a home block in proportion to block population, and a work tract from LODES
- Carry over commute mode/time, years in home and children from the PUMS record
- Write to `s3://citysim-data/personas/district_{n}.parquet`

**Fallback if IPF stalls past 8:30 PM:** sample PUMS by person weight and reweight on tenure + vehicles only. Note it in the Method tab.

**Done when:** each district file has 500 rows that pass `persona.schema.json`, and the district's renter share and zero-car share are within 5 points of ACS.

---

## Step 5 — Traffic engine: `add_building` (Lane B, 4:30–9:00 PM)

Build the full traffic path for one action first, on fixtures, then on real data.

**Pipeline** (`engine/`):
1. **Trips:** size × ITE daily and PM-peak rate from `ite_rates.csv`. A missing code gets the nearest code and `confidence: low`.
2. **Detroit adjustment:** scale car trips by the tract's car-ownership share (ACS). Keep the raw ITE number too, for display.
3. **Distribute:** split by destination using LODES flows from the site's tract (top destinations, grouped by direction).
4. **Assign:** shortest path on the OSM graph from the site to each destination group. **Precompute the graph and paths offline** and load a pickle in Lambda.
5. **Load:** `(AADT × K × D) / (through lanes per direction × 800)` with K = 0.09, D = 0.55, all editable via spec `assumptions`.
6. **Per-block impact:** for each home block, cars/day added on its nearest street, plus distance to the site. This feeds the residents.

**Tests:** 400 apartments at Michigan and 14th gives 400 × 4.54 = 1,816 raw daily trips before adjustment. The Michigan Ave load stays under 0.75.

**Done when:** the engine Lambda returns a valid `run_result.segments[]` and per-block impacts for a real D6 spec in under 2 seconds.

---

## Step 6 — Frontend shell (Lane E, 4:30–10:00 PM)

Build entirely on fixtures. Don't wait for the backend.

**Do** (`web/`, Next.js + deck.gl + MapLibre):
- Amazon Location (or MapLibre demo) base map centered on Corktown
- Extruded buildings layer from a GeoJSON fixture, colored by impact
- Streets layer colored by load (green < 0.50, yellow < 0.75, orange < 0.90, red ≥ 0.90), with before/after toggle
- Left: chat panel (input, message list, confirmation card with Edit / Run)
- Right: results panel (support / neutral / oppose per district, top concerns, quotes), Method tab (assumptions, run stats, drop rate), Calibration tab (simulated vs real, error in points)
- District picker (up to 4)
- **Offline mode:** `?offline=1` loads results from `public/cached/*.json` with no backend

**Done when:** the fixture `run_result` renders fully, and offline mode works with the network off.

---

## Step 7 — Resident runner (Lane C, 5:30–11:00 PM)

**Do** (`residents/`):
- Build prompts from the SCOPE.md template: persona traits + `scenario_summary` + `impact_lines` from the engine's per-block output
- Batch 25 personas per Bedrock call, Nova 2 Lite, temperature 0.7, JSON-only output
- Validate each item: `support` 1–5, `top_concern` from the fixed list, `reaction` under 200 chars, `persona_id` matches
- Retry failed personas once in a smaller batch. Still invalid means dropped. Log valid / retried / dropped / drop rate. Flag the run if drops exceed 5%
- Aggregate: post-stratify to district census totals, report support (4–5) / neutral (3) / oppose (1–2), top 3 concerns, 5 representative quotes
- Range: rerun aggregation on 3 bootstrap resamples, report min–max
- Exponential backoff on 429s, capped concurrency
- Cache by `hash(scenario summary + impact band + persona_id)`

**Done when:** 500 D6 personas on a real spec produce a valid `run_result.districts[]` entry with a drop rate under 5%.

---

## Step 8 — Wire the real pipeline (Lane D, 9:00 PM–12:00 AM)

**Do:**
- Replace the stub Lambdas with the real `engine/` and `residents/` code
- Step Functions: engine → split personas from the touched districts into batches → inline Map (concurrency cap 10) → aggregate → DynamoDB
- Save every spec to `scenarios` and every result to `runs`
- `GET /run/{id}` returns status + result

**Done when:** `POST /run` with a real `add_building` spec in 2 districts returns a full result in under 60 seconds.

---

## Step 9 — Calibration (Lane C, 9:00 PM–2:00 AM)

**Do:**
- Ask all personas the 3 DMACS Wave 22 questions in SCOPE.md (safety walking, neighborhood satisfaction, right direction)
- Compute simulated %, real %, absolute error per check and average error
- Add the persona sanity check (share living in Detroit 20+ years vs 78%) from persona traits
- Store in DynamoDB `calibration` with seed + prompt version
- If one check is consistently off, test one prompt change and rerun. Don't tune more than twice: report what you measured

**Done when:** the calibration result is in DynamoDB and renders in the Calibration tab, whatever the error is.

---

## Step 10 — Scenario chat agent (Lane D, 12:00–4:00 AM)

**Do** (`agent/`, Strands Agents in a plain Lambda, not AgentCore):
- Tools: `geocode` (Amazon Location), `find_parcels`, `lookup_trip_rate`, and one tool per engine action: `add_building`, `modify_road`, `add_drone_route`, `change_transit`, `rezone`, `add_event_surge`
- Output is always a spec that passes `scenario_spec.schema.json`, plus a one-line plain-English summary for the confirmation card
- Follow-ups edit the current spec ("make it 4 stories," "also cut a lane on Michigan")
- Actions not built yet return "not supported yet". Off-topic or unsafe requests get a short refusal
- System prompt: the agent interprets only, never states traffic or sentiment numbers

**Test prompts:**
1. "Expand the Newlab drone route to 200 flights a day over Corktown"
2. "Build 400 apartments at Michigan and 14th"
3. "Turn the vacant lot at Michigan and 14th into a 6-story apartment building with a ground-floor grocery, and cut a lane on Michigan"
4. "Put a skate park on Bagley" (expect nearest code, low confidence)
5. "What's the weather" (expect refusal)

**Done when:** all 5 behave as expected, 3 times in a row.

---

## Step 11 — Remaining engine actions (Lane B, 9:00 PM–5:00 AM)

In this order. Each needs a unit test and a real D6 run.

1. `modify_road`: same volume, new lane count. Closure reroutes to the next shortest path. Test: Michigan Ave 2 → 1 through lane per direction goes from about 0.32 to about 0.64
2. `add_drone_route`: van trips removed = packages to drones ÷ packages per van trip. Flight path buffered as a noise band. Personas inside the band get flagged, and "inside Michigan Central corridor" is added to their impact lines
3. `change_transit`: GTFS frequency change → riders lost (stop-level service × tract transit share) → split into other routes / car / lost trips
4. `rezone`: max units under the new zone → call `add_building`
5. `add_event_surge`: event-day profile added on top of daily AADT

**Done when:** each action returns a valid result for a real spec. Any action not done by 5 AM is marked "not supported yet" in the agent.

---

## Step 12 — Connect the frontend (Lane E, 12:00–4:00 AM)

- Chat panel → `POST /chat` → confirmation card → Run → `POST /run` → poll `GET /run/{id}` → map + results
- Run history list from DynamoDB, with a compare view for two runs side by side
- Loading state while residents run (progress from batches done / total)
- Errors fall back to the cached result, labeled "cached run"

**Done when:** test prompt 3 runs from typing to colored map and sentiment results in the deployed app.

---

## Step 13 — All districts built (Lane A, 2:00–6:00 AM)

- Run the data clip, building tiles and persona steps for all 7 districts (3,500 personas)
- Run calibration on all 3,500
- Note total Bedrock calls and cost for the scale slide

**Done when:** any 4 districts load in the picker in seconds.

---

## Step 14 — Demo cache and polish (Lane E + you, 6:00–9:00 AM)

- Run the 3 demo prompts (drone, housing, combined) and save the results to `web/public/cached/` and `demo/`
- Check every number on screen has a source or an assumption label
- Add the "forecast, not a poll" and "sandbox, not a traffic study" labels
- Deploy to Amplify, then test on the venue Wi-Fi and a phone hotspot
- Record the 1–2 minute backup video of the full demo path

**Done when:** the full demo runs live once and in offline mode once, both under 4 minutes.

---

## Step 15 — Rehearse and submit (9:00–11:30 AM)

- [ ] Three full rehearsals following the demo script in SCOPE.md
- [ ] README updated: what it does, architecture diagram, how to run, data sources, AI tools used
- [ ] Shipyard: title, elevator pitch, AWS track, repo link, AI tools listed, backup video
- [ ] Submit by **11:30 AM** (deadline 12:00 PM). At the table with a working demo by 12:30 PM

---

## Checkpoints

If a checkpoint is missed, apply the cut order in SCOPE.md before moving on.

| Time | Must be true |
| --- | --- |
| 5:30 PM | Bedrock works, contracts + fixtures committed, hello-world stack deployed |
| 8:00 PM (doors lock) | Core datasets in S3, frontend renders fixtures |
| 12:00 AM | `add_building` runs end to end with real residents in 1 district |
| 4:00 AM | Chat → spec → run works; calibration shown |
| 6:00 AM | Feature freeze. Only fixes, cache and polish after this |
| 11:30 AM | Submitted |
