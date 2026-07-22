"""Aggregate trajectory logs -> metrics (commit, retention, compounding, correction,
durability) with bootstrap CIs over seeds, plus plots."""
import glob
import json
import os
import random
import sys
from collections import defaultdict


def load_runs(run_dir):
    runs = []
    for path in sorted(glob.glob(os.path.join(run_dir, "*.jsonl"))):
        meta, steps, cons, end = None, [], [], None
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                if r["record"] == "meta":
                    meta = r
                elif r["record"] == "step":
                    steps.append(r)
                elif r["record"] == "consolidation":
                    cons.append(r)
                elif r["record"] == "end":
                    end = r
        runs.append({"meta": meta, "steps": steps, "cons": cons, "end": end, "path": path})
    return runs


def boot_ci(values, n=2000, seed=0):
    if not values:
        return (float("nan"),) * 3
    rng = random.Random(seed)
    mean = sum(values) / len(values)
    bs = sorted(sum(rng.choices(values, k=len(values))) / len(values) for _ in range(n))
    return mean, bs[int(0.025 * n)], bs[int(0.975 * n)]


def per_run_metrics(run):
    m = run["meta"]
    arm, k = m["arm"], m["k"]
    out = {"arm": arm, "seed": m["seed"]}
    # Commit: false value in notes at first consolidation at/after k
    commit = None
    fv = m["false_value"].lower(); svc = m["cfg"]["target"][0].lower()
    for c in run["cons"]:
        if c["step"] >= k:
            if "notes" in c:   # recompute conflict-aware: a CONFLICT flag is not a belief
                commit = any(fv in n.lower() and svc in n.lower()
                             and "conflict" not in n.lower() for n in c["notes"])
            else:
                commit = c.get("false_in_notes", False)
            break
    out["committed"] = bool(commit) if arm == "E+" else None

    contr = next((s for s in run["steps"] if s["type"] == "contradiction"), None)
    c_step = contr["step"] if contr else None
    out["corrected"] = contr["is_correct"] if contr else None
    out["defended"] = contr.get("defended_false") if contr else None

    # Curves keyed by offset from k
    out["probe_points"] = [
        {"offset": s["step"] - k, "asserted_false": s.get("asserted_false", False),
         "is_correct": s["is_correct"], "post_contradiction": bool(c_step and s["step"] > c_step),
         "retrieved_false": any(m["false_value"].lower() in n.lower() for n in s["retrieved_notes"])}
        for s in run["steps"] if s["type"] == "probe" and s.get("graded")
    ]
    out["derived_points"] = [
        {"offset": s["step"] - k, "asserted_false": s.get("asserted_false", False),
         "is_correct": s["is_correct"]}
        for s in run["steps"] if s["type"] == "derived" and s.get("graded")
    ]
    # Durability, split into two distinct phenomena (see pilot finding 2026-07-13):
    # - lag window: probes AFTER the contradiction but BEFORE the first subsequent
    #   consolidation. The correction lives only in the episodic buffer; retrieval
    #   still serves the old note. False assertions here = "correction lag".
    # - relapse: probes AFTER the first post-contradiction consolidation. False
    #   assertions here = genuine relapse / failed consolidation of the correction.
    first_cons = next((c["step"] for c in run["cons"] if c_step and c["step"] >= c_step), None)
    post = [(p, s) for p, s in
            [({"offset": s["step"] - k, "is_correct": s["is_correct"],
               "asserted_false": s.get("asserted_false", False)}, s["step"])
             for s in run["steps"] if s["type"] == "probe" and s.get("graded")
             and c_step and s["step"] > c_step]]
    lag = [p for p, st in post if first_cons and st <= first_cons]
    late = [p for p, st in post if first_cons and st > first_cons]
    out["lag_false"] = (any(p["asserted_false"] for p in lag) if lag else None)
    out["relapsed"] = (any(p["asserted_false"] for p in late) if late else None)
    out["durable_correction"] = (contr["is_correct"] and not out["relapsed"]
                                 if (contr and late) else None)
    out["distractor_acc"] = _acc([s for s in run["steps"] if s["type"] == "distractor" and s.get("graded")])
    return out


def _acc(steps):
    return sum(s["is_correct"] for s in steps) / len(steps) if steps else float("nan")


