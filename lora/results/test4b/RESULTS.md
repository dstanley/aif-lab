# Test 4b: PiSSA at a lower learning rate

**Cluster:** RKE2, one NVIDIA RTX A2000 12GB shared through KAI + HAMi-core

## Question

The PiSSA paper fine-tunes at a learning rate about ten times lower than test 3's 2e-4. Was test 4
a fair test of PiSSA?

## Setup

Test 4 with `LR=2e-5` ([`recipes/test4b.yaml`](../../recipes/test4b.yaml)). Training 503 s, stopped
early at step 730; peak 4.45 GiB.

## Training

| Epoch | 0.25 | 0.5 | 0.75 | 1.0 | 1.25 | 1.5 | 1.75 | **2.0** | 2.25 | 2.5 |
|---|---|---|---|---|---|---|---|---|---|---|
| Validation loss | 2.22 | 2.11 | 2.03 | 1.96 | 1.96 | 1.94 | 1.89 | **1.87** | 1.93 | 1.92 |

Best 1.867 at epoch 2.0. Gradient norms stay at 12–18, as in test 4: the large norms come from
PiSSA's start, not from the learning rate.

## Results

| | Base | Test 4 (2e-4) | **Test 4b (2e-5)** |
|---|---|---|---|
| Taught facts correct (338) | 44 | 125 | **83** |
| Exact commands (137) | 0% | 29% | 15% |
| Untaught (109) | 21 | 27 | 31 |
| False premises rejected (42) | 6 | 36 | 24 |
| True premises accepted (24) | 21 | 5 | **20** |
| Both premise sets (66) | 27 | 41 | **44** |

## Reading

At its paper's rate PiSSA learns much less (83 taught facts against 125), and so picks up much less
of the "No" reflex: it accepts 20 of 24 true premises, close to the base model's 21. The reflex
comes with learning, so a lower learning rate is not a fix; the fix belongs in the data.
