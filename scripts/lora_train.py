"""LoRA fine-tune of Qwen2.5-1.5B-Instruct on an instruction dataset, sized for a 6 GiB GPU share: bf16
weights (or 4-bit NF4 with QUANT=nf4), gradient checkpointing, short sequences. Model and dataset
downloads go to $HF_HOME; the adapter, a checkpoint per epoch and training.json go to
$CHECKPOINT_DIR/$RUN_NAME (the run's kept checkpoint volume).

Every setting is an environment variable, recorded in training.json; the defaults reproduce the
original example (rank 16 on the attention projections, constant learning rate, STEPS steps).

  data      DATASET (a Hugging Face dataset, or a JSON Lines file of {instruction, input, output}),
            TRAIN_FROM, MASK_PROMPT (loss on the answers only), VAL_FRACTION (hold out that share of
            the training phrasings: validation loss each epoch, and the best checkpoint is kept)
  stopping  VAL_EVERY (validate every that many steps; with EPOCHS and VAL_FRACTION the default is
            four times an epoch), PATIENCE (stop after that many validation checks without a new
            best; 0 = never stop early), MIN_DELTA (how much lower a validation loss must be to reset
            that count, default 0.005; any lower loss is still kept as the best checkpoint)
  length    STEPS, or EPOCHS (with a file dataset); BATCH; SEQ_LEN; BATCH_MODE (sequential: the
            examples of a batch run one at a time and each counts equally, the default; padded: one
            padded forward pass per batch, examples of similar length batched together, each answer
            token counting equally)
  adapter   LORA_R, LORA_ALPHA, LORA_DROPOUT, LORA_TARGETS (attention | all-linear), RSLORA, DORA,
            LORA_INIT (gaussian | pissa | eva), EVA_BATCHES (how many batches EVA may read, default 8)
  optimiser LR, LR_SCHEDULE (constant | cosine), WARMUP (fraction of the steps), SEED,
            MAX_GRAD_NORM (clip gradients to that norm; 0 = no clipping, the default; the norm
            logged is the one before clipping)

Training and validation loss are both the mean over answer tokens (or every token without
MASK_PROMPT), so the two are directly comparable.
  base      MODEL, QUANT (none | nf4)
"""
import collections, contextlib, hashlib, json, math, os, random, shutil, subprocess, sys, threading, time

