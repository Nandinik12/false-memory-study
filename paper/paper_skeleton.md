# Transient Errors, Durable Beliefs: False-Memory Formation and Self-Correction in Memory-Augmented LLM Agents

*Nandini Kansal — draft skeleton v0.1, 2026-07-11. Sections marked [DATA] await real-run results; no claims in those sections until pilot + full runs complete.*

## Abstract (template)

Memory-augmented LLM agents consolidate their experiences into long-term semantic notes. We ask whether a single, natural, transient tool error — the kind tools actually produce — is laundered by consolidation into a durable false belief, whether that belief compounds into downstream errors and second-order false memories, and whether the agent self-corrects or defends the belief when contradicting evidence arrives. In [N]-step controlled trajectories with a soma-style episodic→semantic pipeline, we find commit rate [X], retention half-life [X], compounding rate [X], and self-correction rate [X], with correction probability [rising/flat/falling] in consolidation cycles elapsed ([entrenchment]). A symmetric true-change control separates healthy updating from both stubbornness and credulity. [If null: consolidation proved robust to transient errors; we characterize why and where the robustness comes from.] We [do/do not] find that a contradiction-aware consolidation prompt [reduces defended false memories by X].

## 1. Introduction

- Memory pipelines are shipping (assistant memory, agentic frameworks); consolidation is the step that turns experience into belief.
- Tools fail benignly all the time (stale caches, flaky APIs, race conditions). The safety question is not whether errors enter experience — they will — but whether the memory system's own machinery amplifies or attenuates them.
- Human memory analogy (misinformation effect, reconsolidation): use one paragraph max, as motivation only, not as evidence.
- Contributions: (1) a controlled longitudinal protocol isolating memory as the sole cross-step channel; (2) retention/compounding/entrenchment curves for a canonical consolidation pipeline; (3) the updating-vs-stubbornness 2×2 that separates three failure regimes (amnesia, credulity, stubbornness); (4) [mitigation result].
- **Honest-null commitment sentence in the intro.**

## 2. Related work

*(Verify all four 2026 citations against full texts before submission — flagged in spec §1.)*

- **Adversarial memory poisoning:** AgentPoison (Chen et al., 2024, arXiv:2407.12784) — optimized triggers into memory/RAG stores; MINJA (arXiv:2503.03704) — injection via query-only interaction, notes self-reinforcement; memory control-flow attacks (arXiv:2603.15125); forged-reasoning attacks (arXiv:2607.05029); systematic study (arXiv:2606.04329). All assume an attacker; injection success is the endpoint, not longitudinal belief dynamics.
- **Non-adversarial memory dynamics:** Xiong et al. (arXiv:2505.16067) — experience-following, error propagation from low-quality experiences in a verbatim memory bank under add/delete policies. Closest prior work. Delta: we study *consolidation into semantic beliefs* (not experience replay), a *single transient* error (not a persistent quality regime), and *contradiction response* (they never confront the agent with counter-evidence).
- **Longitudinal memory safety (2026):** Remembering More, Risking More (arXiv:2605.17830); Memory Contagion (arXiv:2606.23195). [READ AND POSITION — closest potential overlap.]
- **Self-correction:** Reflexion, self-refine, critique lines — correction *within* trajectory vs. our question, correction *of consolidated LTM against retrieval-reinforced belief*.
- **Surveys:** memory mechanisms (arXiv:2605.06716); LTM security lifecycle (arXiv:2604.16548).

## 3. Method

Import from DESIGN_SPEC.md §3–§5 (environment, pipeline, arms). Figure 1: protocol timeline (baseline → injection k → probes/derived → contradiction k+Δ → durability window). Key design commitments to state explicitly: context isolation (memory is the only channel), tool-call economy policy + its ablation, exact-match grading with judge only for rhetoric classification (audited).

## 4. Results [DATA]

- 4.1 Commit: E+ vs E− base rate. Consolidation transcript excerpts (the moment the error becomes a note).
- 4.2 Retention curve + retrieval-conditioned retention (belief vs. retrieval-failure decomposition).
- 4.3 Compounding: derived-task errors; census of second-order false notes with provenance chains.
- 4.4 Contradiction response: 2×2 (E+/T × kept/updated); defense-rhetoric taxonomy with quoted rationales; correction durability across the next consolidation cycle.
- 4.5 Entrenchment: correction rate vs. cycles elapsed (E+early vs E+late; use-count arm).
- 4.6 Ablations: verify-policy, consolidation frequency C, model scale.

## 5. Mitigation [DATA, phase 2]

Contradiction-aware consolidation: prompt-level, then fine-tuned consolidation model (synthetic conflict pairs; SFT to flag-and-resolve). Metric: defended-false-memory rate and true-change arm regression (mitigation must not induce credulity — report both sides).

## 6. Limitations

Synthetic world; single pipeline family; tool-economy regime dependence; lexical retrieval in pilot; mock mode used only for pipeline validation, never for claims; results may be model-family-specific.

## 7. Ethics / safety statement

Non-adversarial by design; no attack capability released beyond what tool flakiness already provides. Harness released for defensive evaluation.

---
### Figure plan
F1 protocol timeline · F2 retention curve (per arm, CIs) · F3 compounding curve · F4 2×2 contradiction bars · F5 entrenchment slope · F6 Kaplan–Meier belief survival · T1 arms/conditions · T2 defense-rhetoric taxonomy.
