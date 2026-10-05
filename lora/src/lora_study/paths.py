import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data")
EVAL = os.path.join(ROOT, "eval")
RECIPES = os.path.join(ROOT, "recipes")
RESULTS = os.environ.get("RESULTS", os.path.join(ROOT, "results"))
