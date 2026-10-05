# Test 6: DoRA

**Cluster:** RKE2, one NVIDIA RTX A2000 12GB shared through KAI + HAMi-core

## Question

DoRA splits each weight update into a magnitude and a direction and learns them separately, which
its paper reports closes part of the gap to full fine-tuning. Does a more expressive adaptation
method beat plain LoRA here?

## Setup

Test 5 with `DORA=1` ([`recipes/test6.yaml`](../../recipes/test6.yaml)): 74.5M trainable parameters
(the magnitudes add 0.6M), all 3 epochs, the best checkpoint kept.

## Training

| Epoch | 0.25 | 0.5 | 0.75 | 1.0 | 1.25 | 1.5 | 1.75 | **2.0** | 2.25 | 2.5 | 2.75 | 3.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Validation loss | 2.17 | 2.01 | 1.91 | 1.83 | 1.89 | 1.91 | 1.82 | **1.79** | 2.21 | 2.25 | 2.20 | 2.22 |

Almost the same curve as test 5's (best 1.785 against 1.778), at a fraction of the speed:

| | Test 5 | **Test 6 (DoRA)** |
|---|---|---|
| Training time | 450 s | **2,091 s** (4.6×) |
| Throughput | 7.8 examples/s | 1.7 examples/s |
| Peak GPU memory | 4.97 GiB | 4.98 GiB |

## Results

| | Base | Test 5 | **Test 6** |
|---|---|---|---|
| Taught facts correct (338) | 44 | 123 | **122** |
| Exact commands (137) | 0% | 32% | 33% |
| Untaught (109) | 21 | 35 | 33 |
| facts v1 now teaches (27) | 2 | 11 | 13 |
| False premises rejected (42) | 6 | 35 | 34 |
| True premises accepted (24) | 21 | 11 | 10 |

## Reading

The same quality at 4.6 times the training time, and its evaluations are slower too. At this scale
DoRA is not worth its cost. With tests 3–6 the adapter knobs have plateaued: rank 64 on every layer
with the default start is as good as anything tried.
