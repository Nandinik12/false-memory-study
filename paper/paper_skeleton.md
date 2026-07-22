# Transient Errors, Durable Beliefs: False-Memory Formation and Self-Correction in Memory-Augmented LLM Agents

*Nandini Kansal — draft skeleton v0.2, 2026-07-13. Sections marked [DATA] await full-grid results. Pilot (n=3–6/cell, single model) supports direction of claims only; every bracketed number below must come from the confirmatory grid, not the pilot.*

## Abstract (template, rewritten around pilot findings)

Memory-augmented LLM agents consolidate their experiences into long-term semantic notes. We ask what happens when a single, natural, transient tool error — a stale cache read — enters that pipeline. In controlled 60–90-step trajectories where memory is the only cross-step channel, we find a two-regime picture. In the silent regime, the error is committed as a durable belief ([X]% of runs), retained without decay, compounded into [X]% of downstream dependent decisions, and never spontaneously re-verified ([0]/[N] re-verifications). In the confronted regime, agents update readily ([X]% correction, [X]% defense): the failure surface is not stubbornness but the absence of any self-initiated verification. We further identify two timing mechanisms. First, commit is a race: an error becomes belief only if consolidation fires before the next independent correct observation, so *more frequent* consolidation increases vulnerability to transients [confirm: C-sweep]. Second, corrections race their own echoes: accepted corrections can be outvoted at consolidation by the false belief's own lag-window repetitions, producing relapse after acknowledged correction [confirm: use-count arm]. A symmetric true-change control separates healthy updating from credulity. We evaluate three pipeline-level mitigations targeting each mechanism: event-driven consolidation on conflict, provenance-weighted consolidation, and staleness-triggered re-verification. [Mitigation results.]

## 1. Introduction

- Memory pipelines are shipping (assistant memory, agentic frameworks); consolidation is the step that turns experience into belief.
- Tools fail benignly all the time (stale caches, flaky APIs, race conditions). The safety question is not whether errors enter experience — they will — but whether the memory system's own machinery amplifies or attenuates them.
- Human memory analogy (misinformation effect, reconsolidation): use one paragraph max, as motivation only, not as evidence.
- Contributions: (1) a controlled longitudinal protocol isolating memory as the sole cross-step channel; (2) retention/compounding/entrenchment curves for a canonical consolidation pipeline; (3) the updating-vs-stubbornness 2×2 that separates three failure regimes (amnesia, credulity, stubbornness); (4) [mitigation result].
- **Honest-null commitment sentence in the intro.**

## 2. Related work

*(Full-text overlap check completed 2026-07-13 for all five adjacent 2026 papers; see spec §1 table. Remaining TODO: PDF-skim appendices of 2605.17830 and discussion of 2606.23195 — unretrievable by fetcher, low residual risk.)*

- **Benchmarks:** MemEvoBench (arXiv:2604.15774) — adversarially pre-seeded misleading memories + biased feedback over 3 rounds in an append-only bank; asserts in passing that accidental noise "solidifies into historical evidence" but never instantiates it. Two useful contrasts: their compounding requires biased user feedback (ours arises under neutral conditions), and their design cannot express consolidation timing, lag, or relapse.

