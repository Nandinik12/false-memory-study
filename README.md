# False-Memory Study Harness

Does a single natural tool error become a durable, compounding false belief in an
agent's consolidated memory — and does the agent self-correct or defend it?
See `DESIGN_SPEC.md` for the full design; `paper/paper_skeleton.md` for the writeup scaffold.

## Quick start

```bash
pip install -r requirements.txt

# 1. Validate the full pipeline at zero cost (rule-based mock agent):
python3 -m fmr.runner configs/mock.json
python3 -m fmr.analyze runs/mock

# 2. Real pilot (3 seeds x {E+, E-, T} x 60 steps, Haiku-class):
export ANTHROPIC_API_KEY=sk-...
./run_pilot.sh configs/pilot.json
```

Outputs per run dir: `*.jsonl` trajectory logs, `summary.json`,
`retention_curve.png`, `compounding_curve.png`, `correction_rates.png`.

## Layout

- `fmr/world.py` — synthetic ops world, ground truth, lookup tool, single-shot injection at step k, task schedule (probes, derived/compounding tasks, contradiction event, distractors)
- `fmr/memory.py` — episodic buffer → LLM consolidation → semantic notes; lexical retrieval; optional contradiction-aware mitigation prompt (`"mitigation": true`)
- `fmr/agent.py` — per-step loop; context = system + retrieved notes + task only (memory is the sole cross-step channel)
- `fmr/llm.py` — Anthropic backend + MockLLM (pipeline validation only — never a scientific result)
- `fmr/runner.py` — arms × seeds → graded JSONL logs
- `fmr/analyze.py` — commit/retention/compounding/correction/durability metrics, bootstrap CIs, plots

## Arms

`E+` error injected at k · `E-` no error (base rates) · `T` true change at k
(the updating-vs-stubbornness control). Entrenchment arms (early/late contradiction):
run two configs differing only in `contradiction_offset`.

## Cost notes

Pilot ≈ 9 runs × ~75 LLM calls ≈ 700 calls of a few hundred tokens each — small.
Scale seeds/steps in config. Mock mode is free and validates everything downstream of the LLM.