QUANT = os.environ.get("QUANT", "none")
LIBS = ["transformers==4.51.3", "peft==0.15.2", "datasets==3.5.0", "accelerate==1.6.0"] + (["bitsandbytes==0.45.5"] if QUANT == "nf4" else [])
print(f"INFO | installing {', '.join(LIBS)} (about a minute)", flush=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-cache-dir", *LIBS], check=True)

# Under a GPU-memory cap (KAI share + HAMi-core) the cap counts everything the process holds, cached
# blocks included. Expandable segments keep fragmentation down, and a per-process fraction makes
# PyTorch free its cache before the cap would refuse an allocation (logged by HAMi-core as an OOM).
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import torch
torch.cuda.set_per_process_memory_fraction(float(os.environ.get("CUDA_MEMORY_FRACTION", "0.9")))
from datasets import load_dataset
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer


def env(name, default, cast=str):
    v = os.environ.get(name, "")
    return cast(v) if v != "" else default


flag = lambda name: os.environ.get(name, "0") in ("1", "true", "yes")

MODEL = env("MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
STEPS = env("STEPS", 60, int)
EPOCHS = env("EPOCHS", 0.0, float)
SEQ = env("SEQ_LEN", 256, int)
BATCH = env("BATCH", 2, int)
DATASET = env("DATASET", "yahma/alpaca-cleaned")
TRAIN_FROM = env("TRAIN_FROM", 0, int)
MASK_PROMPT = flag("MASK_PROMPT")
VAL_FRACTION = env("VAL_FRACTION", 0.0, float)
VAL_EVERY = env("VAL_EVERY", 0, int)
PATIENCE = env("PATIENCE", 0, int)
MIN_DELTA = env("MIN_DELTA", 0.005, float)
MAX_GRAD_NORM = env("MAX_GRAD_NORM", 0.0, float)
BATCH_MODE = env("BATCH_MODE", "sequential")
R = env("LORA_R", 16, int)
ALPHA = env("LORA_ALPHA", 2 * R, int)
DROPOUT = env("LORA_DROPOUT", 0.05, float)
TARGETS = env("LORA_TARGETS", "attention")
RSLORA, DORA = flag("RSLORA"), flag("DORA")
INIT = env("LORA_INIT", "gaussian")
LR = env("LR", 2e-4, float)
SCHEDULE = env("LR_SCHEDULE", "constant")
WARMUP = env("WARMUP", 0.0, float)
SEED = env("SEED", 42, int)
RUN = os.environ.get("RUN_NAME", "lora")
out = os.path.join(os.environ.get("CHECKPOINT_DIR", "/tmp/out"), RUN)
random.seed(SEED)
torch.manual_seed(SEED)


def no_retry(msg):
    """A run that cannot succeed on a retry: exit 3, and leave the marker the training chart's torchrun
    wrapper turns into exit 3 (job.failFastExitCodes), rather than be re-run as it is."""
    print(f"ERROR | {msg}", flush=True)
    with contextlib.suppress(OSError):
        open(os.environ.get("AIF_NO_RETRY_FILE", "/tmp/tj/no-retry"), "w").close()
    sys.exit(3)


@contextlib.contextmanager
def heartbeat(what, every=30):
    """A line every `every` seconds while `what` runs: a download prints nothing for minutes, and a
    log stream that is quiet that long can be closed by a proxy on the way (the log viewer then shows
    Disconnected)."""
    cache = os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface")
    done, t0 = threading.Event(), time.time()
    def size():
        n = 0
        for d, _, fs in os.walk(cache):
            for f in fs:
                try:  # a partial download is renamed as it completes: it can be gone by now
                    n += 0 if os.path.islink(os.path.join(d, f)) else os.path.getsize(os.path.join(d, f))
                except OSError:
                    pass
        return n
    def beat():
        while not done.wait(every):
            print(f"INFO | {what}: {time.time() - t0:.0f}s, {size() / 2**30:.2f} GiB in {cache}", flush=True)
    threading.Thread(target=beat, daemon=True).start()
    try:
        yield
    finally:
        done.set()


free, total = torch.cuda.mem_get_info()
print(f"GPU share: {free / 2**30:.2f} GiB free of {total / 2**30:.2f} GiB visible ({torch.cuda.get_device_name(0)})", flush=True)

# ---- data
source = {"dataset": DATASET, "split": "train"}
if os.path.isfile(DATASET):
    raw = open(DATASET, "rb").read()
    rows = [json.loads(l) for l in raw.decode().splitlines() if l.strip()]
    source.update({"file": os.path.basename(DATASET), "sha256": hashlib.sha256(raw).hexdigest(), "examples": [0, len(rows)]})
    print(f"INFO | {len(rows)} examples from {DATASET} (sha256 {source['sha256'][:12]})", flush=True)
else:
    n = STEPS * BATCH
    source["examples"] = [TRAIN_FROM, TRAIN_FROM + n]
    print(f"INFO | loading examples [{TRAIN_FROM}, {TRAIN_FROM + n}) of {DATASET}", flush=True)
    with heartbeat("loading the dataset"):
        rows = list(load_dataset(DATASET, split=f"train[{TRAIN_FROM}:{TRAIN_FROM + n}]"))

# validation: one phrasing of a fact that has several (its other phrasings stay in training), so the
# validation loss measures learning the fact, not memorising the example; random rows without fact ids
val_rows = []
if VAL_FRACTION > 0:
    want = max(1, round(len(rows) * VAL_FRACTION))
    by_fact = {}
    for i, r in enumerate(rows):
        if r.get("fact"):
            by_fact.setdefault(r["fact"], []).append(i)
    pool = [random.choice(ix) for ix in by_fact.values() if len(ix) >= 3] or list(range(len(rows)))
    random.shuffle(pool)
    held = set(pool[:want])
    val_rows = [r for i, r in enumerate(rows) if i in held]
    rows = [r for i, r in enumerate(rows) if i not in held]
    val_facts = {r.get("fact") for r in val_rows if r.get("fact")}
    train_facts = {r.get("fact") for r in rows if r.get("fact")}
    source["validation"] = {"examples": len(val_rows), "from": "training phrasings of facts with 3 or more",
                            "facts": len(val_facts), "facts_also_in_training": len(val_facts & train_facts),
                            "measures": "new wording of facts the run trains on, not unseen facts" if val_facts else "held-out rows"}
    print(f"INFO | {len(val_rows)} examples held out for validation, {len(rows)} to train on", flush=True)

steps_per_epoch = math.ceil(len(rows) / BATCH)
total_steps = math.ceil(steps_per_epoch * EPOCHS) if EPOCHS else STEPS
epochs = EPOCHS or round(total_steps * BATCH / len(rows), 2)
if not VAL_EVERY and val_rows and EPOCHS:
    VAL_EVERY = max(25, steps_per_epoch // 4)

# ---- model and adapter
print(f"INFO | loading {MODEL}{' in 4-bit NF4' if QUANT == 'nf4' else ''} (first run downloads it to {os.environ.get('HF_HOME', 'the cache')})", flush=True)
with heartbeat(f"loading {MODEL}"):
    tok = AutoTokenizer.from_pretrained(MODEL)
    if QUANT == "nf4":
        from peft import prepare_model_for_kbit_training
        from transformers import BitsAndBytesConfig
        model = AutoModelForCausalLM.from_pretrained(MODEL, device_map={"": 0}, torch_dtype=torch.bfloat16, quantization_config=BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True))
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    else:
        model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.bfloat16).cuda()
        model.gradient_checkpointing_enable()
        model.enable_input_require_grads()


def user_turn(r):
    return (r["instruction"] + "\n" + (r.get("input") or "")).strip()


def encode(r, mask=MASK_PROMPT):
    """An example's ids, and its labels: the same ids, with the question masked out under MASK_PROMPT."""
    msgs = [{"role": "user", "content": user_turn(r)}, {"role": "assistant", "content": r.get("output") or r.get("reference") or ""}]
    full = tok(tok.apply_chat_template(msgs, tokenize=False), return_tensors="pt")["input_ids"]
    lengths.append(full.shape[1])
    ids = full[:, :SEQ]
    labels = ids.clone()
    if mask:
        asked = len(tok(tok.apply_chat_template(msgs[:1], tokenize=False, add_generation_prompt=True))["input_ids"])
        labels[:, :asked] = -100
    return ids, labels


lengths = []  # every encoded example's length before truncation


targets = "all-linear" if TARGETS == "all-linear" else ["q_proj", "k_proj", "v_proj", "o_proj"]
init = {"gaussian": True, "pissa": "pissa_niter_4", "eva": "eva"}.get(INIT)
if init is None:
    no_retry(f"LORA_INIT={INIT} is not one of gaussian, pissa, eva")
kw = {}
if INIT == "eva":
    from peft import EvaConfig
    kw["eva_config"] = EvaConfig(rho=2.0)
cfg = LoraConfig(r=R, lora_alpha=ALPHA, lora_dropout=DROPOUT, task_type="CAUSAL_LM", target_modules=targets,
                 use_rslora=RSLORA, use_dora=DORA, init_lora_weights=init, **kw)
model = get_peft_model(model, cfg, low_cpu_mem_usage=INIT == "eva")
pissa_init = None
if INIT == "pissa":
    # PiSSA moves the base weights' principal directions into the adapter (B0 A0) and trains on the
    # residual base W - s B0 A0. An adapter saved as it is only works on that residual, which PEFT
    # recomputes, differently (randomised SVD), when it loads one. So every save is converted, on the
    # CPU, into a plain LoRA adapter for the original base model: s (B A - B0 A0) = s' [B, -B0][A; A0],
    # twice the rank, with alpha scaled so the effective scale s' equals s. (PEFT's own conversion
    # loads a second adapter on the GPU, which a training run's share has no room for.)
    pissa_init = {n.replace(".default", ""): p.detach().to("cpu", copy=True) for n, p in model.named_parameters() if ".lora_" in n}


def save(path):
    model.save_pretrained(path)
    if not pissa_init:
        return
    from safetensors.torch import load_file, save_file
    f = os.path.join(path, "adapter_model.safetensors")
    w = load_file(f)
    for k in [k for k in w if k.endswith("lora_A.weight")]:
        kb = k.replace("lora_A", "lora_B")
        a0, b0 = pissa_init[k].to(w[k].dtype), pissa_init[kb].to(w[kb].dtype)
        w[k], w[kb] = torch.cat([w[k], a0], 0), torch.cat([w[kb], -b0], 1)
    save_file(w, f, metadata={"format": "pt"})
    c = json.load(open(os.path.join(path, "adapter_config.json")))
    c.update(r=2 * R, lora_alpha=ALPHA * (math.sqrt(2) if RSLORA else 2), init_lora_weights=True)
    json.dump(c, open(os.path.join(path, "adapter_config.json"), "w"), indent=2)


if INIT == "eva":
    # EVA starts each adapter in the directions that explain the layer's inputs on this data
    from peft import initialize_lora_eva_weights
    tok.padding_side = "right"
    # EVA reads batches until every layer's directions settle, or the batches run out: on a small GPU
    # share with all-linear and a high rank that can take far longer than training, so it is capped
    eva_batches, eva_size = env("EVA_BATCHES", 8, int), max(BATCH, 8)
    pool = random.sample(rows, min(len(rows), eva_batches * eva_size))
    texts = [tok.apply_chat_template([{"role": "user", "content": user_turn(r)}, {"role": "assistant", "content": r.get("output") or ""}],
                                     tokenize=False) for r in pool]
    batches = [tok(texts[i:i + eva_size], padding=True, truncation=True, max_length=SEQ, return_tensors="pt").to("cuda")
               for i in range(0, len(texts), eva_size)]
    t_eva = time.time()

    class Logged:
        """The batches EVA reads, with a line per batch: EVA itself reports nothing while it works."""
        def __init__(self, items):
            self.items = items
        def __len__(self):
            return len(self.items)
        def __iter__(self):
            for i, b in enumerate(self.items, 1):
                print(f"INFO | EVA initialisation: batch {i} of {len(self.items)}, {time.time() - t_eva:.0f}s", flush=True)
                yield b

    initialize_lora_eva_weights(model, dataloader=Logged([dict(b) for b in batches]), show_progress_bar=False)
    source["eva"] = {"batches": len(batches), "batch_size": eva_size, "seconds": round(time.time() - t_eva)}
    print(f"INFO | EVA initialisation: {len(batches)} batches of {eva_size} in {time.time() - t_eva:.0f}s", flush=True)
model.print_trainable_parameters()
trainable, all_params = model.get_nb_trainable_parameters()
scale = ALPHA / (math.sqrt(R) if RSLORA else R)

enc = [encode(r) for r in rows]
val_enc = [encode(r, mask=True) for r in val_rows]
# the answer is the end of an example, so truncation at SEQ_LEN cuts the answer: the run then teaches
# a fact with its end missing
cut = sum(n > SEQ for n in lengths)
source["truncation"] = {"seq_len": SEQ, "examples_cut": cut, "of": len(lengths), "longest": max(lengths)}
if cut:
    print(f"WARN | {cut} of {len(lengths)} examples are longer than SEQ_LEN={SEQ} (longest {max(lengths)} tokens): their answers are cut "
          f"short; raise SEQ_LEN to teach them whole", flush=True)
else:
    print(f"INFO | every example fits SEQ_LEN={SEQ} (longest {max(lengths)} tokens)", flush=True)
answer_tokens = lambda labels: int((labels[:, 1:] != -100).sum())
if BATCH_MODE not in ("sequential", "padded"):
    no_retry(f"BATCH_MODE={BATCH_MODE} is not one of sequential, padded")
pad_id = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id


def collate(items):
    """A padded batch on the GPU: ids padded on the right, padding masked out of attention and loss."""
    longest = max(ids.shape[1] for ids, _ in items)
    ids = torch.full((len(items), longest), pad_id, dtype=torch.long)
    labels = torch.full((len(items), longest), -100, dtype=torch.long)
    mask = torch.zeros((len(items), longest), dtype=torch.long)
    for k, (i, l) in enumerate(items):
        ids[k, :i.shape[1]], labels[k, :l.shape[1]], mask[k, :i.shape[1]] = i[0], l[0], 1
    return ids.cuda(), mask.cuda(), labels.cuda()

opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR)
warm = int(total_steps * WARMUP)


