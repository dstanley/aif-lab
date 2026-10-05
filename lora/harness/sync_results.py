"""Copy test results into results/, without lab details: node names, AIJob manifests, local paths.
usage: sync_results.py <source dir with testN folders> [test ...]"""
import os, re, shutil, sys
src = os.path.expanduser(sys.argv[1])
dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
tests = sys.argv[2:] or sorted(d for d in os.listdir(src) if d.startswith("test") and os.path.isdir(os.path.join(src, d)))
SCRUB = [(re.compile(r"rke2-(worker|master|longhorn)\d+"), "gpu-node"), (re.compile(r"/Users/[^/\s\"']+"), "~"),
         (re.compile(r"\baif-submit\b"), "my-project"),
         # write-ups read as part of the tutorial: no run dates
         (re.compile(r"^\*\*Date:\*\* [0-9-]+ · \*\*Cluster:\*\* lab RKE2,", re.M), "**Cluster:** RKE2,")]
SKIP = {"overnight-notes.md"}
for t in tests:
    out = os.path.join(dst, t)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    for f in sorted(os.listdir(os.path.join(src, t))):
        if f.endswith("-aijob.yaml") or f.startswith(".") or f == "__pycache__" or f in SKIP:
            continue
        text = open(os.path.join(src, t, f), encoding="utf-8", errors="replace").read()
        for pat, rep in SCRUB:
            text = pat.sub(rep, text)
        open(os.path.join(out, f), "w", encoding="utf-8").write(text)
    print("synced", t, len(os.listdir(out)), "files")
