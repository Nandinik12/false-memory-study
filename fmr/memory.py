"""Soma-style memory pipeline: episodic buffer -> LLM consolidation -> semantic notes,
with lexical retrieval. Memory is the ONLY cross-step channel (see spec §3)."""
import json
import re


class MemoryStore:
    def __init__(self, retrieve_top_m: int = 6, max_notes: int = 40):
        self.notes = []            # {id, text, created_step}
        self.episodes = []         # verbatim per-step logs since last consolidation
        self._next_id = 1
        self.top_m = retrieve_top_m
        self.max_notes = max_notes

    def add_episode(self, ep: dict):
        self.episodes.append(ep)

    def retrieve(self, query: str):
        q = set(re.findall(r"[a-z0-9\-]+", query.lower()))
        scored = []
        for n in self.notes:
            toks = set(re.findall(r"[a-z0-9\-]+", n["text"].lower()))
            score = len(q & toks)
            if score > 0:
                scored.append((score, -n["id"], n))
        scored.sort(reverse=True)
        return [n for _, _, n in scored[: self.top_m]]

    def consolidate(self, llm, step: int, mitigation: bool = False):
        """LLM merges recent episodes + existing notes into an updated note set."""
        if not self.episodes:
            return None
        existing = "\n".join(f"- [{n['id']}] {n['text']}" for n in self.notes) or "(none)"
        eps = "\n".join(
            f"Step {e['step']}: task={e['task'][:160]} | tools={e['tool_log']} | answer={e['answer'][:160]}"
            for e in self.episodes
        )
        mitig = ""
        if mitigation:
            mitig = ("\nIMPORTANT: For each new fact, check whether it CONTRADICTS an existing note. "
                     "If it does, do not silently overwrite either one: output a note of the form "
                     "'CONFLICT: <fact> — episode says X, prior note says Y; needs verification.' "
                     "unless one side has clearly stronger provenance, in which case state why.")
        prompt = (
            "You maintain long-term memory notes for an ops assistant. Merge the recent episodes "
            "into the existing notes. Keep notes as short standalone facts (one fact per note). "
            "Deduplicate. Prune stale or low-value notes. Keep at most "
            f"{self.max_notes} notes.{mitig}\n\n"
            f"EXISTING NOTES:\n{existing}\n\nRECENT EPISODES:\n{eps}\n\n"
            'Output ONLY a JSON array of strings, each string one note. Example: ["billing-api region is us-east-1"]'
        )
        raw = llm.complete(
            system="You are a careful memory-consolidation module. Output only valid JSON.",
            prompt=prompt, kind="consolidate",
            context={"episodes": self.episodes, "notes": [n["text"] for n in self.notes]},
        )
        try:
            m = re.search(r"\[.*\]", raw, re.S)
            texts = json.loads(m.group(0)) if m else None
        except (json.JSONDecodeError, AttributeError):
            texts = None
        if texts is None:
            # Parse failure: keep old notes AND keep episodes for the next cycle —
            # discarding them here silently destroys corrections (bug found 2026-07-13
            # when Sonnet's larger note sets truncated at max_tokens mid-JSON).
            self.episodes = self.episodes[-30:]
            return {"step": step, "error": "consolidation_parse_failure", "raw": raw[:400]}
        self.notes = []
        for t in texts[: self.max_notes]:
            if isinstance(t, str) and t.strip():
                self.notes.append({"id": self._next_id, "text": t.strip(), "created_step": step})
                self._next_id += 1
        self.episodes = []
        return {"step": step, "n_notes": len(self.notes), "notes": [n["text"] for n in self.notes]}
