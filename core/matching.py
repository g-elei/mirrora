"""Phase 4 — the matching engine.

Three layers, weighted 0.45 / 0.25 / 0.30 exactly as Phase 1 §5.4 specifies:

  emotion    shared taxonomy overlap, weighted by reported intensity; a passage that
             *expresses* an emotion counts 1.0, one that merely *addresses* it counts 0.6
  theme      primary theme 1.0, secondary 0.6
  semantic   lexical similarity — a placeholder for Sentence Transformers

Every match carries an `explanation`: per §5.4 a match without a reason is not a match.
Nothing here is tuned; the weights are frozen provisional values.
"""
from __future__ import annotations

import json, math, re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEIGHT_EMOTION, WEIGHT_THEME, WEIGHT_SEMANTIC = 0.45, 0.25, 0.30
EXPRESS, ADDRESS = 1.0, 0.6

STOP = set("""a an the and or but if then than that this these those i you he she it we they
me him her us them my your his its our their is are was were be been being am do does did
have has had will would can could shall should may might must not no so as at by for from
in into of on onto to with about over under again very just too also there here when what
which who whom whose how why all any both each few more most other some such only own same
s t don now""".split())


def _tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z']+", text.lower()) if w not in STOP and len(w) > 2]


def _lexical(a: str, b: str) -> float:
    """Cosine over content words. Deterministic, offline, and honest about being weak:
    it rewards shared vocabulary, not shared meaning."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    ca, cb = {}, {}
    for t in ta:
        ca[t] = ca.get(t, 0) + 1
    for t in tb:
        cb[t] = cb.get(t, 0) + 1
    keys = set(ca) | set(cb)
    dot = sum(ca.get(k, 0) * cb.get(k, 0) for k in keys)
    na = math.sqrt(sum(v * v for v in ca.values()))
    nb = math.sqrt(sum(v * v for v in cb.values()))
    return dot / (na * nb) if na and nb else 0.0


def load_corpus() -> list[dict]:
    return json.loads((ROOT / "data" / "seed" / "passages.json").read_text(encoding="utf-8"))


def load_taxonomy() -> dict:
    return json.loads((ROOT / "evaluation" / "taxonomy.json").read_text(encoding="utf-8"))


@dataclass
class Match:
    passage_id: str
    book: str
    author: str
    text: str
    score: float
    layers: dict = field(default_factory=dict)
    explanation: list[str] = field(default_factory=list)

    def fit(self) -> str:
        """How much of this match is real: a match carried only by theme, or only by a
        single weak emotion, is a partial fit and should be shown as one."""
        e, t = self.layers["emotion"], self.layers["theme"]
        if e >= 0.6 and t > 0:
            return "strong"
        if e >= 0.4 or t >= 0.5:
            return "partial"
        return "weak"

    def to_dict(self) -> dict:
        return {
            "passage_id": self.passage_id, "book": self.book, "author": self.author,
            "text": self.text, "score": round(self.score, 3),
            "layers": {k: round(v, 3) for k, v in self.layers.items()},
            "explanation": self.explanation,
            "fit": self.fit(),
        }


def match(
    checkin_text: str,
    emotions: list[tuple[str, int]] | list[dict],
    primary_theme: str | None,
    secondary_theme: str | None = None,
    corpus: list[dict] | None = None,
    top_k: int = 3,
) -> list[Match]:
    corpus = corpus if corpus is not None else load_corpus()
    tax = load_taxonomy()
    known = set(tax["emotions"])

    pairs: list[tuple[str, int]] = []
    for e in emotions:
        if isinstance(e, dict):
            pairs.append((e.get("label") or e.get("id", ""), int(e.get("intensity", 3))))
        else:
            pairs.append((e[0], int(e[1])))
    pairs = [(l, max(1, min(5, i))) for l, i in pairs if l in known]

    # A check-in with no usable signal must return nothing. Returning a near-arbitrary
    # passage for every input is how the README's "11/11 returned, 4/11 apt" happened.
    if not pairs and not primary_theme:
        return []

    out: list[Match] = []
    for p in corpus:
        p_primary = p["themes"][0] if p["themes"] else None
        p_secondary = p["themes"][1:]

        total_w = sum(i / 5 for _, i in pairs)
        got = 0.0
        express_hits = 0
        hits = []
        for label, intensity in pairs:
            w = intensity / 5
            if label in p["expresses"]:
                got += w * EXPRESS
                express_hits += 1
                hits.append((label, "expresses", EXPRESS, intensity))
            elif label in p["addresses"]:
                got += w * ADDRESS
                hits.append((label, "addresses", ADDRESS, intensity))
        emo = got / total_w if total_w else 0.0

        q = [(primary_theme, 1.0)] if primary_theme else []
        if secondary_theme:
            q.append((secondary_theme, 0.6))
        tw = sum(w for _, w in q)
        tg = 0.0
        theme_hits = []
        for name, w in q:
            if name and name == p_primary:
                tg += w
                theme_hits.append((name, "principal", 1.0))
            elif name and name in p_secondary:
                tg += w * 0.6
                theme_hits.append((name, "secondary", 0.6))
        th = tg / tw if tw else 0.0

        sem = _lexical(checkin_text, p["text"])
        score = WEIGHT_EMOTION * emo + WEIGHT_THEME * th + WEIGHT_SEMANTIC * sem

        expl = []
        for label, rel, wt, intensity in hits:
            verb = "speaks as one who feels" if rel == "expresses" else "considers without itself feeling"
            expl.append(f"emotion: this passage {verb} {label} — you reported {label} at intensity {intensity}")
        for name, rel, _w in theme_hits:
            expl.append(f"theme: {name} is this passage's {rel} theme")
        if sem >= 0.12:
            shared = sorted(set(_tokens(checkin_text)) & set(_tokens(p["text"])))[:4]
            expl.append("wording: shared vocabulary " + ", ".join(f"'{s}'" for s in shared))
        if not expl:
            expl.append("surface wording only — no shared emotion or theme; this is a weak match by construction")

        m = Match(p["id"], p["book"], p.get("author", ""), p["text"], score,
                  {"emotion": emo, "theme": th, "semantic": sem}, expl)
        # A passage that genuinely feels the emotion outranks one that only consults it.
        m.rank = (score, express_hits, sem)
        out.append(m)

    out.sort(key=lambda m: (-m.rank[0], -m.rank[1], -m.rank[2]))
    # A passage carried by neither a real emotion overlap nor a real theme overlap is
    # returned only to fill the silence. Those are dropped: an empty result is more
    # honest than an irrelevant one, and the composer says so explicitly.
    out = [m for m in out
           if m.layers["emotion"] >= 0.25 or m.layers["theme"] >= 0.5]
    return out[:top_k]
