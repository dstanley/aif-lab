# Test 5: real batching (the baseline)

**Cluster:** RKE2, one NVIDIA RTX A2000 12GB shared through KAI + HAMi-core

## Question

Until now a "batch of 4" ran its four examples through the model one at a time, then took one
optimiser step. Can one padded forward pass per batch make training much faster without losing
quality?

## Setup

Test 3's recipe with `BATCH_MODE=padded` and gradient clipping at 1.0
([`recipes/test5.yaml`](../../recipes/test5.yaml)):

- each batch is one padded forward pass; examples of similar length are batched together (sorted
  within windows of 50 batches, then the batches shuffled), so little of each batch is padding;
- the loss is the mean over the batch's answer tokens, so every answer token counts equally
  (before, every example did): a small change to the objective, which is why this is a new baseline
  rather than a speed-up of test 3;
- all 3 epochs, keeping the checkpoint with the lowest validation loss.

## Training

| Epoch | 0.25 | 0.5 | 0.75 | 1.0 | 1.25 | 1.5 | 1.75 | **2.0** | 2.25 | 2.5 | 2.75 | 3.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Validation loss | 2.17 | 2.01 | 1.91 | 1.82 | 1.88 | 1.90 | 1.82 | **1.78** | 2.20 | 2.23 | 2.18 | 2.20 |

Best 1.778 at epoch 2.0, the lowest of any test. Gradient norms 2.4–3.0 before clipping.

| | Test 3 (one example at a time) | **Test 5 (padded)** |
|---|---|---|
| Training time | ~630 s | **450 s** |
| Throughput | 5.8 examples/s | 7.8 examples/s (1.4×; 2.3× with a rank-16 adapter) |
| Peak GPU memory | 4.45 GiB | 4.97 GiB |

Batch 8 does not fit the 6 GiB share at this adapter size: its first steps run out of memory on the
output scores (Qwen's vocabulary is about 152,000 tokens, so every padded position is costly).

## Results

| | Base | Test 3 | **Test 5** |
|---|---|---|---|
| Taught facts correct (338) | 44 | 130 | **123** |
| gained / lost vs base | | +101 / −15 | +97 / −18 |
| Exact commands (137) | 0% | 31% | **32%** |
| Untaught (109) | 21 | 36 | 35 |
| facts v1 now teaches (27) | 2 | 12 | 11 |
| False premises rejected (42) | 6 | 31 | 35 |
| True premises accepted (24) | 21 | 8 | 11 |
| Both premise sets (66) | 27 | 39 | 46 |

## Early stopping and the post-epoch bump

The first run of this test stopped early, at epoch 1.5, and kept its epoch-1 checkpoint: 74 taught
facts instead of 123 ([`test5-early-stop`](../test5-early-stop/README.md)). Validation rises for
about a quarter of an epoch after each epoch boundary, as the model starts its second pass over the
same facts, then falls below its previous best (1.82 → 1.90 → 1.78 here). With four checks an epoch,
a patience of three checks is shorter than that bump. Tests from here run all 3 epochs and keep the
best checkpoint (`PATIENCE=0`).

## Reading

A quality tie with test 3: the differences (130 vs 123 taught, 31% vs 32% commands) are within the
grader's noise of roughly ±5 questions. Test 5 is the baseline because it is as good and faster.
Optimising the training implementation mattered more here than a more sophisticated adapter method.
