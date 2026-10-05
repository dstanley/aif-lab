# Results

One folder per test. Each has a write-up (`RESULTS.md`) and the records it is based on.

| Test | Question | Answer |
|---|---|---|
| [test1](test1/RESULTS.md) | Can a small LoRA on a GPU share visibly improve SUSE answers? | style yes, facts barely: 19% → 23% on mostly untaught facts |
| [test2](test2/RESULTS.md) | Is better training data alone enough to make facts stick? | facts start to stick: 13% → 20% taught, commands 0% → 11% |
| [test3](test3/RESULTS.md) | Is adapter capacity or coverage the bottleneck? | yes: 38% taught, 31% exact commands; overfits after epoch 2 |
| [test4](test4/RESULTS.md) | Does PiSSA initialisation learn a better adapter? | no: slightly worse, stronger "No" reflex |
| [test4b](test4b/RESULTS.md) | Does PiSSA do better at its paper's learning rate? | it learns much less (83 taught), and the reflex fades with it |
| [test5](test5/RESULTS.md) | Can real batching make training faster without losing quality? | yes: a quality tie with test 3, 1.4× faster; the baseline |
| [test6](test6/RESULTS.md) | Does DoRA beat plain LoRA? | no: the same quality at 4.6× the training time |
| [test9](test9/RESULTS.md) | Is the 1.5B base model the limit? | yes, for facts: Qwen2.5-3B in 4-bit on the same share learns 45% of taught facts, 42% exact commands; behaviour unchanged |

Two folders record runs that went wrong and why, kept because they explain the method:
[test4-invalid-save](test4-invalid-save/README.md) (a PiSSA adapter saved for the wrong base model)
and [test5-early-stop](test5-early-stop/README.md) (early stopping inside the post-epoch bump).

## The comparison

| test | recipe | best_val | taught | exact_commands | untaught | newly_taught | fp_rejected | tp_accepted | premises_both | train_s |
|---|---|---|---|---|---|---|---|---|---|---|
| base model | no adapter | - | 44/338 | 0% | 21/109 | 2/27 | 6/42 | 21/24 | 27/66 | - |
| test2 | r16 attention lr 0.0002 sequential | 1.978 | 66/338 | 11% | 28/109 | 9/27 | 26/42 | 14/24 | 40/66 | - |
| test3 | r64 all-linear rsLoRA lr 0.0002 sequential | 1.791 | 130/338 | 31% | 36/109 | 12/27 | 31/42 | 8/24 | 39/66 | - |
| test4 | r64 all-linear rsLoRA pissa lr 0.0002 sequential | 1.878 | 125/338 | 29% | 27/109 | 9/27 | 36/42 | 5/24 | 41/66 | 552 |
| test4b | r64 all-linear rsLoRA pissa lr 2e-05 sequential | 1.867 | 83/338 | 15% | 31/109 | 8/27 | 24/42 | 20/24 | 44/66 | 503 |
| test5 | r64 all-linear rsLoRA lr 0.0002 padded | 1.778 | 123/338 | 32% | 35/109 | 11/27 | 35/42 | 11/24 | 46/66 | 450 |
| test6 | r64 all-linear rsLoRA DoRA lr 0.0002 padded | 1.785 | 122/338 | 33% | 33/109 | 13/27 | 34/42 | 10/24 | 44/66 | 2091 |
| test9 | r64 all-linear rsLoRA lr 0.0002 padded 3B 4-bit | 1.717 | 153/338 | 42% | 32/109 | 11/27 | 36/42 | 13/24 | 49/66 | 2654 |

The base-model row is Qwen2.5-1.5B-Instruct; test 9's own base model (Qwen2.5-3B in 4-bit) scores 47/338
taught and 1% exact commands. A model that always answered "No" would score 42/66 on both premise sets. The grader has roughly
±5 questions of noise, so tests 3, 5 and 6 are a quality tie.

`python3 scripts/table.py` prints this table (with more columns) from the records.

## What each folder holds

| File | What |
|---|---|
| `RESULTS.md` | the write-up: question, setup, training curve, results, reading |
| `training.json` | the run's recipe as trained, data provenance (file and sha256), the validation history, the selected checkpoint, throughput, peak memory |
| `adapter_config.json` | the saved adapter's PEFT configuration |
| `eval-<set>.json` | an evaluation's report, as the run printed it (`AIF_RESULT`) and its AIJob kept |
| `answers-<set>.jsonl` | every question of that evaluation set with the base model's and the adapter's answers, each graded |
| `metrics.json` | measures computed from the answers (`scripts/metrics.py`): partial commands, gains and regressions, declines, the frozen set split by what v1 teaches, the premise sets |
| `run-output.log` | the runs' log lines (tests 1–3) |

The evaluation sets (`<set>`) are taught (338), untaught (109), false-premise (42) and
true-premise (24); see [`../eval`](../eval) and [`../DATA.md`](../DATA.md). Test 1 predates
them and has a single evaluation (`eval-report.json`).
