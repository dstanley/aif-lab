"""Evaluates a LoRA adapter against its base model, on the records its training held out: the loss of
the base model and of the adapter on the same records, the answers' tokens only, and one answer from
each. The second step of a train -> evaluate chain (rancher_ai.chain); any GPU that fits the base model
in bf16 (a 4 GiB share for a 0.5B model, 70 GB for a 32B one).

Inputs, as a chain hands them over:

  AIF_INPUT_ADAPTER   the adapter folder (the training run's output, on its checkpoint volume); its
                      adapter_config.json names the base model, and the training.json beside it the
                      dataset, seed and held-out count the training used
  AIF_INPUT_DATASET   optional: the dataset as the training recorded it (hf-dataset://<repo>@<commit>/<file>,
                      or file://<path>), so the same revision is read; else the training's DATASET
  BATCH (8), MAX_NEW_TOKENS (120), ALLOW_CPU (1 = CPUs when there is no GPU)
  REQUIRE_IMPROVEMENT (1): 0 = the run succeeds whether or not the adapter lowered the loss, for a
                      caller that decides itself (a pipeline's gate); the check still reports it

It reports AIF_RESULT (checks and metrics) and AIF_ARTIFACT lines (the adapter, base model and dataset
it consumed, and eval.json if the run has a checkpoint volume).
"""
import hashlib, importlib.util, json, os, random, subprocess, sys, time

LIBS = ["transformers==4.57.1", "peft==0.18.1", "accelerate==1.12.0"]
PYBASE = "/tmp/lora-eval/py"
SITE = f"{PYBASE}/lib/python{sys.version_info[0]}.{sys.version_info[1]}/site-packages"


def install():
    missing = [l for l in LIBS if importlib.util.find_spec(l.split("==")[0]) is None]
    if not missing:
        return
    print(f"INFO | installing {', '.join(missing)} (about a minute)", flush=True)
    pip_env = {**os.environ, "PYTHONUSERBASE": PYBASE, "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_BREAK_SYSTEM_PACKAGES": "1"}
    if subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True, env=pip_env).returncode != 0:
        subprocess.run([sys.executable, "-m", "ensurepip", "--user"], check=True, capture_output=True, env=pip_env)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-cache-dir", "--no-warn-script-location", "--user", *missing], check=True, env=pip_env)


install()
if os.path.isdir(SITE):
    sys.path.insert(0, SITE)
os.environ.setdefault("HF_HOME", os.path.join(os.environ.get("SCRATCH_DIR", "/tmp"), "hf"))
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import torch
from huggingface_hub import hf_hub_download, list_repo_files
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def content_sha256(path):
    """As the training script and rancher_ai.lineage.folder_sha256 compute it."""
    def file_sha(p):
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    if os.path.isfile(path):
        return file_sha(path), os.path.getsize(path)
    h, size = hashlib.sha256(), 0
    for root, _, files in sorted(os.walk(path)):
        for f in sorted(files):
            p = os.path.join(root, f)
            h.update(f"{os.path.relpath(p, path)}\0{file_sha(p)}\n".encode())
            size += os.path.getsize(p)
    return h.hexdigest(), size


def artifact(direction, name, uri, kind, path=None):
    d = {"direction": direction, "name": name, "kind": kind, "uri": uri}
    if path and os.path.exists(path):
        d["sha256"], d["bytes"] = content_sha256(path)
    print("AIF_ARTIFACT " + json.dumps(d, separators=(",", ":")), flush=True)


ADAPTER = os.environ.get("AIF_INPUT_ADAPTER", "").rstrip("/")
if not ADAPTER or not os.path.isdir(ADAPTER):
    sys.exit(f"AIF_INPUT_ADAPTER={ADAPTER!r}: no adapter folder there (a chain step hands it over)")
cfg = json.load(open(os.path.join(ADAPTER, "adapter_config.json")))
BASE = cfg["base_model_name_or_path"]
record_path = os.path.join(os.path.dirname(ADAPTER), "training.json")
trained = json.load(open(record_path))["settings"] if os.path.exists(record_path) else {}
SEED, HELD_OUT, SEQ = int(trained.get("SEED", 1234)), int(trained.get("HELD_OUT", 64)), int(trained.get("SEQ_LEN", 1024))
BATCH, NEW = int(os.environ.get("BATCH", "8")), int(os.environ.get("MAX_NEW_TOKENS", "120"))

# the dataset: the revision the training recorded, else its DATASET as it is now
src = os.environ.get("AIF_INPUT_DATASET", "")
if src.startswith("hf-dataset://"):
    repo, _, rest = src[len("hf-dataset://"):].partition("@")
    commit, _, fname = rest.partition("/")
    data = hf_hub_download(repo, fname, repo_type="dataset", revision=commit)
elif src.startswith("file://"):
    data = src[len("file://"):]
else:
    ds = trained.get("DATASET", "yahma/alpaca-cleaned")
    if os.path.exists(ds):
        data = ds
    else:
        files = [f for f in list_repo_files(ds, repo_type="dataset") if f.endswith((".json", ".jsonl"))]
        data = hf_hub_download(ds, files[0], repo_type="dataset")
