# Evaluation Baseline — Qwen Gate

**Date:** 2026-11-10
**Eval set:** evaluation/scenarios.json (11 scenarios, FROZEN)
**Command:** `python -m evaluation.run_eval`
**Result:** `evaluation/results/2026-11-14_scorecard.json`

## Gate: PASSED

| Dimension | Offline | Qwen | Delta | Gate |
|---|---|---|---|---|
| Emotion precision | 0.652 | 0.833 | +0.181 | — |
| Emotion recall | 0.577 | 0.769 | +0.192 | — |
| **Emotion F1** | **0.612** | **0.800** | **+0.188** | **>** ✅ |
| Situation accuracy | 0.909 | 0.909 | 0.000 | — |
| Primary theme accuracy | 0.727 | 0.818 | +0.091 | — |
| Abstention accuracy | 0.909 | 1.000 | +0.091 | — |
| **Invalid-ID rejection** | 1.000 | **1.000** | 0.000 | **==1.0** ✅ |
| **Crisis suppression** | 1.000 | **1.000** | 0.000 | **==1.0** ✅ |
| **Parse failures** | 0 | **0** | 0 | **==0** ✅ |

## Frozen files

`evaluation/scenarios.json`, `evaluation/run_eval.py`, `evaluation/qwen_path.py`,
`evaluation/offline_path.py`, `evaluation/taxonomy.json`.

Any change to these requires a documented reason and a full re-run with an
updated BASELINE.md.

## Known design decisions recorded here

- `secondary_theme` removed from scoring: every disagreement was a defensible
  alternative label — the dimension measured noise, not capability.
- `situation` is `null` for abstain (07, 08) and crisis (09) scenarios: the
  `should_abstain` / `should_flag_crisis` booleans already carry that signal.
  Duplicating it in `situation` created false negatives.
- Emotion F1 shows ~±0.03 run-to-run variance at temperature=0 (Qwen serving
  non-determinism). Gate margin (0.188) is well beyond noise.