- **Adversarial memory poisoning:** AgentPoison (Chen et al., 2024, arXiv:2407.12784) — optimized triggers into memory/RAG stores; MINJA (arXiv:2503.03704) — injection via query-only interaction. MPBench (arXiv:2606.04329) treats **compaction as an attack write-channel** and shows attackers can time payloads to the compaction trigger, and that aggressively-consolidating agents are more exploitable — the adversarial pre-figuration of our commit-race, which we generalize to a clean causal cadence sweep with no attacker. FARMA (arXiv:2607.05029) manufactures consensus via forged-entry amplification so repetition outvotes contrary signals — the adversarial analogue of our echo-relapse, which in our setting arises *endogenously*: the pipeline's own lag-window echoes outvote an already-accepted correction. All of these assume an attacker; injection success is the endpoint, not longitudinal belief dynamics.
- **Non-adversarial memory harm:** "Remembering More, Risking More" (arXiv:2605.17830) establishes that benign accumulation alone raises violation rates longitudinally, and *names* stale-memory-overrides-correction and summarization-fabrication as observed categories — anecdotes our protocol turns into measured rates. We position ours as event-level etiology of a single identified false belief vs. their population-level drift. Xiong et al. (arXiv:2505.16067): experience-following/error propagation in verbatim memory banks; no consolidation-into-beliefs, no transient single error, no contradiction protocol. Memory Contagion (arXiv:2606.23195): persistent evaluator bias (≥20% of store) propagates cross-agent; studies consolidation *fidelity* where we study consolidation *timing* — their attenuation finding makes a sharp foil for our faster-is-worse result.
- **Self-correction:** Reflexion/self-refine — correction *within* a trajectory; our question is correction of consolidated LTM against retrieval-reinforced belief. Note: consensus-based memory defenses (e.g., A-MemGuard as cited in FARMA) assume repetition signals reliability — echo-relapse is a non-adversarial counterexample to that assumption.
- **Surveys:** memory mechanisms (arXiv:2605.06716); LTM security lifecycle (arXiv:2604.16548).

## 3. Method

Import from DESIGN_SPEC.md §3–§5 (environment, pipeline, arms). Figure 1: protocol timeline (baseline → injection k → probes/derived → contradiction k+Δ → durability window). Key design commitments to state explicitly: context isolation (memory is the only channel), tool-call economy policy + its ablation, exact-match grading with judge only for rhetoric classification (audited).

## 4. Results [DATA — structure updated to pilot-driven narrative]

- 4.1 **The silent regime.** Commit rate (E+ vs E− base); retention curve (flat at [X] out to +[N]); compounding on derived tasks; the zero-re-verification census. Consolidation transcript excerpt: the moment a stale read becomes a note.
- 4.2 **The confronted regime.** 2×2 (E+/T × kept/updated); correction after 60 steps of held belief; defense-rhetoric taxonomy (pilot: empty — report as null with CIs); entrenchment slope (pilot: null; full grid decides).
- 4.3 **Mechanism 1 — commit as a race.** C-sweep with matched schedules; commit vs. presence of a correct re-observation inside the first consolidation window; the faster-consolidation-is-worse result.
- 4.4 **Mechanism 2 — correction lag and echo-relapse.** Lag_false vs. position in window and vs. C; relapse vs. lag-window use count; case study: 1 correction episode outvoted by 3 echoes + prior note.
- 4.5 Ablations: verify-policy prompt, model scale (does capability restore self-initiated verification?), target-fact type, retrieval mechanism.

## 5. Mitigation [DATA, phase 2] — one intervention per mechanism

1. **Event-driven consolidation on conflict** (targets correction lag): consolidate immediately when an episode contradicts a retrieved note. Prompt/control-flow change.
2. **Provenance-weighted consolidation** (targets echo-relapse): an explicit-resolution episode outweighs any number of note-derived echoes; echoes of a note are not independent evidence. Prompt-level first; fine-tuned consolidation model second (synthetic conflict/echo training pairs; SFT to flag-and-weigh) — the ML-depth contribution.
3. **Staleness-triggered re-verification** (targets the silent regime): high-use facts accrue a verification debt; policy re-checks after N uses or T steps.

Each mitigation is evaluated on BOTH the E+ arm (does it fix the failure?) and the T arm (does it induce credulity or thrash on true changes?). Report the pair, always.

## 6. Limitations

Synthetic world; single pipeline family; tool-economy regime dependence; lexical retrieval in pilot; mock mode used only for pipeline validation, never for claims; results may be model-family-specific.

## 7. Ethics / safety statement

Non-adversarial by design; no attack capability released beyond what tool flakiness already provides. Harness released for defensive evaluation.

---
### Figure plan
F1 protocol timeline · F2 retention curve (per arm, CIs) · F3 compounding curve · F4 2×2 contradiction bars · F5 entrenchment slope · F6 Kaplan–Meier belief survival · T1 arms/conditions · T2 defense-rhetoric taxonomy.
