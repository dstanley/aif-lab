#!/usr/bin/env python3
"""Build this pack's profiles in ../profiles from the scripts in this directory, so a profile always
carries its script's current text. Run after changing a script:

  python3 profile-packs/nvidia-180g/scripts/build_profiles.py
"""
import os

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "profiles")
TORCH = {"repository": "dp.apps.rancher.io/containers/pytorch", "tag": "2.14.0-nvidia-2.1"}
PULL = [{"name": "suse-ai-pull-combined"}]


def script(name):
    with open(os.path.join(HERE, name)) as f:
        return f.read()


def var(name, value):
    return {"name": name, "value": str(value)}


PROFILES = [
    ("10-lora-distributed-test", "lora-distributed-test", {
        "displayName": "LoRA Distributed Training Test",
        "purpose": "test",
        "description": "LoRA fine-tune of Qwen2.5-32B across three GPUs of one node with torchrun and DDP, 200 steps; "
                       "reports whether every GPU trained in step, the loss, and each GPU's throughput and memory, and keeps "
                       "the adapter. Stopped after 6 hours.",
        "framework": "PyTorch",
        "status": "ready",
        # 32B in bf16 on every GPU: 65 GB of weights and about 25 GB more for training. With
        # MODEL=Qwen/Qwen2.5-14B-Instruct it fits GPUs of 80 GB, but the Catalog asks for this tier.
        # The Application Collection PyTorch image: driver 580+ (CUDA 13), amd64 and arm64.
        "requires": {"gpuMemoryGiB": 160, "driver": 580, "arch": ["amd64", "arm64"]},
        "values": {
            "image": TORCH, "imagePullSecrets": PULL,
            "job": {"kind": "job", "mode": "torchrun", "nodes": 1, "gpusPerNode": 3, "script": script("lora_distributed_test.py")},
            "rendezvous": {"backend": "c10d"},
            # three processes that feed GPUs need few CPUs; 4 is also the CPU limit of training charts
            # before 2.3.0-training.12, which do not raise a limit to its request
            "resources": {"requests": {"cpu": "4", "memory": "128Gi", "ephemeral-storage": "10Gi"}},
            "storage": {
                # outputs: a new volume per run, kept after it; scratch: the model download, a
                # per-pod volume (both of the cluster's default storage class)
                "checkpointCreate": {"enabled": True, "size": "20Gi", "keep": True},
                "scratchSize": "200Gi", "scratchMedium": "volume", "shmSizeLimit": "16Gi",
            },
            # the script's settings, here so the Submit page shows them (its docstring lists them all)
            "env": [var("PYTHONUNBUFFERED", 1), var("MODEL", "Qwen/Qwen2.5-32B-Instruct"), var("DATASET", "yahma/alpaca-cleaned"),
                    var("STEPS", 200), var("BATCH", 4), var("SEQ_LEN", 1024), var("LORA_R", 32), var("LORA_TARGETS", "all-linear")],
        },
        "editable": ["image", "tag", "script", "configMap", "env", "gpusPerNode", "datasetPVC", "checkpointPVC", "runtimeLimitHours"],
        "limits": {"nodes": {"min": 1, "max": 1}, "gpusPerNode": {"min": 1, "max": 4},
                   "registries": ["dp.apps.rancher.io/containers/", "nvcr.io/nvidia/", "pytorch/"], "maxRuntimeHours": 6},
    }),
]


class Literal(str):
    pass


yaml.add_representer(Literal, lambda d, s: d.represent_scalar("tag:yaml.org,2002:str", s, style="|"))


def literal_scripts(o):
    if isinstance(o, dict):
        return {k: (Literal(v) if isinstance(v, str) and "\n" in v else literal_scripts(v)) for k, v in o.items()}
    if isinstance(o, list):
        return [Literal(v) if isinstance(v, str) and "\n" in v else literal_scripts(v) for v in o]
    return o


for fname, name, doc in PROFILES:
    body = yaml.dump(literal_scripts(doc), sort_keys=False, width=1000, allow_unicode=True)
    cm = {"apiVersion": "v1", "kind": "ConfigMap",
          "metadata": {"name": name, "namespace": "ai-profiles", "labels": {"trainingjobs/profile": "training"}},
          "data": {"profile.yaml": Literal(body)}}
    with open(os.path.join(OUT, f"{fname}.yaml"), "w") as f:
        f.write(f"# {doc['displayName']}: {doc['description']}\n# Built by ../scripts/build_profiles.py from ../scripts/; edit the script there and rebuild.\n")
        yaml.dump(cm, f, sort_keys=False, width=1000, allow_unicode=True)
    print("wrote", fname)
