"""One row per test from its saved files (training.json, eval-*.json, metrics.json) under results/ (or $RESULTS):
python3 table.py [test ...]"""
import json, os, sys
L = os.environ.get("RESULTS", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results"))
tests = sys.argv[1:] or sorted(d for d in os.listdir(L) if d.startswith("test") and os.path.exists(f"{L}/{d}/metrics.json"))
def J(p):
    try:
        return json.load(open(p))
    except Exception:
        return {}
def pct(m, key):
    v = (m.get("metrics") or {}).get(key, "")
    return v.split(" / ")[-1] if v else "-"
rows = [("Test", "Recipe", "Best val", "Taught", "Exact cmds", "Untaught", "Newly taught", "FP rejects+doc", "TP opens No", "Train s", "Peak GiB")]
for t in tests:
    tr, m = J(f"{L}/{t}/training.json"), J(f"{L}/{t}/metrics.json")
    lo = tr.get("lora", {})
    recipe = f"r{lo.get('r','?')} {lo.get('targets','?')}{' rsLoRA' if lo.get('rslora') else ''}{' DoRA' if lo.get('dora') else ''} {lo.get('init','')}" \
             f" lr {tr.get('optimiser',{}).get('lr','?')} {tr.get('batch_mode','sequential')}" + (" 3B-nf4" if "3B" in tr.get("base_model", "") else "")
    sel = tr.get("selection") or {}
    best = sel.get("value") or (min((h.get("val_loss") for h in tr.get("history", []) if h.get("val_loss")), default=None))
    ta, un = m.get("taught", {}), m.get("untaught", {})
    fp, tp = m.get("false-premise", {}).get("adapter", {}), m.get("true-premise", {}).get("adapter", {})
    rows.append((t, recipe, f"{best:.3f}" if best else "-",
                 f"{ta.get('adapter',{}).get('correct','-')}/338", pct(J(f"{L}/{t}/eval-taught.json"), "Commands (base / adapter)"),
                 f"{un.get('adapter',{}).get('correct','-')}/109", f"{un.get('v1_taught=True',{}).get('adapter','-')}/27",
                 f"{fp.get('rejects_and_documented','-')}/42", f"{tp.get('opens',{}).get('no','-')}/24" if tp else "-",
                 str(tr.get("throughput", {}).get("training_seconds", "-")), str(tr.get("throughput", {}).get("peak_gib", "-"))))
print("| " + " | ".join(rows[0]) + " |\n|" + "---|" * len(rows[0]))
for r in rows[1:]:
    print("| " + " | ".join(r) + " |")
