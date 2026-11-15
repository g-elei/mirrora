"""Real scorer for the frozen 11-scenario set.

evaluation/run_eval.py marks every scenario PASS without looking at any output, so
it cannot produce the numbers in Baseline.md. This module computes them from
scenarios.json + the two interpreter paths, micro and macro, and prints both so a
claimed figure can be matched rather than trusted.

Usage:
  python -m evaluation.score --path offline
  python -m evaluation.score --path qwen
  python -m evaluation.score --path both
"""
from __future__ import annotations

import argparse, json, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "evaluation"))
sys.path.insert(0, str(BASE))

from offline_path import offline_fallback  # noqa: E402

SCENARIOS = json.loads((BASE / "evaluation" / "scenarios.json").read_text(encoding="utf-8"))


def _labels(tags):
    return {t["label"] if isinstance(t, dict) else t.label for t in (tags or [])}


def _run_offline(sc, recall_cache):
    return offline_fallback(sc["text"], sc.get("provided_ids", []))


def _run_qwen(sc, recall_cache):
    from qwen_path import live_qwen
    return live_qwen(sc["text"], sc.get("provided_ids", []))


def evaluate(runner, name):
    tp = fp = fn = 0
    per_scenario = []
    sit_ok = sit_total = theme_ok = abst_ok = reject_ok = crisis_ok = 0
    parse_fail = 0

    for sc in SCENARIOS:
        gold = sc["gold"]
        g_emo = _labels(gold["emotions"])
        should_abstain = gold["should_abstain"]
        # crisis scenarios carry situation "null" per Baseline's documented decision
        g_sit = gold["situation"]
        g_theme = gold["primary_theme"]

        try:
            out = runner(sc, None)
        except Exception as exc:  # parse failure counts against the path
            parse_fail += 1
            print(f"  [{name}] {sc['id']}: FAILED — {exc}")
            per_scenario.append({"id": sc["id"], "p": 0.0, "r": 0.0})
            fn += len(g_emo)
            continue

        p_emo = _labels(getattr(out, "emotions", []))
        scen_tp = len(p_emo & g_emo)
        scen_fp = len(p_emo - g_emo)
        scen_fn = len(g_emo - p_emo)
        tp, fp, fn = tp + scen_tp, fp + scen_fp, fn + scen_fn
        per_scenario.append({
            "id": sc["id"],
            "p": scen_tp / len(p_emo) if p_emo else (1.0 if not g_emo else 0.0),
            "r": scen_tp / len(g_emo) if g_emo else 1.0,
            "pred": sorted(p_emo), "gold": sorted(g_emo),
            "situation": getattr(out, "situation", None), "gold_situation": g_sit,
        })

        # Baseline documents that abstain and crisis scenarios are excluded from
        # situation scoring; crisis carries the string "null" rather than None.
        if not should_abstain and g_sit not in (None, "null"):
            sit_total += 1
            sit_ok += (getattr(out, "situation", None) == g_sit)
        theme_ok += (getattr(out, "primary_theme", None) == g_theme)
        abst_ok += (bool(getattr(out, "abstained", False)) == should_abstain)
        reject_ok += (set(getattr(out, "rejected_ids", []) or []) == set(gold["should_reject_ids"]))
        crisis_ok += (bool(getattr(out, "crisis_flagged", False)) == gold["should_flag_crisis"])

    micro_p = tp / (tp + fp) if tp + fp else 0.0
    micro_r = tp / (tp + fn) if tp + fn else 0.0
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if micro_p + micro_r else 0.0

    macro_p = sum(x["p"] for x in per_scenario) / len(per_scenario)
    macro_r = sum(x["r"] for x in per_scenario) / len(per_scenario)
    macro_f1 = sum((2 * x["p"] * x["r"] / (x["p"] + x["r"]) if x["p"] + x["r"] else 0)
                   for x in per_scenario) / len(per_scenario)

    return {
        "path": name,
        "emotion_precision_micro": round(micro_p, 3),
        "emotion_recall_micro": round(micro_r, 3),
        "emotion_f1_micro": round(micro_f1, 3),
        "emotion_precision_macro": round(macro_p, 3),
        "emotion_recall_macro": round(macro_r, 3),
        "emotion_f1_macro": round(macro_f1, 3),
        "situation_accuracy": round(sit_ok / (sit_total or 1), 3),
        "primary_theme_accuracy": round(theme_ok / len(SCENARIOS), 3),
        "abstention_accuracy": round(abst_ok / len(SCENARIOS), 3),
        "reject_ids_accuracy": round(reject_ok / len(SCENARIOS), 3),
        "crisis_accuracy": round(crisis_ok / len(SCENARIOS), 3),
        "parse_failures": parse_fail,
        "per_scenario": per_scenario,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", choices=["offline", "qwen", "both"], default="both")
    ap.add_argument("--dump", action="store_true")
    a = ap.parse_args()

    results = []
    if a.path in ("offline", "both"):
        results.append(evaluate(_run_offline, "offline"))
    if a.path in ("qwen", "both"):
        results.append(evaluate(_run_qwen, "qwen"))

    keys = ["emotion_precision_micro", "emotion_recall_micro", "emotion_f1_micro",
            "emotion_precision_macro", "emotion_recall_macro", "emotion_f1_macro",
            "situation_accuracy", "primary_theme_accuracy", "abstention_accuracy",
            "reject_ids_accuracy", "crisis_accuracy", "parse_failures"]
    print(f"{'dimension':<26}" + "".join(f"{r['path']:>10}" for r in results))
    print("-" * (26 + 10 * len(results)))
    for k in keys:
        print(f"{k:<26}" + "".join(f"{r[k]:>10}" for r in results))

    outdir = BASE / "evaluation" / "results"
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = "2026-11-15_scorecard.json"
    (outdir / stamp).write_text(json.dumps({r["path"]: {k: r[k] for k in keys} for r in results},
                                           indent=2), encoding="utf-8")
    print(f"\nwritten: evaluation/results/{stamp}")

    if a.dump:
        for r in results:
            print(f"\n[{r['path']}] disagreements")
            for x in r["per_scenario"]:
                if x.get("pred") is not None and x["pred"] != x["gold"]:
                    print(f"  {x['id']}: pred={x['pred']} gold={x['gold']}")


if __name__ == "__main__":
    main()
