# LoRA fine-tuning across GPUs

A LoRA fine-tune of a 32B model across three GPUs of one node, submitted to SUSE AI Factory from a
notebook: [`lora-distributed-3gpu.ipynb`](lora-distributed-3gpu.ipynb). The notebook installs the
`rancher_ai` SDK, checks the cluster can run the profile, submits the run, follows its log, shows its
checks and metrics, and plots its loss and throughput from the run's `training.json`. An optional
last step runs the same job on one GPU, to compare the throughput.

The run is the **LoRA Distributed Training Test** profile from the
[`nvidia-180g` pack](../profile-packs/nvidia-180g/README.md), which says what it checks and what it
needs. The same run can be submitted from the cluster's **AI Jobs → Catalog** without the notebook.

A second notebook, [`serve-adapter-vllm.ipynb`](serve-adapter-vllm.ipynb), serves a run's adapter:
it reads the adapter's base model and rank, starts a vLLM endpoint for that base model with LoRA on
(an AI Factory Blueprint of the Application Collection vLLM chart, and a workload from it, in the
project's KAI queue), copies the adapter onto the endpoint's model volume in the cluster
(`volumes.copy`, checksums compared), loads it into the running server through vLLM's API, and asks
the base model and the adapter the same question. Creating the Blueprint takes a user who may create
Blueprints (cluster-wide), such as an administrator.

## Running it

1. Install the pack on the cluster:

   ```sh
   git clone https://github.com/dstanley/aif-lab && cd aif-lab
   helm install aif-profiles-nvidia-180g profile-packs/nvidia-180g -n ai-profiles
   ```

2. In AI Factory: Application Collection credentials in **Settings**, and a project whose GPU quota
   allows three GPUs.
3. Open the notebook in Jupyter, set `CONTEXT` and `PROJECT` in its second cell, and run the cells in
   order.

## Trying the script without GPUs

The script runs on CPUs with Gloo when `ALLOW_CPU=1`, for checking a change before a GPU run (a small
model, a few steps):

```sh
ALLOW_CPU=1 MODEL=Qwen/Qwen2.5-0.5B-Instruct STEPS=20 BATCH=2 SEQ_LEN=128 LOG_EVERY=2 LR=5e-4 LORA_R=8 HELD_OUT=24 \
  CHECKPOINT_DIR=/tmp/out torchrun --standalone --nproc_per_node=3 profile-packs/nvidia-180g/scripts/lora_distributed_test.py
```

It needs PyTorch; it installs transformers, PEFT and Accelerate when they are missing. On macOS, use
`--master_addr=127.0.0.1 --master_port=29512` in place of `--standalone`, with `GLOO_SOCKET_IFNAME=lo0`.
