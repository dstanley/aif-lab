# Test 3: high-capacity adapter on dataset v1

**Date:** 2026-10-05 · **Cluster:** lab RKE2, one NVIDIA RTX A2000 12GB shared through KAI + HAMi-core

## Question

Test 2 learned v1's facts partly (20% of taught facts). Is the adapter's capacity the limit?

## Setup

Data and evaluations as test 2. A "high-capacity recipe", not one change: several settings move
together, so a gain can't be pinned on any one of them.

| | Test 2 | Test 3 |
|---|---|---|
| Layers adapted | attention (q, k, v, o) | **all linear**: attention + MLP (gate, up, down) |
| Rank | 16 | **64** |
| Scaling | standard, alpha 32 → scale 32/16 = 2 | **rsLoRA**, alpha 16 → scale 16/√64 = 2 (kept equal on purpose) |
| Schedule | constant 2e-4 | **cosine** 2e-4, 5% warm-up |
| Initialisation | default (gaussian) | default (gaussian) |
| Trainable parameters | 4.4M (0.27%) | **73.9M (4.57%)**; three quarters of them in the MLP |
| Peak GPU memory | | 4.45 GiB of the 6 GiB share |
| Training time | | 10½ min (882 steps) |

## Training

| Epoch | Train loss | Validation loss |
|---|---|---|
| 1 | 2.06 | 1.85 |
| **2** | **1.09** | **1.79** (kept) |
| 3 | 0.40 | 2.15 |

Test 2's best validation loss was 1.98. The larger adapter reaches a better solution (1.79), then
memorises in epoch 3 (training loss −63%, validation +20%). The run kept epoch 2, so this argues for
early stopping, not for a smaller adapter. Validation once an epoch is too coarse to find the best
point; from test 4, `lora_train.py` validates four times an epoch and stops early (`PATIENCE`).

## Results (evaluation of the epoch-2 adapter)

| | Base | Test 2 | **Test 3** |
|---|---|---|---|
| **Taught facts** correct (338) | 13% | 20% | **38%** |
| gained / lost vs base | | +41 / −19 | **+101 / −15** |
| Exact commands (137) | 0% | 11% | **31%** |
| Partial commands (right tool and subcommand) | 3 | 32 | 16 (many now exact) |
| Answer loss, taught | 2.85 | 1.84 | **1.49** |
| **Untaught** (109) correct | 19% | 26% | **33%** |
| facts v1 now teaches (27) | 2 | 9 | **12** |
| facts still untaught (82) | 19 | 19 | 24 (mostly grader noise, see below) |
| Declines on untaught questions | 3 | 0 | 0 |

By area (taught): every area improves, and SUSE Virtualization's apparent regression in test 2
reverses (base 12, test 2 6, test 3 **21** of 53), consistent with it having been mostly grader noise.

### False premises (42 questions, new, none taught)

Questions that rest on a wrong premise: 24 contradict a v1 fact, 18 name an invented command or
setting. The 66 negative examples in v1 all correct false premises, so this measures what they were
built to teach.

| | Base | Test 2 | **Test 3** |
|---|---|---|---|
| Rejects the premise (first sentence) | 6 | 26 | **31** |
| contradicts a fact (24) | 3 | 17 | 19 |
| invented command or setting (18) | 3 | 9 | 12 |
| Rejects **and** gives the documented answer | 2 | 8 | **14** |
| Opens with "Yes" / "No" / neither | 19 / 3 / 20 | 8 / 19 / 15 | 4 / 29 / 9 |

The negatives work at their job, and generalise to premises they never mention. But "No" often
comes with wrong reasoning (one answer recommends `apk` for a SUSE image), so the stricter number,
rejects and documented, is the honest one. A true-premise control (24 true statements phrased the
same way) checks whether the adapter has simply learned to answer "…, correct?" with "No";
results in test 4's write-up.

## Grader notes

- The 9 still-untaught questions the adapter now passes: about 4 are right (one is a fact v1 does
  teach that the `v1_taught` mark missed), about 5 pass on a checked word in a wrong answer. So
  term-matching has noise of roughly ±5 questions on this set; differences that small need a better
  grader (a model-based judge) before they mean anything.
- Test 2's Virtualization "regression" was the same effect the other way round (base answers long
  and generic, passing on a word).

## Reading

Capacity was a real limit: the same data with a larger adapter, reaching into the MLP layers, nearly
doubles taught-fact accuracy (20% → 38%) and triples exact commands (11% → 31%). The gain is
on facts the data teaches; on untaught facts the adapter still invents and never declines, which is
what v1 teaches (it has no "I don't know" examples). Premise correction, which v1 does teach, works.
