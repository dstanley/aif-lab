"""Drive the data lifecycle of one LoRA training run through S3-compatible storage:

  upload    the dataset, from this workstation, through presigned URLs (no storage credentials here
            beyond the platform stand-in's)
  stage     the dataset onto a read-only RWX volume, by a Data Mover Job with presigned GETs
  train     a LoRA run (a recipe from ../lora) reading its dataset from that volume
  collect   the run's adapter and records from its checkpoint volume to S3, by an inventory Job and an
            upload Job with presigned multipart URLs; then the run volume is deleted
  archive   the run's artifacts to the archive bucket, by a Data Mover Job that holds the credentials,
            verifying every copy before deleting the active one
  restore   the artifacts back to the active bucket, verified
  evaluate  stage the restored adapter onto a volume and evaluate it (an evaluation set from ../lora)

This script plays the platform's part (the operator API of docs/design/data-lifecycle.md in the aif
repo): it holds the storage credentials, presigns URLs scoped to one object or part, completes
multipart uploads, writes manifests and verifies objects. The Jobs it starts in the project's
namespace receive URLs, never credentials.

Usage: python lifecycle.py <step> [...]   (see --help). Settings come from the environment; see README.
"""
import argparse
import atexit
import base64
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

import boto3
from botocore.config import Config

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LORA = os.path.join(os.path.dirname(ROOT), "lora")

CTX = os.environ.get("AIF_CONTEXT")
PROJECT = os.environ.get("AIF_PROJECT", "default")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "http://seaweedfs-s3.seaweedfs:8333")         # as pods reach it
S3_LOCAL = os.environ.get("S3_LOCAL_ENDPOINT", "")                                       # as this machine reaches it; unset: port-forward S3_SERVICE
S3_SERVICE = os.environ.get("S3_SERVICE", "seaweedfs/seaweedfs-s3:8333")                  # port-forwarded when S3_LOCAL is local
CREDS = os.environ.get("S3_CREDENTIALS_SECRET", "seaweedfs/aif-lab-s3-config")            # <namespace>/<secret>, key seaweedfs_s3_config
ACTIVE = os.environ.get("ACTIVE_BUCKET", "aif")
ARCHIVE = os.environ.get("ARCHIVE_BUCKET", "aif-cold")
RWX_CLASS = os.environ.get("RWX_STORAGE_CLASS", "seaweedfs-rwx")
RWO_CLASS = os.environ.get("RWO_STORAGE_CLASS", "longhorn")
MOVER_NODES = [n for n in os.environ.get("MOVER_NODES", "").split(",") if n]               # nodes that can mount the RWX class
IMAGE = os.environ.get("MOVER_IMAGE", "registry.suse.com/bci/python:3.12")
PART = int(os.environ.get("PART_MIB", "8")) << 20
URL_TTL = 3600
MOVER_NS, CRED_SECRET = CREDS.split("/")
RESULTS = os.path.join(ROOT, "results", "steps.jsonl")


def kubectl(*args, input=None, check=True):
    cmd = ["kubectl"] + (["--context", CTX] if CTX else []) + list(args)
    r = subprocess.run(cmd, input=input, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"kubectl {' '.join(args[:3])}: {r.stderr.strip()}")
    return r.stdout


# ── the platform's side: credentials, presigning, completing, verifying ─────────────────────────

def _credentials():
    raw = kubectl("-n", MOVER_NS, "get", "secret", CRED_SECRET, "-o", "jsonpath={.data.seaweedfs_s3_config}")
    c = json.loads(base64.b64decode(raw))["identities"][0]["credentials"][0]
    return c["accessKey"], c["secretKey"]


def _client(endpoint):
    ak, sk = _credentials()
    return boto3.client("s3", endpoint_url=endpoint, aws_access_key_id=ak, aws_secret_access_key=sk, region_name="us-east-1",
                        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}))


