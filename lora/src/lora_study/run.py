"""Running a recipe on SUSE AI Factory through the rancher_ai SDK: one training run, then its
evaluations, then the records fetched into results/<test>/.

Settings from the environment: AIF_CONTEXT (kubeconfig context), AIF_PROJECT (the project's
namespace), AIF_PROFILE (a training profile with a GPU share), IMAGE. The ConfigMaps come from
harness/make_configmaps.sh."""
import json
import os
import time

from . import grading, recipes
from .paths import RESULTS

IMAGE = os.environ.get("IMAGE", "pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime")
EVALS = {  # evaluation set -> (ConfigMap, file in it, score breakdowns)
    "taught": ("lora-eval-taught", "suse-eval-taught.jsonl", "area,type"),
    "untaught": ("lora-eval-untaught", "suse-eval-untaught.jsonl", "area,type,v1_taught"),
    "false-premise": ("lora-eval-false-premise", "suse-eval-false-premise.jsonl", "premise,area"),
    "true-premise": ("lora-eval-true-premise", "suse-eval-true-premise.jsonl", "area"),
}
SHORT = {"false-premise": "fp", "true-premise": "tp"}


def client():
    from rancher_ai import Client
    return Client(context=os.environ.get("AIF_CONTEXT"), project=os.environ.get("AIF_PROJECT", "default"))


def _submit(ai, name, configmap, env, gib=6, hours=2, checkpoints=None):
    kw = {"checkpoints": checkpoints} if checkpoints else {}
    return ai.runs.create(profile=os.environ.get("AIF_PROFILE", "shared-gpu-dev"), name=name, image=IMAGE, gpu_memory=gib,
                          runtime_hours=hours, config_map=configmap, env=env, **kw)


def train(recipe, run_name, ai=None, gib=6, wait=True):
    """Submit the recipe's training run; with wait, block until it ends and return (run, state)."""
    ai = ai or client()
    r = _submit(ai, run_name, recipe["configmap"], recipes.env(recipe, run_name), gib=gib)
    return (r, r.wait(timeout=3 * 3600)) if wait else (r, None)


def evaluate(run_name, label, ai=None, gib=6):
    """Evaluate a finished run's adapter on one evaluation set; returns (run, state)."""
    ai = ai or client()
    cm, f, groups = EVALS[label]
    env = {"HF_HOME": "/scratch/hf", "EVAL_DATASET": f"/mnt/config/{f}", "EVAL_LABEL": label, "EVAL_GROUPS": groups,
           "MAX_NEW_TOKENS": "200", "TRAIN_DATASET": "/mnt/config/suse-train-v1.jsonl"}
    r = _submit(ai, f"{run_name}-eval-{SHORT.get(label, label)}", cm, env, gib=gib, hours=2, checkpoints=f"{run_name}-checkpoints")
    return r, r.wait(timeout=3 * 3600)


def fetch(test, run_name, ai=None):
    """The run's training.json, adapter config, each evaluation's answers and report, then the measures."""
    ai = ai or client()
    out = os.path.join(RESULTS, test)
    os.makedirs(out, exist_ok=True)
    vol = ai.checkpoints.get(f"{run_name}-checkpoints")
    for row in vol.ls():
        p = row["path"]
        if p in (f"{run_name}/training.json", f"{run_name}/adapter_config.json"):
            vol.get(p, out + "/")
        elif p.startswith(f"{run_name}/eval/"):
            label = os.path.basename(p).rsplit("-", 1)[0]
            vol.get(p, os.path.join(out, f"answers-{label}.jsonl"))
    for label in EVALS:
        try:
            r = ai.runs.get(f"{run_name}-eval-{SHORT.get(label, label)}")
            with open(os.path.join(out, f"eval-{label}.json"), "w") as f:
                json.dump(r.result() or {}, f, indent=1)
        except Exception:
            pass
    return grading.write(out)


def run_test(test, run_name, labels=tuple(EVALS), log=print):
    """A whole test: train its recipe, run each evaluation, fetch everything."""
    ai = client()
    recipe = recipes.load(test)
    log(f"training {run_name}: {recipe.get('changes', '')}")
    r, state = train(recipe, run_name, ai)
    log(f"training: {state}")
    if "Completed" not in str(state):
        return None
    for label in labels:
        _, st = evaluate(run_name, label, ai)
        log(f"evaluation {label}: {st}")
        time.sleep(5)
    return fetch(test, run_name, ai)
