"""Build 500 AI residents per council district from census microdata (BACKEND_PLAN.md section 7).

    python -m data.personas.build

Every value on a persona is copied from one real, anonymous census record (PUMS 2020-2024, Michigan)
or drawn from a census count. Nothing is invented. Method:

1. Blocks -> districts: each 2020 block goes to the official 2026 council district holding its interior point.
2. District controls: ACS 2024 tract tables, split across districts by the tract's adult population (2020 P3)
   in each district. Household tables use the same adult split (an approximation, stated in the summary).
3. Seed: PUMS households in Detroit's six 2020 PUMAs, housing units only (group quarters excluded).
   For district d a household starts at WGTP x (share of its PUMA's adults who live in d).
4. Fit: iterative proportional fitting of household weights to three district tables: income (B19001),
   tenure x vehicles (B25044), tenure x household size (B25009).
5. Draw 500 adults per district with probability proportional to the fitted household weight (seed 1114).
6. Weight: the 500 are post-stratified to the district's adults by age band x sex (B01001).
7. Home block: drawn within the district in proportion to block adult population.
8. Work tract: for employed residents who travel to work, drawn from LODES 2021 flows out of the home tract.

Tier 1 fields (BACKEND_PLAN.md 7.1) are copied from the same record. Code meanings were checked against the
Census Bureau's PUMS Data Dictionary 2020-2024 on Nov 14, 2026.

Outputs: data/processed/personas/district_{n}.parquet and personas_summary.json (targets vs results).
"""
from __future__ import annotations

import io
import json
import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd

from data.config import INTERIM, PERSONA_SEED, PERSONAS_PER_DISTRICT, PROCESSED, RAW

CENSUS = RAW / "census"
OUT = PROCESSED / "personas"

INCOME_EDGES = [10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 75, 100, 125, 150, 200]   # $ thousands; B19001_002..017
AGE_BANDS = ["18-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75+"]
AGE_EDGES = [25, 35, 45, 55, 65, 75]
# B01001 male cells for each adult band; female cells are the same + 24
AGE_CELLS = {"18-24": range(7, 11), "25-34": range(11, 13), "35-44": range(13, 15), "45-54": range(15, 17),
             "55-64": range(17, 20), "65-74": range(20, 23), "75+": range(23, 26)}

MOVE_IN = {1: "12 months or less", 2: "13 to 23 months", 3: "2 to 4 years", 4: "5 to 9 years",
           5: "10 to 19 years", 6: "20 to 29 years", 7: "30 years or more"}
BLD = {1: "mobile home", 2: "single-family house, detached", 3: "single-family house, attached", 4: "2-unit building",
       5: "3-4 unit building", 6: "5-9 unit building", 7: "10-19 unit building", 8: "20-49 unit building",
       9: "50+ unit building", 10: "boat, RV or van"}
HHL = {1: "English only", 2: "Spanish", 3: "other Indo-European", 4: "Asian or Pacific Island", 5: "other"}
RACE = {1: "White", 2: "Black", 3: "American Indian or Alaska Native", 4: "American Indian or Alaska Native",
        5: "American Indian or Alaska Native", 6: "Asian", 7: "Native Hawaiian or Pacific Islander",
        8: "some other race", 9: "two or more races"}


def education(schl: int) -> str:
    if schl <= 15:
        return "less than high school"
    if schl <= 17:
        return "high school diploma or GED"
    if schl <= 19:
        return "some college, no degree"
    return {20: "associate degree", 21: "bachelor's degree"}.get(schl, "graduate or professional degree")


def employment(esr) -> str:
    return {1: "employed", 2: "employed", 3: "unemployed", 4: "armed forces", 5: "armed forces", 6: "not in labor force"}[int(esr)]


