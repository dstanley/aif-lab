# Test 5, first run: stopped too early

Test 5's recipe with early stopping at a patience of 3 validation checks (four checks an epoch).
Validation rose after the first epoch boundary (1.82 at epoch 1.0, 1.88 at 1.25, 1.90 at 1.5) and
the run stopped at epoch 1.5, keeping its epoch-1 checkpoint (validation 1.822): 74 of 338 taught
facts correct, against 123 when the same recipe runs all 3 epochs. That rise is a short bump after
each epoch boundary, not overfitting; see [test 5](../test5/RESULTS.md). Kept as a record of why
the later tests run with `PATIENCE=0` (all epochs, best checkpoint kept).
