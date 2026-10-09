"""LoRA fine-tune across several GPUs with torchrun and DistributedDataParallel (DDP): every GPU holds
the whole model in bf16 and trains on its own share of each batch, and the adapter's gradients are
averaged across the GPUs at every step. It is a test as well as a training run: it reports whether
every process trained on its own GPU, whether the processes' adapters stayed identical (the proof
that the gradients were averaged), whether the loss on records it never trained on came down, and
each GPU's throughput and memory.

The defaults are sized for GPUs with about 180 GB of memory (GB200, B200): Qwen2.5-32B-Instruct, LoRA
rank 32 on every linear layer, sequences of up to 1024 tokens. Every setting is an environment
variable, recorded in training.json:

  MODEL         a Hugging Face model (Qwen/Qwen2.5-32B-Instruct, 65 GB to download;
                Qwen/Qwen2.5-14B-Instruct is 30 GB and fits GPUs of 80 GB)
  DATASET       a Hugging Face dataset repository holding one JSON or JSON Lines file of
                {instruction, input, output} records (yahma/alpaca-cleaned), or such a file's path,
                for example under $DATASET_DIR
  STEPS         optimiser steps (200)
  BATCH         sequences per GPU per step (4); a step trains on BATCH x the number of GPUs
  SEQ_LEN       tokens per sequence, at most (1024)
  LR, WARMUP    learning rate (1e-4), reached over WARMUP steps (20), then cosine decay to a tenth
  LORA_R        the adapter's rank (32)
  LORA_ALPHA    its scale (twice LORA_R: the updates scale by LORA_ALPHA / LORA_R, so a fixed alpha
                with a smaller rank trains with a larger step)
  LORA_DROPOUT  (0.05)
  LORA_TARGETS  all-linear | attention (all-linear)
  GRAD_CKPT     1 = gradient checkpointing (1): much less memory, about a third more compute
  LOG_EVERY     steps between log lines (10)
  HELD_OUT      records kept out of training, whose loss is measured before and after it (64)
  SEED          (1234)
  HF_HOME       where the model downloads to ($SCRATCH_DIR/hf, the run's scratch volume); a kept
                volume here saves the download on the next run
  HF_TOKEN      for a gated model
  ALLOW_CPU     1 = run on CPUs with Gloo when there is no GPU, to try the script anywhere

Outputs, in $CHECKPOINT_DIR/<run name>/: adapter/ (the LoRA adapter, loadable with PEFT onto MODEL)
and training.json (the settings, each logged step's loss and throughput, and the result).

The image needs PyTorch only: transformers, PEFT and Accelerate are installed when the run starts
(pip comes from Python's own ensurepip, for images that ship without it), once per node.
"""
import importlib.util, json, math, os, random, socket, subprocess, sys, time
from datetime import timedelta

LOCAL_RANK, RANK, WORLD = (int(os.environ.get(k, d)) for k, d in (("LOCAL_RANK", "0"), ("RANK", "0"), ("WORLD_SIZE", "1")))
RUN_ID = os.environ.get("TORCHELASTIC_RUN_ID", "local")
LIBS = ["transformers==4.57.1", "peft==0.18.1", "accelerate==1.12.0"]
# the libraries go to a user site of the run's own, which resolves against the image's packages (its
# PyTorch is used, not downloaded again)
PYBASE = f"/tmp/lora-ddp-{RUN_ID}/py"
SITE = f"{PYBASE}/lib/python{sys.version_info[0]}.{sys.version_info[1]}/site-packages"


def log(msg, all_ranks=False):
    if RANK == 0 or all_ranks:
        print(f"INFO | rank {RANK} | {msg}" if all_ranks else f"INFO | {msg}", flush=True)


