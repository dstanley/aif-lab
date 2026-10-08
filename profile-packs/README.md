# Profile packs

Compute profiles for SUSE AI Factory, beyond the four hardware-neutral ones it ships (CPU Smoke Test,
CPU Job, PyTorch GPU Test, Single GPU Development). Each pack is a Helm chart that installs its
profiles into `ai-profiles`, where each cluster's **AI Jobs → Catalog** reads them.

| Pack | For |
|---|---|
| [`nvidia-tests/`](nvidia-tests/README.md) | tests and benchmarks for any NVIDIA GPU, whole or shared: smoke tests, DCGM, diagnostics, NCCL, storage |
| [`nvidia-16g/`](nvidia-16g/README.md) | work sized for GPUs with up to 16 GB (RTX A2000, T4): development on a GPU share, distributed training, Qwen2.5-1.5B endpoints |

Packs are tiered by GPU memory (`nvidia-16g`, then 48, 96 and 180 GB), because memory decides which
models and runs fit. A cluster can install every pack: each profile states what it needs, and the
Catalog shows only the profiles the cluster can run, the rest on request with why not. A larger GPU
runs the smaller tiers' profiles too.

## What a profile needs

A profile states it in `requires`; AI Factory adds what the profile's values imply (a GPU at all, a
GPU-memory share and KAI to schedule it, as many GPUs as its fewest workers need):

```yaml
requires:
  gpuMemoryGiB: 70          # per GPU, at least
  gpusPerNode: 4            # on one node, at least
  nodes: 2                  # GPU nodes that each meet the above
  computeCapability: "9.0"  # at least: 8.0 Ampere, 9.0 Hopper, 10.0 Blackwell
  driver: 580               # NVIDIA driver major version, at least
  arch: [amd64, arm64]      # CPU architectures its images are built for
```

The facts come from the nodes' GPU Feature Discovery labels; a fact a node does not report does not
rule a profile out.

## Install a pack

```sh
git clone https://github.com/dstanley/aif-lab && cd aif-lab
helm install aif-profiles-nvidia-tests profile-packs/nvidia-tests -n ai-profiles
helm install aif-profiles-nvidia-16g  profile-packs/nvidia-16g  -n ai-profiles
kubectl -n ai-profiles get configmaps -L ai-factory.suse.com/profile-pack
```

`helm upgrade` takes a newer pack; `helm uninstall` removes its profiles (runs already started from
them keep the values they were submitted with). A profile already in `ai-profiles` that Helm did not
install has to be deleted, or adopted by the release, before a pack can install one of the same
name.

## Check a pack

```sh
python3 profile-packs/tools/check_profiles.py profile-packs/nvidia-16g
```

Each profile must parse with no problems (the AI Factory SDK's own parser), and the training chart
must render with its values as a run would install it (under KAI by default; `--scheduler`). It
needs `helm` and the SDK.

## The format

A pack is a Helm chart: `profiles/` holds one ConfigMap per profile in the form AI Factory reads
(label `trainingjobs/profile: training` or `inference`, the profile in `data.profile.yaml`); its
template sets each one's namespace and adds the label `ai-factory.suse.com/profile-pack: <pack>`;
`Chart.yaml` names the pack and the training chart version its profiles were checked with. Bump the
chart's `version` with each change.
