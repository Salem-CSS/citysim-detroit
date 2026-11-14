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
| Data (census, LODES, Detroit open data → S3) | Partner | Not started. Scripts ready; follow DATA_SETUP.md | 11-14 17:50 |
| Buildings (Overture + SEMCOG → S3) | Partner | Not started. Follow BUILDINGS.md after data | 11-14 17:50 |
| Engine (traffic Lambda) | — | Scaffolded: load + trips work, 6 actions are stubs | 11-14 17:50 |
| Residents (Bedrock) | — | Scaffolded: prompt + response checks work, batching stubbed | 11-14 17:50 |
| Agent + Infra (Strands, AWS stack) | — | Not started | 11-14 17:50 |
| Web (Next.js + deck.gl) | Salem | Static prototype done (`web/prototype/index.html`); Next.js not started | 11-14 17:50 |
| Deploy (Vercel) | Salem | **Live: https://citysim-detroit.vercel.app** (auto-deploys from `main`) | 11-14 17:58 |

## Open questions / handoffs

- **For Partner:** run DATA_SETUP.md, then BUILDINGS.md. Post bucket name, object count and building totals here when done.
- **For Partner:** confirm which AWS region you're using (docs assume `us-east-1`; Overture/Athena work runs in `us-west-2`).
- **For Salem:** pick the final frontend direction before Next.js work starts (current pick: combined design in `web/prototype`).

---

## Entries

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
