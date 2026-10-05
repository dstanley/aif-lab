# Teaching a small model SUSE facts on a shared GPU

A worked LoRA fine-tuning study on SUSE AI Factory: a 1.5B-parameter model, a 6 GiB share of one
GPU, a dataset drafted from SUSE's documentation, and an evaluation designed to tell learning apart
from style, guessing and reflexes. Each step changes one thing and records why.

**Status:** draft, local only. Tests 1–5 complete; 6 (DoRA) and 9 (Qwen2.5-3B, 4-bit) running.

## What's here

| Path | What |
|---|---|
| `docs/` | the tutorial (outline in `docs/outline.md`) |
| `data/v0/` | first dataset: ~700 facts stated once each (taught style, not facts) |
| `data/v1/` | 338 canonical facts, 3–4 independently worded training examples each, plus 66 premise corrections |
| `eval/` | four evaluation sets: **taught** (new wording of each v1 fact), **untaught** (v0's 109 questions, frozen), **false-premise** (42), **true-premise** (24, the control) |
| `scripts/` | `lora_train.py`, `lora_eval.py` (from the AI Factory SDK examples), `metrics.py` (extra measures from saved answers), `table.py` (the comparison table) |
| `harness/` | `run_test.py` (one test: train, four evaluations, fetch), `make_configmaps.sh`, `sync_results.py` |
| `results/` | every test: `training.json`, each evaluation's report, every answer graded, and a write-up |

## Results so far

```
python3 scripts/table.py
```

(The tutorial walks through these; `results/README.md` has the per-test summaries.)

## Running it

You need an AI Factory cluster with a training profile that gives a GPU share (these runs used 6 GiB
of an RTX A2000 12GB through KAI + HAMi-core), and the `rancher_ai` SDK from the aif repo.

```
export AIF_CONTEXT=<kubeconfig context> AIF_PROJECT=<project namespace> AIF_PROFILE=<training profile>
harness/make_configmaps.sh
PYTHONPATH=<aif>/sdk/python python3 harness/run_test.py test5 my-test5 suse-v1-train-next '{}'
```

## Before publishing

- The datasets paraphrase SUSE and upstream project documentation: check those licences.
- They were drafted by a model from the docs and are **not reviewed**; see each `data/*/notes/`.
