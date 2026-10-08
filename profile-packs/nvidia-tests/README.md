# Profile pack: nvidia-tests

Tests and benchmarks for any NVIDIA GPU, whole or on a share, on amd64 and arm64: whether a cluster
can run GPU work, and how well. They complement AI Factory's own PyTorch GPU Test and CPU Smoke Test.

| Profile | Purpose | Notes |
|---|---|---|
| `gpu-smoke`, `gpu-smoke-shared` | test | the GPU is allocated and the driver answers; on a whole GPU, or a 1 GiB share |
| `pytorch-gpu-test-shared` | test | the PyTorch GPU Test on a 4 GiB share |
| `pytorch-distributed-test` | test | torchrun, NCCL and DDP training steps across two or more workers, one whole GPU each |
| `nccl-fabric-benchmark` | benchmark | all-reduce bandwidth between two or more nodes |
| `training-storage-test` | test | a dataset through a DataLoader into training on the GPU, then a checkpoint written and read back |
| `gpu-diagnostics-bundle`, `gpu-diagnostics-bundle-shared` | test | a support bundle from the GPU, kept on a small volume |
| `gpu-health-check` | test | NVIDIA DCGM diagnostics on one GPU |
| `cpu-inference-test` | test | a small model answering on CPUs, no GPU |

The shared variants need KAI with GPU sharing. The PyTorch tests use the SUSE Application Collection
image, so driver 580 or newer.

Install: see [the packs' README](../README.md#install-a-pack).

## Change a test

The profiles carry their scripts inline: edit the script in `scripts/`, then rebuild them with

```sh
python3 profile-packs/nvidia-tests/scripts/build_profiles.py
```

and check the pack (`python3 profile-packs/tools/check_profiles.py profile-packs/nvidia-tests`). Bump
`version` in `Chart.yaml` with each change.
