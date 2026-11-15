# CitySim Detroit — Backend Master Plan

Written Nov 14, 2026. Covers `data/`, `engine/`, `residents/`, `agent/`, `infra/` and the API. It changes no existing file: every correction to a script, schema, fixture or doc is listed here as a proposed change for its owner to apply. [SCOPE.md](SCOPE.md) says what and why, [BUILD.md](BUILD.md) gives the order; where this plan disagrees with them, it says so and gives the evidence.

## 1. The rule this plan enforces

Every number the site shows must be one of four things, and the API must say which:

| Kind | Example | How it is labelled in the result |
| --- | --- | --- |
| **Data** | AADT, lanes, census counts, bus headways | dataset name + vintage |
| **Published rate** | ITE trips per unit, FHWA vehicle occupancy | citation + URL |
| **User input** | flights per day, units, seats | echoed from the spec |
| **Assumption** | K, D, lane capacity, noise-band width | listed in `assumptions[]`, editable |

If none of the four is available, the backend returns "not available" for that field. It never substitutes a default silently. Section 4 lists the places where the current scope would have required invented numbers, and what replaces them.

## 2. What was verified today

Checked live from this session on Nov 14, 2026: endpoints were queried, field lists and row counts read, published PDFs opened. "Not checked" means the host refused this session, not that the source is bad.

### 2.1 Data sources

| Source | Status | What was found |
| --- | --- | --- |
| Council districts 2026 | Confirmed | 7 polygons, `district_number`, names are only "District 1"…"District 7". GeoJSON download works. |
| Traffic volumes | Confirmed, better than scoped | One layer per year, **2017–2024**. 2024 has 1,427 rows (1,038 roads + 389 ramps) with `num_aadt`, `num_lanes`, `posted_speed`, `nfc_name`, and `route_id` + begin/end milepoint. `num_lanes` filled on 98.5%. |
| City road layer (`City_of_Detroit_Roads`) | Confirmed, not in the scope | 38,117 segments with node ids (`BPT`, `EPT`), `PR` + milepoints, `LANES`, `NFC`. 99.9% of segments form one connected network. **98.2% of 2024 counted road segments join to it exactly** by `PR` + milepoint overlap. |
| Parcels | Confirmed, but the catalog points at a stale copy | The catalog's `Parcels_Current` was last edited Feb 2025. `parcel_file_current` was edited today: 377,940 parcels with `zoning_district`, `property_class_description` (vacant classes), `total_square_footage`, `census_tract_geoid_2020`, `cross_street_1/2`, `neighborhood`. |
| Zoning | Confirmed | 28,290 polygons, `ZONING_REV` code + description. No density or unit limits in the data. |
| Neighborhoods | Confirmed | 205 named polygons. Its `council_district` column is the old map. |
| DDOT routes (`DDOT_Bus_Routes_202509`) | Confirmed | 37 routes with peak, base and night headways in minutes, run pick June 2026. |
| DDOT stop ridership (`BusStopAmenitiesForArcGIS`) | Found, provenance unstated | 5,101 stops with `Boardings`, `Alightings`, `Ridership_at_Stop`; boardings sum to 57,517. The layer has no description, so the period (weekday? which month?) is unknown. |
| DDOT GTFS | Not checked | detroitmi.gov and the MobilityData API refused this session. Test from a laptop. |
| Building footprints (city, SEMCOG-derived) | Confirmed | 380,076 footprints; `STORIES` and `MEDIAN_HGT` filled on 98.8%; last edited 2020. |
| Overture buildings | Confirmed | Latest release `2026-10-21.0`, schema v2.0.0 (a breaking change in Sept 2026). `height` and `num_floors` still present. |
| Crashes | Confirmed | One layer per year 2011–2024. |
| 311 (Improve Detroit) | Confirmed | 765,518 points with request type and neighborhood. |
| Census API | Confirmed, **key now mandatory** | Requests without a key return a "Missing Key" page. With a key: all 9 ACS 2024 tables return 627 Wayne County tracts, and P1 + P3 return 32,022 blocks. Tracts 5214 + 5215 total 2,824 residents (ACS 2024), not the scope's 2,520. |
| TIGER 2025 | Confirmed | Tract, block group, 2020 block (122 MB), place and PUMA files all present. |
| PUMS 2024 5-year | Confirmed | Michigan person (70 MB) and household (32 MB) zips present. All needed variables exist. `PUMA` uses 2020 definitions only. |
| LODES 8 Michigan | Confirmed, older than scoped | Newest **OD and WAC year is 2021**. 2022 and 2023 exist for RAC only. |
| OSM via Overpass | Not checked | Overpass and Geofabrik refused this session. |
| DMACS microdata | Partly confirmed | Wave 22 is on ICPSR for member institutions; Wave 21 has an open release on U-M Deep Blue. Toplines publish citywide percentages only, no subgroup tables. |

### 2.2 Published numbers

