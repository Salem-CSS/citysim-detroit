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
| Data (census, LODES, Detroit open data → S3) | Partner | Scripts fixed; downloads running locally (8 city files done, parcels failing at 333k rows). Census API pulls wait on key. Nothing in S3 | 11-14 19:08 |
| Buildings (Overture + SEMCOG → S3) | Partner | Not started. Follow BUILDINGS.md after data | 11-14 17:50 |
| Engine (traffic Lambda) | — | Load, trips, impact lines work; 6 actions are stubs taking v2 `values` | 11-14 19:05 |
| Residents (Bedrock) | — | v2 framework: prompt + checks + tests done (stance/reason/quote sample); batching stubbed | 11-14 19:05 |
| Agent + Infra (Strands, AWS stack) | — | Not started | 11-14 17:50 |
| Web (Next.js + deck.gl) | Salem | Static prototype done (`web/prototype/index.html`); Next.js not started | 11-14 17:50 |
| Deploy (Vercel) | Salem | **Live: https://citysim-detroit.vercel.app** (auto-deploys from `main`) | 11-14 17:58 |

## Open questions / handoffs

- **For Partner:** contracts changed to v2 (see 19:05 entry). If your AI already wrote code against the old `top_concern` / 1–5 `support` / `assumptions` fields, update it.
- **For Partner:** run DATA_SETUP.md, then BUILDINGS.md. Post bucket name, object count and building totals here when done.
- **For Partner:** confirm which AWS region you're using (docs assume `us-east-1`; Overture/Athena work runs in `us-west-2`).
- **For Salem:** pick the final frontend direction before Next.js work starts (current pick: combined design in `web/prototype`).

---

## Entries

### 2026-11-15 ET · Partner (AI) · Residents + Data (plan only)
**Did:** Switched the resident model to Claude Haiku 5.5 and added a researched plan for richer personas (more census fields per resident, plus what is around their home). No code changed.
**Files:** BACKEND_PLAN.md (sections 2.3, 5.1, 7.1, 9, 10, 13), .env.example
**Contracts changed:** none. Section 7.1 would add fields to `persona.schema.json` when built; not done yet.
**Decisions:** Resident model is `us.anthropic.claude-haiku-5-5` with effort low; Nova 2 Lite is kept only as the calibration comparison. Richer persona tiers are adopted only if they lower calibration error (7.1).
**Blocked / needs:** Confirm Haiku 5.5 and Nova prices on the Bedrock pricing page; read the Haiku 5.5 quota; the account needs the AWS Marketplace subscribe permission for Anthropic models.
**Next:** Build the base personas first, then test the Tier 1 and Tier 2 cards against calibration.

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