def lr_at(step):
    if step < warm:
        return (step + 1) / warm
    if SCHEDULE == "cosine":
        return 0.5 * (1 + math.cos(math.pi * (step - warm) / max(1, total_steps - warm)))
    return 1.0


sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_at)
print(f"INFO | training: {total_steps} steps ({epochs} epochs) of batch {BATCH} ({BATCH_MODE}), sequences up to {SEQ} tokens, loss on "
      f"{'the answers' if MASK_PROMPT else 'whole conversations'}; LoRA r={R} alpha={ALPHA} on {TARGETS}"
      f"{', rsLoRA' if RSLORA else ''}{', DoRA' if DORA else ''} (scale {scale:.3f}), init {INIT}; {trainable:,} trainable parameters "
      f"({100 * trainable / all_params:.2f}%); lr {LR} {SCHEDULE}, warm-up {warm} steps"
      + (f"; validation every {VAL_EVERY} steps" if val_enc and VAL_EVERY else "")
      + (f", stopping after {PATIENCE} checks without a gain of {MIN_DELTA}" if val_enc and PATIENCE else ""), flush=True)


@torch.no_grad()
def val_loss():
    model.eval()
    total = tokens = 0
    for ids, labels in val_enc:
        n = int((labels[:, 1:] != -100).sum())
        if n:
            total += model(input_ids=ids.cuda(), labels=labels.cuda()).loss.item() * n
            tokens += n
    model.train()
    return total / tokens if tokens else float("nan")


