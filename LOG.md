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
| Engine (traffic Lambda) | Partner | Buildings (trips, one-street load) and bus route reach computed and deployed; other types not built | 11-15 |
| Residents (Bedrock) | Partner | **Working end to end** on Nova 2 Lite, base card. Two modes per run: Fast (25 residents per call) and Accurate (one per call, about 2 to 3 min per district). GET /runs/{id}/answers gives each resident's answer. Accuracy check 13.1 pts average error (measured on the old batches) | 11-15 04:15 |
| Agent + Infra (scenario step, AWS stack) | Salem + Partner | Live in account 707604458164, us-east-2: free input, place verification with questions (crossing, address, landmark, coordinates, a stretch of a street), run progress, failed runs reported. Limits: $10 a run, **$50 a day (raised by Partner for Nov 15)** | 11-15 04:15 |
| Web (Next.js + deck.gl) | Salem | Prototype on a real 3D Detroit map. Partner (AI) added on Nov 15: Fast/Accurate switch in Settings, real census-built residents on the map (click one for their profile and answer), results by distance, run progress. Next.js not started | 11-15 04:15 |
| Deploy (Vercel) | Salem | **Live: https://citysim-detroit.vercel.app** (auto-deploys from `main`) | 11-14 17:58 |

## Open questions / handoffs

- **For Partner (reminder, set Nov 15):** bring up **weighting residents by distance** with teammates before it is built. Three options and a recommendation are in BACKEND_PLAN.md section 16. Any assistant starting a session: remind Partner of this until it is decided.
- **For both:** a resident's answer depends on who shares their batch of 25 (BACKEND_PLAN.md 15.1). That is Fast mode. Accurate mode (one resident per call) removes it; pick it in Settings. Fast overstates support close to a site.
- **For Partner and Salem (side branches, not on main):** `correction-engine` (the correction engine, deployed to `citysim-partner` only; its config.js points there) and `demo-mode` (Settings > Presentation > Demo mode, or `?demo=1`). Both are up to date with main as of 04:10 on Nov 15 and waiting for Partner's review.
- **For Salem:** correction engine plan and as-built notes are BACKEND_PLAN.md section 15 (15.13 on the `correction-engine` branch). On that branch its button is "Find a better version" in the results footer.
- **For Partner:** read AWS_ACCESS.md. Salem adds your IAM user; you deploy your own `citysim-partner` stack with `./infra/deploy.sh partner`. Your lane: `residents/batch.py` + `aggregate.py` and `data/`/personas. The pipeline already calls them (see `infra/runs.py`).
- **For Salem:** enable Bedrock model access (Nova Pro + Nova Lite) in us-east-1 and check the Free plan allows it; then `./infra/deploy.sh salem` (CloudShell works).
- **For Partner:** after DATA_SETUP.md, rerun `python -m data.buildings.export_tiles --districts data/raw/detroit/council_districts_2026.geojson` so buildings carry their district.
- **For Partner:** contracts changed to v2 (see 19:05 entry). If your AI already wrote code against the old `top_concern` / 1–5 `support` / `assumptions` fields, update it.
- **For Partner:** run DATA_SETUP.md, then BUILDINGS.md. Post bucket name, object count and building totals here when done.
- **For Partner:** confirm which AWS region you're using (docs assume `us-east-1`; Overture/Athena work runs in `us-west-2`).
- **For Salem:** pick the final frontend direction before Next.js work starts (current pick: combined design in `web/prototype`).

---

## Entries

### 2026-11-15 · Salem (AI) · main: panel side tabs centred and wider
- Hide/show tabs for both panels are now 36×72 px with bigger arrows, vertically centred on the panel edge (and on the screen edge when a panel is hidden).
- Files: web/prototype/index.html only.

### 2026-11-15 · Salem (AI) · main: curved drone path, white dropdown text, distance selector on Public approval
- Drone animation: flight path bows to one side (quadratic curve, 22% of the distance), drone faces along the curve.
- Block dropdown lists: option text was forced black; now white on dark (dark theme) / dark on white (light theme).
- Public approval: the "Live · N residents · Fast" badge is replaced by a distance selector (All residents / Within ¼ mile / ¼ to 1 mile / Over 1 mile). It switches the top support/neutral/oppose numbers to that distance band from the run's `groups` (needs per-group neutral/oppose from the updated aggregate; bands the run doesn't report are disabled, and the selector hides when none are available). Shows how many residents are in the band.
- Files: web/prototype/index.html only. Done directly on main at Salem's request.

### 2026-11-15 · Salem (AI) · branch salem/frontend-try: side tabs to hide both panels
- Hide controls are now tabs attached to the panels' outer edges: ‹ on the right edge of Check the details, › on the left edge of Public approval. When hidden, a tab on the screen edge brings each back. Results panel reopens when new results arrive; the map key slides right when it is hidden.
- Files: web/prototype/index.html only.

### 2026-11-15 · Salem (AI) · branch salem/frontend-try: hideable details panel, cleaner bus animation, no loading text on the button
- Check the details panel: ‹ button (top right) slides it away; a › tab on the left edge brings it back. Opens again on a new question.
- Bus animation redone as a transit-map style: dark-cased blue route line drawing along the streets, round stops (white with blue ring) at both ends and every ~400 m appearing as the line reaches them, a yellow bus marker riding the route once. No 3D poles/signs/ripple.
- Ask residents button no longer shows "Asking 2,000 residents…" / counts; the progress card covers that.
- Files: web/prototype/index.html only.

### 2026-11-15 · Salem (AI) · branch salem/frontend-try: run progress in the proposal panel, animation after results, themed dropdowns
- While residents are asked, the proposal panel fades out and the progress card (dot grid, count, bar, districts) takes its place on the left; no dimming, the map stays fully usable.
- The build animation now plays after the results arrive (live and sample runs), not before the run.
- Native dropdown lists (Rank by, block selects) follow the theme: color-scheme dark/light + option colours.
- Files: web/prototype/index.html only.

