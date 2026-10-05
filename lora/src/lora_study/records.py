"""Reading the study's files: JSON Lines datasets, and a test's saved records."""
import json
import os

from .paths import RESULTS


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


EVAL_SETS = ("taught", "untaught", "false-premise", "true-premise")


def load_test(name, results=RESULTS):
    """Everything a test left behind: training.json, each evaluation's report and graded answers, metrics."""
    d = os.path.join(results, name)
    answers = {s: read_jsonl(os.path.join(d, f"answers-{s}.jsonl")) for s in EVAL_SETS if os.path.exists(os.path.join(d, f"answers-{s}.jsonl"))}
    return {"name": name, "dir": d, "training": read_json(os.path.join(d, "training.json"), {}),
            "reports": {s: read_json(os.path.join(d, f"eval-{s}.json"), {}) for s in EVAL_SETS},
            "answers": answers, "metrics": read_json(os.path.join(d, "metrics.json"), {})}


def tests(results=RESULTS):
    """The tests with results, in order (test1, test2, ..., test4b, ...)."""
    import re
    names = [n for n in os.listdir(results) if n.startswith("test") and os.path.isdir(os.path.join(results, n))]
    key = lambda n: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", n)]
    return sorted(names, key=key)