def once_per_node(tag, fn):
    """fn on each node's first process; the node's others wait for it. A file, not a collective: a
    model download can outlast any collective's timeout."""
    done, failed = (f"/tmp/lora-ddp-{RUN_ID}/{tag}.{s}" for s in ("done", "failed"))
    os.makedirs(os.path.dirname(done), exist_ok=True)
    if LOCAL_RANK == 0:
        try:
            fn()
        except BaseException:
            open(failed, "w").close()
            raise
        open(done, "w").close()
    else:
        while not os.path.exists(done):
            if os.path.exists(failed):
                sys.exit(f"rank {RANK}: this node's first process could not {tag}")
            time.sleep(2)


def install():
    missing = [l for l in LIBS if importlib.util.find_spec(l.split("==")[0]) is None]
    if not missing:
        return
    log(f"installing {', '.join(missing)} (about a minute)")
    # PIP_BREAK_SYSTEM_PACKAGES: an image may mark its Python as system-managed; this touches only the run's own folder
    pip_env = {**os.environ, "PYTHONUSERBASE": PYBASE, "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_BREAK_SYSTEM_PACKAGES": "1"}
    if subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True, env=pip_env).returncode != 0:
        # no pip in the image: Python's bundled one
        subprocess.run([sys.executable, "-m", "ensurepip", "--user"], check=True, capture_output=True, env=pip_env)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-cache-dir", "--user", *missing], check=True, env=pip_env)


once_per_node("install the libraries", install)
if os.path.isdir(SITE):
    sys.path.insert(0, SITE)

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP


def env(name, default, cast=str):
    v = os.environ.get(name, "")
    return cast(v) if v != "" else default


S = {
    "MODEL": env("MODEL", "Qwen/Qwen2.5-32B-Instruct"), "DATASET": env("DATASET", "yahma/alpaca-cleaned"),
    "STEPS": env("STEPS", 200, int), "BATCH": env("BATCH", 4, int), "SEQ_LEN": env("SEQ_LEN", 1024, int),
    "LR": env("LR", 1e-4, float), "WARMUP": env("WARMUP", 20, int),
    "LORA_R": env("LORA_R", 32, int), "LORA_ALPHA": env("LORA_ALPHA", 2 * env("LORA_R", 32, int), int), "LORA_DROPOUT": env("LORA_DROPOUT", 0.05, float),
    "LORA_TARGETS": env("LORA_TARGETS", "all-linear"), "GRAD_CKPT": env("GRAD_CKPT", 1, int),
    "LOG_EVERY": env("LOG_EVERY", 10, int), "HELD_OUT": env("HELD_OUT", 64, int), "SEED": env("SEED", 1234, int),
}
RUN = env("RUN_NAME", os.environ.get("JOB_NAME", "lora-distributed-test"))
OUT = os.path.join(env("CHECKPOINT_DIR", "/tmp/lora-ddp-out"), RUN)
os.environ.setdefault("HF_HOME", os.path.join(env("SCRATCH_DIR", "/tmp"), "hf"))

GPU = torch.cuda.is_available()
if not GPU and os.environ.get("ALLOW_CPU") != "1":
    sys.exit(f"rank {RANK}: no GPU visible (CUDA_VISIBLE_DEVICES={os.environ.get('CUDA_VISIBLE_DEVICES', '')}); set ALLOW_CPU=1 to run on CPUs")
if GPU:
    torch.cuda.set_device(LOCAL_RANK)
DEVICE = torch.device("cuda", LOCAL_RANK) if GPU else torch.device("cpu")
DTYPE = torch.bfloat16 if GPU else torch.float32
dist.init_process_group("nccl" if GPU else "gloo", timeout=timedelta(minutes=30), **({"device_id": DEVICE} if GPU else {}))
assert dist.get_world_size() == WORLD


def gather(obj):
    out = [None] * WORLD
    dist.all_gather_object(out, obj)
    return out


me = {"rank": RANK, "host": os.environ.get("HOSTNAME") or socket.gethostname(), "device": str(DEVICE),
      "gpu": torch.cuda.get_device_name(DEVICE) if GPU else "cpu",
      "uuid": str(torch.cuda.get_device_properties(DEVICE).uuid) if GPU else f"cpu-{RANK}",
      "memory_gib": round(torch.cuda.get_device_properties(DEVICE).total_memory / 2**30, 1) if GPU else 0}