def commute(jwtrns, jwrip) -> str:
    if pd.isna(jwtrns):
        return "not_working"
    j = int(jwtrns)
    if j == 1:
        return "drive_alone" if (not pd.isna(jwrip) and int(jwrip) == 1) else "carpool"
    return {2: "bus", 9: "bike", 10: "walk", 11: "work_from_home"}.get(j, "other")


# ---------- geography ----------
def blocks_with_districts() -> pd.DataFrame:
    """Wayne County 2020 blocks with population, tract, PUMA and (where inside the city) council district."""
    zpath = next((CENSUS / "tiger").glob("tl_*_26_tabblock20.zip"))
    b = gpd.read_file(f"zip://{zpath}", columns=["COUNTYFP20", "GEOID20", "INTPTLON20", "INTPTLAT20"], ignore_geometry=True)
    b = b[b.COUNTYFP20 == "163"]
    if b.empty:
        raise SystemExit(f"no Wayne County blocks found in {zpath.name}")
    pts = gpd.GeoDataFrame(b[["GEOID20"]], geometry=gpd.points_from_xy(b.INTPTLON20.astype(float), b.INTPTLAT20.astype(float)),
                           crs=4326)
    d = gpd.read_file(RAW / "detroit" / "council_districts_2026.geojson")[["district_number", "geometry"]].to_crs(4326)
    j = gpd.sjoin(pts, d, how="left", predicate="within")[["GEOID20", "district_number"]].drop_duplicates("GEOID20")
    pop = pd.read_csv(CENSUS / "decennial" / "dec2020_pl_P1_P3_blocks_wayne.csv", dtype=str)
    pop["GEOID20"] = pop.state + pop.county + pop.tract + pop.block
    pop["adults"] = pop.P3_001N.astype(int)
    out = j.merge(pop[["GEOID20", "adults"]], on="GEOID20", how="left").fillna({"adults": 0})
    out["tract"] = out.GEOID20.str[:11]
    rel = pd.read_csv(CENSUS / "rel" / "2020_Census_Tract_to_2020_PUMA.txt", dtype=str, encoding="utf-8-sig")
    rel["tract"] = rel.STATEFP + rel.COUNTYFP + rel.TRACTCE
    out = out.merge(rel[["tract", "PUMA5CE"]], on="tract", how="left").rename(columns={"PUMA5CE": "puma", "district_number": "district"})
    return out


def acs(table: str) -> pd.DataFrame:
    df = pd.read_csv(CENSUS / "acs" / f"acs5_2024_{table}_tract_wayne.csv", dtype=str)
    df["tract"] = df.state + df.county + df.tract
    est = [c for c in df.columns if c.startswith(table) and c.endswith("E")]
    df[est] = df[est].astype(float)
    return df.set_index("tract")[est]


def district_controls(blocks: pd.DataFrame) -> dict:
    """Per district: target counts for each fitted table, tracts split by adult population."""
    in_city = blocks.dropna(subset=["district"])
    tract_total = blocks.groupby("tract").adults.sum()
    share = (in_city.groupby(["district", "tract"]).adults.sum() / tract_total).rename("share").reset_index()
    share = share[share.share > 0]
    inc, veh, size, age, ten = acs("B19001"), acs("B25044"), acs("B25009"), acs("B01001"), acs("B25003")
    out = {}
    for d, g in share.groupby("district"):
        w = g.set_index("tract").share

        def tot(df, cols):
            return np.array([(df.reindex(w.index)[c] * w).sum() for c in cols])

        age_t = {}
        for sex, off in (("male", 0), ("female", 24)):
            for band, cells in AGE_CELLS.items():
                age_t[(sex, band)] = float(tot(age, [f"B01001_{i + off:03d}E" for i in cells]).sum())
        out[int(d)] = {
            "income": tot(inc, [f"B19001_{i:03d}E" for i in range(2, 18)]),
            "ten_veh": tot(veh, [f"B25044_{i:03d}E" for i in list(range(3, 9)) + list(range(10, 16))]),      # owner 0..5+, renter 0..5+
            "ten_size": tot(size, [f"B25009_{i:03d}E" for i in list(range(3, 10)) + list(range(11, 18))]),   # owner 1..7+, renter 1..7+
            "age_sex": age_t,
            "households": float(tot(ten, ["B25003_001E"])[0]),
            "renter_share": float(tot(ten, ["B25003_003E"])[0] / tot(ten, ["B25003_001E"])[0]),
            "zero_car_share": float(tot(veh, ["B25044_003E", "B25044_010E"]).sum() / tot(veh, ["B25044_001E"])[0]),
        }
    return out


