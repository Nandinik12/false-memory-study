"""Experiment runner: arms x seeds -> JSONL trajectory logs with programmatic grading."""
import json
import os
import time

from .world import World, build_schedule
from .memory import MemoryStore
from .agent import run_step, norm
from .llm import make_llm


def grade(world, task, episode):
    step = task["step"]
    g = {}
    if task["type"] in ("probe", "inject_lookup", "derived"):
        truth = norm(world.target_truth_at(step))
        false_v = norm(world.false_value)
        av = episode["answer_value"]
        g = {"graded": True, "truth": truth, "answer": av,
             "is_correct": av == truth, "asserted_false": av == false_v and world.arm == "E+"}
    elif task["type"] == "contradiction":
        truth = norm(world.target_truth_at(step))
        false_v = norm(world.false_value)
        av = episode["answer_value"]
        g = {"graded": True, "truth": truth, "answer": av,
             "is_correct": av == truth,
             "defended_false": av == false_v and world.arm == "E+",
             "reason": episode["reason"]}
    elif task["type"] == "distractor":
        key = tuple(task["distractor_key"])
        truth = norm(world.truth.get(key, ""))
        g = {"graded": True, "truth": truth, "answer": episode["answer_value"],
             "is_correct": episode["answer_value"] == truth}
    return g


def false_in_notes(memory, world):
    fv = norm(world.false_value)
    svc = world.target[0]
    return any(fv in n["text"].lower() and svc in n["text"].lower()
               and "conflict" not in n["text"].lower() for n in memory.notes)


def run_one(cfg, arm, seed, out_dir):
    target = tuple(cfg["target"])
    world = World(seed=seed, arm=arm, target=target, k=cfg["k"])
    schedule = build_schedule(world, cfg["n_steps"], cfg["contradiction_offset"], seed,
                              consolidate_every=cfg.get("consolidate_every", 5),
                              lag_probes=cfg.get("lag_probes"))
    memory = MemoryStore(retrieve_top_m=cfg.get("retrieve_top_m", 6))
    llm = make_llm(cfg, seed)
    C = cfg.get("consolidate_every", 5)
    mitigation = cfg.get("mitigation", False)

    path = os.path.join(out_dir, f"{arm.replace('+','p').replace('-','m')}_seed{seed}.jsonl")
    with open(path, "w") as f:
        f.write(json.dumps({"record": "meta", "arm": arm, "seed": seed, "cfg": cfg,
                            "truth": world.truth[target], "false_value": world.false_value,
                            "new_value": world.new_value, "k": world.k}) + "\n")
        for task in schedule:
            from .agent import SYSTEM_VERIFY
            ep = run_step(world, task, memory, llm, target,
                          system=SYSTEM_VERIFY if cfg.get("verify_policy") else None,
                          conflict_forces_lookup=cfg.get("conflict_forces_lookup", False))
            rec = {"record": "step", **{k: ep[k] for k in
                   ("step", "type", "answer_value", "reason", "tool_log", "n_tool_calls",
                    "retrieved_notes")},
                   "offset": task.get("offset"), "post_contradiction": task.get("post_contradiction", False),
                   **grade(world, task, ep)}
            f.write(json.dumps(rec) + "\n")
            if task["step"] % C == 0:
                cons = memory.consolidate(llm, task["step"], mitigation=mitigation)
                if cons:
                    cons.update({"record": "consolidation",
                                 "false_in_notes": false_in_notes(memory, world)})
                    f.write(json.dumps(cons) + "\n")
        f.write(json.dumps({"record": "end", "n_llm_calls": llm.n_calls,
                            "in_tokens": llm.in_tokens, "out_tokens": llm.out_tokens,
                            "final_notes": [n["text"] for n in memory.notes]}) + "\n")
    return path


def run_experiment(cfg):
    out_dir = cfg["out_dir"]
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    paths = []
    for arm in cfg["arms"]:
        for seed in cfg["seeds"]:
            p = run_one(cfg, arm, seed, out_dir)
            print(f"[{time.time()-t0:7.1f}s] done arm={arm} seed={seed} -> {p}", flush=True)
            paths.append(p)
    return paths


if __name__ == "__main__":
    import sys
    with open(sys.argv[1]) as fh:
        cfg = json.load(fh)
    run_experiment(cfg)
