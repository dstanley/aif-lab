# Test 1: LoRA on SUSE dataset v0

**Cluster:** RKE2, one NVIDIA RTX A2000 12GB shared through KAI + HAMi-core

## Question

Can a small model, fine-tuned with LoRA on a shared GPU, visibly learn to answer SUSE questions
better?

## Setup

| | |
|---|---|
| Base model | Qwen/Qwen2.5-1.5B-Instruct (bf16) |
| Adapter | LoRA rank 16, alpha 32, dropout 0.05, on q/k/v/o projections |
| Training data | `suse-train.jsonl`, 701 examples, sha256 `0c6b4033e5e2…` (SUSE dataset v0, drafted from SUSE docs) |
| Training | 525 steps × batch 4 (3.0 epochs), seq 512, AdamW lr 2e-4 constant, loss on answers only (`MASK_PROMPT=1`) |
| Evaluation data | `suse-eval.jsonl`, 109 questions, sha256 `f8f10a09b42b…`; none appears in the training file |
| GPU | training on a 6 GiB share (peak 3.85 GiB), evaluation on 4 GiB (peak 3.15 GiB) |
| Runs | `dev-suse-lora` (training, 5¼ min), `dev-suse-eval` (evaluation, ~2 min of scoring) |
| Image | pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime; transformers 4.46.3, peft 0.13.2 |

Files here: `training.json` and `adapter_config.json` (from the adapter), `eval-report.json` (the
run's kept report), both runs' AIJob records (`*-aijob.yaml`), `run-output.log` (training steps,
the report, three side-by-side answers), `dataset-README.md`.

## Results

| | Base | Adapter |
|---|---|---|
| Answer loss (held out) | 2.809 | **2.454** (−12.6%) |
| Answer perplexity | 16.6 | **11.6** |
| Correct answers¹ | 19% | **23%** (+4 points) |
| Expected terms present | 21% | **25%** |
| Exact commands | 0% | 0% |

| Area | Base | Adapter |
|---|---|---|
| SUSE Rancher Prime | 3/18 | **5/18** |
| SUSE Security | 3/18 | **5/18** |
| RKE2 / K3s | 2/18 | **3/18** |
| SLES / Micro / BCI / AI | 3/19 | **4/19** |
| SUSE Storage | 3/18 | 2/18 |
| SUSE Virtualization | 7/18 | 6/18 |

¹ every `expect_any` term group satisfied, no `expect_none` term, and the `expect_command` verbatim.

Training loss was noisy and still about 2 at the end (1.2–2.8 per step over the last 300 steps).

## What the answers show

The adapter learned the dataset's **style**: short, direct, command first, SUSE vocabulary. It did
not reliably learn **facts**, and where it lacks one it answers confidently anyway:

- *"How can I follow the progress of a Rancher restore?"* The base model gives a long, generic
  `kubectl` walkthrough; the adapter gives one line with a command that does not exist (a
  `rancher-restore` deployment with a `progress` field).
- *"Which command shows whether the Rancher ingress has the right hostname?"* The adapter says the
  output "should show your SUSE Application Collection hostname", which is meaningless here.

## Why: the evaluation mostly asks about untaught facts

The evaluation questions were drafted as *different facts or situations* from the training set.
Measured afterwards:

- only **22 of 109** evaluation answers share most of their distinctive words with any training
  answer (by type: command 9/23, definition 4/18, procedure 3/12, recommendation 2/17,
  troubleshooting 2/23, architecture 2/16);
- **0 of 22** evaluation commands appear anywhere in the training data, so 0% on commands was
  guaranteed.

So test 1 measured mostly how the model behaves on facts it was **never taught**, where a
style-trained adapter invents plausible SUSE answers. It is a useful baseline for hallucination,
but not a measure of whether the adapter learned what it was shown.

## Next (test 2)

1. **Dataset v1:** about 250–350 canonical facts, each with 3–5 independently worded training
   examples; extra command examples (each command in several contexts); and negative examples
   ("that command does not exist; check …") so unknown → not invented.
2. **Two evaluation sets:**
   - *taught facts, new wording*: one held-back phrasing per canonical fact, which measures
     learning;
   - *untaught facts*: these 109 questions, frozen, which measure invention vs. "not sure".
3. **Scores by question type** as well as by area, and every answer saved, not only three.
4. **Training:** rank 32 including the feed-forward projections, warm-up + cosine schedule,
   validation loss per epoch with a checkpoint per epoch, so the best epoch can be chosen.
5. Later: a larger base model (Qwen2.5-3B with 4-bit QLoRA to fit the share), and LoRA + retrieval
   over the SUSE docs as the final comparison.