ranks = gather(me)
log(f"{WORLD} processes: " + "; ".join(f"rank {r['rank']} {r['gpu']} ({r['memory_gib']} GiB) on {r['host']}" for r in ranks))
log(f"torch {torch.__version__}, CUDA {torch.version.cuda}, NCCL {'.'.join(map(str, torch.cuda.nccl.version())) if GPU else '-'}")

from huggingface_hub import hf_hub_download, list_repo_files, snapshot_download
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer


def fetch_model():
    t = time.time()
    log(f"downloading {S['MODEL']} to {os.environ['HF_HOME']} (once per node; skipped when it is there)")
    snapshot_download(S["MODEL"], allow_patterns=["*.json", "*.safetensors", "*.model", "*.txt", "*.jinja"])
    log(f"model ready in {time.time() - t:.0f}s")


def dataset_file():
    if os.path.exists(S["DATASET"]):
        return S["DATASET"]
    files = [f for f in list_repo_files(S["DATASET"], repo_type="dataset") if f.endswith((".json", ".jsonl"))]
    if len(files) != 1:
        sys.exit(f"DATASET {S['DATASET']}: needs one .json or .jsonl file, found {files}")
    return hf_hub_download(S["DATASET"], files[0], repo_type="dataset")


once_per_node("download the model", fetch_model)
once_per_node("download the dataset", dataset_file)
DATA = dataset_file()

random.seed(S["SEED"])
torch.manual_seed(S["SEED"])
tok = AutoTokenizer.from_pretrained(S["MODEL"])
tok.pad_token = tok.pad_token or tok.eos_token

with open(DATA) as f:
    text = f.read()
records = json.loads(text) if text.lstrip().startswith("[") else [json.loads(l) for l in text.splitlines() if l.strip()]
need = S["STEPS"] * S["BATCH"] * WORLD
random.Random(S["SEED"]).shuffle(records)
# held out, never trained on: their loss before and after training says whether it learned
held, records = records[:S["HELD_OUT"]], records[S["HELD_OUT"]:]
records = (records * math.ceil(need / max(1, len(records))))[:need]


def encode(r):
    """The prompt and answer as the model's chat template has them; loss on the answer's tokens only."""
    user = r["instruction"] + (f"\n\n{r['input']}" if r.get("input") else "")
    prompt = tok.apply_chat_template([{"role": "user", "content": user}], tokenize=False, add_generation_prompt=True)
    p, a = tok(prompt, add_special_tokens=False)["input_ids"], tok(r["output"] + tok.eos_token, add_special_tokens=False)["input_ids"]
    ids = (p + a)[:S["SEQ_LEN"]]
    return ids, ([-100] * len(p) + a)[:S["SEQ_LEN"]]


def batch(step):
    """This process's share of a step: every process takes different records, so the global batch is
    BATCH x WORLD distinct sequences."""
    start = (step * WORLD + RANK) * S["BATCH"]
    return collate(records[start:start + S["BATCH"]])


def collate(recs):
    rows = [encode(r) for r in recs]
    n = max(len(i) for i, _ in rows)
    ids = torch.tensor([i + [tok.pad_token_id] * (n - len(i)) for i, _ in rows])
    labels = torch.tensor([l + [-100] * (n - len(l)) for _, l in rows])
    mask = torch.tensor([[1] * len(i) + [0] * (n - len(i)) for i, _ in rows])
    return ids.to(DEVICE), labels.to(DEVICE), mask.to(DEVICE)


t_load = time.time()
model = AutoModelForCausalLM.from_pretrained(S["MODEL"], dtype=DTYPE, device_map={"": LOCAL_RANK} if GPU else None, attn_implementation="sdpa")
model.config.use_cache = False
if S["GRAD_CKPT"]:
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
targets = "all-linear" if S["LORA_TARGETS"] == "all-linear" else ["q_proj", "k_proj", "v_proj", "o_proj"]
model = get_peft_model(model, LoraConfig(r=S["LORA_R"], lora_alpha=S["LORA_ALPHA"], lora_dropout=S["LORA_DROPOUT"],
                                         target_modules=targets, task_type="CAUSAL_LM"))
trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
total = sum(p.numel() for p in model.parameters())
load_s = time.time() - t_load
log(f"{S['MODEL']} loaded in {load_s:.0f}s: {total / 1e9:.1f}B parameters, {trainable / 1e6:.0f}M trainable (LoRA r={S['LORA_R']}, {S['LORA_TARGETS']})")
# The LoRA weights start random: from the same seed on every process here, and DDP broadcasts rank
# 0's at wrap time besides, so every process starts from the same adapter.
ddp = DDP(model, device_ids=[LOCAL_RANK] if GPU else None)
params = [p for p in ddp.parameters() if p.requires_grad]
opt = torch.optim.AdamW(params, lr=S["LR"], weight_decay=0.0)
sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: (s + 1) / S["WARMUP"] if s < S["WARMUP"] else
                                          0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * (s - S["WARMUP"]) / max(1, S["STEPS"] - S["WARMUP"]))))
sync = (lambda: torch.cuda.synchronize(DEVICE)) if GPU else (lambda: None)


def held_out_loss():
    """The mean loss over the held-out records' answer tokens, each process taking its share."""
    m = ddp.module
    m.eval()
    tot = torch.zeros(2, dtype=torch.float64, device=DEVICE)
    mine = held[RANK::WORLD]
    with torch.no_grad():
        for i in range(0, len(mine), S["BATCH"]):
            ids, labels, mask = collate(mine[i:i + S["BATCH"]])
            n = (labels[:, 1:] != -100).sum()
            tot += torch.stack([m(input_ids=ids, attention_mask=mask, labels=labels).loss.double() * n, n.double()])
    dist.all_reduce(tot)
    m.train()
    return round(float(tot[0] / tot[1]), 4)


before = held_out_loss()
log(f"held-out loss before training: {before:.4f} ({len(held)} records)")

steps, window, t_train = [], [], time.time()
log(f"training: {S['STEPS']} steps of {S['BATCH']} x {WORLD} sequences of up to {S['SEQ_LEN']} tokens")
for step in range(S["STEPS"]):
    t = time.time()
    ids, labels, mask = batch(step)
    loss = ddp(input_ids=ids, attention_mask=mask, labels=labels).loss
    loss.backward()  # DDP averages the adapter's gradients across the processes here
    grad_norm = torch.nn.utils.clip_grad_norm_(params, 1.0)
    opt.step()
    sched.step()
    opt.zero_grad(set_to_none=True)
    sync()
    # the step's mean loss and its tokens, over every process
    stats = torch.tensor([loss.item(), float(mask.sum()), time.time() - t], device=DEVICE, dtype=torch.float64)
    dist.all_reduce(stats)
    window.append(stats.tolist())
    if (step + 1) % S["LOG_EVERY"] == 0 or step + 1 == S["STEPS"]:
        loss_sum, tokens, secs = (sum(w[i] for w in window) for i in range(3))
        secs /= WORLD  # each process's own time, summed across processes: the mean wall time
        row = {"step": step + 1, "loss": round(loss_sum / WORLD / len(window), 4), "lr": sched.get_last_lr()[0],
               "grad_norm": round(float(grad_norm), 4), "tokens_per_s": round(tokens / secs, 1),
               "tokens_per_s_per_gpu": round(tokens / secs / WORLD, 1), "step_s": round(secs / len(window), 3)}
        steps.append(row)
        log(f"step {row['step']}/{S['STEPS']}  loss {row['loss']:.4f}  {row['tokens_per_s']:.0f} tokens/s "
            f"({row['tokens_per_s_per_gpu']:.0f} per GPU)  {row['step_s']:.2f}s/step  lr {row['lr']:.2e}")
        window = []
