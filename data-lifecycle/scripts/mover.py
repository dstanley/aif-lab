"""The Data Mover: one script for every operation, run in a Job.

Operations, chosen by MOVER_OP:

  get        Download presigned GET URLs into a directory and verify each file's SHA-256 against the
             plan (staging a dataset onto a volume; restoring artifacts onto a volume). No credentials.
  inventory  Walk a directory and report each file's size and SHA-256 (the first half of collecting a
             run's outputs: the platform needs sizes before it can presign multipart uploads).
  put        Upload files with presigned single-part or multipart URLs and report the parts' ETags
             (the second half of collecting). No credentials.
  verify     Read objects back through presigned GET URLs and compare each SHA-256 with the manifest
             (the Verifying phase, run next to the store rather than through the platform's own link).
             No credentials.
  copy       Copy objects from one bucket and prefix to another server-side, verify the copies'
             SHA-256 against the manifest, and optionally delete the source (archive and restore).
             The only operation that holds storage credentials, so it runs in the platform's namespace.

The plan comes from /plan/plan.json (a ConfigMap written by the platform). The result is one line,
"AIF_MOVER <json>", on standard output, which the platform reads from the Job's log.
"""
import hashlib
import json
import os
import sys
import time
import urllib.request

PLAN = json.load(open(os.environ.get("MOVER_PLAN", "/plan/plan.json")))
OP = os.environ["MOVER_OP"]
CHUNK = 1 << 20


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(CHUNK), b""):
            h.update(b)
    return h.hexdigest()


def http(method, url, data=None):
    req = urllib.request.Request(url, data=data, method=method)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return r
        except Exception as e:  # retried: transient network errors on a busy store
            if attempt == 4:
                raise
            print(f"retry {attempt + 1} {method}: {e}", file=sys.stderr, flush=True)
            time.sleep(2 ** attempt)


def op_get():
    root = PLAN["dir"]
    out, t0, nbytes = [], time.time(), 0
    for o in PLAN["objects"]:
        dst = os.path.join(root, o["path"])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        req = urllib.request.Request(o["url"])
        with urllib.request.urlopen(req, timeout=300) as r, open(dst, "wb") as f:
            h = hashlib.sha256()
            for b in iter(lambda: r.read(CHUNK), b""):
                f.write(b)
                h.update(b)
        nbytes += o["size"]
        out.append({"path": o["path"], "ok": h.hexdigest() == o["sha256"]})
    if PLAN.get("manifest"):
        with open(os.path.join(root, ".aif-manifest.json"), "w") as f:
            json.dump(PLAN["manifest"], f, indent=1)
    return {"files": len(out), "bytes": nbytes, "seconds": round(time.time() - t0, 1),
            "mismatched": [o["path"] for o in out if not o["ok"]]}


def op_inventory():
    root = PLAN["dir"]
    skip = tuple(PLAN.get("exclude", []))
    files = []
    for d, dirs, names in os.walk(root):
        dirs[:] = sorted(x for x in dirs if not x.startswith(skip))
        for n in sorted(names):
            p = os.path.join(d, n)
            rel = os.path.relpath(p, root)
            files.append({"path": rel, "size": os.path.getsize(p), "sha256": sha256_file(p)})
    return {"files": files}


def op_put():
    root, t0, nbytes, done = PLAN["dir"], time.time(), 0, []
    for o in PLAN["objects"]:
        src = os.path.join(root, o["path"])
        if "url" in o:  # single part
            with open(src, "rb") as f:
                http("PUT", o["url"], f.read())
            done.append({"path": o["path"]})
        else:  # multipart: one presigned URL per part
            etags = []
            with open(src, "rb") as f:
                for part in o["parts"]:
                    r = http("PUT", part["url"], f.read(o["partSize"]))
                    etags.append({"PartNumber": part["number"], "ETag": r.headers["ETag"]})
            done.append({"path": o["path"], "uploadId": o["uploadId"], "parts": etags})
        nbytes += o["size"]
    return {"uploaded": done, "bytes": nbytes, "seconds": round(time.time() - t0, 1)}


def op_verify():
    t0, nbytes, bad = time.time(), 0, []
    for o in PLAN["objects"]:
        h = hashlib.sha256()
        with urllib.request.urlopen(urllib.request.Request(o["url"]), timeout=300) as r:
            for b in iter(lambda: r.read(CHUNK), b""):
                h.update(b)
        nbytes += o["size"]
        if h.hexdigest() != o["sha256"]:
            bad.append(o["path"])
    return {"objects": len(PLAN["objects"]), "bytes": nbytes, "seconds": round(time.time() - t0, 1), "mismatched": bad}


def op_copy():
    import boto3  # installed by the Job: only this operation talks to S3 with credentials
    ident = json.load(open(os.environ["S3_CONFIG"]))["identities"][0]["credentials"][0]
    s3 = boto3.client("s3", endpoint_url=PLAN["endpoint"], region_name="us-east-1",
                      aws_access_key_id=ident["accessKey"], aws_secret_access_key=ident["secretKey"])
    src_b, src_p, dst_b, dst_p = PLAN["sourceBucket"], PLAN["sourcePrefix"], PLAN["destBucket"], PLAN["destPrefix"]
    manifest = json.load(s3.get_object(Bucket=src_b, Key=src_p + ".aif-manifest.json")["Body"])
    t0, nbytes, bad = time.time(), 0, []
    try:
        s3.head_bucket(Bucket=dst_b)
    except Exception:
        s3.create_bucket(Bucket=dst_b)
    keys = [o["path"] for o in manifest["objects"]] + [".aif-manifest.json"]
    for k in keys:
        s3.copy_object(Bucket=dst_b, Key=dst_p + k, CopySource={"Bucket": src_b, "Key": src_p + k})
    for o in manifest["objects"]:  # verify every copy by reading it back
        h = hashlib.sha256()
        for b in s3.get_object(Bucket=dst_b, Key=dst_p + o["path"])["Body"].iter_chunks(CHUNK):
            h.update(b)
        nbytes += o["size"]
        if h.hexdigest() != o["sha256"]:
            bad.append(o["path"])
    deleted = 0
    if PLAN.get("deleteSource") and not bad:  # delete only after every copy verified
        for k in keys:
            s3.delete_object(Bucket=src_b, Key=src_p + k)
            deleted += 1
    return {"objects": len(keys), "bytes": nbytes, "seconds": round(time.time() - t0, 1),
            "mismatched": bad, "deletedFromSource": deleted}


result = {"get": op_get, "inventory": op_inventory, "put": op_put, "verify": op_verify, "copy": op_copy}[OP]()
print("AIF_MOVER " + json.dumps(result), flush=True)