history = []
model.train()
t0 = time.time()
order = []
step = 0
epoch = 0
point_loss = point_tokens = 0.0
recent = collections.deque(maxlen=50)   # (loss x tokens, tokens) of the last 50 steps
seen_examples = seen_tokens = 0
train_time = 0.0
grad_norm = float("nan")
best = None            # the validation point with the lowest loss; its adapter is in best/
gain_ref = None        # the loss at the last improvement of at least MIN_DELTA: what patience counts from
since_best = 0         # validation checks since that improvement
stopped_early = None
while step < total_steps:
    if not order:
        order = list(range(len(enc)))
        random.shuffle(order)
        if BATCH_MODE == "padded":
            # batches of similar length, so little of each is padding: sort within windows of 50
            # batches, cut into batches, and shuffle the batches
            win = BATCH * 50
            order = [i for w in range(0, len(order), win) for i in sorted(order[w:w + win], key=lambda i: enc[i][0].shape[1])]
            groups = [order[i:i + BATCH] for i in range(0, len(order), BATCH)]
            random.shuffle(groups)
            order = [i for g in reversed(groups) for i in reversed(g)]  # popped from the end
    batch = [enc[order.pop()] for _ in range(min(BATCH, len(order)))]
    t_step = time.time()
    try:
        if BATCH_MODE == "padded":
            ids, mask, labels = collate(batch)
            loss = model(input_ids=ids, attention_mask=mask, labels=labels).loss
            losses = [loss] * len(batch)  # one loss for the batch: logged against its whole token count below
        else:
            losses = [model(input_ids=ids.cuda(), labels=labels.cuda()).loss for ids, labels in batch]
            loss = sum(losses) / len(batch)
        loss.backward()
    except torch.OutOfMemoryError as e:
        no_retry(f"out of GPU memory at step {step + 1}: {str(e).splitlines()[0][:200]}; lower BATCH or SEQ_LEN, "
                 f"or give the run a larger GPU share")
    # clip_grad_norm_ returns the norm; with no limit set it leaves the gradients as they are
    grad_norm = torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], MAX_GRAD_NORM or float("inf")).item()
    opt.step()
    sched.step()
    opt.zero_grad()
    train_time += time.time() - t_step
    # token-weighted, like validation: each example's mean loss times its answer tokens
    toks = [answer_tokens(labels) for _, labels in batch]
    step_sum = loss.item() * sum(toks) if BATCH_MODE == "padded" else sum(l.item() * n for l, n in zip(losses, toks))
    point_loss += step_sum
    point_tokens += sum(toks)
    recent.append((step_sum, sum(toks)))
    seen_examples += len(batch)
    seen_tokens += sum(toks)
    step += 1
    if step % 10 == 0 or step == total_steps:
        avg = sum(a for a, _ in recent) / max(1, sum(n for _, n in recent))
        print(f"INFO | step {step}/{total_steps} | loss={loss.item():.3f} | avg{len(recent)}={avg:.3f} | grad norm {grad_norm:.2f} | "
              f"lr {sched.get_last_lr()[0]:.2e} | peak {torch.cuda.max_memory_allocated() / 2**30:.2f} GiB | "
              f"{seen_examples / train_time:.1f} examples/s, {seen_tokens / train_time:.0f} tokens/s | {time.time() - t0:.0f}s", flush=True)
    epoch_end = step % steps_per_epoch == 0 or step == total_steps
    if not (epoch_end or (val_enc and VAL_EVERY and step % VAL_EVERY == 0)):
        continue
    # a validation point: at every epoch's end, and every VAL_EVERY steps
    entry = {"step": step, "epoch": round(step / steps_per_epoch, 2), "train_loss": round(point_loss / max(1, point_tokens), 4),
             "grad_norm": round(grad_norm, 3)}
    point_loss = point_tokens = 0.0
    if val_enc:
        entry["val_loss"] = round(val_loss(), 4)
        # any lower loss is the new best checkpoint; only a gain of MIN_DELTA resets patience
        if best is None or entry["val_loss"] < best["val_loss"]:
            best = entry
            save(os.path.join(out, "best"))
        if gain_ref is None or entry["val_loss"] < gain_ref - MIN_DELTA:
            gain_ref, since_best = entry["val_loss"], 0
        else:
            since_best += 1
    if epoch_end:
        epoch += 1
        save(os.path.join(out, f"epoch-{epoch}"))
    history.append(entry)
    whole = step % steps_per_epoch == 0
    print(f"INFO | {'epoch ' + str(epoch) if whole else 'step ' + str(step)} (epoch {entry['epoch']}): train loss {entry['train_loss']}"
          + (f", validation loss {entry['val_loss']}" + (" (best)" if best is entry else "")
             + (f" ({since_best} check{'s' if since_best > 1 else ''} without a gain of {MIN_DELTA})" if since_best else "") if val_enc else ""),
          flush=True)
    if val_enc and PATIENCE and since_best >= PATIENCE:
        stopped_early = step
        print(f"INFO | stopping early at step {step}: {PATIENCE} validation check{'s' if PATIENCE > 1 else ''} without a gain of {MIN_DELTA}", flush=True)
        break

