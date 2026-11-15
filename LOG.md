# CitySim Detroit — Team log

Shared change log for both teammates **and their AI assistants**. It's how we keep each other in sync without talking: read it before you start, add to it when you finish.

## How to use this file

**Before starting work:** `git pull`, then read **Status board** and the newest 10 entries.

**After finishing a chunk of work** (before or with your commit):
1. Add an entry at the **top** of **Entries** using the template below.
2. Update the **Status board** row for your lane if it changed.
3. If you need something from the other person, add it to **Open questions / handoffs**.
4. Commit `LOG.md` in the same commit as your work, then `git pull --rebase && git push` right away so the other side sees it.

**Rules**
- Newest entry first. Never edit or delete someone else's entry; add a new one that corrects it.
- Times in Eastern (ET). Who = `Salem` or `Partner`, plus `(AI)` if an assistant made the change.
- Say what changed **and why**. List files. Note anything that breaks or changes a contract in `contracts/`.
- Never paste secrets, keys or passwords here.
- If a merge conflict happens in this file, keep both entries.

### Entry template

```markdown
### YYYY-MM-DD HH:MM ET · Who · Lane
**Did:** one or two sentences.
**Files:** path/one, path/two
**Contracts changed:** none | which schema + what
**Decisions:** anything the other side should know or follow
**Blocked / needs:** none | what and from whom
**Next:** what you're doing next
```

Lanes: `Data`, `Engine`, `Residents`, `Agent+Infra`, `Web`, `Docs`, `Deploy`.

---

## Status board

| Lane | Owner | Status | Last update |
| --- | --- | --- | --- |
| Data (census, LODES, Detroit open data → S3) | Partner | **In S3:** `s3://citysim-data-707604458164/raw/` (us-east-2), 35 files, 2.07 GB. Processing not started | 11-14 20:41 |
| Buildings (Overture → tiles) | Salem + Partner | 335,338 bldgs; tiles tagged with **official 2026 districts**; table rebuilt with DuckDB and stored in `s3://citysim-data-707604458164/processed/buildings/` | 11-14 21:04 |
| Engine (traffic Lambda) | — | Load, trips, impact lines work; 6 actions are stubs taking v2 `values` | 11-14 19:05 |
| Residents (Bedrock) | Partner | **Working end to end**: 3,500 personas, batch + totals deployed in us-east-2 on Nova 2 Lite; not calibrated | 11-14 22:15 |
| Agent + Infra (AWS stack) | Salem | `infra/` SAM stack written (not deployed yet). `POST /scenario` works in tests (Bedrock → validated v2 spec); run pipeline wired with stubs | 11-14 20:35 |
| Web (Next.js + deck.gl) | Salem | Prototype now on a real 3D Detroit map (MapLibre + deck.gl overlays); Next.js not started | 11-14 20:00 |
| Deploy (Vercel) | Salem | **Live: https://citysim-detroit.vercel.app** (auto-deploys from `main`) | 11-14 17:58 |

## Open questions / handoffs

- **For Partner:** read AWS_ACCESS.md. Salem adds your IAM user; you deploy your own `citysim-partner` stack with `./infra/deploy.sh partner`. Your lane: `residents/batch.py` + `aggregate.py` and `data/`/personas. The pipeline already calls them (see `infra/runs.py`).
- **For Salem:** enable Bedrock model access (Nova Pro + Nova Lite) in us-east-1 and check the Free plan allows it; then `./infra/deploy.sh salem` (CloudShell works).
- **For Partner:** after DATA_SETUP.md, rerun `python -m data.buildings.export_tiles --districts data/raw/detroit/council_districts_2026.geojson` so buildings carry their district.
- **For Partner:** contracts changed to v2 (see 19:05 entry). If your AI already wrote code against the old `top_concern` / 1–5 `support` / `assumptions` fields, update it.
- **For Partner:** run DATA_SETUP.md, then BUILDINGS.md. Post bucket name, object count and building totals here when done.
- **For Partner:** confirm which AWS region you're using (docs assume `us-east-1`; Overture/Athena work runs in `us-west-2`).
- **For Salem:** pick the final frontend direction before Next.js work starts (current pick: combined design in `web/prototype`).

---

## Entries

### 2026-11-14 23:15 ET · Salem (AI) · Web (branch `salem/frontend-try`)
**Did:** Created branch `salem/frontend-try` from main (8ea8879) for Salem's frontend experiments. Vercel builds a preview for it; production stays on `main`.
**Files:** LOG.md (this branch only)
**Contracts changed:** none
**Decisions:** Nothing on this branch reaches `main` until Salem merges it.
**Blocked / needs:** none
**Next:** frontend edits on this branch.

### 2026-11-14 23:16 ET · Partner (AI) · Residents (calibration)
**Did:** Built and ran the accuracy check. `residents/calibrate.py` asks residents four statements with a known real answer from the Detroit resident survey (DMACS) and compares the census-weighted share who agree. 1,400 residents (200 per district), every result stored in `residents/calibration_results.json`. Each run result now carries `calibration` for the deployed model and persona card, and the prototype's "forecast, not a poll" note shows it.

| Model, card | Safe walking (real 85) | Satisfied with neighborhood (67) | Right direction (55) | Used transit (32) | Avg error |
| --- | --- | --- | --- | --- | --- |
| Nova 2 Lite, base | 62.4 | 71.5 | 45.3 | 12.4 | **14.1** |
| Nova 2 Lite, tier1 | 48.2 | 61.5 | 36.8 | 14.5 | 19.5 |
| Nova Lite, base | 27.1 | 46.3 | 27.2 | 4.4 | 33.5 |
| Nova Lite, tier1 | 27.6 | 35.0 | 18.9 | 2.0 | 38.9 |

