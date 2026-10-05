# Test 4, first run: evaluation invalid

PiSSA (test 3's recipe, `LORA_INIT=pissa`). Training is valid: best validation loss 1.880 at epoch
2.0 (test 3: 1.791), gradient norms 10–20 against about 1 for test 3's default start, stopped early
at step 730. The **evaluation is not**: `lora_train.py` saved the PiSSA adapter as trained, which
only works on the residual base model PiSSA trains on; `lora_eval.py` loaded it on the original
model, where PEFT recomputed PiSSA's randomised decomposition, so both the "base" model (loss 18,
gibberish) and the adapter were broken. Fixed in `lora_train.py` (every save converts the adapter to
a plain rank-128 LoRA for the original model); test 4 was rerun.
