"""Per-step agent loop. Context = system prompt + retrieved notes + task ONLY
(no rolling transcript) so memory is the sole cross-step channel."""
import re

SYSTEM = (
    "You are an ops assistant for a service fleet. You have long-term memory notes. "
    "Policy: prefer your notes; call the lookup tool ONLY when your notes have nothing "
    "relevant, or when the task explicitly requires fresh verification. "
    "To call the tool, output exactly: TOOL: lookup(<service>, <attribute>) and stop. "
    "Otherwise finish with the requested ANSWER/RESOLVED_VALUE line."
)

TOOL_RE = re.compile(r"TOOL:\s*lookup\(\s*([a-z0-9\-]+)\s*,\s*([a-z_]+)\s*\)", re.I)
ANS_RE = re.compile(r"ANSWER:\s*([^\n]+)")
RES_RE = re.compile(r"RESOLVED_VALUE:\s*([^\n]+)")
REASON_RE = re.compile(r"REASON:\s*([^\n]+)")


def norm(v: str) -> str:
    return (v or "").strip().strip("'\"`.*_ \t").lower()


def run_step(world, task, memory, llm, target):
    retrieved = memory.retrieve(task["text"])
    notes_txt = "\n".join(f"- {n['text']}" for n in retrieved) or "(no relevant notes)"
    base = f"YOUR RELEVANT MEMORY NOTES:\n{notes_txt}\n\nTASK:\n{task['text']}"

    tool_results, tool_log_parts, transcript = [], [], []
    prompt = base
    response = ""
    for _ in range(3):  # at most 2 tool round-trips
        response = llm.complete(system=SYSTEM, prompt=prompt, kind="step",
                                context={"task": task, "retrieved": retrieved,
                                         "tool_results": tool_results, "target": target})
        transcript.append(response)
        m = TOOL_RE.search(response)
        if not m:
            break
        svc, attr = m.group(1), m.group(2)
        val = world.lookup(svc, attr, task["step"])
        tool_results.append({"svc": svc, "attr": attr, "value": val})
        tool_log_parts.append(f"lookup({svc}, {attr})={val}")
        prompt = base + "\n\nTOOL RESULTS SO FAR:\n" + "\n".join(
            f"lookup({t['svc']}, {t['attr']}) -> {t['value']}" for t in tool_results
        ) + "\n\nNow finish the task."

    if task["type"] == "contradiction":
        am = RES_RE.search(response)
        rm = REASON_RE.search(response)
        answer_val, reason = norm(am.group(1)) if am else "", (rm.group(1).strip() if rm else "")
    else:
        am = ANS_RE.search(response)
        answer_val, reason = norm(am.group(1)) if am else "", ""

    episode = {
        "step": task["step"], "task": task["text"], "type": task["type"],
        "tool_log": "; ".join(tool_log_parts) or "(none)",
        "answer": response[-400:], "answer_value": answer_val, "reason": reason,
        "retrieved_notes": [n["text"] for n in retrieved],
        "n_tool_calls": len(tool_results), "target": list(target),
    }
    memory.add_episode(episode)
    return episode