# the adapter at the top of the run's directory: the checkpoint with the lowest validation loss, else the last
if best is None:
    best = history[-1]
    save(os.path.join(out, "best"))
for f in os.listdir(os.path.join(out, "best")):
    shutil.copy(os.path.join(out, "best", f), os.path.join(out, f))
shutil.rmtree(os.path.join(out, "best"))
selection = {"criterion": "min_validation_loss" if val_enc else "last", "step": best["step"], "epoch": best["epoch"],
             "value": best.get("val_loss")}
print(f"INFO | selected checkpoint: step {best['step']}, epoch {best['epoch']}"
      + (f", validation loss {best['val_loss']} (the lowest)" if val_enc else " (the last; no validation set)"), flush=True)
print(f"INFO | throughput: {seen_examples / train_time:.1f} examples/s, {seen_tokens / train_time:.0f} answer tokens/s over {train_time:.0f}s of training",
      flush=True)

# provenance, beside the adapter: what it was trained on and how, so an evaluation can be held out
import peft, transformers
with open(os.path.join(out, "training.json"), "w") as f:
    json.dump({"base_model": MODEL, "quant": QUANT, **source, "steps": total_steps, "epochs": epochs, "batch": BATCH, "seq_len": SEQ,
               "batch_mode": BATCH_MODE, "mask_prompt": MASK_PROMPT,
               "lora": {"r": R, "alpha": ALPHA, "dropout": DROPOUT, "targets": TARGETS, "rslora": RSLORA, "dora": DORA, "init": INIT,
                        "effective_scale": round(scale, 4),
                        "saved_as": f"plain LoRA, rank {2 * R}, converted from PiSSA for the original base model" if pissa_init else "as trained"},
               "parameters": {"trainable": trainable, "total": all_params, "trainable_percent": round(100 * trainable / all_params, 3)},
               "optimiser": {"lr": LR, "schedule": SCHEDULE, "warmup_steps": warm, "seed": SEED, "max_grad_norm": MAX_GRAD_NORM or None},
               "loss": "mean over answer tokens" if MASK_PROMPT else "mean over all tokens",
               "history": history, "selection": selection, "best_epoch": best["epoch"],
               "stopping": {"val_every": VAL_EVERY, "patience": PATIENCE, "min_delta": MIN_DELTA, "stopped_early_at": stopped_early},
               "throughput": {"examples_per_s": round(seen_examples / train_time, 2), "answer_tokens_per_s": round(seen_tokens / train_time),
                              "training_seconds": round(train_time), "peak_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2)},
               "libraries": {"transformers": transformers.__version__, "peft": peft.__version__},
               "run": RUN, "finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, f, indent=2)
print(f"adapter saved to {out}: {sorted(os.listdir(out))}", flush=True)