def _port_forward():
    """When S3_LOCAL_ENDPOINT is unset, port-forward S3_SERVICE on a free local port for this process
    (a port-forward left running from earlier can accept connections and then drop them)."""
    global S3_LOCAL
    if os.environ.get("S3_LOCAL_ENDPOINT"):
        return
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    ns, svc = S3_SERVICE.split("/")
    name, rport = svc.split(":")
    pf = subprocess.Popen(["kubectl"] + (["--context", CTX] if CTX else []) + ["-n", ns, "port-forward", f"svc/{name}", f"{port}:{rport}"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    atexit.register(pf.terminate)
    for _ in range(60):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                S3_LOCAL = f"http://127.0.0.1:{port}"
                return
        time.sleep(0.25)
    raise RuntimeError(f"cannot port-forward {S3_SERVICE}")


class Platform:
    """The operator API's part, held in this process: it alone has the storage credentials."""

    def __init__(self):
        _port_forward()
        self.s3 = _client(S3_LOCAL)               # for the platform's own reads and writes
        self.presign_pod = _client(S3_ENDPOINT)   # signs URLs for pods (offline: no connection made)
        self.presign_here = self.s3               # signs URLs for this workstation
        for b in (ACTIVE, ARCHIVE):
            try:
                self.s3.head_bucket(Bucket=b)
            except Exception:
                self.s3.create_bucket(Bucket=b)

    def plan_put(self, bucket, prefix, files, signer):
        """Presigned single-part or multipart uploads for each file, scoped to its key."""
        out = []
        for f in files:
            key = prefix + f["path"]
            if f["size"] <= PART:
                out.append({**f, "url": signer.generate_presigned_url("put_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=URL_TTL)})
            else:
                uid = self.s3.create_multipart_upload(Bucket=bucket, Key=key)["UploadId"]
                n = (f["size"] + PART - 1) // PART
                out.append({**f, "uploadId": uid, "partSize": PART, "parts": [
                    {"number": i, "url": signer.generate_presigned_url("upload_part", Params={"Bucket": bucket, "Key": key, "UploadId": uid, "PartNumber": i}, ExpiresIn=URL_TTL)}
                    for i in range(1, n + 1)]})
        return out

    def complete(self, bucket, prefix, uploaded):
        for u in uploaded:
            if "uploadId" in u:
                self.s3.complete_multipart_upload(Bucket=bucket, Key=prefix + u["path"], UploadId=u["uploadId"],
                                                  MultipartUpload={"Parts": u["parts"]})

    def write_manifest(self, bucket, prefix, manifest):
        self.s3.put_object(Bucket=bucket, Key=prefix + ".aif-manifest.json", Body=json.dumps(manifest, indent=1).encode())

    def read_manifest(self, bucket, prefix):
        return json.load(self.s3.get_object(Bucket=bucket, Key=prefix + ".aif-manifest.json")["Body"])

    def verify(self, bucket, prefix, manifest, job):
        """The Verifying phase: a Data Mover Job reads every object back through presigned GETs and
        compares its SHA-256 with the manifest. Returns the mismatched paths and the Job's result."""
        res, wall = mover(job, "verify", {"objects": self.plan_get(bucket, prefix, manifest)})
        return res["mismatched"], {**res, "job_seconds": wall}

    def plan_get(self, bucket, prefix, manifest):
        return [{**o, "url": self.presign_pod.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": prefix + o["path"]}, ExpiresIn=URL_TTL)}
                for o in manifest["objects"]]


# ── Data Mover Jobs ────────────────────────────────────────────────────────────────────────────

def mover(name, op, plan, namespace=PROJECT, volume=None, read_only=True, credentials=False):
    """Run one Data Mover Job and return its AIF_MOVER result and wall time."""
    kubectl("-n", namespace, "delete", "job", name, "--ignore-not-found", "--wait=true")
    cm = kubectl("-n", namespace, "create", "configmap", f"{name}-plan", f"--from-file=mover.py={HERE}/mover.py",
                 "--from-literal=plan.json=" + json.dumps(plan), "--dry-run=client", "-o", "json")
    kubectl("apply", "-f", "-", input=cm)
    mounts, vols = [{"name": "plan", "mountPath": "/plan"}], [{"name": "plan", "configMap": {"name": f"{name}-plan"}}]
    env = [{"name": "MOVER_OP", "value": op}]
    if volume:
        mounts.append({"name": "data", "mountPath": "/data", "readOnly": read_only})
        vols.append({"name": "data", "persistentVolumeClaim": {"claimName": volume, "readOnly": read_only}})
    cmd = "python3 /plan/mover.py"
    if credentials:  # only copy (archive, restore): the platform's namespace, with the storage credentials
        mounts.append({"name": "s3", "mountPath": "/etc/s3", "readOnly": True})
        vols.append({"name": "s3", "secret": {"secretName": CRED_SECRET}})
        env.append({"name": "S3_CONFIG", "value": "/etc/s3/seaweedfs_s3_config"})
        cmd = "pip install -q --disable-pip-version-check boto3==1.35.36 2>/dev/null && " + cmd
    affinity = {"nodeAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": {"nodeSelectorTerms": [
        {"matchExpressions": [{"key": "kubernetes.io/hostname", "operator": "In", "values": MOVER_NODES}]}]}}} if MOVER_NODES else None
    job = {"apiVersion": "batch/v1", "kind": "Job",
           "metadata": {"name": name, "namespace": namespace, "labels": {"app": "aif-data-mover", "aif-data-mover/op": op}},
           "spec": {"backoffLimit": 0, "ttlSecondsAfterFinished": 86400, "template": {
               "metadata": {"labels": {"app": "aif-data-mover"}},
               "spec": {"restartPolicy": "Never", **({"affinity": affinity} if affinity else {}),
                        "containers": [{"name": "mover", "image": IMAGE, "command": ["/bin/sh", "-ec", cmd], "env": env, "volumeMounts": mounts,
                                        "resources": {"requests": {"cpu": "500m", "memory": "256Mi"}, "limits": {"memory": "1Gi"}}}],
                        "volumes": vols}}}}
    t0 = time.time()
    kubectl("apply", "-f", "-", input=json.dumps(job))
    while True:
        s = json.loads(kubectl("-n", namespace, "get", "job", name, "-o", "json"))["status"]
        if s.get("succeeded") or s.get("failed"):
            break
        time.sleep(3)
    logs = kubectl("-n", namespace, "logs", f"job/{name}", check=False)
    line = next((x for x in logs.splitlines() if x.startswith("AIF_MOVER ")), None)
    if not s.get("succeeded") or not line:
        raise RuntimeError(f"mover {name} failed:\n{logs[-2000:]}")
    return json.loads(line[len("AIF_MOVER "):]), round(time.time() - t0, 1)


def pvc(name, cls, size, mode):
    kubectl("apply", "-f", "-", input=json.dumps({"apiVersion": "v1", "kind": "PersistentVolumeClaim",
            "metadata": {"name": name, "namespace": PROJECT, "labels": {"app": "aif-data-lifecycle"}},
            "spec": {"accessModes": [mode], "storageClassName": cls, "resources": {"requests": {"storage": size}}}}))


def record(step, **facts):
    os.makedirs(os.path.dirname(RESULTS), exist_ok=True)
    row = {"step": step, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **facts}
    with open(RESULTS, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(json.dumps(row, indent=1))


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dataset_prefix(name, version):
    return f"{PROJECT}/datasets/{name}/{version}/"


def run_prefix(run):
    return f"{PROJECT}/runs/{run}/"


# ── the steps ──────────────────────────────────────────────────────────────────────────────────

def upload(src, name, version):
    """datasets.upload: this workstation sends the files with presigned URLs and a manifest."""
    p = Platform()
    files = []
    for d, _, names in os.walk(src):
        for n in sorted(names):
            path = os.path.join(d, n)
            files.append({"path": os.path.relpath(path, src), "size": os.path.getsize(path), "sha256": sha256_file(path)})
    prefix = dataset_prefix(name, version)
    t0 = time.time()
    plan = p.plan_put(ACTIVE, prefix, files, p.presign_here)       # the platform presigns: the client gets URLs only
    done = []
    for o in plan:                                                  # the client: plain HTTP, no credentials
        with open(os.path.join(src, o["path"]), "rb") as f:
            if "url" in o:
                urllib.request.urlopen(urllib.request.Request(o["url"], data=f.read(), method="PUT"), timeout=300).read()
                done.append({"path": o["path"]})
            else:
                parts = []
                for part in o["parts"]:
                    r = urllib.request.urlopen(urllib.request.Request(part["url"], data=f.read(PART), method="PUT"), timeout=300)
                    parts.append({"PartNumber": part["number"], "ETag": r.headers["ETag"]})
                done.append({"path": o["path"], "uploadId": o["uploadId"], "parts": parts})
    t1 = time.time()
    p.complete(ACTIVE, prefix, done)
    manifest = {"kind": "dataset", "name": name, "version": version, "project": PROJECT, "objects": files}
    p.write_manifest(ACTIVE, prefix, manifest)
    bad, ver = p.verify(ACTIVE, prefix, manifest, f"verify-ds-{name}-{version}")
    record("upload", dataset=f"{name}/{version}", files=len(files), bytes=sum(f["size"] for f in files),
           multipart=sum("uploadId" in o for o in plan), seconds=round(t1 - t0, 1), verify=ver,
           mismatched=bad, location=f"s3://{ACTIVE}/{prefix}")


def stage(name, version, volume):
    """A stage DataTransfer: the dataset onto an RWX volume, read-only for runs, verified."""
    p = Platform()
    prefix = dataset_prefix(name, version)
    manifest = p.read_manifest(ACTIVE, prefix)
    pvc(volume, RWX_CLASS, "1Gi", "ReadWriteMany")
    res, wall = mover(f"stage-{volume}", "get", {"dir": "/data", "objects": p.plan_get(ACTIVE, prefix, manifest), "manifest": manifest},
                      volume=volume, read_only=False)
    record("stage", dataset=f"{name}/{version}", volume=volume, job_seconds=wall, **res)


def train(run, recipe_name, volume, dataset_file):
    """A LoRA run whose dataset comes from the staged volume, not a ConfigMap."""
    sys.path.insert(0, os.path.join(LORA, "src"))
    from lora_study import recipes, run as lrun
    recipe = recipes.load(recipe_name)
    env = recipes.env(recipe, run)
    env["DATASET"] = f"/mnt/dataset/{dataset_file}"
    ai = lrun.client()
    t0 = time.time()
    r = ai.runs.create(profile=os.environ.get("AIF_PROFILE", "shared-gpu-dev"), name=run, image=lrun.IMAGE, gpu_memory=6,
                       runtime_hours=2, config_map=recipe["configmap"], env=env, dataset=volume)
    state = r.wait(timeout=3 * 3600)
    record("train", run=run, recipe=recipe_name, dataset_volume=volume, state=str(state), seconds=round(time.time() - t0, 1))


def collect(run, keep=("adapter_config.json", "adapter_model.safetensors", "training.json")):
    """A collect DataTransfer: what the artifact policy keeps, from the run volume to S3."""
    p = Platform()
    volume = f"{run}-checkpoints"
    inv, w1 = mover(f"inventory-{run}", "inventory", {"dir": f"/data/{run}"}, volume=volume)
    # the artifact policy: the final adapter and the run's record; intermediate checkpoints (epoch-*)
    # stay on the run volume and go with it
    files = [f for f in inv["files"] if "/" not in f["path"] and f["path"] in keep]
    skipped = [f["path"] for f in inv["files"] if f not in files]
    prefix = run_prefix(run)
    plan = p.plan_put(ACTIVE, prefix, files, p.presign_pod)
    res, w2 = mover(f"collect-{run}", "put", {"dir": f"/data/{run}", "objects": plan}, volume=volume)
    p.complete(ACTIVE, prefix, res["uploaded"])
    manifest = {"kind": "run-artifacts", "run": run, "project": PROJECT, "objects": files}
    p.write_manifest(ACTIVE, prefix, manifest)
    bad, ver = p.verify(ACTIVE, prefix, manifest, f"verify-{run}")
    if not bad:
        kubectl("-n", PROJECT, "delete", "pvc", volume, "--wait=false")
    record("collect", run=run, files=len(files), bytes=sum(f["size"] for f in files), multipart=sum("uploadId" in o for o in plan),
           left_behind=skipped, inventory_job_seconds=w1, upload_job_seconds=w2, upload_seconds=res["seconds"],
           verify=ver, mismatched=bad, run_volume_deleted=not bad, location=f"s3://{ACTIVE}/{prefix}")


def move(run, op):
    """archive (Active → Archive, then delete Active) or restore (Archive → Active): a copy Job with credentials."""
    src, dst = (ACTIVE, ARCHIVE) if op == "archive" else (ARCHIVE, ACTIVE)
    prefix = run_prefix(run)
    res, wall = mover(f"{op}-{run}", "copy", {"endpoint": S3_ENDPOINT, "sourceBucket": src, "sourcePrefix": prefix,
                                              "destBucket": dst, "destPrefix": prefix, "deleteSource": op == "archive"},
                      namespace=MOVER_NS, credentials=True)
    record(op, run=run, source=f"s3://{src}/{prefix}", destination=f"s3://{dst}/{prefix}", job_seconds=wall, **res)


def evaluate(run, label):
    """Stage the restored adapter onto a new volume and evaluate it with ../lora's evaluation."""
    p = Platform()
    volume = f"{run}-restored"   # a new volume: the run's own may still be held by its finished pods
    prefix = run_prefix(run)
    manifest = p.read_manifest(ACTIVE, prefix)
    pvc(volume, RWO_CLASS, "2Gi", "ReadWriteOnce")
    res, wall = mover(f"stage-{volume}", "get", {"dir": f"/data/{run}", "objects": p.plan_get(ACTIVE, prefix, manifest)},
                      volume=volume, read_only=False)
    sys.path.insert(0, os.path.join(LORA, "src"))
    from lora_study import run as lrun
    cm, f, groups = lrun.EVALS[label]
    env = {"HF_HOME": "/scratch/hf", "EVAL_DATASET": f"/mnt/config/{f}", "EVAL_LABEL": label, "EVAL_GROUPS": groups,
           "MAX_NEW_TOKENS": "200", "TRAIN_DATASET": "/mnt/config/suse-train-v1.jsonl"}
    t0 = time.time()
    r = lrun._submit(lrun.client(), f"{run}-eval-{lrun.SHORT.get(label, label)}", cm, env, gib=6, hours=2, checkpoints=volume)
    state = r.wait(timeout=3 * 3600)
    rep = r.result()
    record("evaluate", run=run, eval_set=label, volume=volume, staged_files=res["files"], stage_job_seconds=wall,
           mismatched=res["mismatched"], state=str(state), seconds=round(time.time() - t0, 1),
           checks=[{"name": c.get("name"), "ok": c.get("ok"), "detail": c.get("detail")} for c in (rep or {}).get("checks", [])])


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = a.add_subparsers(dest="step", required=True)
    s = sub.add_parser("upload"); s.add_argument("src"); s.add_argument("--name", required=True); s.add_argument("--version", required=True)
    s = sub.add_parser("stage"); s.add_argument("--name", required=True); s.add_argument("--version", required=True); s.add_argument("--volume", required=True)
    s = sub.add_parser("train"); s.add_argument("run"); s.add_argument("--recipe", required=True); s.add_argument("--volume", required=True); s.add_argument("--file", required=True)
    s = sub.add_parser("collect"); s.add_argument("run")
    s = sub.add_parser("archive"); s.add_argument("run")
    s = sub.add_parser("restore"); s.add_argument("run")
    s = sub.add_parser("evaluate"); s.add_argument("run"); s.add_argument("--set", default="taught")
    x = a.parse_args()
    {"upload": lambda: upload(x.src, x.name, x.version), "stage": lambda: stage(x.name, x.version, x.volume),
     "train": lambda: train(x.run, x.recipe, x.volume, x.file), "collect": lambda: collect(x.run),
     "archive": lambda: move(x.run, "archive"), "restore": lambda: move(x.run, "restore"),
     "evaluate": lambda: evaluate(x.run, x.set)}[x.step]()