# ---------- PUMS ----------
def read_pums(pumas: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    hz, pz = CENSUS / "pums" / "pums5_2024_csv_hmi.zip", CENSUS / "pums" / "pums5_2024_csv_pmi.zip"
    hcols = ["SERIALNO", "PUMA", "ADJINC", "WGTP", "NP", "TYPEHUGQ", "ACCESSINET", "BLD", "FS", "TEN", "VEH", "GRPIP", "HHL",
             "HINCP", "HUPAC", "MV", "OCPIP", "R65"]
    pcols = ["SERIALNO", "SPORDER", "PUMA", "PWGTP", "AGEP", "DPHY", "JWMNP", "JWRIP", "JWTRNS", "MIL", "SCHL", "SEX", "DIS", "ESR",
             "HISP", "NATIVITY", "POVPIP", "RAC1P"]

    def load(z, cols):
        with zipfile.ZipFile(z) as zf:
            name = next(n for n in zf.namelist() if n.endswith(".csv"))
            df = pd.read_csv(io.BytesIO(zf.read(name)), usecols=cols, dtype={"SERIALNO": str, "PUMA": str})
        return df[df.PUMA.str.zfill(5).isin(pumas)].assign(PUMA=lambda x: x.PUMA.str.zfill(5))

    h = load(hz, hcols)
    h = h[(h.TYPEHUGQ == 1) & (h.NP > 0) & (h.WGTP > 0) & h.TEN.notna()].copy()
    h["income"] = (h.HINCP * h.ADJINC / 1_000_000).round().astype(int)
    h["inc_band"] = np.searchsorted(np.array(INCOME_EDGES) * 1000, h.income, side="right")
    h["renter"] = h.TEN.isin([3, 4]).astype(int)                       # 3 rented, 4 occupied without rent (ACS counts both as renter)
    h["ten_veh"] = h.renter * 6 + h.VEH.clip(upper=5).astype(int)
    h["ten_size"] = h.renter * 7 + (h.NP.clip(upper=7).astype(int) - 1)
    p = load(pz, pcols)
    p = p[(p.AGEP >= 18) & p.SERIALNO.isin(h.SERIALNO)].copy()
    return h, p


def ipf(w0: np.ndarray, margins: list[tuple[np.ndarray, np.ndarray]], iters: int = 200) -> tuple[np.ndarray, float]:
    """Rake weights to each (cell index per record, target per cell). Returns weights and the worst relative miss."""
    w = w0.astype(float).copy()
    for _ in range(iters):
        for idx, target in margins:
            cur = np.bincount(idx, weights=w, minlength=len(target))
            f = np.divide(target, cur, out=np.ones_like(target, dtype=float), where=cur > 0)
            w *= f[idx]
    miss = 0.0
    for idx, target in margins:
        cur = np.bincount(idx, weights=w, minlength=len(target))
        big = target > 0.005 * target.sum()                            # ignore near-empty cells when reporting fit
        miss = max(miss, float(np.max(np.abs(cur[big] - target[big]) / target[big])))
    return w, miss


def work_flows() -> pd.DataFrame:
    od = pd.read_csv(RAW / "lodes" / "mi_od_main_JT00_2021.csv.gz", usecols=["w_geocode", "h_geocode", "S000"], dtype={"w_geocode": str, "h_geocode": str})
    od = od[od.h_geocode.str.startswith("26163")]
    od["h_tract"], od["w_tract"] = od.h_geocode.str[:11], od.w_geocode.str[:11]
    return od.groupby(["h_tract", "w_tract"], as_index=False).S000.sum()


def main() -> None:
    pumas = json.loads((INTERIM / "detroit_pumas.json").read_text())["pumas"]
    blocks = blocks_with_districts()
    controls = district_controls(blocks)
    h, p = read_pums(pumas)
    flows = work_flows()
    flows_by_home = {t: (g.w_tract.to_numpy(), g.S000.to_numpy()) for t, g in flows.groupby("h_tract")}
    puma_adults = blocks.groupby("puma").adults.sum()
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {"seed": PERSONA_SEED, "per_district": PERSONAS_PER_DISTRICT, "pums": "ACS PUMS 2020-2024 5-year, Michigan",
               "pums_households_in_detroit_pumas": int(len(h)), "pums_adults_in_those_households": int(len(p)),
               "notes": ["Group quarters are excluded.",
                         "Household tables are split across districts by tract adult population (2020 P3), an approximation.",
                         "PUMA 03213 also covers tracts outside Detroit; its households enter a district only in proportion "
                         "to that district's share of the PUMA's adults.",
                         "years_in_home is null: the census gives a move-in band, stored as move_in_band.",
                         "LODES work tracts and PUMS commute minutes come from different sources and may disagree for one persona."],
               "districts": {}}
    for d in sorted(controls):
        c = controls[d]
        rng = np.random.default_rng(PERSONA_SEED + d)
        dblocks = blocks[(blocks.district == d) & (blocks.adults > 0)]
        f = (dblocks.groupby("puma").adults.sum() / puma_adults).reindex(pumas).fillna(0)
        w0 = h.WGTP.to_numpy() * h.PUMA.map(f).to_numpy()
        keep = w0 > 0
        hd = h[keep].reset_index(drop=True)
        w, miss = ipf(w0[keep], [(hd.inc_band.to_numpy(), c["income"]), (hd.ten_veh.to_numpy(), c["ten_veh"]),
                                  (hd.ten_size.to_numpy(), c["ten_size"])])
        hd["w"] = w
        adults = p.merge(hd, on="SERIALNO", suffixes=("", "_h"))
        pick = rng.choice(len(adults), size=PERSONAS_PER_DISTRICT, replace=False, p=(adults.w / adults.w.sum()).to_numpy())
        s = adults.iloc[np.sort(pick)].reset_index(drop=True)

        s["sex_l"] = np.where(s.SEX == 1, "male", "female")
        s["age_band"] = np.array(AGE_BANDS)[np.searchsorted(AGE_EDGES, s.AGEP, side="right")]
        counts = s.groupby(["sex_l", "age_band"]).size()
        weight = s.apply(lambda r: c["age_sex"][(r.sex_l, r.age_band)] / counts[(r.sex_l, r.age_band)], axis=1)
        empty = [f"{k[0]} {k[1]}" for k, v in c["age_sex"].items() if v > 0 and k not in counts.index]

        home = dblocks.GEOID20.to_numpy()[rng.choice(len(dblocks), size=len(s), p=(dblocks.adults / dblocks.adults.sum()).to_numpy())]
        mode = [commute(a, b) for a, b in zip(s.JWTRNS, s.JWRIP)]
        work = []
        for blk, m in zip(home, mode):
            fl = flows_by_home.get(blk[:11])
            work.append(None if m in ("not_working", "work_from_home") or fl is None
                        else str(fl[0][rng.choice(len(fl[0]), p=fl[1] / fl[1].sum())]))
        cost_share = np.where(s.renter == 1, s.GRPIP, s.OCPIP)
        out = pd.DataFrame({
            "persona_id": [f"d{d}-{i:04d}" for i in range(len(s))],
            "district": d,
            "tract_geoid": [b[:11] for b in home],
            "block_geoid": home,
            "age": s.AGEP.astype(int),
            "sex": s.sex_l,
            "hh_income": s.income.clip(lower=0).astype(int),
            "tenure": np.where(s.renter == 1, "renter", "owner"),
            "years_in_home": pd.array([None] * len(s), dtype="Int64"),
            "move_in_band": s.MV.map(MOVE_IN),
            "vehicles": s.VEH.astype(int),
            "commute_mode": mode,
            "commute_minutes": pd.array([None if pd.isna(x) or x == 888 else int(x) for x in s.JWMNP], dtype="Int64"),
            "hh_size": s.NP.astype(int),
            "children": s.HUPAC.isin([1, 2, 3]),
            "work_tract_geoid": work,
            "weight": weight.round(3),
            "pums_serialno": s.SERIALNO,
            # ---- Tier 1 (BACKEND_PLAN.md 7.1), same census record ----
            "race": s.RAC1P.map(RACE),
            "hispanic": s.HISP != 1,
            "education": s.SCHL.fillna(1).astype(int).map(education),
            "employment": s.ESR.map(employment),
            "disability": s.DIS == 1,
            "difficulty_walking": s.DPHY == 1,
            "born_abroad": s.NATIVITY == 2,
            "veteran": s.MIL.isin([1, 2]),
            "poverty_ratio_pct": pd.array([None if pd.isna(x) else int(x) for x in s.POVPIP], dtype="Int64"),
            "building_type": s.BLD.map(BLD),
            "housing_cost_pct_income": pd.array([None if pd.isna(x) else int(x) for x in cost_share], dtype="Int64"),
            "someone_65_plus_at_home": s.R65 > 0,
            "home_language": s.HHL.map(HHL),
            "internet_at_home": pd.array([None if pd.isna(x) or x == 8 else bool(x in (1, 2)) for x in s.ACCESSINET], dtype="boolean"),
            "snap": s.FS == 1,
        })
        out.to_parquet(OUT / f"district_{d}.parquet", index=False)
        (OUT / f"district_{d}.json").write_text(out.to_json(orient="records"))    # read by residents/batch.py in Lambda
        wsum = out.weight.sum()
        summary["districts"][d] = {
            "personas": int(len(out)), "distinct_census_households": int(out.pums_serialno.nunique()),
            "seed_households": int(keep.sum()), "ipf_worst_relative_miss": round(miss, 4),
            "acs_households": round(c["households"]),
            "renter_share": {"acs_households": round(c["renter_share"], 3), "fitted_households": round(float(hd.w[hd.renter == 1].sum() / hd.w.sum()), 3),
                             "personas_weighted_adults": round(float(out.weight[out.tenure == "renter"].sum() / wsum), 3)},
            "zero_car_share": {"acs_households": round(c["zero_car_share"], 3), "fitted_households": round(float(hd.w[hd.VEH == 0].sum() / hd.w.sum()), 3),
                               "personas_weighted_adults": round(float(out.weight[out.vehicles == 0].sum() / wsum), 3)},
            "adults_target": round(sum(c["age_sex"].values())), "weight_sum": round(float(wsum)),
            "age_sex_cells_with_no_persona": empty,
            "with_work_tract": int(out.work_tract_geoid.notna().sum()),
        }
        r = summary["districts"][d]
        print(f"District {d}: {r['personas']} personas from {r['distinct_census_households']} households; fit miss {miss:.3f}; "
              f"renter ACS {r['renter_share']['acs_households']:.3f} / fitted {r['renter_share']['fitted_households']:.3f}; "
              f"zero-car ACS {r['zero_car_share']['acs_households']:.3f} / fitted {r['zero_car_share']['fitted_households']:.3f}")
    (OUT / "personas_summary.json").write_text(json.dumps(summary, indent=1))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