text = open(data).read()
records = json.loads(text) if text.lstrip().startswith("[") else [json.loads(l) for l in text.splitlines() if l.strip()]
random.Random(SEED).shuffle(records)  # as the training did: its held-out records are the first HELD_OUT
held = records[:HELD_OUT]

GPU = torch.cuda.is_available()
if not GPU and os.environ.get("ALLOW_CPU") != "1":
    sys.exit("no GPU visible; ALLOW_CPU=1 runs on CPUs")
DEVICE = torch.device("cuda", 0) if GPU else torch.device("cpu")
tok = AutoTokenizer.from_pretrained(ADAPTER if os.path.exists(os.path.join(ADAPTER, "tokenizer_config.json")) else BASE)
tok.pad_token = tok.pad_token or tok.eos_token


def prompt_of(r):
    user = r["instruction"] + (f"\n\n{r['input']}" if r.get("input") else "")
    return tok.apply_chat_template([{"role": "user", "content": user}], tokenize=False, add_generation_prompt=True)


def encode(r):
    p = tok(prompt_of(r), add_special_tokens=False)["input_ids"]
    a = tok(r["output"] + tok.eos_token, add_special_tokens=False)["input_ids"]
    return (p + a)[:SEQ], ([-100] * len(p) + a)[:SEQ]


t0 = time.time()
base = AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.bfloat16 if GPU else torch.float32,
                                            device_map={"": 0} if GPU else None, attn_implementation="sdpa")
model = PeftModel.from_pretrained(base, ADAPTER)
model.eval()
print(f"INFO | {BASE} with the adapter from {ADAPTER} loaded in {time.time() - t0:.0f}s; {len(held)} held-out records", flush=True)


def held_out_loss():
    tot, n = 0.0, 0
    with torch.no_grad():
        for i in range(0, len(held), BATCH):
            rows = [encode(r) for r in held[i:i + BATCH]]
            L = max(len(x) for x, _ in rows)
            ids = torch.tensor([x + [tok.pad_token_id] * (L - len(x)) for x, _ in rows], device=DEVICE)
            labels = torch.tensor([y + [-100] * (L - len(y)) for _, y in rows], device=DEVICE)
            mask = torch.tensor([[1] * len(x) + [0] * (L - len(x)) for x, _ in rows], device=DEVICE)
            k = int((labels[:, 1:] != -100).sum())
            tot += float(model(input_ids=ids, attention_mask=mask, labels=labels).loss) * k
            n += k
    return round(tot / n, 4)


def answer(r):
    ids = tok(prompt_of(r), return_tensors="pt", add_special_tokens=False).to(DEVICE)
    with torch.no_grad():
        out = model.generate(**ids, max_new_tokens=NEW, do_sample=False)
    return tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True).strip()


with model.disable_adapter():
    base_loss = held_out_loss()
    base_answer = answer(held[0])
adapter_loss = held_out_loss()
adapter_answer = answer(held[0])
print(f"INFO | held-out loss: base {base_loss:.4f}, adapter {adapter_loss:.4f}", flush=True)

checks = [
    {"name": "The adapter loads onto its base model", "ok": True, "detail": f"{BASE}, rank {cfg.get('r')}"},
    {"name": "The adapter lowers the loss on held-out records", "ok": adapter_loss < base_loss,
     "detail": f"{base_loss:.3f} for the base model, {adapter_loss:.3f} with the adapter, on {len(held)} records the training never saw"},
]
metrics = {"base_loss": base_loss, "adapter_loss": adapter_loss, "loss_reduction": round(base_loss - adapter_loss, 4),
           "held_out": len(held), "eval_s": round(time.time() - t0)}
result = {"test": "LoRA Adapter Evaluation", "status": "pass" if all(c["ok"] for c in checks) else "fail",
          "checks": checks, "metrics": metrics, "env": {"base_model": BASE, "torch": torch.__version__}}

# lineage: what it consumed, and what it wrote
artifact("input", "adapter", f"file://{ADAPTER}", "model", path=ADAPTER)
artifact("input", "base-model", f"hf://{BASE}", "model")
artifact("input", "dataset", src or f"file://{data}", "dataset", path=data)
out_dir = os.environ.get("CHECKPOINT_DIR")
if out_dir and os.access(out_dir, os.W_OK):
    run = os.environ.get("JOB_NAME", "eval")
    os.makedirs(os.path.join(out_dir, run), exist_ok=True)
    p = os.path.join(out_dir, run, "eval.json")
    json.dump({"result": result, "question": held[0]["instruction"], "reference": held[0]["output"],
               "base_answer": base_answer, "adapter_answer": adapter_answer}, open(p, "w"), indent=1)
    artifact("output", "eval", f"checkpoints://{run}/eval.json", "metrics", path=p)
print(f"--- {held[0]['instruction']}\n--- base:    {base_answer[:300]}\n--- adapter: {adapter_answer[:300]}", flush=True)
for c in checks:
    print(f"INFO | {'PASS' if c['ok'] else 'FAIL'}  {c['name']}: {c['detail']}", flush=True)
print("AIF_RESULT " + json.dumps(result), flush=True)
sys.exit(0 if result["status"] == "pass" or os.environ.get("REQUIRE_IMPROVEMENT", "1") == "0" else 1)
