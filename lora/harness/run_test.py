"""Run one test: train its recipe (recipes/<test>.yaml), evaluate on all four sets, fetch the records
into results/<test>/.  usage: run_test.py <test> <run-name>

Needs the rancher_ai SDK (aif repo, sdk/python) on PYTHONPATH, and AIF_CONTEXT, AIF_PROJECT and
AIF_PROFILE set; see src/lora_study/run.py."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from lora_study import run  # noqa: E402

if __name__ == "__main__":
    test, name = sys.argv[1:3]
    m = run.run_test(test, name)
    sys.exit(0 if m else 1)
