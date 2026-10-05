# LoRA testing: a SUSE assistant on a shared GPU

Can a small model, fine-tuned with LoRA on an AI Factory GPU share, visibly learn to answer SUSE
questions better? Each test is a folder with its configuration, records and results.

| Test | Data | Training | Correct (base → adapter) | Answer loss (base → adapter) | Notes |
|---|---|---|---|---|---|
| [test1](test1/RESULTS.md) | dataset v0, 701 examples | Qwen2.5-1.5B, LoRA r16 attention, 3 epochs | 19% → 23% | 2.81 → 2.45 | learned style, not facts; eval mostly untaught facts |
| [test2](test2/RESULTS.md) | dataset v1, 1,306 examples on 338 facts | as test 1 | taught 13% → 20%, untaught 19% → 26% | taught 2.85 → 1.84, untaught 2.81 → 2.30 | facts start to stick (commands 0% → 11%); still invents, never declines |

Pipeline: `sdk/python/examples/lora_train.py` and `lora_eval.py` in the aif repo, run as AIJobs
from the "GPU Development (shared GPU)" profile, with the dataset in a ConfigMap. Each adapter
carries a `training.json`; each evaluation's report is kept in its AIJob (`status.report`).

From test 2, two evaluation sets: **taught** (one new wording of each fact the data teaches: did it
learn?) and **untaught** (test 1's 109 questions, frozen: does it invent?). Datasets:
`~/Downloads/suse-dataset` (v0) and `~/Downloads/suse-dataset-v1`.
