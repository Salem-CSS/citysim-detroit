"""Ask residents who opposed a proposal the seven parked questions (residents/correction_questions.py).

    ask_opponents(rows, personas, spec, places, run_id, per_call) -> [validated answers]

The sample is the opponents nearest to the proposal first, up to SAMPLE residents (a choice, see BACKEND_PLAN 15.3).
Each resident is told the stance and reason they already gave. Every call goes through shared.budget.converse.
"""
from __future__ import annotations

import json
import os
import random
import re
import time

from engine import proximity
from residents import correction_questions as q7
from residents import prompt

SAMPLE = 200
SYSTEM = ("You simulate Detroit residents who were asked about a proposed change in their city and said they oppose it. "
          "Answer the follow-up questions separately for each resident, as that specific person would, based only on their "
          "traits, their personal impact and the answer they already gave. Do not invent facts or numbers beyond what is given. "
          "Return a JSON array only.")


def sample(rows: list[dict]) -> list[dict]:
    opp = [r for r in rows if r["stance"] == "oppose"]
    opp.sort(key=lambda r: (r.get("distance_m") is None, r.get("distance_m") or 0, r["persona_id"]))
    return opp[:SAMPLE]


def message(group: list[dict], personas: dict, spec: dict, places: list[dict]) -> str:
    lines = [f"Proposed change: {spec['summary']}", "", "Residents:"]
    for r in group:
        p = personas[r["persona_id"]]
        lines.append(f"- [{r['persona_id']}] {prompt.persona_line(p)}")
        near, _ = proximity.lines_for(p, places)
        if near:
            lines.append("  Personal impact: " + "; ".join(near))
        lines.append(f"  Already answered: oppose, main reason: {r['reason']}")
    lines += ["", "Questions for each resident:"] + q7.question_lines()
    lines += ["", "Reply with a JSON array, one object per resident, in the same order:",
              '{"persona_id": "...", "support": 1-5, "top_concern": "...", "top_benefit": "...", "daily_life": "...", '
              '"speak_likelihood": "...", "one_change": "...", "reaction": "..."}']
    return "\n".join(lines)


def ask_opponents(rows: list[dict], personas: dict, spec: dict, places: list[dict], run_id: str, per_call: int = 1,
                  client=None, table=None, at_once: int = 1) -> list[dict]:
    from concurrent.futures import ThreadPoolExecutor
    from shared import budget
    from shared.aws import bedrock_runtime

    client = client or bedrock_runtime()
    model = os.environ.get("RESIDENT_MODEL_ID", "")
    chosen = sample(rows)
    groups = [chosen[i:i + per_call] for i in range(0, len(chosen), per_call)]

    def one(group):
        for attempt in range(7):
            try:
                resp = budget.converse(client, run_id, table, modelId=model, system=[{"text": SYSTEM}],
                                       messages=[{"role": "user", "content": [{"text": message(group, personas, spec, places)}]}],
                                       inferenceConfig={"maxTokens": 200 + 220 * len(group), "temperature": 0})
                break
            except Exception as e:
                if "Throttling" not in type(e).__name__ and "Throttling" not in str(e) or attempt == 6:
                    raise
                time.sleep(min(2 ** attempt, 8) + random.random())
        text = "".join(b.get("text", "") for b in resp["output"]["message"]["content"])
        m = re.search(r"\[.*\]", text, re.S)
        try:
            items = json.loads(m.group(0)) if m else []
        except ValueError:
            items = []
        ids = {r["persona_id"] for r in group}
        return [i for i in items if isinstance(i, dict) and q7.check(i, ids) is None]

    if at_once > 1 and len(groups) > 1:
        with ThreadPoolExecutor(min(at_once, len(groups))) as ex:
            parts = list(ex.map(one, groups))
    else:
        parts = [one(g) for g in groups]
    seen, out = set(), []
    for part in parts:
        for item in part:
            if item["persona_id"] not in seen:
                seen.add(item["persona_id"])
                out.append(item)
    return out