**Files:** residents/calibrate.py, residents/calibration_results.json (new), residents/{prompt,aggregate}.py, infra/template.yaml (`PersonaCard`, default `base`), web/prototype/index.html (`accuracyNote`), LOG.md
**Contracts changed:** none. `run_result.calibration` is filled (`measured`, `avg_error_pts`, `checks[]`, plus `model`, `run_at`).
**Decisions:** Deployed residents use **Nova 2 Lite with the base card**. The richer Tier 1 census fields made answers less accurate (19.5 vs 14.1 points): with more hardship detail the model answers more negatively than real Detroiters do. By the plan's own rule (7.1: keep a tier only if error drops) Tier 1 stays off; it is still on every persona row and can be switched on with `PersonaCard=tier1`. Nova Lite is cheaper but far less accurate, so it is not used. Nova Pro could not be measured (throttled).
**Blocked / needs:** Residents are too negative overall, most on safety (62 vs 85) and transit use (12 vs 32). Real values are the ones in BACKEND_PLAN.md section 10 and were not re-read from the survey PDFs; `data/calibration_targets.json` still says 70 for safe walking where the plan says 85. Residents answered a statement, not the survey's own question and scale. Haiku 5.5 was not compared (not available in this account).
**Next:** neighborhood facts (Tier 2), tested the same way.

### 2026-11-14 23:02 ET · Partner (AI) · Engine + Residents + Data
**Did:** Each resident is now told how far the verified proposal is from their home. `engine/proximity.py` (pure Python) measures from the resident's home block interior point to the verified point, or to the straight line between a route's verified start and end (the line says so, since the real path is unknown). Personas gained `home_lon` / `home_lat` (block interior point, not an address); rebuilt with the same seed and re-uploaded. `infra/runs.plan_batches` passes the spec's verified places to each batch; `residents/batch.py` adds the distance line and stores `distance_m`; `aggregate.py` adds `exposure` groups (within a quarter mile / quarter mile to a mile / more than a mile). Deployed to both stacks.
**Verified live (`citysim-partner`):** strip club at Trumbull St & Michigan Ave, District 6, 500 residents, 0 dropped, $0.06. By distance: within 1/4 mile (6 residents) 100% oppose; 1/4 to 1 mile (55) 100% oppose; 1 to 3 miles (208) 58% oppose, 41% neutral; over 3 miles (231) 2% oppose, 98% neutral. Overall 0.3% support / 63.4% neutral / 36.3% oppose. Distance check: Newlab to Michigan & Trumbull measures 782 m.
**Files:** engine/proximity.py (new), engine/tests/test_proximity.py (new), data/personas/build.py, residents/{batch,aggregate}.py, infra/runs.py, LOG.md
**Contracts changed:** none. Persona rows carry extra columns `home_lon`, `home_lat`.
**Decisions:** Distance is the only personal impact until the traffic engine exists. District 6 is large: only 61 of its 500 residents live within a mile of Michigan & Trumbull, so a district-wide total is mostly people far away.
**Blocked / needs:** The same proposal gave 12% support before distance was added and 0.3% after, and the split by distance is very sharp. The model leans hard on whatever line it is given; this needs the calibration check before the numbers are trusted.
**Next:** calibration against the Detroit survey figures.

### 2026-11-14 22:59 ET · Partner (AI) · Agent + Data + Web (contracts)
**Did:** Place resolver (BACKEND_PLAN.md 11.2) built and deployed to `citysim-partner` and `citysim-main`. `shared/places.py` verifies a typed place against the city road layer (2,263 streets, 16,211 crossings, 61,217 address ranges, built by `data/places/build_index.py` into `s3://citysim-data-707604458164/processed/places/places.json`) and, for landmarks, Amazon Location place search limited to Detroit. `agent/handler.check_places` runs it on every spec: a route needs a verified start and end, anything else one verified place. Missing, not found, ambiguous or outside the selected districts → `status: "needs_info"` with `questions[]`; `POST /runs` refuses such a spec (400) and re-checks places after panel edits. The prototype shows the questions with clickable alternatives, disables the run button until answered, and shows "Verified: …" under place boxes.
**Verified live:** "strip club on Trumbull near Michigan" → Trumbull St & Michigan Ave, District 6. "bus route from the Hilton hotel to the Renaissance Center" → asks which of three Hiltons; answering "Hilton Garden Inn" resolves both ends. "Woodward and 5th" → both real, do not cross, offers Woodward & Temple / Edmund / Alfred. "a new drone delivery route" → asks for start and end. "in my neighborhood" → not a specific place. "Michigan and 14th" with only District 5 selected → reports it is in District 6.
**Files:** shared/places.py (new), shared/tests/test_places.py (new), data/places/{__init__,build_index}.py (new), agent/handler.py, contracts/{actions.json,scenario_spec.schema.json,spec.py}, infra/{runs.py,template.yaml}, web/prototype/index.html (`questionsHTML`, `wireQuestions`), LOG.md
**Contracts changed:**
- `scenario_spec`: `status` gains `needs_info`; new `questions[]` (`id`, `label`, `text`, `options`); a text constraint may carry `resolved` (`name`, `method`, `lon`, `lat`, `district`).
- `actions.json`: `add_drone_route` and `change_transit` gain text constraints `from` and `to`.
- `summary_line`: a route reads "… from A to B".
**Decisions:** Nothing is guessed. A landmark hit is accepted only if its title carries the user's own words; otherwise it is offered as a choice. A place the model fills in that the user never named is cleared and asked for. In a follow-up, an unchanged value keeps its earlier source (before, every value became `edited`). Unknown fields the model adds are dropped silently. Each place search adds $0.0005 to the day's spend.
**Blocked / needs:** "Civic Center" returns only a street from the place search, so it is asked about. `modify_road` and `rezone` are checked as a single place, not a stretch or an area. No marker on the map yet (web lane).
**Next:** distance from each resident's home to the proposal.

