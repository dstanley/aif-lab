# Overnight notes (2026-10-05), raw, for the summary

- 23:08 test 4 first run: evaluation invalid (PiSSA adapter saved for the residual base). Kept in test4-invalid-save/.
- PEFT's GPU-side PiSSA conversion ran a training run out of memory at its first save (6 GiB share): replaced by a CPU-side
  conversion in lora_train.py (s(BA - B0A0) as one adapter of rank 2r, alpha scaled to keep the effective scale). Verified:
  base loss normal (2.65), adapter better (2.11) after 73 steps. Converted adapter is 564 MiB (fp32, rank 128): evaluations now 6 GiB.
- PiSSA's gradient norms (10-22) are the same at lr 2e-4 and 2e-5: a property of PiSSA, not instability.
- A Longhorn checkpoint volume once took 10 min to attach ("not ready for workloads"); runs waited it out.
- 00:48 test 4 (PiSSA, test 3's recipe, early stopping): best val 1.878 @ epoch 2.0 (test 3 1.791); stopped early at 803.
  taught 125/338 (test 3 130), untaught 27/109 (test 3 36), fp rejects 36/42, rejects+documented 14 (= test 3).
- TRUE-PREMISE CONTROL (24 true statements, same phrasing): base accepts 21 (19 documented), opens Yes 22 / No 2.
  Test 4 adapter accepts 5, opens No 19 / Yes 5, often then restates the true fact. The negatives taught a "No." reflex
  to "..., correct?" questions, not premise checking. False-premise gains are mostly that reflex.
- True-premise opens "No" (of 24): base 2, test 2 10, test 3 16, test 4 19. Accepts: base 21, test 2 14, test 3 8, test 4 5.
  The reflex grows with adapter capacity.
- 01:54 test 4b (PiSSA, lr 2e-5): best val 1.867 @ 1.99, stopped 730. taught 83, untaught 31, fp rej+doc 9,
  true-premise opens No 4 / Yes 15. Less learning, much less reflex: the reflex comes with learning, so fix it in the data.
  Best recipe stays test 3 (default init, 2e-4); test 5 runs on it.
- 02:54 test 5 (padded batch 4 + clip 1.0, PATIENCE=3): stopped early at epoch 1.49 inside a post-epoch validation bump;
  best epoch 0.99 val 1.822; taught 74 only. Kept as test5-early-stop/. Validation rises for ~a quarter epoch after each
  epoch boundary, then falls (test 4: 2.06 @1.0, 2.13 @1.24, 1.88 @2.0): PATIENCE=3 at 4 checks/epoch is too short.
  Padded throughput at r64 all-linear: 8.1 vs 5.8 examples/s (1.4x; 2.3x at r16). Gradient norms 2.4-3.0 (clipped at 1.0).
- 02:59 batch-8 probe: out of GPU memory at step 4 (a 688 MiB logits allocation) on the 6 GiB share. Batch 4 is the limit at r64.
- 03:00 tests 5, 6, 9 requeued with PATIENCE=0 (3 epochs, best checkpoint kept).
- 03:35 test 5 (padded batch 4 + clip 1.0, PATIENCE=0): best val 1.778 @ 1.99 (test 3 1.791); taught 123 (+97 -18), exact
  commands 32% (test 3 31%), untaught 35, fp rej+doc 18 (14), true-premise opens No 13 (16). Training 450 s vs ~630 s.
  Equivalent to test 3 within grader noise, 1.4x faster: the new baseline.