train_s = time.time() - t_train
after = held_out_loss()
log(f"held-out loss after training: {after:.4f}")

# Did DDP keep the processes in step? Every process's adapter must be the same, to the last bit.
with torch.no_grad():
    digest = torch.stack([p.detach().double().sum() for p in params]).sum().item()
    norm = math.sqrt(sum(float(p.detach().double().pow(2).sum()) for p in params))
digests = gather(digest)
peaks = gather(round(torch.cuda.max_memory_allocated(DEVICE) / 2**30, 1) if GPU else 0.0)

if RANK == 0:
    gpus = {r["uuid"] for r in ranks}
    first, last = steps[0]["loss"], steps[-1]["loss"]
    checks = [
        {"name": "Every process trained on its own GPU", "ok": (GPU and len(gpus) == WORLD) or (not GPU and os.environ.get("ALLOW_CPU") == "1"),
         "detail": f"{WORLD} processes on {len(gpus)} distinct {'GPUs' if GPU else 'CPUs (ALLOW_CPU)'}: " + ", ".join(sorted({r['gpu'] for r in ranks}))},
        {"name": "The processes' adapters are identical", "ok": len(set(digests)) == 1,
         "detail": "the gradients were averaged at every step" if len(set(digests)) == 1 else f"the adapters differ across processes: {digests}"},
        {"name": "It learned: the loss on held-out records came down", "ok": after < before,
         "detail": f"{before:.3f} before training, {after:.3f} after, on {len(held)} records it never trained on"},
        {"name": "The adapter was saved", "ok": False, "detail": ""},
    ]
    try:
        ddp.module.save_pretrained(os.path.join(OUT, "adapter"))
        tok.save_pretrained(os.path.join(OUT, "adapter"))
        checks[3].update(ok=True, detail=f"{OUT}/adapter")
    except Exception as e:  # a full or missing volume
        checks[3]["detail"] = f"{type(e).__name__}: {e}"
    tps = [s["tokens_per_s"] for s in steps[1:]] or [steps[0]["tokens_per_s"]]  # the first window includes warm-up
    metrics = {"gpus": WORLD, "model": S["MODEL"], "parameters_b": round(total / 1e9, 2), "trainable_m": round(trainable / 1e6, 1),
               "tokens_per_s": round(sum(tps) / len(tps), 1), "tokens_per_s_per_gpu": round(sum(tps) / len(tps) / WORLD, 1),
               "step_s": round(train_s / S["STEPS"], 3), "train_minutes": round(train_s / 60, 1), "load_s": round(load_s),
               "held_out_loss_before": before, "held_out_loss_after": after, "loss_first": first, "loss_last": last, "peak_gpu_memory_gib": max(peaks), "adapter_norm": round(norm, 3)}
    result = {"test": "LoRA Distributed Training Test", "status": "pass" if all(c["ok"] for c in checks) else "fail",
              "checks": checks, "metrics": metrics,
              "env": {"torch": torch.__version__, "cuda": torch.version.cuda or "", "gpu": ranks[0]["gpu"], "processes": WORLD,
                      "nodes": len({r["host"] for r in ranks})}}
    record = {"settings": S, "run": RUN, "ranks": [{**r, "peak_gpu_memory_gib": p} for r, p in zip(ranks, peaks)],
              "steps": steps, "result": result}
    try:
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, "training.json"), "w") as f:
            json.dump(record, f, indent=1)
    except OSError as e:
        log(f"could not write training.json: {e}")
    for c in checks:
        log(f"{'PASS' if c['ok'] else 'FAIL'}  {c['name']}: {c['detail']}")
    print("AIF_RESULT " + json.dumps(result), flush=True)
    if result["status"] != "pass":
        # a run that failed its checks fails the same way again: ask the chart not to retry it
        open(os.environ.get("AIF_NO_RETRY_FILE", os.devnull), "a").close()
    status = 0 if result["status"] == "pass" else 1
else:
    status = 0
dist.barrier()
dist.destroy_process_group()
sys.exit(status)