### 2026-11-14 22:49 ET · Partner (AI) · Web + Infra
**Did:** The prototype's "Ask residents" button now runs real residents when `CITYSIM_API` is set and a live spec is open: it sends the spec with the panel's edits to `POST /runs`, polls `GET /runs/{id}` every 2 s, and draws the real result (overall split and range, district tiles and map dots, top three reasons, quotes in the resident card, a "Live · N residents" badge). Without a backend or spec it still plays the mock. Partner approved this web change. Verified on a local copy against `citysim-main`: strip club across Districts 4-7, 2,000 residents, 17% support / 23% neutral / 60% oppose; a What box edited to "a strip club with a rooftop bar" arrived in the spec as `edited`.
**Files:** web/prototype/index.html (ids on the result elements; `specWithEdits`, `showResult`, `runLive`, `finishRun`; run handler branches to live), infra/runs.py, LOG.md
**Contracts changed:** none. `start_run` now rebuilds `spec.summary` with `summary_line` so residents read the edited proposal.
**Decisions:** The traffic note says "not calculated" until the engine returns numbers; it no longer claims "no problem". "Lives in noise zone" in the resident card shows "Not calculated".
**Blocked / needs:** Salem: Compare and Briefing buttons are untouched. The green check styling on the traffic note is left as is.
**Next:** place resolver (BACKEND_PLAN.md 11.2).

### 2026-11-14 22:15 ET · Partner (AI) · Residents + Infra
**Did:** Residents now answer. `residents/batch.py` asks 25 residents per Bedrock call behind the spending limit, checks every answer, asks invalid ones once more, then drops and counts them. `residents/aggregate.py` builds the run result (census-weighted overall split with bootstrap range, per district, reasons, groups by tenure / age / vehicles, quotes, per block, run stats). Wired into `infra/runs.py`; deployed to `citysim-partner` and `citysim-main` (us-east-2) with `ResidentModelId=us.amazon.nova-2-lite-v1:0`. Real runs on `citysim-partner`: strip club, District 6: 500 residents, 37 calls, 13 s, $0.06, 0 dropped, 12.3% support / 25.4% neutral / 62.3% oppose. 120-unit apartment building, Districts 5 and 6: 1,000 residents, 88 calls, 20 s, $0.13, 8 dropped, 18.0 / 25.8 / 56.1.
**Files:** residents/batch.py, residents/aggregate.py, residents/prompt.py, residents/tests/test_batch_aggregate.py (new), infra/runs.py, data/personas/build.py (also writes `district_{n}.json`), LOG.md
**Contracts changed:** none. The result validates against `run_result.schema.json`. Extra fields beyond it: `engine_status`, `stopped` (when the spending limit ends a run early), `run_stats.model_cost_usd`. `GET /runs/{id}` now returns `result` with real numbers (it is stored as text, so numbers are no longer strings).
**Decisions:**
- **Quotes are a second call.** In the first 500-resident trial every resident marked "quote: yes" answered support and nobody else did: the marker was steering the stance. Stances are now asked with no mention of quotes (`SYSTEM_STANCE`), then the sampled residents are asked for a sentence given the stance they already gave (`SYSTEM_QUOTES`, `build_quotes`). `prompt.build(..., quotes=True)` and `SYSTEM` are unchanged for other callers.
- **No engine result means no impact line.** With "Personal impact: not calculated" 24 of 25 residents answered neutral. `build(personas, spec, None)` now leaves the line out and tells the model no impact figures exist.
- **Resident line** adds the Tier 1 census facts (`census_details`); `PERSONA_CARD=base` turns them off for the calibration comparison.
- **Haiku 5.5 is not available in this AWS account** ("not available for this account"), so residents run on Nova 2 Lite.
- Answers go to the runs table (`resp#<run_id>#<batch>`), not through Step Functions, whose payload limit a 2,000-resident run would exceed.
**Blocked / needs:** Not calibrated: nothing yet shows these splits match real Detroiters, and one model call answers 25 residents at once, so answers within a batch may be more alike than real neighbors. Reasons are limited to the fixed list (a strip club draws mostly "noise"). Salem: the prototype's run button is still the mock; it needs `POST /runs` with the spec, then `GET /runs/{id}` until `stage` is `done`.
**Next:** engine for `add_building`, then bus; place resolver (11.2); calibration.

### 2026-11-14 21:49 ET · Partner (AI) · Data (personas) + Residents
**Did:** Built the residents: `data/personas/build.py` writes 500 per district (3,500 total) to `data/processed/personas/district_{n}.parquet`, uploaded to `s3://citysim-data-707604458164/personas/`. Every row is one real anonymous PUMS 2020-2024 record; all 3,500 pass `contracts/persona.schema.json`. Household weights were fitted per district to income, tenure x vehicles and tenure x household size; renter and zero-car household shares match ACS to three decimals in every district. Tier 1 fields from BACKEND_PLAN.md 7.1 are included as extra columns (race, Hispanic origin, education, employment, disability, difficulty walking, born abroad, veteran, poverty ratio, building type, housing cost share of income, someone 65+ at home, home language, internet, SNAP). Also: the quote share is now a deploy setting, and Amazon Location place search was tested.
**Files:** data/personas/build.py, residents/prompt.py, infra/template.yaml (`QuoteShare`), BACKEND_PLAN.md (11.2 place-search result), LOG.md
**Contracts changed:** none. Persona rows carry extra columns beyond the schema (it does not forbid them): `move_in_band` and the Tier 1 fields. `years_in_home` is null for everyone because the census gives a band, not a number.
**Decisions:** `QuoteShare` (default 0.1) sets how many residents also write a sentence; raise it at deploy time, no code change. PUMS code meanings were checked against the Census PUMS Data Dictionary 2020-2024. Blocks are assigned to the official 2026 districts by interior point.
**Blocked / needs:** Known gap: among adults, renter share runs 4 to 9 points below the household share (for example District 5: 56.5% of adults vs 65.7% of households). Owner households hold more adults, so some gap is expected, but it has not been checked against an adult-level census table (B25008 is not downloaded). Not built: nearest street per persona, Tier 2 (what is around their home), occupation and departure time.
**Next:** `residents/batch.py` with real model calls, then `aggregate.py`.

