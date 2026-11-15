"""Questions the correction engine asks residents, beyond the first engine's stance and reason.

    ask_opponents(rows, personas, spec, places, run_id, per_call) -> [validated answers]
        Residents who opposed are asked the seven parked questions (residents/correction_questions.py).
        The sample is the opponents nearest to the proposal first, up to SAMPLE residents (a choice, BACKEND_PLAN 15.3).

    follow_up(variant, targets, personas, spec, places, change, run_id, per_call) -> [validated answers]
        After a rerun, residents who still oppose (or newly oppose) are asked why. Two wordings are kept side by
        side so they can be compared on the same residents (BACKEND_PLAN 15.14):
          "change"  short: why do you still oppose now that this was changed, and what one change would help
          "stance"  descriptive: explain your overall position, whether it depends on where it is, and whether any
                    version would be acceptable

Each resident is told the answers they already gave. Every call goes through shared.budget.converse.
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
FOLLOW_UP_VERSION = "fu-2026-11-15"
SYSTEM = ("You simulate Detroit residents who were asked about a proposed change in their city and said they oppose it. "
          "Answer the follow-up questions separately for each resident, as that specific person would, based only on their "
          "traits, their personal impact and the answer they already gave. Do not invent facts or numbers beyond what is given. "
          "Return a JSON array only.")
SCOPES = ["anywhere in the city", "only near my home"]
YES_NO = ["yes", "no"]
# variant -> [(answer field, question as asked, answer options or a character limit for free text)]
FOLLOW_UPS = {
    "change": [
        ("why", "This change was made and you oppose the proposal as it now stands. In one sentence (under 200 characters), why?", 200),
        ("would_change", "What one change would make you more supportive now?", q7.CHANGES),
    ],
    "stance": [
        ("explanation", "Explain your overall position on this proposal in two or three sentences (under 500 characters): "
                        "what you object to, and how the change that was made affected your view.", 500),
        ("scope", "Would you object to this proposal anywhere in the city, or only near your home?", SCOPES),
        ("acceptable_version", "Is there any version of this proposal you would accept?", YES_NO),
    ],
}


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


def follow_up_message(variant: str, group: list[dict], personas: dict, spec: dict, places: list[dict], change: str) -> str:
    """group: follow-up targets (core.follow_up_targets): persona_id, before, before_reason, after_reason, asked_for."""
    lines = [f"Proposed change, as now revised: {spec['summary']}", f"What was changed from the original version: {change}", "", "Residents:"]
    for t in group:
        p = personas[t["persona_id"]]
        lines.append(f"- [{t['persona_id']}] {prompt.persona_line(p)}")
        near, _ = proximity.lines_for(p, places)
        if near:
            lines.append("  Personal impact now: " + "; ".join(near))
        before = f"  Answer to the original version: {t['before']}" + (f", main reason: {t['before_reason']}" if t.get("before_reason") and t["before"] != "neutral" else "")
        if t.get("asked_for"):
            before += f". Asked what one change would make them more supportive, said: {t['asked_for']}"
        lines += [before, f"  Answer to the revised version: oppose, main reason: {t['after_reason']}"]
    lines += ["", "Questions for each resident:"]
    shape = ['"persona_id": "..."']
    for i, (field, text, opts) in enumerate(FOLLOW_UPS[variant], 1):
        lines.append(f"{i}. {text}" + (f" Options: {', '.join(opts)}." if isinstance(opts, list) else "") + f" -> {field}")
        shape.append(f'"{field}": "..."')
    lines += ["", "Reply with a JSON array, one object per resident, in the same order:", "{" + ", ".join(shape) + "}"]
    return "\n".join(lines)


def check_follow_up(variant: str, item: dict, ids: set[str]) -> str | None:
    if item.get("persona_id") not in ids:
        return "unknown persona_id"
    for field, _, opts in FOLLOW_UPS[variant]:
        v = item.get(field)
        if isinstance(opts, list):
            if v not in opts:
                return f"{field} not in list"
        elif not isinstance(v, str) or not v.strip() or len(v) >= opts:
            return f"{field} missing or too long"
    return None


def _ask_groups(groups: list[list[dict]], build, valid, run_id: str, tokens_each: int, client=None, table=None, at_once: int = 1) -> list[dict]:
    """One model call per group; keeps only valid items, one per resident."""
    from concurrent.futures import ThreadPoolExecutor
    from shared import budget
    from shared.aws import bedrock_runtime

    client = client or bedrock_runtime()
    model = os.environ.get("RESIDENT_MODEL_ID", "")

    def one(group):
        for attempt in range(7):
            try:
                resp = budget.converse(client, run_id, table, modelId=model, system=[{"text": SYSTEM}],
                                       messages=[{"role": "user", "content": [{"text": build(group)}]}],
                                       inferenceConfig={"maxTokens": 200 + tokens_each * len(group), "temperature": 0})
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
        return [i for i in items if isinstance(i, dict) and valid(i, ids) is None]

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


def ask_opponents(rows: list[dict], personas: dict, spec: dict, places: list[dict], run_id: str, per_call: int = 1,
                  client=None, table=None, at_once: int = 1) -> list[dict]:
    chosen = sample(rows)
    groups = [chosen[i:i + per_call] for i in range(0, len(chosen), per_call)]
    return _ask_groups(groups, lambda g: message(g, personas, spec, places), q7.check, run_id, 220, client, table, at_once)


def follow_up(variant: str, targets: list[dict], personas: dict, spec: dict, places: list[dict], change: str, run_id: str,
              per_call: int = 1, client=None, table=None, at_once: int = 1) -> list[dict]:
    groups = [targets[i:i + per_call] for i in range(0, len(targets), per_call)]
    return _ask_groups(groups, lambda g: follow_up_message(variant, g, personas, spec, places, change),
                       lambda item, ids: check_follow_up(variant, item, ids), run_id, 120 if variant == "change" else 260,
                       client, table, at_once)