### 2026-11-15 · Salem (AI) · main: redeploy after Vercel Pro upgrade
- Vercel was rate-limiting deploys (free plan). Salem upgraded the project to Pro; this commit triggers a fresh production deploy of main (all frontend work through the person-card cleanup).
- Files: LOG.md only.

### 2026-11-15 · Salem (AI) · branch salem/frontend-try: person card title + stats
- Title is now sex and age ("Female, 19"). Stat strip: Income · Cars · Home (Owns/Rents). Commute (how they get to work) moved into "More about them" next to commute time; Sex no longer repeated there.
- Files: web/prototype/index.html only.

### 2026-11-15 · Salem (AI) · branch salem/frontend-try: cleaner persona card, styled scrollbars
- Person card: distance moves into the subtitle ("District 6 · North Corktown · 0.5 mi away"); one strip of three stats (Income $199k · Cars · Commute); "More about them" opens a 2-column grid with short labels and shortened values (Detached house, 20–29 yrs ago, 5 people, Bachelor's). No repeated fields.
- Scrollbars: thin, rounded, slate-tinted on a transparent track in every panel (both themes).
- Files: web/prototype/index.html only.

### 2026-11-15 · Salem (AI) · branch salem/frontend-try: people stand out on the light map
- Light theme: residents use deeper colours (not asked = dark slate, support = sky-600, oppose = orange-600, neutral = slate-500) with a white outline and slightly bigger dots; walkers use the same colours. Dark theme unchanged.
- Files: web/prototype/index.html only.

### 2026-11-15 · Salem (AI) · branch salem/frontend-try: earthy light map
- Light theme now swaps the basemap to CARTO Voyager (no labels) and recolours it: blue water, green parks/grass/woods, warm beige land; buildings use a warm tan height ramp; road overlay and outside-district tint use light warm colours. Dark theme unchanged. Our sources/layers (buildings, outside tint, roads) are carried across the style swap (setStyle transformStyle) and repainted.
- Files: web/prototype/index.html only.

### 2026-11-15 · Salem (AI) · branch salem/frontend-try: rezoning by two corners
- Rezoning blocks show "First corner" (the spec's Where) and a frontend-only "Opposite corner" pin field (not sent to the backend). With both: the local street-grid angle is measured from nearby road segments, the other two corners are placed on that grid, and each edge is traced along the streets (shortest road path; a straight edge if the path detours >1.6×). The edge draws, then the area fills with the zone colour and the label sits in the middle. One corner only → the 180 m circle as before.
- Files: web/prototype/index.html only.

### 2026-11-15 · Salem (AI) · branch salem/frontend-try: road change, event surge, rezoning animations
- modify_road: traces the named street itself (picked Where → that road ±320 m; preset street → named street between its ends, falls back to a street path between the ends). Orange = remove lanes, red = close (red end caps), green = bike lane only; a bike lane added alongside draws a light-green line inside.
- add_event_surge: yellow venue disc rises with pulsing rings, then crowds of dots flow in along street paths from 8 directions (~750 m out; one Dijkstra from the venue).
- rezone: a 180 m circle fills with the new zone's colour (R3 green, R5 yellow, B4 purple, SD2 teal) with a dashed edge and a "Rezoned: …" label (no parcel shapes yet).
- Road graph refactor: roadGraph / dijkstra / roadPath / roadPathsTo / streetNear.
- **Note:** Vercel is rate-limiting deploys on this project ("retry in 24 hours"); new pushes (preview and main) will not deploy until it clears. Tested by loading the committed index.html into the existing preview tab.
- Files: web/prototype/index.html only.

### 2026-11-15 · Salem (AI) · branch salem/frontend-try: new building lands on open land
- Building animation searches outward from the picked point (10 m rings, up to 260 m) for a spot where the footprint overlaps no existing building (+3 m) and stays clear of road centrelines, then builds there; camera follows if it moved. Keeps the picked point if tiles aren't loaded or nothing is free. Existing buildings can't be hidden individually (tiles carry no ids), so no demolition.
- Files: web/prototype/index.html only.

### 2026-11-15 · Salem (AI) · branch salem/frontend-try: building + drone build animations
- add_building: camera flies to the site (picked Where, else the preset site), ripple, footprint tint, then a blue block rises to floors × 3.4 m with floor lines appearing as it climbs; footprint sized from homes per floor (illustration only).
- add_drone_route: raised flight line draws from From (or the preset hub) to To/Where at the chosen flying height (climb, cruise, descend) with a ground trace, landing pads at both ends, then a drone flies it once with a pulsing noise ring under it.
- Preset sites/hubs from contracts/actions.json mapped to approximate points (PRESET_LL) for framing only.
- Files: web/prototype/index.html only.

### 2026-11-15 · Salem (AI) · branch salem/frontend-try: map pick snaps to a named road; bus route really follows streets
- Map pick always lands on a named road: snaps to the nearest point on the closest named road (wider search if needed; asks to click closer if none). Two roads at that point → "A & B" at their meeting point. The field shows only the road name; the snapped point is kept on the input (data-ll) and appended as "(lat, lon)" only in the spec sent to the backend, so the resolver gets an exact point and residents never see coordinates.
- Road path fix: tile seams left the road graph disconnected, so every path fell back to a straight line. Loose ends now stitch to the nearest node within 25 m; tested Midtown path = 50 points along the streets.
- Files: web/prototype/index.html only.

### 2026-11-15 · Salem (AI) · branch salem/frontend-try: bus animation follows the streets
- The route line and the bus now follow the shortest drivable path over the basemap's own road lines (Dijkstra in the browser, nodes snapped to 4 m so tile seams join; freeways and service roads weighted down). Falls back to a straight line if no path is found. No outside routing service.
- Files: web/prototype/index.html only.

### 2026-11-15 · Salem (AI) · branch salem/frontend-try: bus build animation
- Pressing Ask residents on a change_transit proposal with known places plays a short animation before the run overlay: camera frames From→To, the route line draws itself, a stop (pole + blue sign) rises with a ripple at each end, a yellow bus drives the route and parks at the last stop. Only From or only Where → one stop rises. Illustration only; feeds no numbers. Cleared on the next question.
- Run overlay waits for the animation (runOver.show delay).
- Files: web/prototype/index.html only.

### 2026-11-15 · Salem (AI) · branch salem/frontend-try: nicer run overlay
- While residents are being asked: the app dims behind a centred card with a 200-dot grid (coloured by district) that lights up as answers come in, the answered count, a progress bar and per-district chips. Pulses until the first answers arrive. Sample (offline) runs animate the same way.
- Files: web/prototype/index.html only.

### 2026-11-15 · Salem (AI) · branch salem/frontend-try: rank-by menu, stance-coloured person badge, compact person card, run overlay
- Compare > By group: "Rank by" menu (default order, average, or any district, high to low).
- Person card: district badge turns blue (supports) / orange (opposes) / grey (neutral); four key facts as tiles (distance, income, cars, commute), the rest under "Show more"; one short footer line.
- Run overlay on the map while a run is going: answered count of total, progress bar (live from GET /runs answered/total), residents per district, mode hint.
- Files: web/prototype/index.html only.

### 2026-11-15 04:11 ET · Partner (AI) · Residents (run-to-run variation measured) + Docs
**Did:** Measured how much results move between two identical runs, in each mode (BACKEND_PLAN 15.1, P2). Proposal "Build a 120-unit apartment building at Michigan Ave and Trumbull", Districts 5 and 6, on `citysim-partner`. Fast: totals differ by 0.4 / 0.4 / 0.8 points (support / neutral / oppose); 22 of 983 residents changed answer. Accurate: 0.2 / 0.5 / 0.3 points; 8 of 943 changed. Updated the Status board and handoffs.
**Files:** BACKEND_PLAN.md (15.1), LOG.md
**Contracts changed:** none
**Decisions:** A difference of a few points between two versions of a proposal is more than run-to-run chance in either mode. It is not proof in Fast mode, where totals also shift with who shares a call when the proposal changes.
**Blocked / needs:** Accurate dropped 52 and 55 of 1,000 residents (no valid answer after one retry) against 9 and 13 in Fast; cause not looked into. The two modes disagree on the same proposal (14% oppose in Fast, 9% in Accurate). The accuracy check (13.1 pts) was measured on the old batches and has not been rerun one resident at a time.
**Next:** Partner reviews `correction-engine` and `demo-mode`.

### 2026-11-15 04:08 ET · Partner (AI) · Web (demo check fixes; touches Salem's lane, approved by Partner)
**Did:** Page-level check on Vercel after the six-type backend check. (1) District detail and Compare showed placeholder "Sample data" numbers before a run. They now show each district's real profile (renters, no car, median household income, age mix) computed in the page from the census-built residents, weighted by each resident's census weight; the "Sample data" badge no longer appears when those residents are loaded. `residents.geojson` now carries `weight`. (2) The map-pick view opened on the middle of the selected districts (for Districts 5 and 6, the river); it now opens on the proposal's verified place. (3) The "Verified: ..." note under a place box is hidden once the box is changed, since the new value has not been verified yet.
**Files:** web/prototype/index.html, web/prototype/geo/residents.geojson, web/prototype/tools/make_residents.py, LOG.md
**Contracts changed:** none
**Decisions:** Checked on Vercel with real clicks: a click on a figure opens that resident's card; Check details retry; map pick fills the place box with coordinates; district detail; Compare; light and dark mode; shared link with `?d=` and `?q=`; Fast and Accurate runs with progress. No console errors from the current build.
**Blocked / needs:** In my browser pane the map pick returned coordinates with "no road name here" at Woodward and Mack; I could not tell whether that is the pane (it was hidden, which pauses map drawing) or the road-name lookup. Worth one manual try.
**Next:** run-to-run variation write-up; morning report.

### 2026-11-15 04:03 ET · Partner (AI) · Shared + Agent (demo check fixes)
**Did:** Ran one proposal of each of the six types through `citysim-main`. Two fixes. (1) `shared/places.py`: a stretch of one street is now understood, "Michigan Ave between Trumbull and 14th St" or "Gratiot from Russell to Chene". Both crossings must exist; the verified point is the midpoint between them (method "midpoint of two crossings"). Before, the road example was refused with "no street named Michigan Ave between Trumbull". (2) `agent/handler.py`: a yes/no setting the model returns as the text "true" is accepted (it was dropped with "'true' isn't an option").
**Files:** shared/places.py, shared/tests/test_places.py, agent/handler.py, agent/tests/test_handler.py, LOG.md
**Contracts changed:** none (`resolved.method` can now be "midpoint of two crossings")
**Decisions:** Deployed to `citysim-main`. Results of the six-type check (District 6, Fast): building, rezoning, event venue and road change ran (15 to 74 s, $0.08 to $0.11 each). The page's own example "expand the Newlab drone route to 200 flights a day" stops and asks for the route's start and end, as designed: a route needs both. A bus route to the Renaissance Center with only District 6 selected is refused because the Renaissance Center is in District 5, as designed.
**Blocked / needs:** For Salem: the ask bar's placeholder example leads to two place questions. An example that runs straight through: "Build a 120-unit apartment building at Michigan Ave and Trumbull".
**Next:** page-level check on Vercel.

### 2026-11-15 03:42 ET · Partner (AI) · Infra + Web (failed runs no longer hang)
**Did:** GET /runs/{id} now checks the run's Step Functions execution while the run is still marked running; if it failed, timed out or was aborted, the response has `status: "failed"` and an `error` line. The page shows "Could not run: ..." and re-enables the button instead of waiting for its time limit. Settings hint for Accurate now reads "about 2 to 3 minutes per district" (measured: 108 s for one district, 631 s for four).
**Files:** infra/runs.py, infra/template.yaml, infra/tests/test_runs.py, web/prototype/index.html, LOG.md
**Contracts changed:** none (GET /runs/{id} may now return `status: "failed"` with `error`)
**Decisions:** Deployed to `citysim-main`. Checked against the run that failed at 03:11: it now returns failed.
**Blocked / needs:** nothing
**Next:** run-to-run variation; correction engine and demo mode stay on side branches (`correction-engine`, `demo-mode`).

### 2026-11-15 03:16 ET · Partner (AI) · Web + Infra + Residents + Contracts (speed switch, person card, Check details fix)
**Did:** At Partner's request (approved edits to web/, contracts/, fixtures/ and a live redeploy for tonight). Merged `salem/frontend-try` (638f333, results + compare revamp) into the backend branch and main. (1) **Fast / Accurate switch** in Settings under the theme buttons: Fast = 25 residents share a model call, Accurate = one resident per call. The page sends `mode` with POST /runs; the choice is kept in the browser. (2) **Check details retry:** the Ask residents button stayed greyed out after a place failed, because it waited for every place box (Where, From and To) to be filled; a route now needs From and To, anything else needs Where. (3) **Real residents on the map:** new `web/prototype/geo/residents.geojson` (3,500 residents, 500 per district, made by `web/prototype/tools/make_residents.py` from the census-built persona files, same ids as the backend). Clicking a figure shows that resident's census profile, and after a run their own answer, reason, sentence and distance from the proposal. (4) **Results by distance** section in the results panel (within a quarter mile, a quarter mile to a mile, farther). (5) **Run progress:** the button shows "Asked 350 of 2,000 residents" while a run is going; Accurate runs are allowed 25 minutes.
**Files:** web/prototype/index.html, web/prototype/geo/residents.geojson, web/prototype/tools/make_residents.py, infra/runs.py, infra/template.yaml, infra/tests/test_runs.py, residents/batch.py, contracts/run_answers.schema.json, contracts/run_result.schema.json, contracts/README.md, fixtures/run_answers.drone.json, LOG.md
**Contracts changed:** NEW `contracts/run_answers.schema.json` + `fixtures/run_answers.drone.json`: GET /runs/{id}/answers returns `{run_id, status, mode, answers: [{persona_id, stance, reason, quote?, distance_m?}]}`. `run_result.schema.json`: `run_stats.mode` ("fast" | "accurate") and `run_stats.model_cost_usd` added (both optional). POST /runs accepts an optional `mode`; with none, the stack default applies (`ResidentsPerCall`, deployed as 25 = fast). GET /runs/{id} now also returns `mode`, `total`, `answered`, `batches`.
**Decisions:** Both stacks redeployed (us-east-2) with `ResidentsPerCall=25 QuoteShare=0.5 MaxDayUsd=50`; Partner raised the daily limit to $50 for tonight. This deploy also puts Salem's map-pick resolver live (his handoff). Temperature 0 is used in both modes. Figures with no answer in a live run are grey, not coloured from district shares.
**Blocked / needs:** My first deploy tonight broke runs on `citysim-main` for about 5 minutes (03:11 to 03:16 ET): `plan_batches` wrote to the runs table without permission. Fixed and redeployed; a 1,000-resident run then passed (22 s, $0.16). A run that fails inside Step Functions still shows as "running" to the page until its time limit; not fixed yet. For Salem: `residents_demo.geojson` is now only the fallback; the person card has more rows and scrolls when tall.
**Next:** live test on Vercel; run-to-run variation; correction engine and demo mode on side branches.

### 2026-11-15 02:45 ET · Partner (AI) · Residents + Infra (one resident per call; test stack only)
**Did:** Partner approved switching to one resident per model call. Built it as a setting and deployed it to `citysim-partner` only. `residents/batch.py`: new `ask_all` splits each group of 25 into calls of `RESIDENTS_PER_CALL` residents (default 1), `CALLS_AT_ONCE` in parallel (default 1), temperature 0, throttling retried up to 7 times. `shared/budget.py`: the spend table handle is made once per thread (making it on every call took longer than the model call). `infra/template.yaml`: parameters `ResidentsPerCall` and `CallsAtOnce`, resident batch timeout 120 → 600 s. One run on `citysim-partner`, bus route Hilton Garden Inn → Renaissance Center, Districts 4-7, QuoteShare 0.5: 2,000 residents, 2,080 calls, **631 s, $0.55**, 0 dropped, 20.9% support / 74.7% neutral / 4.4% oppose. The same run in batches of 25 on `citysim-main` earlier: 162 calls, 46 s, $0.31, 18.3 / 80.6 / 1.2.
**Files:** residents/batch.py, residents/tests/test_batch_aggregate.py, shared/budget.py, infra/template.yaml, LOG.md
**Contracts changed:** none
**Decisions:** `citysim-main` (the live site) is NOT switched: it still asks in batches of 25. A 10-minute run was not what Partner approved (my estimate was 15 to 20 s before the cap was known), so it waits for Partner's decision. To deploy the old behaviour anywhere pass `ResidentsPerCall=25`; the default is now 1.
**Blocked / needs:** The account's cap for Nova 2 Lite is 200 requests a minute (Service Quotas, us-east-2; measured: 218 calls in the first 30 s, then 50 per 15 s with the rest refused). The cap on the `us.` route is not adjustable; the cap on the `global.` route (also 200) is adjustable by request to AWS. No sourced price for the `global.` route is in `shared/bedrock_prices.json`, so the spending limit refuses it. By distance in the one-at-a-time run: within a quarter mile 41.7% support / 39.3% oppose (10 residents); a quarter mile to a mile 48.7 / 10.8 (81); beyond a mile 19.5 / 4.0 (1,909). No car 90.0% support (368); has a car 5.3% (1,632). Salem's handoff (redeploy so the live resolver accepts map picks) is still open: `citysim-main` has not been redeployed.
**Next:** Partner to choose for the live site: one at a time (10 min for four districts), batches of 25 (fast, overstates support near a site), or one at a time with fewer residents. Then P2 (run-to-run spread).

### 2026-11-15 02:19 ET · Partner (AI) · Residents (test only, no code change)
**Did:** Ran the batching test from BACKEND_PLAN 15.1 (P1). 200 real residents of Districts 4-7 at their real homes (all 91 within 1 mile of the bus route Hilton Garden Inn → Renaissance Center, plus 109 drawn at random from the 1,909 farther away), Nova 2 Lite, base card, stance only. Each way of asking was run twice and the residents whose answer changed were counted. Same batches asked twice (control): 2 of 200 changed. Random batches of 25 with different batch-mates (how runs work today): 38 of 200 changed, support 86 → 67. Batches sorted by distance with different batch-mates: 49 of 200 changed, oppose 0 → 17. One at a time, asked twice: 24 of 200 changed but totals held (66/118/16 then 64/118/18 support/neutral/oppose). One at a time with temperature 0, asked twice: 10 of 200 changed (69/115/16 then 70/110/20).
**Files:** BACKEND_PLAN.md (15.1 result), LOG.md
**Contracts changed:** none
**Decisions:** Sorting batches by distance does not fix the problem; it was worse than random batches. Asking one at a time is the only method tested where batch-mates cannot matter. Measured cost for 200 residents: $0.022 and 8 s batched (8 calls, 4 at once) against $0.041 and 49 s one at a time (200 calls, 8 at once), so about 1.85 times the cost. Not switched on: needs Partner's go-ahead because it raises cost and run time.
**Blocked / needs:** One at a time, residents within 1 mile split by vehicles as expected: no vehicle 24 support / 0 neutral / 0 oppose; one vehicle 13 / 20 / 4; two or more 5 / 17 / 8. In random batches the same residents were 24/0/0, 31/6/0 and 23/5/2. So every run made so far overstates support near a site. Even one at a time, 5% to 12% of individual answers differ between two askings; the totals moved by at most 2.5 points on 200 residents. P2 (run-to-run spread on a full run) is still to be measured.
**Next:** If approved: switch resident batches to one resident per call with temperature 0, check throttling and time on a 2,000-resident run, then P2.
### 2026-11-15 · Salem (AI) · branch salem/frontend-try: results panel + compare revamp, traffic only along From→To, collapsible key
- Traffic colours are drawn only on main-road pieces within ~450 m of the line between the picked From and To (map pick, typed coordinates, or backend-verified places). No route → unchanged.
- Public approval: short headline ("Mostly neutral, leaning yes"), By district as big rows (support % / oppose % + bar), engine note is one bold line with Details, forecast note is a one-line expandable.
- District card: Support / Oppose toggle for By group (Oppose disabled until the backend sends per-group oppose — Ammar's redeploy).
- Compare: no descriptions or forecast text; Approval bars, By group table with Support/Oppose toggle, Who lives here table, Age mix.
- Map key can be minimised (remembered).
- Files: web/prototype/index.html only.

### 2026-11-15 · Salem (AI) · branch salem/frontend-try: grey roads back, sample drone corridor removed, pins clear on submit
- Restored the grey 'all-roads' layer and road-name lookup from it (reverts the previous entry's removal).
- Removed the blue sample drone route + noise band (and the Newlab hub marker): it showed for every drone question regardless of the user's own From/To.
- Each picked place keeps its orange pin (one per field); all pins clear when a question is submitted or residents are asked.
- Files: web/prototype/index.html only.

### 2026-11-15 · Salem (AI) · branch salem/frontend-try: no road highlight layer, no pin marker
- Removed the 'all-roads' overlay line layer (basemap roads only again; outside-district dim stays). Map pick reads road names from the basemap road layers.
- No orange marker after picking a place.
- Files: web/prototype/index.html only.

### 2026-11-15 · Salem (AI) · branch salem/frontend-try: pick places on the map (From / To / Where)
- Every place field (where/from/to) has a pin button. It turns the map top-down; click an intersection or road and the field fills with the road name(s) plus exact coordinates, e.g. `Michigan Ave & Trumbull St (42.33120, -83.06710)`. Typing coordinates works too.
- A proposal stuck on needs_info unlocks Run once every place field is filled; POST /runs re-checks it as before.
- **Touched Ammar's lane (logged):**
  - `shared/places.py`: `resolve()` accepts a trailing `(lat, lon)` (or lon, lat) inside the Detroit area → `status: ok, method: "coordinates"`, district from the polygons. `split_coords()` helper.
  - `contracts/spec.py`: `summary_line` strips coordinates so residents read only the place name ("a point on the map" if there is no name).
  - `agent/handler.py`: place questions now say "Tap the pin to pick it on the map, or give two cross streets, an address, a landmark or coordinates."
  - Test added in `shared/tests/test_places.py`; 52 tests pass. No contract schema change.
- **Handoff @Ammar:** redeploy after merge so the live resolver accepts map picks.

### 2026-11-15 · Salem (AI) · branch salem/frontend-try: compact compare profile, no takeaway, no info button
- Compare: "Who lives here" dot plots replaced with a small table (districts as columns, value + thin bar, highest bold). Takeaway line removed.
- Map attribution (i) button removed; credits now in the Settings popover.
- Files: web/prototype/index.html only. main untouched.

### 2026-11-15 01:55 ET · Salem (AI) · Web (branch `salem/frontend-try`)
**Did:** (1) Light mode changes the panels only; the map stays dark. (2) Comparison fully redesigned: a district key at top; "How they feel" as one 100% stacked bar per district (sorted by support, values inside segments); "Support by group" and "Who lives here" as dot plots, one shared 0–100 line per measure with one dot per district (district colour), a span line from lowest to highest, value strip under each line, gap on the right, shared axis; age mix as aligned stacked bars per district. (3) Removed the "Up to 4 districts" hover text. (4) Every road is drawn from the basemap's own road tiles (MapLibre line layer under the buildings), and everything outside the selected districts gets a dark tint, so their streets stand out. `within` couldn't clip them because Protomaps merges a tile's roads into a few MultiLineStrings. Small streets appear as you zoom in. Follows the Roads toggle. The 12 corridors still get traffic colours after a run.
**Files:** web/prototype/index.html, LOG.md (branch only)
**Contracts changed:** none
**Decisions:** none
**Blocked / needs:** none
**Next:** —

### 2026-11-15 01:40 ET · Salem (AI) · Web (branch `salem/frontend-try`)
**Did:** (1) Comparison "Age mix" bar shows each share inside its own segment (no misaligned numbers below), with three distinct indigo steps, kept apart from the stance colours. (2) Ask bar uses the app's panel style (it was white). (3) Settings (gear, top right) with Appearance: Dark / Light. Light theme sets the CSS variables, swaps the basemap to CARTO Positron while carrying our building layer across (`setStyle` + `transformStyle`), lightens building colours, and draws idle resident dots dark. Choice saved in localStorage and applied before first paint.
**Files:** web/prototype/index.html, LOG.md (branch only)
**Contracts changed:** none
**Decisions:** none
**Blocked / needs:** none
**Next:** —

### 2026-11-15 01:20 ET · Salem (AI) · Web (branch `salem/frontend-try`)
**Did:** Comparison table redesigned: grouped sections (How they feel / Support by group / Who lives here); each % cell has a thin bar on a shared 0–100 scale; highest value per row bold, lowest dimmed; a Gap column (highest minus lowest); support shown big with a support/neutral/oppose stacked bar and a "highest" marker; the two age rows merged into one Age mix stacked bar; numbers in text colour (bars carry colour); a one-line takeaway (most/least supportive, biggest difference between districts); sticky district headers; hover titles on cells; legend for bar colours.
**Files:** web/prototype/index.html, LOG.md (branch only)
**Contracts changed:** none
**Decisions:** none
**Blocked / needs:** none
**Next:** —

### 2026-11-15 01:05 ET · Salem (AI) · Web (branch `salem/frontend-try`)
**Did:** (1) Walkers move only while zoomed in (walk clock pauses when zoomed out). City-view dots sit where each person stopped at the roadside, and a newly snapped person's dot jumps to their road. Residents in areas never zoomed into stay at home until their street loads, because the basemap only carries small streets at street level. (2) District picker label is now just "Max 4 districts" + chips. (3) Removed Share and Briefing. (4) "Compare districts" widens the results panel into a side-by-side table of all selected districts: support (highest outlined), oppose, neutral, top reason, support by group, and who lives here when available. The ask bar hides while comparing; "Close comparison" returns.
**Files:** web/prototype/index.html, LOG.md (branch only)
**Contracts changed:** none
**Decisions:** For every dot to be roadside from the start, roadside positions should be precomputed offline (Overture street segments + building footprints) into the residents file; see Next.
**Blocked / needs:** none
**Next:** precompute roadside spots + walk stretches for all residents (needs a one-time street export from Athena).

### 2026-11-15 00:50 ET · Salem (AI) · Web (branch `salem/frontend-try`)
**Did:** Resident dots show at the city view again before a run (white), as Salem asked. Radius 3.2 px.
**Files:** web/prototype/index.html, LOG.md (branch only)
**Contracts changed:** none
**Decisions:** none
**Blocked / needs:** none
**Next:** —

### 2026-11-15 00:40 ET · Salem (AI) · Web + Residents (branch `salem/frontend-try`)
**Did:** Design pass from the critique. (1) Map layers load on `style.load` instead of the basemap's full `load`, which took 15–30 s with Protomaps; main has the same bug. (2) Loading screen with the new logo and load steps. (3) New logo (gradient tile, three skyline bars, orange "voice" dot) + favicon. (4) "Civic Night" palette: one action colour (blue), sky = support, orange = oppose, slate = neutral; Briefing is now outlined; page background is dark (it was green on small screens). (5) Calmer city view: roads neutral grey until results, resident dots only after a run (smaller), traffic legend only with results. (6) Map refits the selected districts when a side panel opens. (7) Results panel fades at the bottom so it reads as scrollable. (8) District tiles are buttons and open a district view: split, top reason, support by group (age bands, renters vs owners, car vs none, distance), and "Who lives here" (renters, no car, median income, age). (9) Share copies a link (`?d=4,5&q=...`) that restores districts and question. (10) Unselected district labels dimmer, district pills more readable, credits collapse to an ⓘ button.
**Files:** web/prototype/index.html, residents/aggregate.py, residents/tests/test_batch_aggregate.py, contracts/run_result.schema.json, fixtures/run_result.drone.json, LOG.md (branch only)
**Contracts changed:** `run_result.schema.json`, additive only: `groups[]` items gain optional `neutral`, `oppose`; `districts[]` items gain optional `groups` (same shape, that district only) and `profile` {residents, age{band: %}, renters, no_car, median_income}. Fixture updated.
**Decisions:** **Touched Partner's lane** (residents/aggregate.py): adds per-district `groups` and `profile`; existing keys unchanged; all 51 tests pass. Offline mode shows plausible sample numbers in the district view, labelled "Sample data". Live mode shows only what the run returns.
**Blocked / needs:** For Partner, when merged: redeploy so runs return per-district groups/profile. `median_income` appears only if `hh_income` is kept on rows (batch.py KEEP).
**Next:** —

### 2026-11-15 00:15 ET · Salem (AI) · Web (branch `salem/frontend-try`)
**Did:** Street snapping read only CARTO/OpenMapTiles road names, but the basemap is now Protomaps (`roads` layer, `kind`), so no streets were found and every walker was hidden. Now reads both schemas. Walkers with no clear stretch stand at the roadside instead of hiding; street search radius 300 m.
**Files:** web/prototype/index.html, LOG.md (branch only)
**Contracts changed:** none
**Decisions:** none
**Blocked / needs:** none
**Next:** —

### 2026-11-15 00:05 ET · Salem (AI) · Web (branch `salem/frontend-try`)
**Did:** Walkers no longer walk into buildings. Each street-snapped path is checked against the building footprints in view (our tiles, 2.5 m clearance), trying sidewalk offsets 6 / 3.5 / 0 / -3.5 / -6 m, and keeps the longest clear stretch. No clear stretch → the figure stands still on the street; no street within 150 m → hidden at street level. Figures capped smaller (2.5–7× life size) and appear from zoom 15. Test: 90 walkers, 0 paths touching a building.
**Files:** web/prototype/index.html, LOG.md (branch only)
**Contracts changed:** none
**Decisions:** none
**Blocked / needs:** none
**Next:** —

### 2026-11-14 23:55 ET · Salem (AI) · Web (branch `salem/frontend-try`)
**Did:** Walkers stay on streets: at street level each figure snaps to the nearest real street in the basemap tiles (OpenMapTiles `transportation`, motorways/rail excluded) and paces the sidewalk on its home's side (6 m off the centerline). Click a figure → person card (district, stance, demographics) and the camera zooms in and follows them; drag the map, ×, or Esc stops it. Selected figure turns yellow.
**Files:** web/prototype/index.html, LOG.md (branch only)
**Contracts changed:** none
**Decisions:** The card shows real demographics only when they exist. The map now loads `geo/residents.geojson` if present (else the demo file), so real residents drop in with no code change.
**Blocked / needs:** **For Partner:** export `web/prototype/geo/residents.geojson`, one Point per persona at a home in its census block, with properties `persona_id, district, age, sex, hh_income, tenure, years_in_home, hh_size, vehicles, commute_mode`. Per-run `stance` / `reason` per persona_id from the run result would let each figure show its own answer.
**Next:** —

### 2026-11-14 23:40 ET · Salem (AI) · Web (branch `salem/frontend-try`)
**Did:** Residents walk. At zoom 14+ each resident is a small 3D figure (body + two swinging legs, deck.gl SimpleMeshLayer, mesh built in code) pacing a short stretch near their home, colored by stance after a run (white before). Zoomed out they stay dots. Figures scale with zoom (~8 px tall). Animation stops when zoomed out or the tab is hidden. Merged latest main into the branch first.
**Files:** web/prototype/index.html, LOG.md (branch only, not on main)
**Contracts changed:** none
**Decisions:** One figure = one resident. Stance per figure is still drawn from the district split; runs don't return per-resident answers with locations yet.
**Blocked / needs:** for real per-person cards: run result needs `residents: [{persona_id, block_geoid, stance, reason, age, tenure, vehicles}]` (Partner's lane, later).
**Next:** —

### 2026-11-14 23:15 ET · Salem (AI) · Web (branch `salem/frontend-try`)
**Did:** Created branch `salem/frontend-try` from main (8ea8879) for Salem's frontend experiments. Vercel builds a preview for it; production stays on `main`.
**Files:** LOG.md (this branch only)
**Contracts changed:** none
**Decisions:** Nothing on this branch reaches `main` until Salem merges it.
**Blocked / needs:** none
**Next:** frontend edits on this branch.

### 2026-11-15 00:46 ET · Partner (AI) · Docs (plan only) + Residents (finding)
**Did:** (1) Wrote the correction engine plan: BACKEND_PLAN.md section 15. (2) Wrote up and parked Partner's idea of weighting residents by distance: section 16. (3) Ran a temporary test, nothing stored: 100 real residents from Districts 5 and 6, split evenly by vehicles, each placed on a real block within a quarter mile of the bus route Hilton Garden Inn → Renaissance Center. Result: no vehicle 16 support / 3 neutral / 15 oppose; one vehicle 3 / 12 / 18; two or more 1 / 9 / 23. In the live run the 10 residents that near (7 with vehicles) all supported it.
**Files:** BACKEND_PLAN.md (sections 15 and 16), LOG.md
**Contracts changed:** none
**Decisions:** Correction engine as planned: diagnose from stored answers plus the parked seven questions asked of opponents; change one lever at a time (location, size, hours); candidate sites come from parcels, Land Bank lots and zoning, never from a model; candidates are ranked by a lookup table built from the residents' own answers; reruns use the same residents and wording; at most 5 reruns, enforced on the server; a gain must exceed the measured run-to-run spread; every attempt is reported, with who lives near each site.
**Blocked / needs:** **A resident's answer depends on who shares their batch of 25** (the test above). This affects every run and must be fixed before the correction engine is built (15.1, P1). Fix not yet tested: batch residents of similar distance together, or ask one at a time.
**Next:** P1 and P2 from section 15.1, then the diagnosis step.

### 2026-11-15 00:12 ET · Partner (AI) · Residents (setting)
**Did:** At Partner's request, redeployed `citysim-main` with `QuoteShare=0.5` (half of residents write a sentence; it was 0.1) and reran the bus route Hilton Garden Inn → Renaissance Center across Districts 4-7: 2,000 residents, 995 sentences, 162 calls, 46 s, $0.31, 0 dropped. 18.3% support / 80.6% neutral / 1.2% oppose.
**Files:** none (deploy parameter), LOG.md
**Contracts changed:** none
**Decisions:** `citysim-partner` is still at 0.1. Deploy `citysim-main` with `QuoteShare=0.5` from now on, or the next deploy resets it to the default.
**Blocked / needs:** Why 80% neutral: the route is 0.4 miles long downtown and the median resident in those four districts lives 5.3 miles from it; only 91 of 2,000 live within a mile. Support by distance: within 1/4 mile 100% (10 residents), 1/4 to 1 mile 84% (81), 1 to 3 miles 35% (339), 3 to 6 miles 13% (749), over 6 miles 8% (821). Neutral sentences are mostly "no strong opinion either way". The site shows only the city-wide total, not this by-distance view.
**Next:** correction engine; show results by distance on the site.

### 2026-11-14 23:46 ET · Partner (AI) · Web (live test)
**Did:** Tested the live Vercel site (citysim-detroit.vercel.app) against `citysim-main` with real clicks and typing. (1) "Build a 400 unit apartment building at Michigan Ave and 14th St": place verified, 1,999 of 2,000 residents answered in about 40 s, 9% support / 83% neutral / 8% oppose, traffic sentence showed Michigan Ave 8,347 → 9,972 vehicles a day, accuracy sentence showed 13.1 points. (2) "I want a bus route from the Hilton hotel to the Renaissance Center" typed while the first proposal was open: replaced it, asked which Hilton with three buttons, run button disabled; clicking "Hilton Garden Inn" verified both ends. (3) Running it: 2,000 residents, 19% / 77% / 4%, 1,966 adults within a quarter mile of the line. No console errors. Then fixed three wording problems the test showed.
**Files:** web/prototype/index.html, LOG.md
**Contracts changed:** none
**Decisions:** A mostly-neutral result now reads "Most residents are neutral…" (it said "Leaning yes" at 9% support and 83% neutral). District tiles say "Top reason" for live results, since the top reason can be why people support (access, for a bus route). The bus headline shows the line's length and no longer repeats the adults sentence.
**Blocked / needs:** With four districts selected most residents live miles from the site and answer neutral, so city-wide totals look flat; the by-distance view is where the signal is, and the site does not show it yet.
**Next:** correction engine; map marker.

### 2026-11-14 23:29 ET · Partner (AI) · Engine + Infra + Web
**Did:** Traffic engine for buildings and a first bus-route result, deployed to `citysim-partner` and `citysim-main`. `engine/handler.py` (pure Python, reads `s3://citysim-data-707604458164/processed/engine/engine_data.json` built by `data/engine_data.py`: 14,243 blocks, 272 tracts, 1,427 counted segments, 5,101 stops).
- **add_building**, when the homes (or a grocery's floor area) were stated: trips from `data/ite_rates.csv`; Detroit adjustment by the site tract's no-vehicle household share (ACS B25044); all adjusted trips placed on the busiest counted street at the verified site; load before and after. Any other use returns no trips and says why.
- **change_transit** with a verified start and end: adults within a quarter mile of the straight line (2020 block counts) and existing DDOT stops and routes in that band. No ridership or traffic forecast.
- Residents within half a mile of the affected street get the added-trips line; the run result carries `segments`, `trips`, `transit`, `engine_notes`; the prototype's traffic note shows them.
**Verified live:** 400 homes at Michigan Ave & 14th St → 1,816 trips a day, 156 in the evening peak (the plan's 8.3 check values), 1,625 after the 11% no-vehicle adjustment; Michigan Ave (I-75 to Rosa Parks) 8,347 → 9,972 vehicles a day, load 0.26 → 0.31 (8,347 and 0.26 are the plan's check values). Bus route Michigan & Trumbull to Woodward & Warren → 6,959 adults within a quarter mile, 72 existing stops; support 64% within a quarter mile and 80% from a quarter mile to a mile, against 17% beyond a mile. Strip club → "no published trip rate", nothing computed. On a local copy of the site against `citysim-main`: the apartment run showed the traffic sentence, the accuracy sentence and "Live · 488 residents" (12 of 500 gave no valid answer).
**Files:** engine/handler.py (rewritten), engine/proximity.py (`street_lines`), engine/tests/test_engine.py (new), data/engine_data.py (new), infra/{runs.py,deploy.sh}, residents/batch.py, web/prototype/index.html (traffic note), LOG.md
**Contracts changed:** none. Run result gains `transit` and `engine_notes` beside the existing `segments` and `trips`; `engine_status` is `computed` or `nothing_computed`.
**Decisions (labelled assumptions, all repeated in `engine_notes`):** every added trip goes on one street, so that street's figure is an upper bound; through lanes per direction = half the counted lanes rounded down; K 0.09, D 0.55 and 800 vehicles per lane per hour are planning defaults, not measurements. `engine/actions/*.py` stubs are no longer called.
**Blocked / needs:** Not built: spreading trips over the network with LODES flows, road changes, rezoning, event venues, drone routes, bus frequency changes, any ridership forecast. Route lists in `transit` repeat some combined entries as the city's stop layer writes them (for example "1, 29 Vernor, Linwood"). The rate table has only housing and supermarkets.
**Next:** Salem: Compare and Briefing buttons, a map marker for verified places. Backend: relative (not raw) neighborhood facts, more trip rates, network assignment.

### 2026-11-14 23:23 ET · Partner (AI) · Data (personas) + Residents
**Did:** Neighborhood facts (Tier 2) built for every resident and tested. `data/personas/context.py` computes, for each of the 2,656 home blocks, facts within a quarter mile or to the nearest feature: neighborhood name; crimes reported in 2026 and the most common kinds (74,094 incidents); vacant Land Bank lots (53,860); active liquor licenses (1,712); nearest park, school and bus stop with route; vehicles a day on the nearest counted street; most common 311 requests in the past 12 months (84,494); share of adults in fair or poor health in the tract (CDC PLACES 2023). Stored on every persona row as `context` lines plus numbers; uploaded to `s3://citysim-data-707604458164/personas/`. Five new downloads added to `data/download/detroit.py`.
**Tested with the accuracy check (Nova 2 Lite, 1,400 residents):**

| Card | Safe walking (real 85) | Satisfied (67) | Right direction (55) | Used transit (32) | Avg error |
| --- | --- | --- | --- | --- | --- |
| base (rerun) | 65.2 | 70.4 | 46.1 | 11.7 | **13.1** |
| tier2 (base + neighborhood facts) | 18.1 | 31.9 | 13.5 | 21.7 | 38.5 |

Direct test from the plan: with Tier 2, residents on the lowest-crime third of blocks agree they feel safe 38.3% of the time, on the highest-crime third 2.6%; with the base card 66.8% vs 64.2%. So the model does use the facts, but it over-reacts to them.
**Files:** data/personas/context.py (new), data/download/detroit.py, residents/{prompt,calibrate}.py, residents/calibration_results.json, infra/template.yaml, LOG.md
**Contracts changed:** none. Persona rows gain `context`, `neighborhood`, `crimes_quarter_mile_2026`, `landbank_lots_quarter_mile`, `liquor_licenses_quarter_mile`, `park_m`, `school_m`, `bus_stop_m`, `requests_311_quarter_mile_year`.
**Decisions:** Tier 2 stays **off** in the deployed stacks (`PersonaCard=base`). Raw counts such as "121 crimes within a quarter mile" read as alarming to the model and push every answer negative, tripling the error. `PersonaCard` now accepts `base | tier1 | tier2 | all`, so it can be switched on per deploy.
**Blocked / needs:** Not tried: stating each fact relative to the city ("fewer crimes than most Detroit blocks") instead of as a raw count, which may keep the block-to-block signal without the alarm. Left out for time: 911 calls and response times (319,185 rows), blight tickets (913,837 rows), bus frequency from the schedule feed. The stop ridership period is not stated by the city. `cdc_places_wayne_tracts.json` was fetched directly and is not in the download manifest.
**Next:** traffic numbers for buildings, then bus.

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
