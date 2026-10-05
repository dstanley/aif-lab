# SUSE AI Factory lab

Worked studies on SUSE AI Factory: each one a question, a method that can be rerun, and what the
evidence showed. Each study is self-contained in its own folder.

| Study | Question | Status |
|---|---|---|
| [`lora/`](lora/README.md) | Can a small model learn SUSE-specific knowledge with LoRA on a shared GPU, and how do we know? | in progress |
| `inference/` | | planned |
| `gpu-sharing/` | | planned |
| `training/` | | planned |
| `agents/` | | planned |

`notebooks/` (planned) will hold material that cuts across studies, such as getting started with the
`rancher_ai` SDK and a training profile.

## Setup

```
python3 -m venv .venv && .venv/bin/pip install -r lora/requirements.txt
```

Runs on the cluster need the `rancher_ai` SDK from the aif repo (`sdk/python`) on `PYTHONPATH`, and
`AIF_CONTEXT`, `AIF_PROJECT` and `AIF_PROFILE` set (see each study's README).