| Claim in the repo | Verdict | Correct value and source |
| --- | --- | --- |
| DMACS Wave 22, Aug 6 – Oct 1, 2025 | Confirmed | 2,158 completes, margin ±2.96 pts ([toplines](https://detroitsurvey.umich.edu/wp-content/uploads/2025/11/W22-Toplines-Nov-2025.pdf)) |
| 70% feel safe walking in their neighborhood | **Wrong** | W22 Q76: somewhat safe 58% + very safe 27% = **85%** |
| 67% satisfied with their neighborhood | Confirmed | W22 Q11: 24 + 27 + 16 = 67% |
| 55% say Detroit is headed in the right direction | Confirmed | W22 Q32 |
| 78% lived in Detroit 20+ years | Confirmed | W22 Q5, but see 4.4: personas cannot reproduce it |
| 32% "used public transit recently" | Wrong wave and wording | Wave 20 Q80: used public transportation in Detroit **in the past year**, 32% ([toplines](https://detroitsurvey.umich.edu/wp-content/uploads/2024/11/W20-Toplines-8-30-24-2.pdf)) |
| ITE 221: 4.54 daily, 0.39 PM | Confirmed | Palm Beach County sheet, ITE 11th edition |
| ITE 850: 93.84 daily | Confirmed | PM peak is **8.95** (blank in `ite_rates.csv`) |
| Christiansburg: 87% positive, noise 17% | Confirmed | n = 821, Nov 2020. The 17% is the share who mentioned noise as a negative ([article](https://issues.org/when-the-drone-is-in-your-backyard-nelsen-guthrie-vinsel/)) |
| IMechE: 23% support, 45% of 18–24s | Confirmed | n = 2,010, Great Britain, 2019 |
| Aerial region covers a 3-mile radius | Confirmed | Michigan Central, Oct 2023 |
| Aerialoop route | Partly confirmed | 1-mile round trip, Newlab to "The 23rd", over the rail corridor. Flights per day, altitude and payload are **not published**. |
| Michigan Ave AADT 10,309, 5 lanes | Right number, wrong year and place | 10,309 is the **2020** count for the segment **west of I-75**. That segment is 12,847 in 2024. Michigan at 14th (I-75 to Rosa Parks) is **8,347** in 2024. 5 lanes confirmed. |
| Districts average about 91,000 | Confirmed | 87,393 to 94,815 per district |
| Downtown and Midtown are District 5 | **Wrong** | Under the 2026 map, Campus Martius and most of Downtown are in District 6. District 5 holds Wayne State, New Center, Eastern Market, Lafayette Park. |
| K = 0.09, D = 0.55, 800 cars per lane-hour | **No source found** | K and D appear as FDOT planning defaults in search snippets only. Nothing found for 800. Keep all three as labelled assumptions. |

### 2.3 AWS facts

| Item | Verified fact |
| --- | --- |
| Nova 2 Lite | ID `amazon.nova-2-lite-v1:0` is right, but us-east-1 has no in-region on-demand. Call `us.amazon.nova-2-lite-v1:0`. No manual model-access step. Quotas vary by account: read them in Service Quotas. |
| JSON from Nova | Bedrock "structured outputs" is not supported for it. Use a tool schema with `toolChoice: {"tool": {...}}`, and wrap the array in an object. |
| Claude Haiku 5.5 | `us.anthropic.claude-haiku-5-5`, structured output supported. Used for residents and the chat agent (5.1). Needs the one-time AWS Marketplace subscribe permission on first use. There is no Nova 2 Pro. |
| Strands | `strands-agents` 1.65 on PyPI. Official Lambda layer exists (`…:layer:strands-agents-py3_12-x86_64:2`, an older 1.40). Structured output via `structured_output_model`. Sessions via `S3SessionManager`. |
| Step Functions | Inline Map: 40 concurrent iterations. 256 KB per state payload. |
| API Gateway HTTP API | 30-second hard timeout. A run cannot be synchronous. |
| DynamoDB | 400 KB per item. Large results go to S3 with a pointer. |
| Lambda | Zip limit 250 MB unzipped including layers. `AWSSDKPandas-Python312:32` layer gives pandas, numpy, pyarrow. No managed geopandas layer. |
| Amazon Location | Places v2, `boto3.client("geo-places").geocode(...)`, no place index needed. No bounding-box filter: bias with `BiasPosition`. Whether free-text intersections resolve is untested. |

## 3. Bugs in the current download scripts

These fail today or fetch the wrong thing. Fix before the first data run.

1. **`data/download/detroit.py` saves a web page for traffic volumes and tracts.** Those two catalog entries have no file resource, so the "first preferred format" logic falls through to the HTML link. Pull traffic volumes from the feature service (layer 7 = 2024, paged at 1,000 rows) and drop the tracts entry (TIGER already covers it).
2. **Parcels come from the stale copy.** Switch to `parcel_file_current`, paged at 2,000 rows, and drop the taxpayer name and address columns on download.
3. **`CENSUS_API_KEY` is treated as optional.** The API now refuses keyless requests. Fail fast with a clear message.
4. **Block population pulls `P1_001N` only.** Personas are adults: also pull `P3_001N` (population 18 and over).
5. **Missing downloads:** the city road layer, DDOT routes, stop ridership, neighborhoods, city building footprints, GTFS.
6. **`DETROIT_PUMAS_FALLBACK` holds 2010 PUMA codes.** PUMS 2024 uses 2020 definitions. Derive Detroit's PUMAs from the tract-to-PUMA file and the tracts inside the city; delete the fallback.
7. **`detroit_pumas()` returns all of Wayne County.** Filter to tracts that intersect the Detroit place boundary.
8. **`engine/trips.py` reads `pm_peak_rate` as optional** only because code 850 was blank. Fill it (8.95).

## 4. Where the scope would have needed invented numbers

Each item is a feature that cannot be built as written without making data up, with the honest replacement.

### 4.1 Block popover: "38 residents here, 61% support"

500 personas per district spread over roughly 2,000 populated blocks is under one persona per block. A block-level support percentage would be one simulated person. **Replace with:** the block's real census population (data), plus simulated support reported at **tract** level with its `n`, suppressed below `n = 10`.

### 4.2 Drone: "1 in 5 delivery vans replaced" and vans taken off Michigan Ave

No dataset gives delivery-van volume in Corktown, so a share of it cannot be computed, and nothing says which streets the vans use. The fixture's Michigan Ave drop from 10,309 to 10,180 has no source. **Replace with:**

- Van trips removed = flights per day × packages per flight ÷ packages per van route. All three are stated inputs. Published anchors: one package per flight (Wing, [FAA environmental assessment](https://www.faa.gov/uas/advanced_operations/nepa_and_drones/06272025_Final_EA_Wing_Central_Florida.pdf)); 250–300 packages per van route (one Amazon driver profile, anecdotal).
- Report the result as a district total. Leave street loads unchanged and say why.
- With those anchors, 200 flights replace less than one van route a day. The honest traffic finding for the drone demo is "no measurable change", and the story is sentiment.

### 4.3 Drone noise band of 500 ft

The only measured source found (the FAA assessment for Wing) puts the 60 dB day-night contour within 65 ft of a launch site and reports about 56–62 dBA for a pass at 165 ft. That does not support a 500 ft "noise" band. **Replace with:** a band labelled "under the flight path", width a stated input, used to flag who sees and hears the route. Quote the FAA figures in the Method tab.

### 4.4 "78% lived in Detroit 20+ years" computed from persona traits

PUMS records when a household moved into its current home, in bands. It has no field for years lived in the city. **Replace with:** drop this check. Use persona checks that are computable: renter share and zero-car share against ACS, per district (already the Step 4 "done when").

### 4.5 `years_in_home` as an integer

Same field: PUMS `MV` is a band ("10 to 19 years"). **Replace with:** a `years_in_home_band` string. The prompt says "in this home 10 to 19 years".

### 4.6 Closure and road-diet rerouting

Rerouting existing traffic needs to know where it is going. There is no origin-destination matrix for Detroit streets in the catalog. **Replace with:**

- Lane removal: same counted volume over fewer lanes. Fully computable.
- Closure: move the closed segment's counted volume onto the shortest alternative path between its two ends, and label it "simple detour assumption".
- Bike-lane mode shift: only if the user states a share. No default.

### 4.7 Bus cuts: riders shifting to cars

Riders affected can be computed (stop boardings × headway change × published elasticity of about 0.5, [VTPI summary of TCRP 95](https://www.vtpi.org/tranelas.pdf)). The share who switch to driving has no citable single value. **Replace with:** report riders lost; add car trips only if the user states a diversion share. Label stop ridership "DDOT stop counts, period unstated" until DDOT confirms it. "Job access recomputed from GTFS" is cut: it needs a transit router.

### 4.8 Rezoning: maximum units under a zone

The zoning layer carries codes, not limits, and the ordinance sets **no units-per-lot limit** for apartments in any zone. It limits floor area (FAR), height and lot coverage. **Replace with:**

- `data/zoning_capacity.csv`, typed Nov 14 from the ordinance text (Chapter 50, Articles VIII–XIII), one row per zone with section numbers.
- Maximum floor area = parcel area × FAR. Units = floor area ÷ average unit size, where **average unit size is a stated input**, never a default.
- This works only for zones with a numeric apartment FAR: R2 (0.50, capped at 8 units), R3 (0.70), R4 (1.00), R5 (1.50), R6 (2.00), B1 (1.00), B2 (1.50), B4 (2.00), SD4 (4.50). Every other zone returns "no numeric limit in the ordinance" (height-only, volume-based, or set per project).
- **Checked Nov 14 from a laptop:** all nine FAR values match the official code on [Municode](https://library.municode.com/mi/detroit/codes/code_of_ordinances?nodeId=COCH50_CH50ZO_ARTXIIIINDIST) (version Oct 9, 2025, Sec. 50-13-3 to 50-13-7, 50-13-42, 50-13-43, 50-13-45, 50-13-132). Only the FAR column was checked; the table's other columns and the R2 8-unit cap still come from the third-party mirror.

### 4.9 Stadium trips

ITE has no stadium rate on the open sheet. **Replace with:** vehicles = seats × attendance share × auto share ÷ vehicle occupancy. Occupancy 2.5 (range 2.2–2.8) and auto-share examples come from [FHWA, Managing Travel for Planned Special Events](https://ops.fhwa.dot.gov/publications/fhwaop04010/chapter5_03.htm). Attendance share and auto share are stated inputs.

### 4.10 Loads on "every street"

Only 1,038 road segments citywide have a 2024 count. **Replace with:** a load only where a count exists. Other streets show added trips with `counted: false` and no load or color.

### 4.11 ITE codes with no open rate

Data center (160), high-rise housing (222), public park, stadium and convenience store are not on the open sheet. The agent may only use codes present in `ite_rates.csv`; a data center prompt returns "no published rate available" until a second open sheet is found.

### 4.12 Smaller items

- **District names** ("Corktown, Southwest"): derive from the neighborhoods layer joined to the 2026 districts. The prototype's labels are partly wrong.
- **Time-of-day control:** the data has a daily count and one evening-peak rate. Offer "Daily" and "Evening peak" only.
- **Work location:** attach only to personas the census record shows as employed. LODES 2021 is the newest year.
- **Calibration by subgroup:** toplines are citywide. Subgroup calibration needs the Wave 21 open microdata; without it, report citywide error only and apply no subgroup offsets.

## 5. Architecture

```
POST /chat ──► chat Lambda (Strands, Haiku 5.5) ──► spec saved to DynamoDB
POST /run  ──► start Step Functions (Standard), return run_id at once
                 1. engine Lambda        spec → segments, trips, per-tract and per-persona impacts → S3
                 2. plan Lambda          touched districts → list of 25-persona batches (S3 keys only)
                 3. inline Map (max 20)  residents_batch Lambda → Haiku 5.5 → batch result to S3
                 4. aggregate Lambda     weights, splits, groups, quotes, range → run_result to S3
                 5. DynamoDB             status = done, pointer to the S3 result
GET /run/{id}       status + batches done / total; result when done
GET /runs           run history for the compare view
GET /calibration    latest calibration record
GET /layers/...     static layers from S3: districts, counted segments, tracts, buildings
```

Decisions, each forced by a verified limit:

- **Runs are asynchronous with polling** (30-second API limit).
- **Every state passes S3 keys, not data** (256 KB state limit). A 2,000-resident run stays far below the execution history limit.
- **`run_result` lives in S3**; DynamoDB holds status and the pointer (400 KB item limit).
- **No geopandas or osmnx in any Lambda.** All geometry work happens offline in `data/`. Lambdas load small Parquet and NumPy files, so the engine fits a zip with the pandas layer. Shortest paths use a plain Dijkstra over the 38,000-edge graph.
- **Chat is the one synchronous call.** If the agent with tool calls runs past 20 seconds in testing, move `/chat` to a Lambda function URL.
- **Map concurrency starts at 20**, raised only after reading the account's Haiku 5.5 quota.

DynamoDB tables stay as in `infra/README.md`: `scenarios`, `runs`, `calibration`.

### 5.1 AWS decisions (agreed Nov 14)

| Decision | Detail |
| --- | --- |
| **Infrastructure as code: SAM** | One `infra/template.yaml`, deployed with `sam build && sam deploy`. No console-built resources, so either teammate (or a Claude Code session) can redeploy. |
| **Services in use** | S3, DynamoDB, Lambda, Step Functions, Bedrock, API Gateway (HTTP API), Location Service, Budgets, plus CloudWatch and IAM. |
| **Budgets first** | Create a spending alert before the first Bedrock call. |
| **Resident model** | Claude Haiku 5.5, `us.anthropic.claude-haiku-5-5`, read from `BEDROCK_RESIDENT_MODEL` (decided Nov 15). Listed at $0.10 in / $0.50 out per million tokens on Anthropic's own API, below third-party listings for Nova 2 Lite ($0.30 / $2.50); confirm both on the Bedrock pricing page. Set effort to `low` or disable thinking: it thinks by default and thinking is billed as output. Nova 2 Lite (`us.amazon.nova-2-lite-v1:0`) stays as the comparison model in section 10. |
| **Agent model** | `us.anthropic.claude-haiku-5-5`, read from `BEDROCK_AGENT_MODEL`. Runs in a plain Lambda, not AgentCore (SCOPE.md says AgentCore; BUILD.md is right). |
| **Every resident batch is a Lambda** | No direct Step Functions–Bedrock integration: each batch must build the prompt, validate answers and retry. |
| **Athena: not used** | Data prep runs in Python on a laptop; Overture buildings come from the `overturemaps` CLI. |
| **Dropped** | Bedrock prompt caching (the shared prefix is under the 1,000-token minimum). Secrets Manager (only needed for a Claude API fallback outside Bedrock). |
| **Deferred** | Bedrock Guardrails, until the core loop works. Not verified. |

## 6. Data pipeline (`data/`)

Run on a laptop. Output goes to `s3://$DATA_BUCKET/processed/` and `personas/`.

### 6.1 Processed artifacts

| Artifact | Built from | Used by |
| --- | --- | --- |
| `districts.geojson` + `district_labels.json` | Council districts 2026, neighborhoods | everything; labels for the UI |
| `network_nodes.parquet`, `network_edges.parquet` | City road layer (`BPT`, `EPT`, length, name, class) | engine routing |
| `counted_segments.parquet` + `.geojson` | 2024 traffic volumes joined to edges by `PR` + milepoint | engine loads; map layer |
| `blocks.parquet` | TIGER 2020 blocks, P1 and P3, district by centroid, nearest edge, nearest arterial and distance | personas; impacts |
| `tract_controls.parquet` | ACS 2024 tables, split to districts by block population | personas; zero-car share |
| `tract_od.parquet` | LODES 2021 OD, summed block → tract, top destinations per tract | trip distribution; work tract |
| `parcels_d{n}.parquet` | `parcel_file_current`, centroid lat/lon, no owner columns | agent `find_parcels` |
| `intersections.parquet` | Road-layer nodes with the street names that meet there | agent geocoding fallback |
| `transit_routes.parquet`, `transit_stops.parquet` | DDOT routes (headways), stop ridership | `change_transit` |
| `buildings_d{n}` | City footprints (stories, height); Overture for buildings added since 2020 | map layer |
| `manifest.json` | every step | source URL, vintage, row count, download time |

### 6.2 Rules

- **District tagging uses the 2026 polygons**, never a dataset's own district column: parcels, 311 and neighborhoods all still carry the old map.
- **A tract split by a district line** is shared out by block population on each side.
- **Lanes:** use `num_lanes` from the 2024 count row, the same vintage as the count. The road layer agrees with it on only 708 of 1,000 comparable segments, so write the disagreements to `lane_audit.csv` and review the Corktown ones by hand.
- **Through lanes per direction** is derived from total lanes: two-way, subtract a center turn lane when the total is odd, then halve (5 → 2, matching Michigan Ave); one-way, all lanes. This is an assumption and is listed as one.
- **OSM is optional.** The city road layer already gives a connected, joinable network. Use OSM only if one-way directions are needed.

### 6.3 Done when

`manifest.json` lists every artifact; at least 95% of counted road segments carry an edge id (98.2% measured today); every block and parcel has a 2026 district.

## 7. Personas (`data/personas/`)

1. **Seed:** PUMS 2024 5-year, Michigan, households in Detroit's 2020 PUMAs, housing units only (group quarters excluded; say so in the Method tab). Adults 18+.
2. **Controls per district:** ACS 2024 tract tables summed with the block-population split. Household tables: income (B19001), tenure × vehicles (B25044), tenure × household size (B25009). Person table: age × sex (B01001).
3. **Fit:** IPF on household weights against the three household tables. Draw 500 adults per district from the fitted households, seed 1114. Then rake the 500 to age × sex; that raked value is the `weight` column.
4. **Traits straight from the record:** age, sex, `HINCP × ADJINC`, tenure, vehicles, household size, children (`HUPAC`), commute mode (`JWTRNS`) and minutes (`JWMNP`), move-in band (`MV`), employment (`ESR`).
5. **Home block:** within the district, in proportion to block adult population (P3).
6. **Work tract:** employed personas only, drawn from LODES 2021 flows out of the home tract.
7. **Precomputed per persona:** nearest edge, nearest arterial and distance, so the engine never does geometry.

**Done when:** 500 rows per district pass the schema; renter share and zero-car share are within 5 points of ACS for each district.

**Known limit to state:** LODES work tracts and PUMS commute minutes come from different sources and will not always agree for one persona.

### 7.1 Richer personas (researched Nov 15, not yet built)

Goal: give each resident more real information so reactions differ for real reasons. The rule still holds: every added field comes from a census record or a public dataset joined by where the resident lives. Survey answers stay out of personas and are used only to check them.

**Tier 1: more fields from the same census record.** No new downloads; all confirmed present in PUMS 2024.

| Trait | PUMS field | Why it should change answers |
| --- | --- | --- |
| Race and Hispanic origin | `RAC1P`, `HISP` | The strongest backstory field in the published silicon-sampling research |
| Education | `SCHL` | |
| Work status, occupation and industry group, hours | `ESR`, `OCCP`, `INDP`, `WKHP` | Jobs and construction proposals; delivery drivers on a drone route |
| Leaves for work at | `JWDP` | Peak-hour traffic and early-morning noise |
| Rent or owner cost as a share of income; monthly rent; home value | `GRPIP`, `OCPIP`, `GRNTP`, `VALP` | Housing and displacement proposals |
| Building type and age | `BLD`, `YRBLT` | Apartment dwellers vs single-family owners |
| Household type, multigenerational, grandparent raising grandchildren, anyone 65+ | `HHT2`, `MULTG`, `GCR`, `R65` | Safety and school-related concerns |
| Disability, including difficulty walking | `DIS`, `DPHY` | Transit cuts, road and sidewalk changes |
| Language at home, English ability, born abroad | `HHL`, `ENG`, `NATIVITY` | Southwest Detroit especially |
| Income-to-poverty ratio, SNAP | `POVPIP`, `FS` | Grocery and cost-of-living proposals |
| Internet access | `ACCESSINET` | Delivery proposals |
| Veteran | `MIL` | |

**Tier 2: what is around their home.** Joined by home block or tract from layers confirmed live.

| Context line | Source | Confirmed |
| --- | --- | --- |
| Neighborhood name | Neighborhoods layer (205) | Yes |
| Reported crimes near home this year, by category | `RMS_Crime_Incidents_2026`: 74,166 incidents, carries the 2020 block id | Yes |
| What neighbors complain about (top 311 request types nearby) | Improve Detroit, 765,518 points | Yes |
| Vacant lots and blight on the block | Current parcels (vacant classes); `blight_tickets` (913,837); vacant property registrations (1,517) | Yes |
| Crashes on the nearest main street | Crash layers 2011–2024 | Yes |
| Nearest bus stop: distance, route, how often it comes, boardings | DDOT routes and stop ridership | Yes (ridership period unstated) |
| Nearest counted street: vehicles per day, speed limit | 2024 traffic volumes | Yes |
| Distance to nearest park | `city_parks` (302) | Yes |
| Near a rail line; in a flood zone | Railroads layer; parcel `fema_flood_zone` | Layer exists; fields not inspected |
| Inside Michigan Central's 3-mile aerial region | Computed from the published radius | Yes |
| Tract health and hardship (for example utility shut-off threat, food stamp use, disability) | CDC PLACES, 40 measures per tract, 2023 | Yes (tract 5214 returned data) |

Drop owner and taxpayer name columns from parcels and blight tickets on download. Context is always a count or a distance for an area, never a record about a person.

**How it reaches the model.** One fixed resident card: the same fields in the same order for every resident, Tier 1 then Tier 2, about 12 lines. No field is left out for some residents and included for others, so differences in answers come from the values.

**How we know it helps.** More detail is not automatically better: it can push a small model toward stereotypes. Test it on the calibration questions before adopting it:

1. Run calibration with the current 10-field card, then with the Tier 1 card, then Tier 1 + Tier 2.
2. Keep a tier only if average error drops. Record all three results.
3. A direct test of Tier 2: residents on high-crime blocks should feel less safe walking than residents on low-crime blocks. If the answers do not move with the data, the context is not being used.

**Not checked:** `Plan_Detroit_Participants_Public_View` (2,784 points with a notes field, edited Nov 13) may hold real resident comments from the city's master-plan engagement. If it does, it is calibration material, not persona input.

## 8. Traffic engine (`engine/`)

### 8.1 Shared path

1. **Trips:** size × rate from `ite_rates.csv`. Daily and evening peak.
2. **Detroit adjustment:** × (1 − zero-car household share of the site's tract, ACS B25044). Raw and adjusted both returned.
3. **Distribute:** LODES 2021 tract flows. Housing uses where the site tract's residents work; job and retail uses use where the site tract's workers live. Destinations outside Detroit are routed to the network node nearest the destination's direction at the city edge (an assumption, listed).
4. **Assign:** shortest path by length ÷ posted speed on the city network; each edge on a path gets that destination's share.
5. **Load:** on counted segments only, `(AADT × K × D) ÷ (through lanes per direction × capacity)`, before and after. K, D and capacity come from the spec's assumptions and default to 0.09, 0.55 and 800, shown as unsourced planning assumptions.
6. **Impacts:** for each persona, added vehicles per day on their nearest edge, distance to the site, and action-specific flags. For each tract, the same in aggregate.

### 8.2 Actions

| Action | Computed from | Inputs the user must state | Status |
| --- | --- | --- | --- |
| `add_building` | ITE rate, ACS, LODES, network, 2024 counts | use, size | Fully sourced |
| `modify_road` (lanes) | 2024 count, lanes | lanes removed | Fully sourced |
| `modify_road` (close) | count moved to detour path | segment | Sourced + one labelled assumption |
| `add_drone_route` | path geometry, persona positions | flights, packages per flight, packages per van route, band width | Traffic effect is a district total only (4.2) |
| `change_transit` | route headways, stop boardings, elasticity 0.5 | new headway; diversion share if car trips wanted | Riders lost sourced; car shift input-only (4.7) |
| `rezone` | parcel area × FAR from the zoning table → `add_building` | new zone, average unit size | Nine zones computable; table needs an official-source check (4.8) |
| `add_event_surge` | seats, FHWA occupancy | attendance share, auto share, events per year | Sourced with stated inputs (4.9) |

### 8.3 Tests

- 400 units × 4.54 = 1,816 raw daily trips; × 0.39 = 156 at evening peak.
- Michigan Ave at 14th, 2024: 8,347 vehicles, 2 through lanes per direction → load 0.26. One lane per direction → 0.52. (The repo's 0.32 → 0.64 uses the 2020 count from a different segment; update `test_load.py` and the docs.)
- A spec with an ITE code not in the table raises, and the agent reports "no published rate".
- Engine returns in under 2 seconds for a District 6 spec.

## 9. Residents (`residents/`)

- **Call:** Converse on `us.anthropic.claude-haiku-5-5` (effort `low`), 25 personas per call, forced tool `submit_reactions` whose schema is `{items: [{persona_id, support 1–5, top_concern enum, reaction}]}`.
- **Prompt:** persona traits + scenario summary + that persona's computed impact lines. Impact lines are built only from engine output; a persona with no computed change gets "no direct change".
- **Checks:** as in SCOPE (validate, retry failed personas once, drop, flag above 5%).
- **Aggregate:** weighted by the persona `weight`. Outputs: overall and per-district split, worries, groups (exposure, tenure, age, vehicles), tract-level support with `n`, quotes.
- **Quotes** are verbatim model text for a real persona id, with `who` built from that persona's traits. Never edited.
- **Range:** bootstrap resample of personas within district, 200 draws, 5th–95th percentile. This is sampling spread only, not model error; label it so.
- **Cache key:** spec hash + persona id + impact lines.

### 9.1 Correction-engine questionnaire (seven questions agreed Nov 14; parked)

Decided Nov 14: there are two engines. The first engine, built first, asks each resident only for a stance (support, neutral or oppose) and one reason; those questions are on `main` in `residents/prompt.py` and `contracts/resident_response.schema.json`. The seven questions below are kept for the second engine, the correction engine, which reads why residents opposed a request (by answer, by who they are and by where they live) and proposes a changed request with better support. They are stored in `residents/correction_questions.py` (`PROMPT_VERSION = q7-2026-11-14`) and no schema carries them yet.

| # | Question | Answer options | Feeds |
| --- | --- | --- | --- |
| 1 | Do you support or oppose this proposal? | 1 strongly oppose to 5 strongly support | Support split |
| 2 | What worries you most about it? | traffic, noise, safety, privacy, rent, jobs, access, none | "What worries people" |
| 3 | What is the biggest benefit to you, if any? | jobs, housing, convenience, safety, less traffic, none | Why supporters support |
| 4 | Would it make daily life for your household better, worse or no different? | better, worse, no different | Personal impact vs general opinion |
| 5 | How likely are you to speak at a public meeting about it? | not likely, somewhat, very | "The neighborhood vs the room" |
| 6 | What one change would make you more supportive? | smaller, different location, limited hours, community benefits, nothing | "Test a fix" suggestions |
| 7 | Say what you think in one sentence. | Free text under 200 characters | Quotes |

Fixed alongside it: the resident description uses the same census fields in the same order for everyone, followed by that resident's computed impact lines. The calibration questions (section 10) are a separate set asked once per resident set.

## 10. Calibration (`residents/calibrate.py`)

| Check | Real value | Source |
| --- | --- | --- |
| Feel somewhat or very safe walking in their neighborhood | **85%** | DMACS W22 Q76 |
| Somewhat, mostly or very satisfied with their neighborhood | 67% | DMACS W22 Q11 |
| Detroit headed in the right direction | 55% | DMACS W22 Q32 |
| Used public transportation in Detroit in the past year | 32% | DMACS W20 Q80 |

- Ask each question with the survey's own wording and answer options (copy them from the topline PDFs), so "don't know" and the 7-point satisfaction scale are handled the same way as the real survey.
- Report simulated %, real %, error in points, and the average. Store with seed and prompt version. Show it whatever it is.
- **Model comparison (once):** run the calibration questions for one district's 500 residents on Nova 2 Lite and on Claude Haiku 5.5. Haiku 5.5 is the default; switch to Nova only if its average error is clearly lower, and record both results. Store the model ID with every calibration record.
- Drone polls stay as bounds (23% to 87%), plus the US Postal Service OIG 2016 national figure (44% like the idea, 65% of millennials, 24% of boomers) as a third reference. None is a Detroit result.
- `run_result.calibration.measured` stays `false` until this has run.

## 11. Scenario agent (`agent/`)

- Strands in a Lambda, model `us.anthropic.claude-haiku-5-5`, output forced through `structured_output_model` matching the spec schema, then validated again with `contracts/validate.py`.
- Conversation state in `S3SessionManager`, keyed by a session id from the frontend.
- **Tools return data only:** `geocode` (Amazon Location, biased to Detroit, falling back to `intersections.parquet` for "Michigan and 14th"), `find_parcels` (nearest parcels with class, zoning, area), `lookup_trip_rate` (exact rows of `ite_rates.csv`), `find_segment`, `find_route`.
- **Missing inputs:** where section 8.2 lists a required input the user did not give, the agent asks for it on the confirmation card rather than filling a default. Assumptions with a citation may be pre-filled and are listed.
- The agent writes no traffic or sentiment numbers. "Test a fix" suggestions are prompt text only.

### 11.1 Free input: residents read what the user asked for (decided Nov 14)

The user can type any proposal, for any kind of building, route or change, placed anywhere inside the selected districts. The scenario step sorts it into an action type, but it must not replace what the user said with a preset. Residents are asked about the proposal as the user stated it: a strip club is put to them as a strip club, not as a generic building.

| Rule | How | Status |
| --- | --- | --- |
| The user's own terms reach residents | Every action carries two text constraints, `what` and `where`, filled from the question. `summary_line` leads with them. | Built Nov 14 |
| No nearest-preset substitution | If a use or place has no matching option in a select field, the field is left at its default and marked `assumed`; the use is not listed under `unsupported`. | Built Nov 14 (prompt rule) |
| Assumed values are not read to residents | The summary lists only settings with source `from_question` or `edited`. | Built Nov 14 |
| Numbers the user did not give are labelled | A number that does not appear in the question is marked `assumed` with a note, whatever the model says. | Built Nov 14 |
| Any location inside the selected districts | Verify `where` against map data, check the point is inside a selected district, and give the engine that point in place of the three preset sites. See 11.2. | Planned (11.2) |
| Traffic for any use | Trips are computed only for uses with a published rate in `ite_rates.csv`. For other uses the engine returns "no published trip rate" and residents are still asked, with distance to the site as their impact line. | Not built |
| Reasons fit any use | The fixed reason list (traffic, noise, safety, privacy, rent, jobs, access, none) has nothing for objections to the kind of venue. Propose adding one reason for it; needs both lanes to agree because the website reads the list. | Open |
| The website shows `what` and `where` | The prototype panel shows them as editable text blocks. | Built Nov 14 |

### 11.2 Place resolver: verify where, and ask when it is missing (planned Nov 14, not built)

Goal: a place the user types is checked against real map data before anything runs. A route needs a verified start and a verified end. If a place is missing or cannot be verified, the scenario step asks the user for it; it never guesses and never falls back to a preset.

**What each action type needs before it can run**

| Action | Places required |
| --- | --- |
| `add_drone_route`, `change_transit` (new route) | start point and end point |
| `add_building`, `add_event_surge` | one point |
| `modify_road` | a street, plus the two cross streets that bound the stretch |
| `rezone` | an address, block or named area |

**How a place is verified** (first method that matches wins; each result records the method, the matched name, the point and its council district)

| The user typed | Checked against | Evidence it works |
| --- | --- | --- |
| Two streets ("Michigan and Trumbull") | City road layer (`raw/detroit/roads.geojson`, 38,117 segments, 2,729 street names, field `NAME`): both names must exist and their lines must meet. | Tested Nov 14: Michigan and Trumbull meet at (-83.06695, 42.33142); Bagley and 16th meet; Woodward and 5th both exist but do not meet; Woodward and Cass do not meet (they run parallel). |
| A street address ("2001 Michigan Ave") | Address ranges on the same road layer (`FRADDR`, `TOADDR`), then the parcel file's `address` column (377,940 parcels) for an exact match. | Fields confirmed present; lookup not yet tested. |
| A neighborhood ("Corktown") | Neighborhood layer (205 areas, `nhood_name`). Gives an area, not a point, so it is enough for a rezoning but not for a route end. | Layer downloaded. |
| A landmark or business ("the Hilton", "Renaissance Center", "Newlab roof") | Not in any city file. Amazon Location Service place search, limited to Detroit's bounding box. | Tested Nov 14 in us-east-2 with `geo-places search-text`, limited to Detroit's bounding box: "Renaissance Center" and "Newlab at Michigan Central" each returned the right point; "Civic Center" returned Civic Center Dr; "Hilton hotel" returned three different hotels, so a vague name must go back to the user as a choice. Price: $0.50 per 1,000 searches (Core tier, AWS Price List API, us-east-2). Not yet counted by the spending limit. |

**Rules**

1. The scenario model only splits the text into parts (kind of place, street names, from and to). It does not decide whether a place exists; the lookup does.
2. Every verified point is tested against the official council district polygons. A point outside the selected districts is reported to the user with the district it is in. It is not moved.
3. If a required place is missing, or a typed place is not found, or two streets do not meet, the spec comes back with `status: "needs_info"` and a list of plain questions, for example: "Woodward and 5th don't cross. Which did you mean?" with up to three real alternatives taken from the map (streets that do cross Woodward with a similar name). `POST /runs` refuses a spec in this state.
4. Verified points go to the engine and to each resident's impact line ("about 400 ft from your home"), and to the website as a marker or a line.

**Build**

| Piece | What it does |
| --- | --- |
| `data/places/build_index.py` | From the road layer: a table of every pair of streets that meet, with the point and its district; a table of address ranges per street. From parcels: address to point. Written to `processed/places/` in the bucket. Precomputing keeps map libraries out of the Lambda. |
| `shared/places.py` | `resolve(text, districts)` returns a verified point or the reason it failed, plus alternatives. |
| `agent/handler.py` | Calls `resolve` for `where`, or for `from` and `to` on routes; sets `needs_info` and the questions. |
| Contracts | `scenario_spec`: add `needs_info` to `status`, add `questions[]`; route actions get `from` and `to` text constraints; each resolved place is stored on its constraint (`resolved: {name, method, lon, lat, district}`). Needs the web lane, which must show the questions and the marker. |

## 12. Contract changes to propose

Not applied. Each needs the frontend lane's agreement and a fixture update.

| Schema | Change | Why |
| --- | --- | --- |
| `run_result` | `blocks[]` → `tracts[]` with `support`, `n`, `population` | 4.1 |
| `run_result` | per-number provenance: `sources[]` (dataset, vintage, URL) and `assumptions[]` with `kind` | section 1 |
| `run_result` | `segments[].aadt_year`; `load_*` nullable when `counted` is false | 4.10 |
| `run_result` | `district_totals` for trips that are not assigned to streets | 4.2 |
| `persona` | `years_in_home` → `years_in_home_band`; add `employed` | 4.5 |
| `scenario_spec` | drone: drop `van_share_replaced`, add `packages_per_flight`, rename `noise_band_ft` → `path_band_ft` | 4.2, 4.3 |
| `scenario_spec` | transit: add `car_diversion_share` (optional); event: add `attendance_share`, `auto_share` | 4.7, 4.9 |
| fixtures | drone fixture: street loads unchanged; Michigan Ave values from 2024 | 4.2 |
| `calibration_targets.json` | safe walking 70 → 85; drop the 20-year check; add the W20 transit check | 2.2 |
| `ite_rates.csv` | add the 24 verified rows from the Palm Beach sheet; fill 850 PM peak | 2.2 |

## 13. Build order

| # | Step | Owner | Done when |
| --- | --- | --- | --- |
| 1 | Census key, AWS account, read Haiku 5.5 quota | Human | `converse` returns from `us.anthropic.claude-haiku-5-5` |
| 2 | Fix the download scripts (section 3) and download | Data | every file in the manifest, no HTML saved as data |
| 3 | Agree the contract changes (section 12) | All lanes | schemas and fixtures updated together |
| 4 | Processed artifacts (6.1) | Data | 6.3 passes |
| 5 | Personas | Data | section 7 check passes for District 6, then all 7 |
| 6 | Engine: `add_building`, then `modify_road` | Engine | 8.3 tests pass on real data |
| 7 | Infra: tables, state machine, API, with stub Lambdas | Infra | `POST /run` → poll → result from S3 |
| 8 | Residents: batch, validate, aggregate | Residents | 500 District 6 personas, drop rate under 5% |
| 9 | Calibration | Residents | record stored and returned by `GET /calibration` |
| 10 | Agent | Agent | the 5 test prompts behave, 3 times running |
| 11 | Drone, event, transit actions | Engine | each returns a valid result with its inputs labelled |
| 12 | Rezone | Engine | only if the zoning table is typed and cited |
| 13 | Cache the 3 demo runs | All | saved under `demo/` with `cached: true` |

Steps 4–5, 6, 7 and 10 can run in parallel once 2 and 3 are done.

## 14. Open items that need a person

1. **Census API key** in `.env`. Nothing census-related runs without it. (Tested Nov 14: works.)
2. **GTFS and OSM hosts** refused this session: test both from a laptop. Neither blocks the plan (route headways and the road network have confirmed alternatives).
3. **DDOT stop ridership period:** ask DDOT or find the layer's metadata before quoting riders-lost numbers on stage.
4. **Zoning capacity table:** done Nov 14. The nine FAR values match the official code (4.8). Other columns are still from the mirror.
5. **K, D and lane capacity:** read the FDOT Quality/Level of Service tables directly for a citation, or keep them labelled as assumptions.
6. **DMACS Wave 21 open microdata:** download from U-M Deep Blue if subgroup calibration is wanted.
7. **Demo script:** the housing line "all counted streets stay green" and the drone line "van trips removed from Michigan Ave" both need rewording once real results exist (see 4.2 and 8.3).

## 15. Correction engine (planned Nov 15, not built)

**What it is for.** A proposal has been run and residents mostly said no. The correction engine works out why, proposes a changed version of the same proposal that should do better, runs it against the same residents, and repeats, for at most five reruns. Example: "a bus garage at X" comes back majority opposed; the engine tries other real sites for the same garage and reports the best one found, with every attempt shown.

**What it is not.** It does not reword the proposal to make it sound better, it does not invent places, and it does not claim to have found the best possible answer. It reports the best of the versions it tried.

### 15.1 Prerequisites (must be fixed first, or the engine chases noise)

| # | Problem found on Nov 15 | Fix needed before building |
| --- | --- | --- |
| P1 | A resident's answer depends on who shares their batch of 25. Ten residents near a bus route all supported it when batched with far-away residents; 100 residents placed near the same route, batched together, split 20 support / 24 neutral / 56 oppose and split by vehicles. | Ask residents in batches that are alike in distance (sort by distance to the proposal before batching), or one at a time. Test both on the same residents and keep the one whose answers do not change when batch-mates change. |
| P2 | The same proposal gives different totals on different runs (strip club, District 6: 12%, 0.3%, 2.9% and 2.5% support across four runs with different prompts). | Measure run-to-run spread: run the unchanged proposal twice. A changed version only counts as better if it beats the original by more than that spread. |
| P3 | Only a handful of residents live near any one site (10 of 2,000 within a quarter mile). | Section 16, option C: draw extra residents from the blocks near the site so the near group is large enough to read. |

### 15.2 The loop

```
run 0  the user's proposal, as run today                         (already exists)
  │
  ▼
diagnose   who opposed, where, and why                           (15.3)
  │
  ├─ nothing to fix (support already ahead)            ──► stop: "no correction needed"
  ├─ opposition does not depend on place or settings   ──► stop: "residents object to the thing itself"
  ▼
choose a lever   location, size, hours or another setting        (15.4)
  ▼
generate candidates   real, verified alternatives                (15.5)
  ▼
rank candidates   predicted support from the answers so far      (15.6)
  ▼
rerun k (k = 1..5)   best untried candidate, same residents      (15.7)
  ▼
compare with run 0   beyond the measured spread?                 (15.8)
  │
  ├─ target reached                                    ──► stop
  ├─ 5 reruns used, or spending limit reached          ──► stop
  ├─ no remaining candidate is predicted to beat the best so far ──► stop
  └─ otherwise: add this run's answers to the evidence and go back to "rank candidates"
```

**Target** (chosen by the user, default the first): more support than oppose · support above 50% of all residents · support at or above two thirds.

**Hard caps, enforced on the server, not by the model:** at most 5 reruns per correction; the existing run and day spending limits apply to every rerun; a correction stops the moment either is reached and reports what it had.

### 15.3 Diagnose: why did they say no?

All from data the first engine already stores for a run (stance, reason, distance, age, tenure, vehicles, district, block):

1. **Is opposition local?** Oppose share within 1 mile against beyond 1 mile, and the full by-distance table. If opposition falls with distance, place matters and moving it can help. If opposition is the same at every distance, residents object to the thing itself and no site will fix it.
2. **Who opposes?** Oppose share by tenure, age band, vehicles and district, against the same groups' share of all residents. A group that is strongly over-represented among opponents is named in the report (the user's example: "most opponents have no car").
3. **Where do they cluster?** Blocks and neighborhoods with the highest opposition, and whether anything in the city data sits there (a school, a park, an existing facility of the same kind). This uses the neighborhood facts already computed per block; they are read by the engine, not shown to the model.
4. **What would change their mind?** A sample of opponents (nearest first, up to 200) is asked the parked seven-question set (`residents/correction_questions.py`), in particular "What one change would make you more supportive?" with its fixed options: smaller · different location · limited hours · community benefits · nothing. The answers are counted. This is the only new model call in the diagnosis.

Output: a diagnosis object (tables plus two or three plain sentences built from the numbers by template, not written freely by a model).

### 15.4 Choose the lever

| What opponents and the data say | Lever | Changes |
| --- | --- | --- |
| "different location" leads, and opposition is local | **Location** | the verified place (or a route's start or end) |
| "smaller" leads | **Size** | homes, floors, floor area, flights a day, buses an hour |
| "limited hours" leads | **Hours** | flying hours, event time, operating hours where the action has them |
| "community benefits" leads | none available | reported to the user as what residents asked for; the engine cannot model it |
| "nothing" leads, or opposition does not vary with distance | none | stop and say so |

Only one lever is changed per rerun, so a gain can be attributed. If the first lever is exhausted without reaching the target and reruns remain, the next-ranked lever is tried.

### 15.5 Generate candidates (location lever)

Candidates are real places taken from city data, never free text from a model:

- **Pool:** vacant parcels and Detroit Land Bank lots inside the selected districts (55,751 Land Bank properties, 377,940 parcels with size, zoning district and vacancy; both already downloaded).
- **Fit to the proposal:** at least the lot area the proposal needs, when the user stated a size; in the **same zoning district as the original site**, read from the zoning layer. Whether a use is actually permitted in a zone is not something this project has sourced, so the report says "same zoning district as your site; permitted use not checked" and nothing stronger.
- **Spread:** candidates are thinned so they are at least half a mile apart, and at least half a mile from the original site.
- **Verification:** each candidate goes through the place resolver so it has a real name ("Lot at Trumbull St & Ash St"), a point and a district, exactly like a place the user typed.
- For a **route**, candidates shift one end at a time to verified crossings along the same street.
- For the **size** and **hours** levers, candidates are the other values the action already offers (its steps and options), nothing else.

Typically a few hundred sites become 10 to 20 candidates.

### 15.6 Rank candidates before spending a rerun

This is the step the user described as "where the AI thinks they'll get more yeses". It is done with the residents' own answers, not by asking a model to guess:

1. From all runs so far, tabulate P(support), P(neutral), P(oppose) by distance band and by the trait groups that mattered in the diagnosis.
2. For each candidate, compute every resident's distance to it, look up their probabilities, and sum with census weights. That gives a predicted split for the candidate.
3. Rank by the user's target. Break ties toward the candidate with fewer residents predicted to oppose within a quarter mile.

After each rerun the table is rebuilt with the new answers, so predictions improve as the loop goes on. Each prediction is stored next to the real result of that rerun, so the report shows how good the predictions were.

### 15.7 Rerun under identical conditions

Same residents (the same persona ids), same model, same prompt template, same batching rule, same sentence share. Only the changed setting differs. The proposal sentence is rebuilt by the same template (`summary_line`), so the wording changes only where the place or value changed. The `what` text is never edited.

### 15.8 Compare and stop

- A rerun **beats** the best so far only if its support share exceeds it by more than the measured run-to-run spread (P2).
- **Stop reasons**, one of which is always reported: target reached · five reruns used · spending limit reached · no remaining candidate predicted to beat the best so far · nothing to fix · not fixable by any lever.
- The report always includes the original, every attempt (better or worse), and the best one.

### 15.9 What the user gets back

| Part | Content |
| --- | --- |
| Why they said no | the diagnosis tables and sentences (15.3) |
| What was tried | one row per rerun: what changed, predicted split, real split, change against the original, whether it is beyond the spread |
| Best version found | its proposal sentence, split, by-distance table, traffic numbers if any |
| Who lives near each site | adults within a quarter mile and a mile, and their make-up (renters, no-car households, age) from census data |
| Why it stopped | the stop reason |
| Limits | "best of N tried, not the best possible"; forecast, not a poll; the accuracy figures of the model in use |

**"Who lives near each site" is required, not optional.** The easiest way to get fewer objections is to move something to where fewer people live, or to where residents are less likely to object. That can shift a burden onto a neighborhood without anyone deciding to. Showing who lives near each candidate lets the user see that trade.

### 15.10 How it is built

| Piece | What it does |
| --- | --- |
| `correction/diagnose.py` | tables and template sentences from a run's stored answers; asks the opponent sample the parked questions |
| `correction/candidates.py` | candidate sites from parcels, Land Bank lots and zoning (precomputed index in the bucket, like the place index) |
| `correction/predict.py` | the lookup-table predictor (15.6) |
| `correction/loop.py` | a second Step Functions state machine: diagnose → choose lever → candidates → [rank → rerun → compare] up to 5 times → report. The rerun step calls the existing run machine. The iteration counter lives in the state machine definition. |
| API | `POST /corrections {run_id, target}` → `correction_id`; `GET /corrections/{id}` → progress and report |
| Contracts | new `correction_result.schema.json`; the seven questions get their own response schema. No change to existing contracts. |
| Site | the Compare button opens the report: attempts side by side, sites on the map |

**Cost and time, from tonight's measured runs:** a 500-resident run is about $0.06 and 12 seconds; a 2,000-resident run about $0.25 to $0.31 and 40 seconds. A full correction (diagnosis, a repeat of the original for the spread, five reruns) is about seven runs: under $0.50 for one district, about $2 for four, and one to five minutes. All inside the existing $10 limits.

### 15.11 Order of work

1. P1 batching fix and P2 spread measurement (15.1). Without these nothing else is trustworthy.
2. Diagnosis (15.3), shown on the site by itself. Useful even with no loop: it answers "why did they say no".
3. Candidate index and predictor for the location lever (15.5, 15.6).
4. The loop with its caps (15.2, 15.7, 15.8), then the report and the Compare view.
5. Size and hours levers.

### 15.12 Open questions

- Is "more support than oppose" the right default target when most residents are neutral? An alternative is to count only residents within a set distance (section 16).
- Zoning: a sourced table of which uses each district permits would let candidates be filtered properly. Not found yet.
- Should the user be able to rule sites in or out before the loop starts (for example "not near a school")?

## 16. Parked feature: weighting residents by distance (raised Nov 15, not decided)

**The idea (Partner).** People close to a proposal should count for more in the result than people far from it. Raised after a bus route came back 81% neutral because the typical resident asked lived 5 miles away.

**Why it matters.** With four districts selected, 1,909 of 2,000 residents lived more than a mile from the route. Their near-uniform "neutral" swamps the 91 who live close, where support was 84% to 100%.

**Three ways to do it**

| Option | How | For | Against |
| --- | --- | --- | --- |
| A. Affected-area headline | Report residents within a stated distance (for example 1 mile) as the main number, with the district-wide number beside it. No weights. | Nothing invented: it is a filter, and both numbers are shown. Easy to explain. | The cut-off distance is a choice; a different one gives a different headline. |
| B. Distance-decay weights | Each resident's census weight is multiplied by a factor that falls with distance. | One number that reflects closeness smoothly. | The shape and steepness of the fall-off are not in any dataset. It is a value judgment about whose view counts, expressed as a formula. It must be labelled an assumption and shown next to the unweighted result. |
| C. Oversample near the site | Draw extra residents from the blocks near the proposal, keeping census weights, so the near group is hundreds of people, not ten. | Fixes the real weakness (too few near residents to read) without changing whose view counts. | Costs more calls per run. Does not change the city-wide headline by itself. |

**Recommendation to discuss:** A and C together. C makes the near group reliable; A puts it in front of the user without hiding the wider district. B only if the team agrees on a fall-off and is willing to label it.

**Bearing on the rule in section 1:** A and C use only data. B needs a labelled assumption for the fall-off.

**Status:** parked. To be raised with teammates before any of it is built (LOG.md, Open questions / handoffs).
