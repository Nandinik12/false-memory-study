"""Headline figure: commit rate (and lag/relapse) vs consolidation frequency C.
Usage: python3 -m fmr.fig_csweep runs/csweep_C1 runs/csweep_C3 runs/csweep_C5 runs/csweep_C10 runs/csweep_C20
Reads each dir's per-run records via analyze.py; writes runs/fig_commit_vs_C.png
"""
import json
import re
import sys

from .analyze import load_runs, per_run_metrics, boot_ci


def main(dirs):
    rows = []
    for d in dirs:
        m = re.search(r"C(\d+)", d)
        C = int(m.group(1))
        per = [per_run_metrics(r) for r in load_runs(d) if r["meta"]["arm"] == "E+"]
        if not per:
            continue
        commit = boot_ci([1.0 if p["committed"] else 0.0 for p in per])
        lag = [1.0 if p["lag_false"] else 0.0 for p in per if p["lag_false"] is not None]
        rel = [1.0 if p["relapsed"] else 0.0 for p in per if p["relapsed"] is not None]
        rows.append({"C": C, "n": len(per), "commit": commit,
                     "lag": boot_ci(lag) if lag else None,
                     "relapse": boot_ci(rel) if rel else None})
    rows.sort(key=lambda r: r["C"])

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4.4))
    xs = [r["C"] for r in rows]
    for key, color, label in [("commit", "#c0392b", "P(error committed to memory)"),
                              ("lag", "#e67e22", "P(re-asserts after accepted correction)"),
                              ("relapse", "#8e44ad", "P(relapse after consolidated correction)")]:
        pts = [(r["C"], r[key]) for r in rows if r[key]]
        if not pts:
            continue
        cx = [p[0] for p in pts]
        cm = [p[1][0] for p in pts]
        lo = [p[1][0] - p[1][1] for p in pts]
        hi = [p[1][2] - p[1][0] for p in pts]
        ax.errorbar(cx, cm, yerr=[lo, hi], fmt="-o", color=color, label=label, capsize=3)
    ax.set_xscale("log")
    ax.set_xticks(xs)
    ax.set_xticklabels([str(x) for x in xs])
    ax.set_xlabel("consolidation interval C (steps between memory writes)")
    ax.set_ylabel("rate")
    ax.set_ylim(-0.05, 1.1)
    ax.set_title("Commit is a race: faster consolidation → more durable false memories")
    ax.legend(fontsize=9)
    fig.tight_layout()
    out = "runs/fig_commit_vs_C.png"
    fig.savefig(out, dpi=150)
    print(json.dumps([{**r, "commit": r["commit"]} for r in rows], indent=2, default=str))
    print("->", out)


if __name__ == "__main__":
    main(sys.argv[1:])
