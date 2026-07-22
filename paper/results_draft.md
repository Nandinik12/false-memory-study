# Results (draft v1 — 2026-07-14)

*All numbers below are from real runs (Claude Haiku 4.5 unless noted; Claude Sonnet 5 where noted), programmatically graded, with anomalous cells transcript-audited. Bootstrap 95% CIs over seeds. Total compute cost of every experiment in this section: ≈ $10. Sections marked [PENDING] await the corrected h7v2 dose-response runs.*

## Setup recap (one paragraph)

An ops-assistant agent runs 60–90 sequential tasks over a fleet of fictional services with programmatic ground truth. Per-step context contains only the system prompt, retrieved memory notes, and the current task — memory (episodic buffer → LLM consolidation every C steps → semantic notes → lexical retrieval) is the sole cross-step channel. At step k=15 the lookup tool returns one wrong value for one target fact, once (E+); controls are no-error (E−) and true-change (T, the world actually changes at k). Contradiction events deliver a fresh correct lookup at k+Δ with a forced structured resolution. Probes and fact-dependent derived tasks are exact-match graded.

## 1. The silent regime: one stale read becomes operating truth

**Commit.** Across every Haiku arm with C ≤ 5, the single false tool return was committed to consolidated long-term memory in 32/32 runs; Sonnet 5 committed 4/4. Across four different target fact types: region 3/3, port 6/6, owner 5/6, memory_limit 6/6 — commit is not an artifact of one fact's surface form. E− runs produced zero spontaneous false memories of the target fact (0/3, and target-probe accuracy 1.00 throughout).

**Retention.** Once committed, the belief did not decay. In the 90-step arm (Δ=60, n=6), direct-probe assertion of the false value was 1.00 at every measured offset (+2 through +33) and the belief remained load-bearing until confronted at +60. No run showed spontaneous reversion.

**Compounding.** Derived tasks that depend on the fact but never mention it (colocation decisions) went with the false value in 100% of post-commit instances (all offsets +3 through +38, n=6 runs × 6 probes). The error was not merely stored; it silently propagated into downstream decisions.

**No self-initiated verification.** Pooled across all real E+ runs (both models, all arms): when a relevant memory note had been retrieved, the agent re-verified with the tool in 19/1,427 opportunities (1.3%). When no relevant note existed, it correctly used the tool 30/30. The asymmetry is the phenomenon: the pipeline's economy policy ("prefer notes") is honored almost absolutely, so nothing inside the system ever re-tests a stored belief. [Ablation with a "verify when uncertain" prompt: NOT YET RUN — flag as limitation or run before submission.]

## 2. The confronted regime: agents update; the failure is not stubbornness

When presented with fresh contradicting evidence and forced to resolve, agents chose the correct value in 62/62 contradiction events across all Haiku arms and 8/8 Sonnet events — including after 60 steps of holding and repeatedly using the false belief. Defense (explicitly discounting fresh evidence in favor of memory) occurred 0 times in any real run. Entrenchment (H4) was null over the delays tested (Δ=26 vs 60). The symmetric control behaved correctly: in T-arm runs the agent retained the new true value when evidence confirmed it (13/13 across both models) — so the universal updating in E+ is not mere credulity toward the latest input; the 2×2 is clean.

We pre-registered "agents defend false memories" as a live hypothesis. At these scales and models, they do not. The failure surface is elsewhere: in what happens *between* confrontations (§1) and in the machinery of correction itself (§§3–4).

## 3. Mechanism 1 — commit is a race, and faster consolidation loses

Commit rate as a function of consolidation interval C (n=10 seeds/cell, identical probe schedule, Haiku):

| C (steps between memory writes) | 1 | 3 | 5 | 10 | 20 |
|---|---|---|---|---|---|
| Commit rate | 1.00 | 1.00 | 1.00 | 0.90 | 0.10 |

(Figure: fig_commit_vs_C.png.)

Transcript-level mechanism, from the audited non-commit seeds: the error becomes a belief **iff consolidation fires before the next independent correct observation of the same fact**. At small C, consolidation lands immediately, the false note is created, and every subsequent task trusts the note (no re-lookup, per §1) — the error is locked in. At large C, some later task encounters the fact while no note exists yet, is forced to use the tool, receives the truth, and the consolidation batch then contains contradicting observations, which the consolidator resolves — in the audited cases, correctly. The counterintuitive design implication: **within this regime, consolidating more frequently makes the pipeline more vulnerable to transient errors**, because fast consolidation forecloses the natural verification that slow consolidation accidentally permits. [Boundary conditions: single environment, one retrieval scheme, C=20 cell rests on 10 seeds; the C at which the transition occurs should scale with task-revisit frequency — untested prediction.]