def aggregate(runs):
    per = [per_run_metrics(r) for r in runs]
    arms = sorted({p["arm"] for p in per})
    summary = {}
    for arm in arms:
        ps = [p for p in per if p["arm"] == arm]
        s = {"n_runs": len(ps)}
        if arm == "E+":
            s["commit_rate"] = boot_ci([1.0 if p["committed"] else 0.0 for p in ps])
        s["correction_rate"] = boot_ci([1.0 if p["corrected"] else 0.0 for p in ps if p["corrected"] is not None])
        if arm == "E+":
            s["defense_rate"] = boot_ci([1.0 if p["defended"] else 0.0 for p in ps if p["defended"] is not None])
            for key, name in [("lag_false", "lag_false_rate"), ("relapsed", "relapse_rate"),
                              ("durable_correction", "durable_correction_rate")]:
                vals = [1.0 if p[key] else 0.0 for p in ps if p[key] is not None]
                s[name] = boot_ci(vals) if vals else None
        s["distractor_acc"] = boot_ci([p["distractor_acc"] for p in ps if p["distractor_acc"] == p["distractor_acc"]])
        # retention / compounding curves: offset -> rate across runs
        for key, name in [("probe_points", "retention"), ("derived_points", "compounding")]:
            buckets = defaultdict(list)
            for p in ps:
                for pt in p[key]:
                    buckets[pt["offset"]].append(1.0 if (pt["asserted_false"] if arm == "E+" else not pt["is_correct"]) else 0.0)
            s[name + "_curve"] = {str(off): boot_ci(v) for off, v in sorted(buckets.items())}
        summary[arm] = s
    return per, summary


def plot(summary, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def curve(ax, arm, name, color, label):
        c = summary.get(arm, {}).get(name + "_curve", {})
        pts = sorted((int(k), v) for k, v in c.items())
        if not pts:
            return
        xs = [p[0] for p in pts]
        ys = [p[1][0] for p in pts]
        lo = [p[1][1] for p in pts]
        hi = [p[1][2] for p in pts]
        ax.plot(xs, ys, "-o", color=color, label=label)
        ax.fill_between(xs, lo, hi, alpha=0.15, color=color)

    fig, ax = plt.subplots(figsize=(7, 4.2))
    curve(ax, "E+", "retention", "#c0392b", "E+ : P(assert false value)")
    curve(ax, "E-", "retention", "#7f8c8d", "E− : P(any wrong answer) [base]")
    ax.axvline(0, ls="--", c="k", lw=0.8)
    ax.set_xlabel("steps since injection (k)")
    ax.set_ylabel("rate")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("False-memory retention (direct probes)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "retention_curve.png"), dpi=150)

    fig, ax = plt.subplots(figsize=(7, 4.2))
    curve(ax, "E+", "compounding", "#8e44ad", "E+ : P(false-derived answer)")
    curve(ax, "E-", "compounding", "#7f8c8d", "E− : P(any wrong answer) [base]")
    ax.axvline(0, ls="--", c="k", lw=0.8)
    ax.set_xlabel("steps since injection (k)")
    ax.set_ylabel("rate")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("Compounding (derived tasks that depend on the fact)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "compounding_curve.png"), dpi=150)

    fig, ax = plt.subplots(figsize=(6, 4))
    bars, labels = [], []
    for arm, lab in [("E+", "E+ corrected\n(should update)"), ("T", "T kept truth\n(should keep)")]:
        cr = summary.get(arm, {}).get("correction_rate")
        if cr:
            bars.append(cr)
            labels.append(lab)
    if "E+" in summary and summary["E+"].get("defense_rate"):
        bars.append(summary["E+"]["defense_rate"])
        labels.append("E+ defended\nfalse memory")
    xs = range(len(bars))
    ax.bar(xs, [b[0] for b in bars],
           yerr=[[b[0] - b[1] for b in bars], [b[2] - b[0] for b in bars]],
           color=["#27ae60", "#2980b9", "#c0392b"][: len(bars)], capsize=4)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(0, 1.05)
    ax.set_title("Contradiction response (updating vs stubbornness 2x2)")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "correction_rates.png"), dpi=150)
    print(f"plots -> {out_dir}")


def main(run_dir):
    runs = load_runs(run_dir)
    per, summary = aggregate(runs)
    with open(os.path.join(run_dir, "summary.json"), "w") as f:
        json.dump({"per_run": per, "summary": summary}, f, indent=2, default=str)
    for arm, s in summary.items():
        print(f"\n=== arm {arm} (n={s['n_runs']}) ===")
        for key in ("commit_rate", "correction_rate", "defense_rate", "lag_false_rate",
                    "relapse_rate", "durable_correction_rate", "distractor_acc"):
            if s.get(key):
                m, lo, hi = s[key]
                print(f"  {key:26s} {m:.2f}  [{lo:.2f}, {hi:.2f}]")
    plot(summary, run_dir)


if __name__ == "__main__":
    main(sys.argv[1])