### 2026-11-14 21:39 ET · Partner (AI) · Web + Docs
**Did:** (1) The prototype panel now shows the spec's `what` and `where` text constraints as editable text blocks (Partner asked for this one web change and nothing else). Checked locally against the live backend: a strip club question shows What = "a strip club", Where = "Trumbull Ave near Michigan Ave". (2) Wrote the plan for verifying places and asking the user for missing ones: BACKEND_PLAN.md section 11.2. Plan only, nothing built.
**Files:** web/prototype/index.html (one CSS rule; `blockHTML`, `specToLib`, `wireBlocks`, and the run handler's baseline line), BACKEND_PLAN.md, LOG.md
**Contracts changed:** none. Section 11.2 proposes: `status: "needs_info"`, `questions[]`, `from` / `to` text constraints on route actions, and a `resolved` place on a constraint. Not applied.
**Decisions:** Places are verified against map data, never guessed: cross streets and addresses from the city road layer and parcels, landmarks from Amazon Location Service (not yet verified or priced). A route needs a verified start and end; if a place is missing or not found, the scenario step asks the user and a run is refused until it is answered. Quick test on the road layer: Michigan and Trumbull meet; Woodward and 5th exist but do not meet.
**Blocked / needs:** Salem: text edits in the panel are local only, like the other blocks (the run button is still the mock). When 11.2 is built the web side needs to show the questions and a marker.
**Next:** personas, `residents/batch.py`, `residents/aggregate.py`.

### 2026-11-14 21:32 ET · Partner (AI) · Agent (contracts)
**Did:** Free input. Residents are now asked about what the user actually typed, not the nearest preset. Before: "What if a strip club opens on Trumbull Ave near Michigan Ave?" became "New building (site: Parking lot on Trumbull, apartments: 0 homes, floors: 3, ground floor: Shops, ...)". Now: "Proposal: a strip club at Trumbull Ave near Michigan Ave in District 6." Also added Claude Haiku 5.5 to the price file. Deployed to `citysim-partner` and `citysim-main` (us-east-2).
**Files:** contracts/actions.json, contracts/spec.py, fixtures/scenario_spec.drone.json, agent/handler.py, agent/system_prompt.md, agent/tests/test_free_input.py (new), shared/bedrock_prices.json, BACKEND_PLAN.md (new section 11.1), LOG.md
**Contracts changed:**
- `actions.json`: every action template starts with two text constraints, `what` (the thing proposed, in the user's terms) and `where` (the place they named). The schema already allowed `type: "text"`, so `scenario_spec.schema.json` is unchanged.
- `spec.summary_line`: leads with `what` and `where`, then lists only settings whose source is `from_question` or `edited`. Assumed defaults are no longer read to residents. A preset place (`site`, `hub`, `street`, `route`) is left out when the user gave their own `where`.
- `fixtures/scenario_spec.drone.json`: has `what` / `where`; summary regenerated ("Proposal: an expanded Newlab drone delivery route (takes off from: Newlab rooftop, flights a day: 200 flights) in Districts 4, 5, 6, 7.").
**Decisions:** Partner's rule (BACKEND_PLAN.md 11.1): any proposal, placed anywhere in the selected districts, reaches residents as stated. On a first question, a number or option that does not appear in the question is marked `assumed` with a note, whatever the model returns.
**Blocked / needs:** Salem: the prototype panel renders only number and select blocks, so `what` / `where` do not show as editable blocks yet (they do show in the summary). The reason list has nothing for objections to the kind of venue; propose adding one. Not built: geocoding `where` and checking it is inside the selected districts; traffic for uses with no published rate.
**Next:** personas, `residents/batch.py`, `residents/aggregate.py`, then `add_building` in the engine.

### 2026-11-14 21:04 ET · Partner (AI) · Data + Web + Infra
**Did:** (1) Rebuilt the Detroit buildings table on a laptop with DuckDB from the same Overture release (2026-10-21.0); it matches the Athena build exactly: 335,338 buildings, 318,480 measured, 94 from floors, 16,764 defaulted, max 221.5 m. Uploaded to `s3://citysim-data-707604458164/processed/buildings/detroit_buildings.parquet`. (2) Replaced the hand-drawn districts with the city's **official 2026 council districts** in `geo/districts.geojson`, re-split the road corridors by them, and re-exported all 222 tiles so each building's `d` tag is official. (3) Deployed `citysim-main` in account 707604458164 (us-east-2) and pointed `web/prototype/config.js` at it. (4) Fixed the agent dropping a value the model wrapped as `{value, source}`. (5) $10 monthly AWS budget with email alerts at 50% and 100%. (6) Git tags `checkpoint-2026-11-14-before-build` (branch) and `checkpoint-2026-11-14-main` (main before this merge).
**Files:** data/buildings/duckdb_build.py (new), web/prototype/tools/make_geo.py (`--districts`), web/prototype/geo/{districts,overlays,residents_demo}.geojson, web/prototype/tiles/** (regenerated), web/prototype/config.js, agent/handler.py, agent/tests/test_handler.py, LOG.md
**Contracts changed:** none
**Decisions:** Live backend = `citysim-main` in 707604458164: `https://ja14jurk92.execute-api.us-east-2.amazonaws.com`. Test stack `citysim-partner`: `https://6dxcfjf4tg.execute-api.us-east-2.amazonaws.com`. Buildings per district changed a lot with the official boundaries (old → new): D1 68,621 → 63,015; D2 53,395 → 49,792; D3 63,179 → 50,452; D4 12,632 → 45,953; D5 32,700 → 32,416; D6 24,994 → 36,538; D7 79,653 → 57,052; outside any district 164 → 120.
**Blocked / needs:** Salem: `detroit_map.py` REGIONS are no longer used when `--districts` is passed; anything else in index.html that assumed the old shapes should be checked. Resident dots in `residents_demo.geojson` are still demo placements.
**Next:** personas, `residents/batch.py`, `residents/aggregate.py`.

### 2026-11-14 20:50 ET · Partner (AI) · Agent+Infra
**Did:** Deployed `citysim-partner` in account 707604458164, **us-east-2**: `https://6dxcfjf4tg.execute-api.us-east-2.amazonaws.com`. `POST /scenario` returned a valid drone spec from a real Nova Pro call in that account (no second account needed); `POST /runs` → `GET /runs/{id}` completes through the stubs. Added a hard spending limit for every Bedrock call.
**Files:** shared/budget.py (new), shared/bedrock_prices.json (new), shared/tests/test_budget.py (new), agent/handler.py (model call goes through `budget.converse`), infra/template.yaml (MaxRunUsd, MaxDayUsd, MaxResidentsPerRun; BedrockRegion default is now the stack's region; spend-counter table access), infra/runs.py (resident cap in `start_run`), infra/deploy.sh (comment)
**Contracts changed:** none
**Decisions:** All Bedrock calls must use `shared.budget.converse(client, run_id, modelId=..., inferenceConfig={"maxTokens": ...})`. It refuses a call when the run or the UTC day has reached its limit ($10 each by default), when `maxTokens` is missing, or when the model has no price in `shared/bedrock_prices.json` (prices come from the AWS Price List API for us-east-2; Haiku 5.5 is not listed there yet, so it is refused until a sourced price is added). Spend is stored in the runs table under `spend#...` keys. Deploy here with `AWS_REGION=us-east-2 ./infra/deploy.sh <stage> DataBucket=citysim-data-707604458164`.
**Blocked / needs:** Salem: this touched your `agent/handler.py` and `infra/` files; shout if the BedrockRegion default change affects your stack (empty now means the stack's own region). No budget email alert yet.
**Next:** personas and `residents/batch.py`.

### 2026-11-14 20:41 ET · Partner (AI) · Data + Infra
**Did:** Created the data bucket and uploaded all raw data: `s3://citysim-data-707604458164/raw/` in **us-east-2**, 35 objects, 2.07 GB (byte count matches the laptop). Merged `main` (backend skeleton, dual-account Bedrock) into `claude/confident-ritchie-ccwiqs`; 19 tests pass. Parcels (377,940 rows) and city building footprints (380,076 rows) are complete after a downloader fix.
**Files:** data/download/_arcgis.py, LOG.md
**Contracts changed:** none
**Decisions:** Partner wants the live backend in account **707604458164** (AWS project "Fresh Deploy"), not 574246332084. That account's organization policy refuses us-east-1, us-west-1 and us-west-2; **us-east-2 (Ohio) works**. Read access checked there for S3, Lambda, DynamoDB, Step Functions, API Gateway, CloudFormation, Bedrock, Location, Budgets. Inference profiles `us.amazon.nova-2-lite-v1:0` and `us.anthropic.claude-haiku-5-5` are listed in us-east-2; no model call has been made yet. The command line signs in with `aws login` (browser session), so no access keys exist.
**Blocked / needs:** Salem: `infra/deploy.sh` and `BedrockRegion` default to us-east-1; in this account they need `AWS_REGION=us-east-2` and `BedrockRegion=us-east-2`. Athena (us-west-2) cannot run in this account. Real council districts are at `raw/detroit/council_districts_2026.geojson` (7 rows).
**Next:** spending alert, then a first deploy of the stack in us-east-2.

### 2026-11-15 ET · Partner (AI) · Residents + Data (plan only)
**Did:** Switched the resident model to Claude Haiku 5.5 and added a researched plan for richer personas (more census fields per resident, plus what is around their home). No code changed.
**Files:** BACKEND_PLAN.md (sections 2.3, 5.1, 7.1, 9, 10, 13), .env.example
**Contracts changed:** none. Section 7.1 would add fields to `persona.schema.json` when built; not done yet.
**Decisions:** Resident model is `us.anthropic.claude-haiku-5-5` with effort low; Nova 2 Lite is kept only as the calibration comparison. Richer persona tiers are adopted only if they lower calibration error (7.1).
**Blocked / needs:** Confirm Haiku 5.5 and Nova prices on the Bedrock pricing page; read the Haiku 5.5 quota; the account needs the AWS Marketplace subscribe permission for Anthropic models.
**Next:** Build the base personas first, then test the Tier 1 and Tier 2 cards against calibration.
### 2026-11-14 20:45 ET · Salem (AI) · Agent+Infra
**Did:** Dual-account mode. Main account (574246332084) is still being verified by AWS, so Bedrock calls are refused there. The stack can now call Bedrock through a role in a second, verified account: `infra/bedrock-role.yaml` (deploy in the second account) + `BedrockRoleArn=` deploy parameter. `shared/aws.py:bedrock_runtime()` borrows the role (cached temporary credentials) or uses this account when the parameter is empty. Steps in AWS_ACCESS.md §3.
**Files:** shared/{aws.py,tests/test_aws.py}, infra/{template.yaml,bedrock-role.yaml,deploy.sh}, agent/handler.py, residents/batch.py (docstring), AWS_ACCESS.md, LOG.md
**Contracts changed:** none
**Decisions:** All Bedrock calls go through `shared.aws.bedrock_runtime()`. Partner: use it in residents/batch.py instead of boto3.client("bedrock-runtime").
**Blocked / needs:** a verified second account to deploy bedrock-role.yaml and send its RoleArn; then deploy citysim-salem with it.
**Next:** deploy + test real questions.

### 2026-11-14 20:35 ET · Salem (AI) · Agent+Infra
**Did:** Backend skeleton as code. `agent/handler.py` = `POST /scenario`: question → Bedrock (tool call with the action catalog from contracts/actions.json) → values checked against the contract (clamped / defaulted with notes) → draft v2 spec with `from_question` / `assumed` / `edited` sources and a summary built from the values. `infra/template.yaml` (SAM): HTTP API, scenario + run Lambdas, DynamoDB runs table, Step Functions (engine → Map over 25-resident batches, 10 at a time → aggregate). Stubbed steps record `not_implemented` instead of failing. `infra/deploy.sh <stage>` deploys a per-person stack. Prototype calls `/scenario` when `web/prototype/config.js` sets `CITYSIM_API`, and falls back to the offline mock otherwise.
**Files:** agent/handler.py, agent/tests/test_handler.py, infra/{template.yaml,runs.py,deploy.sh,README.md,__init__.py}, AWS_ACCESS.md, web/prototype/{config.js,index.html}, CLAUDE.md, .gitignore
**Contracts changed:** none (agent output validates against scenario_spec.schema.json in tests)
**Decisions:** SAM (not CDK). Stacks: citysim-salem / citysim-partner / citysim-main in us-east-1. Default models are parameters: AgentModelId `us.amazon.nova-pro-v1:0`, ResidentModelId `us.amazon.nova-lite-v1:0` (switch to Nova 2 Lite once enabled). No Strands for the agent; one Bedrock Converse tool call keeps it fast and simple.
**Blocked / needs:** Bedrock model access + a first deploy (Salem). Partner IAM user (Salem).
**Next:** deploy citysim-salem, set CITYSIM_API, try real questions; then the engine for add_drone_route.

### 2026-11-14 20:20 ET · Salem (AI) · Web
**Did:** Resident dots are white before a run (were grey). After a run they keep the stance colors: blue support, grey neutral, orange oppose.
**Files:** web/prototype/index.html
**Contracts changed:** none
**Decisions:** none
**Blocked / needs:** none
**Next:** —

### 2026-11-14 20:15 ET · Salem (AI) · Web
**Did:** Roads only show inside the selected districts (corridors pre-split per district in overlays.geojson, property `d`). Added a Roads on/off toggle in the map key; roads show before and after a run while the toggle is on.
**Files:** web/prototype/tools/make_geo.py, web/prototype/geo/overlays.geojson, web/prototype/index.html, LOG.md
**Contracts changed:** none
**Decisions:** Road pieces are split by the APPROXIMATE district shapes; rerun make_geo.py when the real districts land.
**Blocked / needs:** none
**Next:** —

### 2026-11-14 20:10 ET · Salem (AI) · Web
**Did:** Road overlay now uses real street geometry: 12 corridors (Michigan, Woodward, Gratiot, Grand River, Jefferson, 8 Mile, I-94, I-75 Fisher + Chrysler, M-10 Lodge, I-96 Jeffries, M-39 Southfield) pulled from Overture transportation segments in Athena (`overture.segments`), clipped to city limits. Freeways drawn wider; hover shows name + traffic band; map key shows Light / Busy / Heavy.
**Files:** web/prototype/tools/roads_overture.json (raw WKT from Athena), web/prototype/tools/make_geo.py (CORRIDORS), web/prototype/geo/overlays.geojson, web/prototype/index.html, LOG.md
**Contracts changed:** none
**Decisions:** The road loads in overlays.geojson are DEMO values. Engine output (`impacts` per road segment) replaces them; join on corridor name for now, segment id later.
**Blocked / needs:** none
**Next:** W Vernor Hwy isn't in the corridor set (not tagged as a primary road in Overture); add it if the road-change block keeps using it.

### 2026-11-14 20:00 ET · Salem (AI) · Web + Data
**Did:** Main prototype (`web/prototype/index.html`) now runs on a real 3D Detroit map: MapLibre `fill-extrusion` buildings from vector tiles + deck.gl overlays (district outlines, busy roads after a run, drone route + noise band, resident dots by stance). District picker dims other districts and flies to the selection; blocks panel pads the map. Replaced the JSON tile format with Mapbox Vector Tiles because it's much faster: shapes are processed in web workers and low zooms only carry big buildings. Loaded in 1.8 s even in a software-rendered test browser; the JSON version took minutes there.
**Files:** data/buildings/export_mvt.py (new, replaces export_tiles.py), data/buildings/tests/test_export.py, web/prototype/{index.html,map3d.html}, web/prototype/tiles/** (generated), web/prototype/geo/{detroit,districts,overlays,residents_demo}.geojson, web/prototype/tools/make_geo.py, BUILDINGS.md, data/requirements.txt (+mapbox-vector-tile). Removed web/prototype/buildings/, js/buildings.js.
**Contracts changed:** none
**Decisions:** City limits are the real Overture polygon. Districts in `geo/districts.geojson` are APPROXIMATE (hand regions clipped to city limits) and every building's `d` tag comes from them. Resident dots are demo placements (~1 in 120 homes), not engine output.
**Blocked / needs:** Partner: `council_districts_2026.geojson` → rerun make_geo.py (point it at the real file) + export_mvt, commit.
**Next:** Next.js port uses the same tiles (`<SimMap />` = MapLibre + deck.gl MapboxOverlay).

### 2026-11-14 19:45 ET · Salem (AI) · Data
**Did:** Exported `overture.detroit_buildings` as one Parquet (Athena CTAS `detroit_buildings_export`, bucket_count 1), downloaded it, ran `export_tiles`: 335,338 buildings in 465 tiles, 12.8 MB, counts match Athena. Checked the render locally (downtown, stadiums, RenCen correct). Committed tiles so Vercel serves `/map3d.html`.
**Files:** web/prototype/buildings/** (generated), .gitignore (tiles no longer ignored), BUILDINGS.md, LOG.md
**Contracts changed:** none
**Decisions:** Tiles live in the repo under web/prototype/buildings/ (not data/processed). Regenerate + commit when district tagging lands.
**Blocked / needs:** council districts GeoJSON (Partner, DATA_SETUP.md) to tag buildings by district.
**Next:** use map3d as the base map in the main prototype / Next.js.

### 2026-11-14 19:35 ET · Salem (AI) · Data
**Did:** Built accurate Detroit buildings in Athena (us-west-2, account 574246332084): Overture 2026-10-21.0 → bbox cut → clipped to the Overture `Detroit` locality polygon → height filled. 335,338 buildings; 318,480 measured height, 94 from floors, 16,764 defaulted; median 5.1 m, max 221.5 m, 105 at 50 m+. Scripted the whole thing (SQL + boto3 runner), wrote a tile exporter and a deck.gl 3D map page (tested on synthetic tiles).
**Files:** data/buildings/{athena_build.py,export_tiles.py,sql/01-04,tests/test_export.py}, web/prototype/map3d.html, BUILDINGS.md (fast path section; bbox fields fixed to `double`), data/requirements.txt (+boto3), .gitignore (+web/prototype/buildings/)
**Contracts changed:** none
**Decisions:** Overture only (95% measured heights; SEMCOG optional). AWS account is on the Free plan (no charges). Athena bucket: `citysim-athena-574246332084-usw2`; tables `overture.detroit_buildings` (clipped) and `overture.detroit_bbox_buildings`. Tile format documented in export_tiles.py docstring.
**Blocked / needs:** someone with AWS CLI creds runs `athena_build --download-only` + `export_tiles` (the AI workspace can't reach S3). Tile hosting decision (see handoffs).
**Next:** generate tiles, host them, then wire map3d into the Next.js app as the base map.
### 2026-11-14 19:08 ET · Partner (AI) · Data + Residents
**Did:** Merged `main` (contracts v2) into `claude/confident-ritchie-ccwiqs`, no conflicts; 8 tests pass. Fixed the download scripts per BACKEND_PLAN.md section 3 and started the downloads on Partner's laptop. Confirmed the nine FAR values in `data/zoning_capacity.csv` against the official Municode text. Parked a seven-question set for a later second engine.
**Files:** data/download/* (new `_arcgis.py`, rewritten `detroit.py`, `census.py`, `_http.py`, `all.py`), data/config.py, data/ite_rates.csv, engine/trips.py, data/zoning_capacity.csv, residents/correction_questions.py (new), BACKEND_PLAN.md, DATA_SETUP.md, data/README.md
**Contracts changed:** none
**Decisions:** Two engines. Engine one (build first) is the v2 flow already on `main`: stance + one reason. Engine two, the correction engine (later), reads why residents opposed and proposes a changed request; its seven questions sit in `residents/correction_questions.py` and touch no contract. Detroit files now come straight from the city's ArcGIS feature services with row counts checked; every download is listed in `data/raw/manifest.json`. `CENSUS_API_KEY` is required.
**Blocked / needs:** Census key in `.env` for the ACS and block-population pulls. Parcels download stops at row 333,000 with a server error; being fixed. No S3 bucket created yet (waiting on Partner's AWS walkthrough).
**Next:** finish downloads, then AWS setup, then BACKEND_PLAN.md section 13.

### 2026-11-14 19:10 ET · Salem (AI) · Agent+Infra
**Did:** Read-only look at the team AWS account (console). It is empty: 0 S3 buckets, 0 Lambda functions (us-east-1 and us-east-2), 0 DynamoDB tables, 0 IAM users. Console defaults to us-east-2 (Ohio). Bedrock no longer needs "model access" turned on; models enable on first call.
**Files:** none
**Contracts changed:** none
**Decisions:** Use **us-east-1** for everything except the Overture/Athena step (us-west-2), as the docs assume. Nothing created yet.
**Blocked / needs:** Data setup (DATA_SETUP.md) can start: create `citysim-data-<account-id>` in us-east-1.
**Next:** —

### 2026-11-14 19:05 ET · Salem (AI) · All lanes (contracts)
**Did:** Switched the whole repo to the **v2 question framework**: question → standard spec with constraints (editable blocks) → user edits → confirmed spec → engine impacts → per-resident impact lines → residents answer **only support / neutral / oppose + one reason** (quote for a fixed ~10% sample) → totals.
**Files:** contracts/actions.json (new), contracts/scenario_spec.schema.json (v2), contracts/impacts.schema.json (new), contracts/resident_response.schema.json (new), contracts/run_result.schema.json, contracts/spec.py (new helpers), contracts/README.md, fixtures/* (all updated + impacts.drone.json, resident_responses.drone.json), residents/prompt.py, residents/validate.py, residents/{batch,aggregate,calibrate}.py docstrings, residents/tests/, agent/system_prompt.md, agent/tools.py, engine/handler.py, engine/actions/*, engine/impact_lines.py (new), engine/tests/, data/calibration_targets.json, SCOPE.md, BUILD.md, web/prototype/index.html
**Contracts changed:**
- `scenario_spec`: actions now carry `constraints[]` (`id, label, type, value, unit, min, max, step, options, ui, show, show_if, source`); added `version`, `status` (draft/confirmed), `unsupported`; removed `assumptions` (use `source: "assumed"`). `summary` is the neutral sentence residents are asked about.
- `actions.json`: one source of truth for the 6 action types and their constraints.
- `impacts` (new): blocks[] numbers + persona_impacts[].lines (templates, no AI).
- `resident_response` (new): `stance` support/neutral/oppose, `reason` fixed list (`none` only with neutral), `quote` only for the sample.
- `run_result`: `worries` → `reasons` (with `share_among_oppose`); `districts[].top_concern` and `blocks[].top_concern` → `top_reason`; quotes need `reason`; added `spec_version`, `run_stats.quotes_requested`.
**Decisions:** Residents never see the raw prompt. Calibration questions are asked as statements (support = agree). Engine action modules now take `values` dicts (`contracts.spec.values(action)`).
**Blocked / needs:** none. Tests: `python -m pytest engine/tests residents/tests` (8 pass).
**Next:** —

### 2026-11-14 18:10 ET · Salem (AI) · Web
**Did:** Removed the welcome card. Rebuilt the prototype map in Detroit's shape: north-up camera, city outline (8 Mile, riverfront, southwest wedge), Detroit River, Belle Isle, Highland Park and Hamtramck cut out, all 7 council districts outlined in their colors. Unselected districts in the top picker are dimmed on the map. Main roads on real-ish paths (Woodward, Gratiot, Grand River, Michigan, Jefferson, Vernor, I-94). Drone route runs from Michigan Central east across Districts 6, 5, 4.
**Files:** web/prototype/index.html, web/prototype/tools/detroit_map.py (generator)
**Contracts changed:** none
**Decisions:** City and district shapes are **approximate** (hand-placed lon/lat in `tools/detroit_map.py`). The real app must draw them from `data/raw/detroit/council_districts_2026.geojson` and the TIGER Detroit place boundary.
**Blocked / needs:** real district GeoJSON from Partner's data run.
**Next:** —

### 2026-11-14 17:58 ET · Salem (AI) · Deploy
**Did:** First Vercel deploy succeeded. Site is live at **https://citysim-detroit.vercel.app** (serves `web/prototype/index.html`).
**Files:** none (Vercel dashboard)
**Contracts changed:** none
**Decisions:** Vercel project `citysim-detroit` on Salem's Hobby account, root directory `web/prototype`, preset Other, no build. Every push to `main` redeploys. When Next.js is ready: Project Settings → General → Root Directory = `web`, framework auto-detects. The backend API URL will go in Vercel env vars (e.g. `NEXT_PUBLIC_API_URL`).
**Blocked / needs:** none
**Next:** —

### 2026-11-14 17:55 ET · Salem (AI) · Deploy
**Did:** Dropped Render (the service was configured but never deployed, so nothing exists there). Hosting the frontend on **Vercel** instead.
**Files:** none yet (Vercel dashboard)
**Contracts changed:** none
**Decisions:** Vercel project settings: repo `Salem-CSS/citysim-detroit`, branch `main`, framework preset **Other**, root directory `web/prototype`, no build command, no install command. When Next.js lands in `web/`, change the root directory to `web` and the framework preset to Next.js (auto-detected). Backend stays on AWS; the site calls API Gateway. Ignore the Render entry below.
**Blocked / needs:** Salem to install the Vercel GitHub app for this repo.
**Next:** first deploy, then post the live URL here.

### 2026-11-14 17:50 ET · Salem (AI) · Deploy
**Did:** Configured a Render **web service** (not static) for the site: repo `Salem-CSS/citysim-detroit`, branch `main`, Python 3, region Virginia (US East), free instance. Until the Next.js app exists it serves the prototype with `python -m http.server $PORT --directory web/prototype`. Auto-deploys on commits that touch `web/**`.
**Files:** none (Render dashboard)
**Contracts changed:** none
**Decisions:** When Next.js lands in `web/`, change Render to Node: root directory `web`, build `npm ci && npm run build`, start `npm start`. Free instances sleep after inactivity (first load can take about a minute); switch to the $7 plan before demo day or open the site a few minutes before presenting.
**Blocked / needs:** none
**Next:** add the live URL here after the first deploy.

### 2026-11-14 17:45 ET · Salem (AI) · Docs
**Did:** Added this log and `CLAUDE.md` so both AI assistants read the log first and append to it after changes.
**Files:** LOG.md, CLAUDE.md
**Contracts changed:** none
**Decisions:** Every commit that changes behavior gets a LOG.md entry.
**Blocked / needs:** none
**Next:** —

### 2026-11-14 17:30 ET · Salem (AI) · Docs
**Did:** Added BUILDINGS.md: Overture (Athena or DuckDB) + SEMCOG footprints → merged heights → Detroit clip → tagged with district, parcel, census block → one GeoJSON per district for deck.gl.
**Files:** BUILDINGS.md, data/requirements.txt (duckdb), README.md, DATA_SETUP.md
**Contracts changed:** none (building fields listed in BUILDINGS.md)
**Decisions:** Height order: Overture height → Overture floors × 3.5 m → SEMCOG stories × 3.5 m → default by type. SEMCOG 2020 layer confirmed; look for 2024 first.
**Blocked / needs:** Partner to run it after DATA_SETUP.md.
**Next:** —

### 2026-11-14 17:15 ET · Salem (AI) · Web
**Did:** Rebuilt the static prototype as the combined design: district picker in the top bar (max 4), question-built constraint blocks in the left panel, district results on the right, floating resident cards on map click, bottom ask bar.
**Files:** web/prototype/index.html
**Contracts changed:** none (blocks map 1:1 to `scenario_spec.actions`)
**Decisions:** Keyword matching in the prototype is a stand-in for the agent; real blocks come from the agent's spec.
**Blocked / needs:** none
**Next:** —

### 2026-11-14 16:55 ET · Salem (AI) · Docs
**Did:** Added DATA_SETUP.md: download everything on a laptop and `aws s3 sync` into the partner's bucket (data does not go in GitHub).
**Files:** DATA_SETUP.md, README.md, data/README.md
**Contracts changed:** none
**Decisions:** S3 layout `raw/`, `processed/`, `personas/` in `citysim-data-<account-id>`.
**Blocked / needs:** Partner runs it.
**Next:** —

### 2026-11-14 16:45 ET · Salem (AI) · Data / all lanes
**Did:** Scaffolded the repo: `contracts/` (scenario spec, run result, persona schemas + validator), `fixtures/`, `data/` download scripts (census, LODES, Detroit open data), `engine/` (load + trip generation with tests), `residents/` (prompt + checks), `agent/`, `infra/`, `web/`, `demo/`.
**Files:** many; see commit 28ea46e
**Contracts changed:** created v1 of all three schemas. `run_result` includes overall split, worries, groups, districts, quotes, segments, blocks, calibration, run_stats.
**Decisions:** Contracts are the source of truth between lanes; change them only with fixtures.
**Blocked / needs:** none
**Next:** —

### 2026-11-14 15:35 ET · Salem (AI) · Docs
**Did:** Updated SCOPE.md (free-form prompts → 6 engine actions, 80 Bedrock calls per run, 3 cached demo prompts, up to 4 districts) and added BUILD.md (step-by-step build guide with lanes and checkpoints).
**Files:** SCOPE.md, BUILD.md, README.md
**Contracts changed:** none
**Decisions:** No preset scenarios; the chat agent maps any question to the 6 actions.
**Blocked / needs:** none
**Next:** —
