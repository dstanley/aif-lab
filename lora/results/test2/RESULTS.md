# Test 2: same adapter, better data (SUSE dataset v1)

**Cluster:** RKE2, one NVIDIA RTX A2000 12GB shared through KAI + HAMi-core

## Question

Test 1 learned style, not facts. With the adapter settings unchanged, does data built to teach
facts (each fact several ways, plus "not documented" examples) make the adapter learn them?

## Setup

Only the data changed from test 1.

| | |
|---|---|
| Base model | Qwen/Qwen2.5-1.5B-Instruct (bf16) |
| Adapter | LoRA rank 16, alpha 32, dropout 0.05, on q/k/v/o (as test 1) |
| Training data | `suse-train-v1.jsonl`, 1,306 examples on 338 facts, sha256 `1cf0058b922a…`; 131 phrasings held out for validation, 1,175 trained on |
| Training | 882 steps × batch 4 (3 epochs), seq 512, AdamW lr 2e-4 constant, answers only; a checkpoint per epoch, best kept |
| Evaluation | **taught**: `suse-eval-taught.jsonl`, 338 questions, one new wording per fact · **untaught**: test 1's 109 questions, frozen |
| Libraries | transformers 4.51.3, peft 0.15.2, datasets 3.5.0, accelerate 1.6.0 |
| Runs | `dev-suse-v1`, `dev-suse-v1-eval-taught`, `dev-suse-v1-eval-untaught` |

Files here: `training.json`, `adapter_config.json`, every answer from both evaluations
(`answers-*.jsonl`: base and adapter side by side, graded), the AIJob records, `run-output.log`.

## Training

| Epoch | Train loss | Validation loss |
|---|---|---|
| 1 | 2.22 | 2.10 |
| 2 | 1.85 | 2.00 |
| 3 | 1.52 | **1.98** (kept) |

Validation was still falling at epoch 3, but only just; train loss falling much faster says more
epochs would mostly memorise the phrasings.

## Results

| | Taught (338) base → adapter | Untaught (109) base → adapter | Test 1 (109) |
|---|---|---|---|
| Answer loss | 2.85 → **1.84** (−36%) | 2.81 → **2.30** (−18%) | 2.81 → 2.45 (−13%) |
| Correct answers | 13% → **20%** | 19% → **26%** | 19% → 23% |
| Expected terms | 17% → 28% | 21% → 30% | 21% → 25% |
| Exact commands | 0% → **11%** (15/137) | 0% → 9% (2/23) | 0% → 0% |
| Answer length (words) | 137 → 40 | 138 → 40 | |

Untaught set split by whether v1 now teaches the fact:

| | Base | Adapter |
|---|---|---|
| Fact now taught by v1 (27) | 2/27 | **9/27** |
| Still untaught (82) | 19/82 | 19/82 |

By area (taught set): Linux 5 → 14, RKE2/K3s 3 → 13, Security 11 → 15, Rancher 4 → 8,
Storage 9 → 10, **Virtualization 12 → 6** (worse). By type: commands 0 → 15, knowledge 30 → 38,
recommendation 7 → 10, troubleshooting 7 → 3 (worse).

## What the answers show

- **Facts are now being learned**, but not yet reliably: on taught facts with new wording, the
  adapter gets the exact command 11% of the time, and another 32 of 137 command answers use the
  right tool and subcommand with the wrong arguments. All 9 gains on the untaught set are facts v1
  teaches; on the 82 still-untaught questions the adapter is no better than the base model.
- **It still invents rather than declining.** The 66 negative examples were not enough: on 109
  untaught questions it never says something is not documented. Typical failures are confident and
  wrong, sometimes mixing products: a SUSE Virtualization control-plane check answered with
  `kubectl get nodes -n longhorn-system` and a Rancher `helm install`; "SUSE Storage does not
  support multiple NVMe devices per node".
- **Virtualization "got worse" (12 → 6), but none of it is lost knowledge.** Read one by one, the
  8 questions the base model passed and the adapter failed are:
  - 7 where the base answer is long and generic (once plainly wrong: "Yes, it is generally acceptable"
    to run production Rancher in one Docker container) and passes only because the term check found a
    word such as `affinity`, `Manual` or `2`; the adapter's short answer is wrong, usually invented;
  - 1 where the adapter is right ("No … three or more in high availability mode") and fails only
    because the check wanted `high-availability` with a hyphen.

  So the grader rewards long answers that touch the right words, and the adapter is not better than
  the base model on facts it hasn't learned; it is shorter and more confident. One answer also mixes
  products (a Rancher secret and `helm upgrade` for a SUSE Virtualization import).

## Further measures (`../metrics.py`, from the saved answers)

| | Taught: base | Taught: adapter | Untaught: base | Untaught: adapter |
|---|---|---|---|---|
| Correct | 44/338 | **66/338** | 21/109 | **28/109** |
| Gained / lost vs base | | +41 / −19 | | +14 / −7 |
| Partial commands (right tool and subcommand, wrong arguments) | 3/137 | **32/137** | 0/23 | 6/23 |
| Declines ("not documented", "not sure", …) | 9 | 4 | 3 | **0** |

On the 82 questions v1 still doesn't teach the adapter declines **0** times. That is what the data
teaches: all 66 negative examples correct a **false premise** ("There is no `rancher-restore`
deployment …; use …"); none declines a real question the model doesn't know. And the taught
evaluation set has no false-premise questions, so the one thing the negatives teach is not measured.

## Reading

Data was the right first lever, and the cleanest evidence is the frozen set: on the 27 questions
whose facts v1 now teaches, 2 → 9 correct; on the 82 it doesn't, 19 → 19. The gain is the new
facts, not a general effect. The model is learning them, partly (32 more commands with the right
tool), but not precisely enough to reproduce them reliably from a new wording. Whether that is the
adapter's capacity, the examples' variety or the grader's strictness is what test 3 starts to answer.

## Next (test 3: E1)

- Same v1 data and evaluations; `LORA_TARGETS=all-linear`, `LORA_R=64`, `RSLORA=1`, cosine
  schedule with 5% warm-up, 3 epochs. One change of kind (capacity), so the comparison stays clean.
- Then PiSSA initialisation (E2) in place of EVA: EVA read its batches in 100 s but then ran for
  55 minutes without finishing on this GPU share, so it is not practical here.
- Abstention needs its own work: more negative examples, and a check in the evaluation for
  "declined" vs "invented" on untaught questions.
