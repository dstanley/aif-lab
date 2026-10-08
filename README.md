# SUSE AI Factory lab

Worked studies on SUSE AI Factory: each one a question, a method that can be rerun, and what the
evidence showed. Each study is self-contained in its own folder.

| Study | Question |
|---|---|
| [`lora/`](lora/README.md) | Can a small model learn SUSE-specific knowledge with LoRA on a shared GPU, and how do we know? |
| [`data-lifecycle/`](data-lifecycle/README.md) | Can a training run's data and outputs move through S3-compatible storage end to end, verified, without the people and pods doing the work holding storage credentials? |

| Profile packs | For |
|---|---|
| [`profile-packs/`](profile-packs/README.md) | AI Factory compute profiles as Helm charts: [`nvidia-tests`](profile-packs/nvidia-tests/README.md) (tests and benchmarks for any NVIDIA GPU) and [`nvidia-16g`](profile-packs/nvidia-16g/README.md) (work for GPUs up to 16 GB) |

## Setup

```
python3 -m venv .venv && .venv/bin/pip install -r lora/requirements.txt
```

Runs on the cluster need the `rancher_ai` SDK from the aif repo (`sdk/python`) on `PYTHONPATH`, and
`AIF_CONTEXT`, `AIF_PROJECT` and `AIF_PROFILE` set (see each study's README).

## Disclaimer

This is an independent lab, not an official SUSE project, product or documentation, and nothing here
is supported by SUSE. SUSE, Rancher, RKE2, K3s, Longhorn, Harvester and NeuVector are trademarks of
their owners.

The datasets in the studies were **drafted by a language model** from public SUSE and upstream
project documentation and have **not been reviewed**: they will contain mistakes, and they are not a
reference for how to use any product. The model answers recorded in the results are generated text
and are often wrong, which is part of what the studies measure. Facts paraphrased from the
documentation remain subject to that documentation's own terms. See [`lora/DATA.md`](lora/DATA.md).

The code is licensed under the Apache License 2.0 (see [`LICENSE`](LICENSE)).
