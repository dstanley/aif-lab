# Tutorial outline (draft)

1. **The goal and the setup.** A SUSE assistant from a small model on a GPU share; why LoRA; the AI
   Factory pieces (training profile, AIJob, checkpoint volume, the SDK).
2. **A first try (test 1).** v0 data, a small adapter: answers look SUSE-like, facts don't stick, and
   the evaluation asked mostly about facts it was never taught.
3. **Building data that teaches facts (dataset v1).** Canonical facts × independent wordings; a held-out
   wording per fact; premise corrections; checks (overlap, commands verbatim).
4. **Measuring honestly.** Four evaluation sets and what each answers; partial credit for commands;
   regressions; the grader's limits (term matching: ±5 questions of noise).
5. **The ladder, one change at a time.**
   - test 2: better data, same adapter: facts start to stick (20%)
   - test 3: capacity (rank 64, all linear layers): 38%, exact commands 31%; overfits after epoch 2
   - test 4 / 4b: PiSSA initialisation: no gain; at a lower learning rate, learns less
   - test 5: real batching and clipping: same quality, 1.4× faster: the baseline
   - test 6: DoRA (pending)
   - test 9: a 3B model in 4-bit on the same share (pending)
6. **What went wrong, and what it taught.** PiSSA adapters saved for the wrong base; early stopping
   inside the post-epoch validation bump; the "No" reflex the premise corrections taught (the
   true-premise control).
7. **Next.** Knowledge-boundary data (answer vs decline), balanced yes/no premise data, preference
   tuning (DPO), and LoRA vs retrieval over the SUSE docs.
