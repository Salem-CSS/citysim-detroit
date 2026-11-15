"""Accuracy check: ask residents survey statements with a known real answer and compare.

    python -m residents.calibrate --model us.amazon.nova-2-lite-v1:0 --per-district 200 [--card base|tier1]

For each check in CHECKS, residents answer support (agree) / neutral / oppose (disagree) to a statement. The
census-weighted share who agree is compared with the real share of Detroiters from the Detroit Metro Area
Communities Study (DMACS). Results are appended to residents/calibration_results.json, keyed by model and
persona card, and whatever the error is, it is stored and shown.

Limits, stated in the results file:
- The real values are the ones recorded in BACKEND_PLAN.md section 10 (DMACS waves 20 and 22). They were not
  re-read from the survey's topline PDFs when this was written.
- The survey asks questions with its own scales; here residents react to a statement, so "agree" stands in for
  the survey's positive answers. This is an approximation of the survey wording, not a copy of it.

Spending: calls go through shared.budget.converse. Set RUNS_TABLE to count them against the daily limit.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from residents import batch, prompt, validate

RESULTS = Path(__file__).parent / "calibration_results.json"
CHECKS = [   # real_pct and source: BACKEND_PLAN.md section 10
    {"id": "safe_walking", "label": "Feel somewhat or very safe walking in their neighborhood", "real_pct": 85, "source": "DMACS W22 Q76",
     "statement": "I feel somewhat or very safe walking in my neighborhood."},
    {"id": "neighborhood_satisfied", "label": "Somewhat, mostly or very satisfied with their neighborhood", "real_pct": 67, "source": "DMACS W22 Q11",
     "statement": "I am satisfied with my neighborhood as a place to live."},
    {"id": "right_direction", "label": "Detroit headed in the right direction", "real_pct": 55, "source": "DMACS W22 Q32",
     "statement": "Detroit is generally headed in the right direction."},
    {"id": "used_transit", "label": "Used public transportation in Detroit in the past year", "real_pct": 32, "source": "DMACS W20 Q80",
     "statement": "I have used public transportation in Detroit in the past year."},
]
SYSTEM = (
    "You simulate Detroit residents answering one survey statement. Answer separately for each resident, as that specific "
    "person would, based only on their traits. For each resident give: stance (support = agree, neutral = neither or not "
    "sure, oppose = disagree) and the single closest reason from the allowed list. Do not invent facts or numbers beyond "
    "what is given. Return a JSON array only."
)


def message(personas: list[dict], statement: str) -> str:
    lines = ["Residents:"] + [f"- [{p['persona_id']}] {prompt.persona_line(p)}" for p in personas]
    lines += ["", prompt.CALIBRATION_TEMPLATE.format(statement=statement), "",
              f"Allowed stances: {', '.join(prompt.STANCES)}", f"Allowed reasons: {', '.join(prompt.REASONS)} (use 'none' only with neutral)",
              "Reply with a JSON array, one object per resident, in the same order:", '{"persona_id": "...", "stance": "...", "reason": "..."}']
    return "\n".join(lines)


def ask(client, model: str, run_id: str, personas: list[dict], statement: str) -> dict:
    from shared import budget

    for attempt in range(5):
        try:
            resp = budget.converse(client, run_id, modelId=model, system=[{"text": SYSTEM}],
                                   messages=[{"role": "user", "content": [{"text": message(personas, statement)}]}],
                                   inferenceConfig={"maxTokens": 200 + 60 * len(personas)})
            break
        except budget.BudgetError:
            raise
        except Exception as e:
            if attempt == 4 or "Throttling" not in (type(e).__name__ + str(e)):
                raise
            time.sleep(2 ** attempt)
    ids, out = {p["persona_id"] for p in personas}, {}
    for item in batch.parse("".join(b.get("text", "") for b in resp["output"]["message"]["content"])):
        pid = item.get("persona_id") if isinstance(item, dict) else None
        if pid in ids and pid not in out:
            if item.get("reason") == "none" and item.get("stance") in ("support", "oppose"):
                item["reason"] = "access"            # only the stance is scored here; keep the answer valid
            if validate.check(item, ids, False) is None:
                out[pid] = item["stance"]
    return out


def run(model: str, per_district: int, card: str, personas_dir: str, workers: int = 8) -> dict:
    from shared.aws import bedrock_runtime

    os.environ["PERSONA_CARD"] = card
    people = []
    for d in range(1, 8):
        people += json.loads(Path(personas_dir, f"district_{d}.json").read_text())[:per_district]
    client, run_id = bedrock_runtime(), f"calibration-{int(time.time())}"
    groups = [people[i:i + 25] for i in range(0, len(people), 25)]
    weight = {p["persona_id"]: p["weight"] for p in people}
    checks, t0 = [], time.time()
    for c in CHECKS:
        with ThreadPoolExecutor(workers) as ex:
            answers = {}
            for part in ex.map(lambda g: ask(client, model, run_id, g, c["statement"]), groups):
                answers.update(part)
        total = sum(weight[i] for i in answers)
        share = {s: round(100 * sum(weight[i] for i, v in answers.items() if v == s) / total, 1) for s in prompt.STANCES} if total else {}
        sim = share.get("support")
        checks.append({"id": c["id"], "label": c["label"], "real": c["real_pct"], "source": c["source"], "statement": c["statement"],
                       "simulated": sim, "error_pts": None if sim is None else round(sim - c["real_pct"], 1),
                       "neutral": share.get("neutral"), "disagree": share.get("oppose"), "answered": len(answers), "asked": len(people)})
        print(f"  {c['id']:<24} real {c['real_pct']:>3}%  simulated {sim}%  (neutral {share.get('neutral')}%, disagree {share.get('oppose')}%)  "
              f"answered {len(answers)}/{len(people)}")
    errs = [abs(c["error_pts"]) for c in checks if c["error_pts"] is not None]
    return {"model": model, "card": card, "prompt_version": "statement-v1", "residents": len(people), "per_district": per_district,
            "avg_error_pts": round(sum(errs) / len(errs), 1) if errs else None, "measured": bool(errs), "checks": checks,
            "run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "seconds": round(time.time() - t0),
            "limits": ["Real values are those recorded in BACKEND_PLAN.md section 10; not re-read from the survey PDFs.",
                       "Residents react to a statement; the survey uses its own questions and scales.",
                       "Residents were given their census traits only, with no facts about their neighborhood."]}


def load() -> list[dict]:
    return json.loads(RESULTS.read_text()) if RESULTS.exists() else []


def latest(model: str, card: str = "tier1") -> dict | None:
    """Most recent stored result for this model and card, in the run_result.calibration shape."""
    for r in reversed(load()):
        if r["model"] == model and r["card"] == card and r.get("measured"):
            return {"measured": True, "avg_error_pts": r["avg_error_pts"], "model": r["model"], "run_at": r["run_at"],
                    "checks": [{"label": c["label"], "real": c["real"], "simulated": c["simulated"], "error_pts": c["error_pts"]}
                               for c in r["checks"] if c["simulated"] is not None]}
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--per-district", type=int, default=200)
    ap.add_argument("--card", choices=["base", "tier1"], default="tier1")
    ap.add_argument("--personas", default="data/processed/personas")
    a = ap.parse_args()
    print(f"{a.model}, card {a.card}, {a.per_district} residents per district")
    result = run(a.model, a.per_district, a.card, a.personas)
    RESULTS.write_text(json.dumps(load() + [result], indent=1))
    print(f"  average error {result['avg_error_pts']} points -> {RESULTS.name}")


if __name__ == "__main__":
    main()