## 4. Mechanism 2 — corrections are not atomic

**Correction lag.** An accepted correction lives only in the episodic buffer until the next consolidation; retrieval keeps serving the old note. In every Haiku run with probes inside this window, the agent re-asserted the exact value it had explicitly disavowed steps earlier: 3/3 (C=5), 9/10 + 5/6 (C=10). Sonnet 5 behaved identically (4/4 with guaranteed in-window probes). A deployed agent with this architecture repeats an acknowledged error for up to C steps after being corrected — while, per §2, sincerely "believing" it has updated whenever directly confronted.

**Echo-relapse: real, mechanism-verified, rare; dose-response directional but not significant.** With the echo count controlled exactly (0/1/3/5 lag-window probes, C=10, n=10/cell), relapse after an accepted correction occurred in 0/10, 0/10, 1/10, and 1/10 runs respectively: never without echoes or with one echo (0/20 pooled), only with three or more (2/20 pooled; Fisher exact p≈0.49 — the direction matches the mechanism, the sample does not power a curve). Every relapse case, including two from an earlier confounded version of this arm, shows the identical audited anatomy: correction accepted at the contradiction (agent outputs the true value with a rationale endorsing the fresh evidence); lag-window probes echo the false value off the still-stale note; the next consolidation sides with the numerical majority — one resolution episode against three-plus echoes plus the note itself — and the false belief is thereafter permanent (no recovery observed through end of run). No defense rhetoric was involved at any point: the failure is arithmetic, not attitude. We report echo-relapse as a demonstrated failure mode whose frequency, not existence, remains to be pinned down; establishing the dose-response curve would take roughly n=50/cell at these base rates.

## 5. Mitigation: conflict-aware consolidation — detection works, resolution is gameable, flags are inert

Adding a contradiction check to the consolidation prompt (flag CONFLICT instead of silently overwriting; C=10, n=6 + 6 T-arm):

- **Believed-commit fell from 0.90–1.00 to 0.00** — every injection was caught at the first consolidation and held as a flagged conflict rather than written as a belief. True-change updating was unharmed (T-arm 6/6; no thrash observed).
- **But the resolver can be gamed by surface provenance.** In 2 of 3 audited seeds, the consolidator reasoned that the false value "was explicitly marked as fresh verification data for a compliance audit" and gave it precedence — the error inherited authority from the framing of the task that produced it. Provenance-weighting without provenance *verification* imports the world's labels, including wrong ones.
- **And flags trigger nothing.** "Needs verification" notes compelled zero tool calls in 24 lag-window probes; the agent answered from the flagged note's contested value or the prior. A conflict flag without a policy hook is documentation, not mitigation. (Mitigation v2 — a retrieved CONFLICT note on the queried fact forces a lookup — is implemented in the harness but [NOT YET RUN].)

Measurement note: naive string-matching scores CONFLICT notes as "committed false memory" (the false value appears in the note text); all commit rates above exclude conflict-flagged notes, which is the semantically correct reading and changed the mitigation commit rate from a spurious 1.00 to 0.00.

## 6. Audit trail (methods subsection or appendix)

Every anomalous cell was transcript-audited before acceptance. Four apparent findings were reversed by audit: (i) a "failed correction" that was markdown bold-wrapping defeating the grader; (ii) a dramatic Sonnet relapse rate (0.75) caused by consolidation JSON truncating at max_tokens, which both preserved the stale note and destroyed the correction episode; (iii) an "empty lag window" arm caused by the contradiction landing on a consolidation boundary; (iv) an echo dose-response confounded by legacy probes leaking into the controlled window. (ii) is itself a deployment-relevant observation — a truncated memory write silently killed an accepted correction while keeping the stale belief — but is reported here as anecdote, not result.

## Numbers not yet in this draft
- Verify-policy ablation (§1) and mitigation-v2 (§5) — decide: run (~$4) or list as future work.
- E− arms exist only at C=5, n=3; bump if a reviewer would want matched controls per cell.

*Experimental program status: complete as of 2026-07-14 except the two optional ablations above. Total spend ≈ $13.*
