# Test 4: PiSSA initialisation

**Cluster:** RKE2, one NVIDIA RTX A2000 12GB shared through KAI + HAMi-core

## Question

Test 3's adapter starts the usual way: one LoRA matrix random, the other zero, so training begins
from the base model. PiSSA instead starts the adapter from the base weights' principal directions
(their largest singular vectors) and trains on the residual. Does that smarter start learn a better
adapter?

## Setup

Test 3's recipe with one change, `LORA_INIT=pissa` ([`recipes/test4.yaml`](../../recipes/test4.yaml)),
validated four times an epoch and stopped after 3 checks without a gain of 0.005.

| | |
|---|---|
| Adapter | rank 64 on every linear layer, rsLoRA, scale 2; 73.9M trainable parameters |
| Saved as | a plain LoRA adapter of rank 128 for the original model (see "Saving PiSSA" below) |
| Training | 552 s, 5.8 examples/s, peak 4.45 GiB of the 6 GiB share; stopped early at step 803 of 882 |

## Training

| Epoch | 0.25 | 0.5 | 0.75 | 1.0 | 1.25 | 1.5 | 1.75 | **2.0** | 2.25 | 2.5 | 2.75 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Validation loss | 2.51 | 2.34 | 2.17 | 2.06 | 2.13 | 2.06 | 1.93 | **1.88** | 2.21 | 2.24 | 2.24 |

Best 1.878 at epoch 2.0, against 1.791 for test 3. Gradient norms of 10–20 throughout, against
2–3 for the default start (test 5): a property of PiSSA's start in the large principal directions, not
instability (test 4b shows the same at a tenth of the learning rate). Note the rise after each epoch
boundary (2.06 → 2.13 at 1.25) before validation falls again: it matters in test 5.

## Results

| | Base | Test 3 | **Test 4** |
|---|---|---|---|
| Taught facts correct (338) | 44 | 130 | **125** |
| gained / lost vs base | | +101 / −15 | +92 / −11 |
| Exact commands (137) | 0% | 31% | 29% |
| Untaught (109) | 21 | 36 | 27 |
| facts v1 now teaches (27) | 2 | 12 | 9 |
| False premises rejected (42) | 6 | 31 | 36 |
| True premises accepted (24) | 21 | 8 | **5** |
| Both premise sets (66) | 27 | 39 | 41 |

On 24 true statements phrased as "…, correct?", the adapter opens with "No" on 19 and often goes on
to restate the true fact ("No. Deleting a registered cluster disconnects it… The cluster stays
up."). The reflex is stronger than test 3's.

## Saving PiSSA

PiSSA trains on a residual base (the original weights minus the adapter's starting value). An
adapter saved as trained only works on that residual, and PEFT recomputes the residual when it
loads one, with a randomised decomposition that does not match training's: the first evaluation of
this test loaded garbage (see [`test4-invalid-save`](../test4-invalid-save/README.md)).
`lora_train.py` therefore converts every save into a plain LoRA adapter for the original model:
the trained update minus the starting one, as a single adapter of twice the rank, with alpha scaled
so the effective scale is unchanged. It does the conversion on the CPU; PEFT's own conversion loads a
second adapter on the GPU, which ran a 6 GiB share out of memory.

## Reading

No gain from PiSSA at this learning rate: validation, taught facts and exact commands are a little
worse than test 3, the untaught set clearly so, and the "No" reflex stronger.
