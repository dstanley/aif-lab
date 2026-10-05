"""The comparison across tests: one row per test (and the base model), as a pandas DataFrame."""
from .records import load_test


def _pct(report, key):
    v = (report.get("metrics") or {}).get(key, "")
    return v.split(" / ")[-1] if v else None


def recipe_label(tr):
    lo = tr.get("lora", {})
    parts = [f"r{lo.get('r', '?')}", lo.get("targets", "?")]
    parts += [x for x, on in (("rsLoRA", lo.get("rslora")), ("DoRA", lo.get("dora"))) if on]
    if lo.get("init") not in (None, "gaussian"):
        parts.append(lo["init"])
    parts.append(f"lr {tr.get('optimiser', {}).get('lr', '?')}")
    parts.append(tr.get("batch_mode", "sequential"))
    if "3B" in tr.get("base_model", ""):
        parts.append("3B 4-bit")
    return " ".join(str(p) for p in parts)


def row(t):
    tr, m, rep = t["training"], t["metrics"], t["reports"]
    sel = tr.get("selection") or {}
    vals = [h.get("val_loss") for h in tr.get("history", []) if h.get("val_loss")]
    fp, tp = m.get("false-premise", {}).get("adapter"), m.get("true-premise", {}).get("adapter")
    ta, un = m.get("taught", {}), m.get("untaught", {})
    return {"test": t["name"], "recipe": recipe_label(tr), "best_val": sel.get("value") or (min(vals) if vals else None),
            "taught": ta.get("adapter", {}).get("correct"), "exact_commands": _pct(rep["taught"], "Commands (base / adapter)"),
            "partial_commands": ta.get("adapter", {}).get("partial_commands"), "gains": ta.get("gains"), "regressions": ta.get("regressions"),
            "untaught": un.get("adapter", {}).get("correct"), "newly_taught": un.get("v1_taught=True", {}).get("adapter"),
            "fp_rejected": fp and fp["rejects_premise"], "tp_accepted": tp and tp["accepts_premise"],
            "premises_both": fp and tp and fp["rejects_premise"] + tp["accepts_premise"],
            "premises_strict": fp and tp and fp["rejects_and_documented"] + tp["accepts_and_documented"],
            "train_s": tr.get("throughput", {}).get("training_seconds"), "peak_gib": tr.get("throughput", {}).get("peak_gib")}


def base_row(t):
    m, rep = t["metrics"], t["reports"]
    fp, tp = m.get("false-premise", {}).get("base"), m.get("true-premise", {}).get("base")
    return {"test": "base model", "recipe": "no adapter", "taught": m["taught"]["base"]["correct"],
            "exact_commands": ((rep["taught"].get("metrics") or {}).get("Commands (base / adapter)", "-").split(" / ")[0]),
            "partial_commands": m["taught"]["base"]["partial_commands"], "untaught": m["untaught"]["base"]["correct"],
            "newly_taught": m["untaught"].get("v1_taught=True", {}).get("base"),
            "fp_rejected": fp and fp["rejects_premise"], "tp_accepted": tp and tp["accepts_premise"],
            "premises_both": fp and tp and fp["rejects_premise"] + tp["accepts_premise"],
            "premises_strict": fp and tp and fp["rejects_and_documented"] + tp["accepts_and_documented"]}


def table(names, with_base=True):
    import pandas as pd
    loaded = [load_test(n) for n in names]
    rows = [row(t) for t in loaded]
    with_tp = [t for t in loaded if t["metrics"].get("true-premise")]
    if with_base and with_tp:
        rows.insert(0, base_row(with_tp[0]))
    cols = list(row({"name": "", "training": {}, "metrics": {}, "reports": {"taught": {}}}).keys())
    return pd.DataFrame(rows, columns=cols).set_index("test")


OF = {"taught": 338, "untaught": 109, "newly_taught": 27, "fp_rejected": 42, "tp_accepted": 24, "premises_both": 66, "premises_strict": 66}


def markdown(df):
    """The table as Markdown, counts shown as n/of."""
    cols = list(df.columns)
    out = ["| test | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for name, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if v is None or v != v:
                cells.append("-")
            elif c in OF:
                cells.append(f"{int(v)}/{OF[c]}")
            elif c == "best_val":
                cells.append(f"{v:.3f}")
            else:
                cells.append(str(int(v)) if isinstance(v, float) and v.is_integer() else str(v))
        out.append(f"| {name} | " + " | ".join(cells) + " |")
    return "\n".join(out)
