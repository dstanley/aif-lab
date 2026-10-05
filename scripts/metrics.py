"""Extra measures from a test's saved answers: declines, partial commands, regressions, newly taught subset."""
import json, re, sys
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = sys.argv[1]
DECLINE = re.compile(r"not (?:a )?documented|isn'?t documented|no documented|(?:do not|don't) (?:have|know)|not sure|cannot confirm|can't confirm|not aware|no information|unable to (?:find|confirm)|check the (?:official )?(?:SUSE )?documentation", re.I)
first = lambda s: (re.search(r"`([^`]+)`", s or "") or [None, ""])[1]
def partial(r, who):
    ref, ans = first(r["reference"]).split()[:2], first(r[who]).split()[:2]
    return bool(ref) and ref == ans and not r[f"{who}_correct"]
untaught_flags = {json.loads(l)["instruction"]: json.loads(l).get("v1_taught") for l in open(os.path.join(ROOT, "eval", "untaught.jsonl"))}
# a premise is rejected when the answer's first sentence says it is wrong
REJECT = re.compile(r"^\W*(no\b|not\b|nope|there is no|there's no|there isn't|that is not|that's not|this is not|it is not|it isn't|incorrect|false|wrong)"
                    r"|\b(?:is|are|does|do|can|will|has|have)(?: not|n't)\b|\bnot (?:supported|documented|possible|correct|true|required)\b|\bno (?:such|documented)\b|\bcannot\b|\bcan't\b", re.I)
first_sentence = lambda s: re.split(r"(?<=[.!?])\s|\n", (s or "").strip(), maxsplit=1)[0]
def false_premise(rows):
    m = {}
    for who in ("base", "adapter"):
        rej = [bool(REJECT.search(first_sentence(r[who]))) for r in rows]
        op = [opening(r[who]) for r in rows]
        m[who] = {"rejects_premise": sum(rej), "rejects_and_documented": sum(a and r[f"{who}_correct"] for a, r in zip(rej, rows)),
                  "opens": {k: op.count(k) for k in ("yes", "no", "neither")}, "of": len(rows)}
        for kind in ("contradicts", "invented"):
            m[who][kind] = f"{sum(a for a, r in zip(rej, rows) if r.get('premise', premises.get(r['instruction'])) == kind)}/{sum(premises.get(r['instruction']) == kind for r in rows)}"
    return m
YES = re.compile(r"^\W*(yes|correct|right|that's right|that is right|exactly|true)\b", re.I)
NO = re.compile(r"^\W*(no\b|nope|not\b|incorrect|false|wrong|there is no|there's no|there isn't|that is not|that's not)", re.I)
opening = lambda s: "yes" if YES.search(s or "") else "no" if NO.search(s or "") else "neither"
def true_premise(rows):
    m = {}
    for who in ("base", "adapter"):
        rej = [bool(REJECT.search(first_sentence(r[who]))) for r in rows]
        op = [opening(r[who]) for r in rows]
        m[who] = {"accepts_premise": sum(not x for x in rej), "accepts_and_documented": sum((not x) and r[f"{who}_correct"] for x, r in zip(rej, rows)),
                  "opens": {k: op.count(k) for k in ("yes", "no", "neither")}, "of": len(rows)}
    return m
import os
premises = {}
if os.path.exists(os.path.join(ROOT, "eval", "false-premise.jsonl")):
    premises = {json.loads(l)["instruction"]: json.loads(l)["premise"] for l in open(os.path.join(ROOT, "eval", "false-premise.jsonl"))}
out = {}
if os.path.exists(f"{D}/answers-false-premise.jsonl"):
    out["false-premise"] = false_premise([json.loads(l) for l in open(f"{D}/answers-false-premise.jsonl")])
if os.path.exists(f"{D}/answers-true-premise.jsonl"):
    out["true-premise"] = true_premise([json.loads(l) for l in open(f"{D}/answers-true-premise.jsonl")])
for label in ("taught", "untaught"):
    rows = [json.loads(l) for l in open(f"{D}/answers-{label}.jsonl")]
    cmd = [r for r in rows if r["type"] == "command"]
    m = {}
    for who in ("base", "adapter"):
        m[who] = {"correct": sum(r[f"{who}_correct"] for r in rows), "of": len(rows),
                  "declines": sum(bool(DECLINE.search(r[who] or "")) for r in rows),
                  "partial_commands": sum(partial(r, who) for r in cmd), "commands": len(cmd)}
    m["regressions"] = sum(r["base_correct"] and not r["adapter_correct"] for r in rows)
    m["gains"] = sum(r["adapter_correct"] and not r["base_correct"] for r in rows)
    if label == "untaught":
        for flag in (True, False):
            sub = [r for r in rows if untaught_flags.get(r["instruction"]) is flag]
            m[f"v1_taught={flag}"] = {who: sum(r[f"{who}_correct"] for r in sub) for who in ("base", "adapter")} | {"of": len(sub)}
        m["adapter_declines_on_still_untaught"] = sum(bool(DECLINE.search(r["adapter"] or "")) for r in rows if untaught_flags.get(r["instruction"]) is False)
    out[label] = m
json.dump(out, open(f"{D}/metrics.json", "w"), indent=1)
print(json.dumps(out, indent=1))
