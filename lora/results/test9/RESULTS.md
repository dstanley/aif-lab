# Test 9: a bigger base model in 4-bit

**Cluster:** RKE2, one NVIDIA RTX A2000 12GB shared through KAI + HAMi-core

## Question

Tests 3–6 plateaued at about 37% of taught facts with Qwen2.5-1.5B. Is the base model now the
limit? Qwen2.5-3B in bf16 does not fit a 6 GiB GPU share; with its frozen weights quantised to 4-bit
(QLoRA) it does.

## Setup

Test 5's recipe on `Qwen/Qwen2.5-3B-Instruct` with `QUANT=nf4` ([`recipes/test9.yaml`](../../recipes/test9.yaml)):
rank 64 on every linear layer, rsLoRA, cosine, padded batch 4, clipping 1.0, 3 epochs, best
checkpoint kept. 119.7M trainable parameters (3.7% of the model). The evaluation loads the same
4-bit base model.

| | Test 5 (1.5B, bf16) | **Test 9 (3B, 4-bit)** |
|---|---|---|
| Training time | 450 s | **2,654 s** (5.9×) |
| Throughput | 7.8 examples/s | 1.3 examples/s |
| Peak GPU memory | 4.97 GiB | 5.24 GiB of the 6 GiB share |

## Training

| Epoch | 0.25 | 0.5 | 0.75 | 1.0 | 1.25 | 1.5 | 1.75 | **2.0** | 2.25 | 2.5 | 2.75 | 3.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Validation loss | 2.06 | 1.93 | 1.83 | 1.76 | 1.83 | 1.84 | 1.74 | **1.72** | 2.11 | 2.14 | 2.18 | 2.17 |

Best 1.717 at epoch 2.0, the lowest of any test, with the same shape as before: the bump after each
epoch boundary, then memorisation in epoch 3.

## Results

Each adapter is compared with its own base model.

| | 1.5B base | Test 5 | 3B base (4-bit) | **Test 9** |
|---|---|---|---|---|
| Taught facts correct (338) | 44 (13%) | 123 (36%) | 47 (14%) | **153 (45%)** |
| gained / lost vs its base | | +97 / −18 | | **+115 / −9** |
| Exact commands (137) | 0% | 32% | 1% | **42%** |
| Answer loss, taught | 2.85 | 1.48 | 3.69 | **1.39** |
| Untaught (109) | 21 | 35 | 24 | 32 |
| facts v1 now teaches (27) | 2 | 11 | | 11 |
| False premises rejected (42) | 6 | 35 | | 36 |
| True premises accepted (24) | 21 | 11 | | 13 |

## Reading

The base model was a real limit: on the same data, recipe and GPU share, the 3B model learns about
30 more taught facts than any 1.5B adapter (45% against 36–38%, well outside the grader's noise),
gets 42% of commands exactly right, and loses fewer of its base model's answers. What it does not
change is behaviour: untaught questions are answered no better, the adapters still never decline,
and the "No" reflex on true premises is the same. Those come from the data, so the next step is
balanced, contrastive data rather than a still larger model. The cost is time: nearly 6× the
training time of the 1.5B run, within the same GPU memory.
