"""Matcher-level fit evaluation — the metric the old README was missing.

`run_eval`-era scoring asked "did the pipeline return something?" and counted 11/11.
That number is meaningless. This asks whether the passage returned is actually apt:

  emotion_fit  top-1 passage expresses at least one emotion in the scenario's gold set
  theme_fit    top-1 passage's themes include the gold primary theme
  fit          both of the above (a genuinely apt match)
  returned     a passage was returned at all (kept only for comparison)

Usage: python -m evaluation.match_eval
"""
from __future__ import annotations

import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core.matching as matching
from evaluation.offline_path import offline_fallback

SCEN = json.loads((ROOT / "evaluation" / "scenarios.json").read_text(encoding="utf-8"))


def main() -> int:
    corpus = matching.load_corpus()
    rows, returned, efit, tfit, both = [], 0, 0, 0, 0
    for s in SCEN:
        gold = s["gold"]
        if gold.get("should_abstain") or gold.get("crisis"):
            continue
        out = offline_fallback(s["text"])
        d = out.to_dict()
        ge = gold.get("emotions", [])
        gold_e = {e["label"] if isinstance(e, dict) else e for e in ge}
        gold_t = gold.get("primary_theme")
        ms = matching.match(s["text"], d.get("emotions", []), d.get("primary_theme"),
                            d.get("secondary_theme"), corpus=corpus, top_k=1)
        if not ms:
            rows.append((s["id"], "-", False, False, False, "no match"))
            continue
        top = ms[0]
        p = next(x for x in corpus if x["id"] == top.passage_id)
        emo_ok = bool(gold_e & (set(p["expresses"]) | set(p["addresses"])))
        theme_ok = bool(gold_t and gold_t in p["themes"])
        returned += 1
        efit += emo_ok
        tfit += theme_ok
        both += (emo_ok and theme_ok)
        rows.append((s["id"], f"{p['book']} ({top.score:.2f}, {top.fit()})",
                     emo_ok, theme_ok, emo_ok and theme_ok, ""))

    scored = len(rows)
    print(f"scored scenarios (excl. abstain/crisis): {scored}")
    print(f"returned a passage      {returned}/{scored}")
    print(f"emotion fit             {efit}/{scored}  = {efit/scored:.2f}")
    print(f"theme fit               {tfit}/{scored}  = {tfit/scored:.2f}")
    print(f"fit (emotion AND theme) {both}/{scored}  = {both/scored:.2f}\n")
    print(f"{'scenario':<12}{'top match':<34}{'emo':<5}{'theme':<7}{'fit'}")
    for sid, top, e, t, b, note in rows:
        print(f"{sid:<12}{top:<34}{'yes' if e else 'no':<5}{'yes' if t else 'no':<7}"
              f"{'yes' if b else 'no'}  {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
