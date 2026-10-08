# Profile pack: nvidia-16g

Work sized for NVIDIA GPUs with up to 16 GB of memory, such as the RTX A2000 12 GB and the T4. Larger
GPUs run these profiles too.

| Profile | Purpose | Needs |
|---|---|---|
| `shared-gpu-dev` | development | a 4 GiB share of a GPU, queued by KAI until it fits; runs named `dev-…`; driver 580 |
| `pytorch-distributed` | training | torchrun across one to four workers, one GPU each, a kept checkpoint volume; driver 580 |
| `suse-inference-endpoint-qwen` | inference | the SUSE Inference Endpoint blueprint with Qwen2.5-1.5B on a whole GPU of 10 GiB or more; amd64 |
| `suse-inference-endpoint-qwen-shared` | inference | the same on a 5 GiB share; amd64 |

The PyTorch profiles use the SUSE Application Collection image (amd64 and arm64; CUDA 13, so driver
580 or newer). The endpoints are amd64 until their vLLM image is checked on arm64. Volumes use the
cluster's default storage class.

Install: see [the packs' README](../README.md#install-a-pack).
