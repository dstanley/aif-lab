# Profile pack: nvidia-180g

Work sized for NVIDIA GPUs with about 180 GB of memory, such as the GB200 and B200.

| Profile | Purpose | Needs |
|---|---|---|
| `lora-distributed-test` | test | three GPUs of 160 GiB or more on one node (one to four with **GPUs per worker**), driver 580 |

**LoRA Distributed Training Test** fine-tunes Qwen2.5-32B-Instruct with LoRA across the GPUs of one
node: torchrun starts one process per GPU, each holds the whole model in bf16, and DDP averages the
adapter's gradients at every step. It is a training run and a test of the node at once. It reports:

| Check | What it shows |
|---|---|
| Every process trained on its own GPU | each process had a distinct GPU |
| The processes' adapters are identical | DDP averaged the gradients: the adapters match to the last bit after 200 steps |
| It learned: the loss on held-out records came down | 64 records kept out of training, measured before and after |
| The adapter was saved | the adapter, on the run's kept checkpoint volume |

with the throughput (tokens per second, in all and per GPU), the step time and each GPU's peak memory.
The script is [`scripts/lora_distributed_test.py`](scripts/lora_distributed_test.py); its docstring
lists every setting, each an environment variable. The profile shows the main ones on the Submit page:
`MODEL` (`Qwen/Qwen2.5-14B-Instruct` downloads in half the time), `STEPS`, `BATCH`, `SEQ_LEN`,
`LORA_R`, `LORA_TARGETS`.

The first run downloads the model, 65 GB, to the run's scratch volume (200 GiB, the cluster's default
storage class); allow 10 to 30 minutes for it before the 200 steps. The image is the SUSE Application
Collection PyTorch image (amd64 and arm64; CUDA 13, so driver 580 or newer), which has PyTorch only:
transformers, PEFT and Accelerate are installed when the run starts. The project's GPU quota must
allow as many GPUs as the run asks for.

The notebook [`lora-distributed/lora-distributed-3gpu.ipynb`](../../lora-distributed/lora-distributed-3gpu.ipynb)
submits the run from Jupyter, follows it, and plots its loss and throughput.

`profiles/` is built from `scripts/`: after changing the script, run
`python3 profile-packs/nvidia-180g/scripts/build_profiles.py`.

Install: see [the packs' README](../README.md#install-a-pack).
