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
| Data (census, LODES, Detroit open data → S3) | Partner | Scripts fixed; all 35 raw files downloaded on Partner's laptop (about 2 GB, row counts match the services). Nothing in S3 yet | 11-14 20:20 |
| Buildings (Overture → Athena → tiles) | Salem | **Built in Athena** (335,338 bldgs, 95% measured height). Vector tiles (z10-14, ~20 MB) power the main prototype map + `/map3d.html`. Districts approximate until real file | 11-14 20:00 |
| Engine (traffic Lambda) | — | Load, trips, impact lines work; 6 actions are stubs taking v2 `values` | 11-14 19:05 |
| Residents (Bedrock) | — | v2 framework: prompt + checks + tests done (stance/reason/quote sample); batching stubbed | 11-14 19:05 |
| Agent + Infra (Strands, AWS stack) | — | Not started | 11-14 17:50 |
| Web (Next.js + deck.gl) | Salem | Prototype now on a real 3D Detroit map (MapLibre + deck.gl overlays); Next.js not started | 11-14 20:00 |
| Deploy (Vercel) | Salem | **Live: https://citysim-detroit.vercel.app** (auto-deploys from `main`) | 11-14 17:58 |

## Open questions / handoffs

- **For Partner:** after DATA_SETUP.md, rerun `python -m data.buildings.export_tiles --districts data/raw/detroit/council_districts_2026.geojson` so buildings carry their district.
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
