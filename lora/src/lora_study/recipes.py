"""Recipes: a test is a recipe file, recipes/<name>.yaml, that may extend another and changes only what
it lists. A recipe resolves to the environment variables lora_train.py reads, so a run from the CLI,
a notebook or the Rancher UI is the same experiment."""
import os

import yaml

from .paths import RECIPES

# recipe key -> lora_train.py environment variable
ENV = {
    "model": "MODEL", "quant": "QUANT", "data": "DATASET", "steps": "STEPS", "epochs": "EPOCHS", "batch": "BATCH",
    "batch_mode": "BATCH_MODE", "seq_len": "SEQ_LEN", "mask_prompt": "MASK_PROMPT",
    "lora.rank": "LORA_R", "lora.alpha": "LORA_ALPHA", "lora.dropout": "LORA_DROPOUT", "lora.targets": "LORA_TARGETS",
    "lora.rslora": "RSLORA", "lora.dora": "DORA", "lora.init": "LORA_INIT",
    "optimiser.lr": "LR", "optimiser.schedule": "LR_SCHEDULE", "optimiser.warmup": "WARMUP", "optimiser.max_grad_norm": "MAX_GRAD_NORM",
    "optimiser.seed": "SEED",
    "validation.fraction": "VAL_FRACTION", "validation.every": "VAL_EVERY", "validation.patience": "PATIENCE",
    "validation.min_delta": "MIN_DELTA",
}


def _flat(d, prefix=""):
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(_flat(v, f"{prefix}{k}."))
        else:
            out[f"{prefix}{k}"] = v
    return out


def _merge(base, over):
    out = dict(base)
    for k, v in over.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load(name):
    """A recipe with everything it extends merged in (its own keys win)."""
    with open(os.path.join(RECIPES, f"{name}.yaml")) as f:
        r = yaml.safe_load(f) or {}
    parent = r.pop("extends", None)
    meta = {k: r.pop(k) for k in ("title", "changes", "question", "configmap") if k in r}
    merged = _merge(load(parent)["settings"], r) if parent else r
    if parent and "configmap" not in meta:
        meta["configmap"] = load(parent).get("configmap")
    return {"name": name, "extends": parent, "configmap": "lora-train-v1", **{k: v for k, v in meta.items() if v}, "settings": merged}


def env(recipe, run_name):
    """The recipe as lora_train.py's environment."""
    e = {"HF_HOME": "/scratch/hf", "RUN_NAME": run_name}
    for k, v in _flat(recipe["settings"]).items():
        if k not in ENV:
            raise KeyError(f"recipe {recipe['name']}: unknown setting {k}")
        e[ENV[k]] = ("1" if v else "0") if isinstance(v, bool) else str(v)
    return e
