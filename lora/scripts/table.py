"""The comparison table, as Markdown.  usage: table.py [test ...]  (default: every test in results/)"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from lora_study import compare, records  # noqa: E402

names = sys.argv[1:] or [t for t in records.tests() if records.load_test(t)["metrics"]]
print(compare.markdown(compare.table(names)))
