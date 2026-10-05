"""Write a test's metrics.json from its saved answers.  usage: metrics.py <results/testN>"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from lora_study import grading  # noqa: E402

print(json.dumps(grading.write(sys.argv[1]), indent=1))
