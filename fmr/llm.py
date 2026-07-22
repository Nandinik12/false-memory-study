"""LLM backends: Anthropic API (real runs) and a rule-based MockLLM that emulates a
'naive believer' agent so the full measurement pipeline can be validated at zero cost.

The mock is NOT a scientific result. It exists to prove logs -> metrics -> plots work.
"""
import os
import random
import re
import time


class AnthropicLLM:
    def __init__(self, model: str, max_tokens: int = 1024, temperature: float = 0.2):
        import anthropic
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.n_calls = 0
        self.in_tokens = 0
        self.out_tokens = 0

    def complete(self, system: str, prompt: str, kind: str = "step", context: dict = None) -> str:
        last_err = None
        for attempt in range(4):
            try:
                mt = max(self.max_tokens, 2500) if kind == "consolidate" else self.max_tokens
                kwargs = dict(model=self.model, max_tokens=mt,
                              system=system, messages=[{"role": "user", "content": prompt}])
                if self.temperature is not None:
                    kwargs["temperature"] = self.temperature
                resp = self.client.messages.create(**kwargs)
                self.n_calls += 1
                self.in_tokens += resp.usage.input_tokens
                self.out_tokens += resp.usage.output_tokens
                return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
            except Exception as e:  # rate limits / transient
                last_err = e
                if "temperature" in str(e):      # model rejects temperature (e.g. Sonnet 5)
                    self.temperature = None
                    continue
                time.sleep(2 ** attempt * 2)
        raise RuntimeError(f"Anthropic call failed after retries: {last_err}")


FACT_RE = re.compile(r"([a-z0-9\-]+) (region|port|owner|memory_limit|depends_on) is ([^\s.,;]+)")


class MockLLM:
    """Deterministic-per-(seed,step) simulated agent with tunable failure knobs:
    p_defend: prob. of defending memory against fresh contradicting evidence
    p_reverify: prob. of re-verifying with the tool despite having a relevant note
    """

    def __init__(self, seed: int, p_defend: float = 0.35, p_reverify: float = 0.1):
        self.seed = seed
        self.p_defend = p_defend
        self.p_reverify = p_reverify
        self.n_calls = 0
        self.in_tokens = 0
        self.out_tokens = 0

    def _rng(self, step, salt=""):
        return random.Random(f"{self.seed}:{step}:{salt}")

    def _note_value(self, notes, svc, attr):
        best = None
        for text in notes:
            m = FACT_RE.search(text.lower())
            if m and m.group(1) == svc and m.group(2) == attr:
                best = m.group(3)  # later notes win
        return best

    def complete(self, system: str, prompt: str, kind: str = "step", context: dict = None) -> str:
        self.n_calls += 1
        ctx = context or {}
        if kind == "consolidate":
            return self._consolidate(ctx)
        task = ctx["task"]
        notes = [n["text"] for n in ctx.get("retrieved", [])]
        tool_results = ctx.get("tool_results", [])
        step = task["step"]
        ttype = task["type"]

        if ttype == "contradiction":
            svc, attr = ctx["target"]
            mem = self._note_value(notes, svc, attr)
            fresh = task["fresh_value"]
            if mem is None or mem == fresh:
                return f"RESOLVED_VALUE: {fresh}\nREASON: fresh lookup is consistent with my notes."
            if self._rng(step, "defend").random() < self.p_defend:
                return (f"RESOLVED_VALUE: {mem}\nREASON: my notes consistently say {mem}; "
                        f"the fresh lookup is likely a transient tool error.")
            return f"RESOLVED_VALUE: {fresh}\nREASON: fresh evidence outweighs my stored note ({mem})."

        # tasks needing a (svc, attr) value
        if ttype in ("probe", "derived", "inject_lookup"):
            svc, attr = ctx["target"]
        else:
            svc, attr = task["distractor_key"]

        if tool_results:
            return f"The tool returned the value.\nANSWER: {tool_results[-1]['value']}"
        mem = self._note_value(notes, svc, attr)
        must_verify = ttype == "inject_lookup"
        if mem is not None and not must_verify and self._rng(step, "rv").random() >= self.p_reverify:
            return f"My notes cover this.\nANSWER: {mem}"
        return f"I need fresh data.\nTOOL: lookup({svc}, {attr})"

    def _consolidate(self, ctx):
        facts = {}
        order = []
        for text in ctx.get("notes", []):
            m = FACT_RE.search(text.lower())
            if m:
                key = (m.group(1), m.group(2))
                if key not in facts:
                    order.append(key)
                facts[key] = m.group(3)
        for ep in ctx.get("episodes", []):
            for svc, attr, val in re.findall(r"lookup\(([a-z0-9\-]+), (\w+)\)=([^\s;|]+)", ep["tool_log"]):
                key = (svc, attr)
                if key not in facts:
                    order.append(key)
                facts[key] = val                       # recency wins (the failure mode under test)
            m = re.search(r"RESOLVED_VALUE:\s*([^\s]+)", ep["answer"])
            if m and "target" in ep:
                key = tuple(ep["target"])
                if key not in facts:
                    order.append(key)
                facts[key] = m.group(1).lower()
        notes = [f"{svc} {attr} is {facts[(svc, attr)]}" for svc, attr in order]
        import json
        return json.dumps(notes[-40:])


def make_llm(cfg, seed: int):
    if cfg["mode"] == "mock":
        return MockLLM(seed, p_defend=cfg.get("p_defend", 0.35), p_reverify=cfg.get("p_reverify", 0.1))
    return AnthropicLLM(cfg["model"], max_tokens=cfg.get("max_tokens", 1024),
                        temperature=cfg.get("temperature", 0.2))
