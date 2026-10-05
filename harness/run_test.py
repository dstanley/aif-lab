"""One LoRA test: train, then evaluate on the taught, untaught, false-premise and true-premise sets, and
fetch the records into results/<test>/.

usage: run_test.py <test> <run-name> <train-configmap> '<json env overrides>' [GPU GiB for training]

The overrides change the recipe below (the best recipe so far, test 5's); everything else comes from
the environment: AIF_CONTEXT (kubeconfig context), AIF_PROJECT, AIF_PROFILE (an AI Factory training
profile with a GPU share), IMAGE. Needs the rancher_ai SDK (aif repo, sdk/python) on the path, and
the ConfigMaps make_configmaps.sh creates."""
import sys, time, json, os, subprocess
from rancher_ai import Client
test, name, cm, overrides = sys.argv[1], sys.argv[2], sys.argv[3], json.loads(sys.argv[4])
gib = int(sys.argv[5]) if len(sys.argv) > 5 else 6
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, "results", test)
os.makedirs(T, exist_ok=True)
ai = Client(context=os.environ.get("AIF_CONTEXT"), project=os.environ.get("AIF_PROJECT", "default"))
PROFILE = os.environ.get("AIF_PROFILE", "shared-gpu-dev")
IMG = os.environ.get("IMAGE", "pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime")
RECIPE = {"HF_HOME": "/scratch/hf", "DATASET": "/mnt/config/suse-train-v1.jsonl", "SEQ_LEN": "512", "BATCH": "4", "MASK_PROMPT": "1",
          "EPOCHS": "3", "VAL_FRACTION": "0.1", "PATIENCE": "0", "LORA_R": "64", "LORA_ALPHA": "16", "LORA_TARGETS": "all-linear",
          "RSLORA": "1", "LR_SCHEDULE": "cosine", "WARMUP": "0.05", "BATCH_MODE": "padded", "MAX_GRAD_NORM": "1.0", "RUN_NAME": name}
env = {k: v for k, v in {**RECIPE, **overrides}.items() if v is not None}

def run(n, configmap, g, e, checkpoints=None, hours=2):
    kw = {"checkpoints": checkpoints} if checkpoints else {}
    r = ai.runs.create(profile=PROFILE, name=n, image=IMG, gpu_memory=g, runtime_hours=hours, config_map=configmap, env=e, **kw)
    st = r.wait(timeout=hours * 3600 + 600)
    time.sleep(5)
    try:
        log = r.logs(tail=400, print_=False) or ""
    except Exception as ex:
        log = f"(no log: {ex})"
    print(f"\n##### {n}: {st}", flush=True)
    print("\n".join(l for l in log.splitlines() if "INFO |" in l or "WARN" in l or "ERROR" in l or "Traceback" in l or "Error:" in l)[-6000:], flush=True)
    return r, st

r, st = run(name, cm, gib, env)
if "Completed" not in str(st):
    print("##### training failed", flush=True); sys.exit(1)
EV = {"taught": ("suse-v1-eval-taught", "suse-eval-taught.jsonl", "area,type"),
      "untaught": ("suse-v1-eval-untaught", "suse-eval-untaught.jsonl", "area,type,v1_taught"),
      "false-premise": ("suse-v1-eval-false-premise", "suse-eval-false-premise.jsonl", "premise,area"),
      "true-premise": ("suse-v1-eval-true-premise", "suse-eval-true-premise.jsonl", "area")}
evq = {"HF_HOME": "/scratch/hf", "MAX_NEW_TOKENS": "200", "TRAIN_DATASET": "/mnt/config/suse-train-v1.jsonl"}
if overrides.get("QUANT"):
    evq["QUANT"] = overrides["QUANT"]
if overrides.get("MODEL"):
    evq["MODEL"] = overrides["MODEL"]
for label, (ecm, f, groups) in EV.items():
    e, _ = run(f"{name}-eval-{ {'false-premise': 'fp', 'true-premise': 'tp'}.get(label, label) }", ecm, 6,
               {**evq, "EVAL_DATASET": f"/mnt/config/{f}", "EVAL_LABEL": label, "EVAL_GROUPS": groups}, checkpoints=f"{name}-checkpoints", hours=1)
    res = e.refresh().result() or {}
    json.dump(res, open(f"{T}/eval-{label}.json", "w"), indent=1)
    print(json.dumps(res.get("metrics", {}), indent=1), flush=True)
vol = ai.checkpoints.get(f"{name}-checkpoints")
for row in vol.ls():
    p = row["path"]
    if p in (f"{name}/training.json", f"{name}/adapter_config.json"):
        vol.get(p, T + "/")
    elif p.startswith(f"{name}/eval/"):
        label = os.path.basename(p).rsplit("-", 1)[0]
        vol.get(p, f"{T}/answers-{label}.jsonl")
subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "metrics.py"), T], stdout=subprocess.DEVNULL)
print("##### done", flush=True)
