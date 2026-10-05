"""Measures computed from a test's saved, graded answers, beyond lora_eval.py's own report:
declines, partial commands, gains and regressions, the frozen set split by what v1 teaches, and the
two premise sets (does the answer open by rejecting, or accepting, the question's premise?)."""
import json
import os
import re

from .paths import EVAL
from .records import read_jsonl

DECLINE = re.compile(r"not (?:a )?documented|isn'?t documented|no documented|(?:do not|don't) (?:have|know)|not sure|cannot confirm|can't confirm|"
                     r"not aware|no information|unable to (?:find|confirm)|check the (?:official )?(?:SUSE )?documentation", re.I)
# a premise is rejected when the answer's first sentence says it is wrong
REJECT = re.compile(r"^\W*(no\b|not\b|nope|there is no|there's no|there isn't|that is not|that's not|this is not|it is not|it isn't|incorrect|false|wrong)"
                    r"|\b(?:is|are|does|do|can|will|has|have)(?: not|n't)\b|\bnot (?:supported|documented|possible|correct|true|required)\b|"
                    r"\bno (?:such|documented)\b|\bcannot\b|\bcan't\b", re.I)
YES = re.compile(r"^\W*(yes|correct|right|that's right|that is right|exactly|true)\b", re.I)
NO = re.compile(r"^\W*(no\b|nope|not\b|incorrect|false|wrong|there is no|there's no|there isn't|that is not|that's not)", re.I)


def first_sentence(s):
    return re.split(r"(?<=[.!?])\s|\n", (s or "").strip(), maxsplit=1)[0]


def opening(s):
    """How an answer opens: yes, no, or neither."""
    return "yes" if YES.search(s or "") else "no" if NO.search(s or "") else "neither"


def rejects(s):
    return bool(REJECT.search(first_sentence(s)))


def _first_command(s):
    m = re.search(r"`([^`]+)`", s or "")
    return m.group(1) if m else ""


def partial_command(r, who):
    """Right tool and subcommand, wrong arguments: the reference's first command and the answer's share
    their first two words, but the answer was not graded correct."""
    ref, ans = _first_command(r["reference"]).split()[:2], _first_command(r[who]).split()[:2]
    return bool(ref) and ref == ans and not r[f"{who}_correct"]


def false_premise(rows):
    m = {}
    for who in ("base", "adapter"):
        rej = [rejects(r[who]) for r in rows]
        op = [opening(r[who]) for r in rows]
        kinds = {r["instruction"]: r.get("premise") for r in read_jsonl(os.path.join(EVAL, "false-premise.jsonl"))}
        m[who] = {"rejects_premise": sum(rej), "rejects_and_documented": sum(a and r[f"{who}_correct"] for a, r in zip(rej, rows)),
                  "opens": {k: op.count(k) for k in ("yes", "no", "neither")}, "of": len(rows)}
        for kind in ("contradicts", "invented"):
            m[who][kind] = f"{sum(a for a, r in zip(rej, rows) if kinds.get(r['instruction']) == kind)}/{sum(kinds.get(r['instruction']) == kind for r in rows)}"
    return m


def true_premise(rows):
    m = {}
    for who in ("base", "adapter"):
        rej = [rejects(r[who]) for r in rows]
        op = [opening(r[who]) for r in rows]
        m[who] = {"accepts_premise": sum(not x for x in rej), "accepts_and_documented": sum((not x) and r[f"{who}_correct"] for x, r in zip(rej, rows)),
                  "opens": {k: op.count(k) for k in ("yes", "no", "neither")}, "of": len(rows)}
    return m


def compute(test_dir):
    """The measures for one test directory (as written to its metrics.json)."""
    out = {}
    path = lambda s: os.path.join(test_dir, f"answers-{s}.jsonl")
    if os.path.exists(path("false-premise")):
        out["false-premise"] = false_premise(read_jsonl(path("false-premise")))
    if os.path.exists(path("true-premise")):
        out["true-premise"] = true_premise(read_jsonl(path("true-premise")))
    taught_flag = {r["instruction"]: r.get("v1_taught") for r in read_jsonl(os.path.join(EVAL, "untaught.jsonl"))}
    for label in ("taught", "untaught"):
        if not os.path.exists(path(label)):
            continue
        rows = read_jsonl(path(label))
        cmd = [r for r in rows if r["type"] == "command"]
        m = {}
        for who in ("base", "adapter"):
            m[who] = {"correct": sum(r[f"{who}_correct"] for r in rows), "of": len(rows),
                      "declines": sum(bool(DECLINE.search(r[who] or "")) for r in rows),
                      "partial_commands": sum(partial_command(r, who) for r in cmd), "commands": len(cmd)}
        m["regressions"] = sum(r["base_correct"] and not r["adapter_correct"] for r in rows)
        m["gains"] = sum(r["adapter_correct"] and not r["base_correct"] for r in rows)
        if label == "untaught":
            for flag in (True, False):
                sub = [r for r in rows if taught_flag.get(r["instruction"]) is flag]
                m[f"v1_taught={flag}"] = {who: sum(r[f"{who}_correct"] for r in sub) for who in ("base", "adapter")} | {"of": len(sub)}
            m["adapter_declines_on_still_untaught"] = sum(bool(DECLINE.search(r["adapter"] or "")) for r in rows if taught_flag.get(r["instruction"]) is False)
        out[label] = m
    return out


def write(test_dir):
    m = compute(test_dir)
    with open(os.path.join(test_dir, "metrics.json"), "w") as f:
        json.dump(m, f, indent=1)
    return m
