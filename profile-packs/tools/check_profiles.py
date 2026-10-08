#!/usr/bin/env python3
"""Check every profile in a pack as AI Factory will read it:

1. it parses as a compute profile, with no problems (the AI Factory SDK's own parser: unknown
   editable fields, bad limits), and
2. the training chart renders with its values, as a run from the profile would install it: with the
   scheduler a project supplies (KAI by default, which this pack's GPU shares need).

  python3 profile-packs/tools/check_profiles.py profile-packs/<pack> [--chart PATH-OR-OCI-REF] [--version V] [--scheduler kai|kueue|none]

--chart defaults to the gpu-train-job chart in an aif checkout beside this repository
(../aif/charts/gpu-train-job); an OCI reference such as
oci://ghcr.io/dstanley/training-charts/gpu-train-job works too, with --version. Needs helm and the
SDK (pip install "rancher-ai @ https://github.com/dstanley/aif/archive/refs/heads/pr/7-designs.tar.gz#subdirectory=sdk/python").
"""
import argparse
import os
import subprocess
import sys
import tempfile

import yaml
from rancher_ai.profiles import from_configmap

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pack", help="the pack's directory, e.g. profile-packs/nvidia-16g")
    ap.add_argument("--chart", default=os.path.join(HERE, "..", "..", "..", "aif", "charts", "gpu-train-job"))
    ap.add_argument("--version", default="")
    ap.add_argument("--scheduler", default="kai", choices=["kai", "kueue", "none"],
                    help="the scheduler the runs' project uses; its queue is a placeholder")
    a = ap.parse_args()

    rendered = subprocess.run(["helm", "template", "pack", a.pack], check=True, capture_output=True, text=True).stdout
    configmaps = [d for d in yaml.safe_load_all(rendered) if d]
    failed = 0
    for cm in configmaps:
        p = from_configmap(cm)
        name = cm["metadata"]["name"]
        if p is None:
            print(f"✗ {name}: not a compute profile (no trainingjobs/profile label)")
            failed += 1
            continue
        if p.problems:
            print(f"✗ {name}: {'; '.join(p.problems)}")
            failed += 1
            continue
        if p.type == "inference":
            # an inference profile deploys a blueprint, not the training chart
            print(f"✓ {name} (inference)")
            continue
        run = f"{p.name_prefix}-check" if p.name_prefix else f"{name[:40]}-check"
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            yaml.safe_dump(p.values, f)
        sched = [] if a.scheduler == "none" else ["--set", f"scheduler.type={a.scheduler}", "--set", "scheduler.queue=check"]
        cmd = ["helm", "template", run, a.chart, "-f", f.name] + sched + (["--version", a.version] if a.version else [])
        r = subprocess.run(cmd, capture_output=True, text=True)
        os.unlink(f.name)
        if r.returncode:
            why = next((ln for ln in r.stderr.splitlines() if ln.startswith("Error")), r.stderr.strip()[-300:])
            print(f"✗ {name}: the training chart refuses its values: {why}")
            failed += 1
        else:
            print(f"✓ {name}")
    print(f"{len(configmaps) - failed} of {len(configmaps)} profiles pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
