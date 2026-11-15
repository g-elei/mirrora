"""Phase 5 — response generation and grounding.

Two rules from Phase 1 that this module enforces mechanically rather than by prompt:

1. A quotation is either verbatim in the corpus or it is not printed. `validate_quotes`
   runs on every generated reply; a failure is repaired by falling back to the
   deterministic composer, never by trusting the model.
2. Crisis is a routing decision, not a literary moment. When crisis is flagged, no
   passage is offered — the reply points at human help.

The LLM is optional. Without one the deterministic composer still produces a warm,
passage-grounded reply, so the product works with no key and no network.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from core.matching import load_corpus

# Each persona must sound different even with no model and no network, because the
# deterministic composer is the default path. Same facts, different stance.
VOICES = {
    "confidant": {
        "name": "Warm Confidant",
        "open": "That sounds heavy, and I'm glad you put it into words here.",
        "bridge": "I'm not handing it to you as a lesson — it's closer to company than advice.",
        "close": "Which part of that feels nearest to where you actually are, and which part doesn't fit?",
    },
    "philosopher": {
        "name": "Stoic Philosopher",
        "open": "Some things are better sat with than solved.",
        "bridge": "Not consolation — perspective. What is yours to carry, and what never was.",
        "close": "Of what you've described, what is actually yours to act on this week?",
    },
    "cinephile": {
        "name": "Witty Cinephile",
        "open": "Okay — this has a shape I recognise.",
        "bridge": "I'm quoting it because it lands, not because it resolves anything.",
        "close": "If this were a scene, what's the next beat?",
    },
    "mentor": {
        "name": "Beihang Senior Mentor",
        "open": "I've been roughly where you are, and it's usually rhythm more than ability.",
        "bridge": "Read it as a note from someone a year ahead, not a verdict.",
        "close": "What's the one thing you could fix before Friday?",
    },
}
DEFAULT_VOICE = "confidant"


def _voice(persona: str | None) -> dict:
    return VOICES.get(persona or DEFAULT_VOICE, VOICES[DEFAULT_VOICE])


QUOTE_RE = re.compile(r"[\u201c\"]([^\u201d\"]{6,400})[\u201d\"]")


def _norm(s: str) -> str:
    s = (s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"')
         .replace("\u201d", '"').replace("\u2014", "—").replace("\u2013", "-")
         .replace("\u00a0", " "))
    return re.sub(r"\s+", " ", s).strip()


@dataclass
class GroundingResult:
    ok: bool
    violations: list[str]

    def to_dict(self) -> dict:
        return {"ok": self.ok, "violations": self.violations}


def validate_quotes(reply: str, corpus: list[dict] | None = None) -> GroundingResult:
    """Every quoted span in `reply` must appear verbatim somewhere in the corpus."""
    corpus = corpus if corpus is not None else load_corpus()
    haystacks = [_norm(p["text"]) for p in corpus]
    bad = []
    for span in QUOTE_RE.findall(reply):
        needle = _norm(span)
        if not any(needle in h for h in haystacks):
            bad.append(span[:80])
    return GroundingResult(not bad, bad)


LABEL_HINTS = {
    "envy": r"envy|envious|jealous", "shame": r"shame|ashamed|humiliat",
    "sadness": r"sad|sorrow|grief|wept|cried", "loneliness": r"lonely|alone|solitary|conceal",
    "anxiety": r"anxious|afraid|dread|agonies|nervous", "fear": r"fear|afraid|terror",
    "anger": r"angry|anger|furious|rage", "frustration": r"frustrat|could not bear|madden",
    "exhaustion": r"tired|weary|exhaust", "guilt": r"guilt|guilty|remorse|penitence",
    "self_doubt": r"doubt|despicable|base and mean|not good enough",
    "hope": r"hope", "relief": r"relief|relieved|ease", "love": r"love|loved",
    "pride": r"proud|pride", "joy": r"joy|delight|happy", "gratitude": r"grateful|thank",
    "determination": r"resolve|determin|would not give", "confusion": r"confus|perplex|bewilder",
    "ambition": r"ambition|rise|career",
}


def _pick_sentence(text: str, labels: list[str] | None = None, max_words: int = 34) -> str:
    """Prefer a sentence that actually carries the matched emotion, so the quotation is
    evidence rather than decoration."""
    sentences = re.split(r"(?<=[.!?])\s+", _norm(text))
    for label in labels or []:
        pat = LABEL_HINTS.get(label)
        if not pat:
            continue
        for sen in sentences:
            if re.search(pat, sen, re.I) and len(sen.split()) >= 6:
                return _clip(sen, max_words)
    return _clip(sentences[0] if sentences else text, max_words)


def _clip(sentence: str, max_words: int) -> str:
    words = sentence.split()
    if len(words) > max_words:
        return " ".join(words[:max_words]).rstrip(",;:") + "…"
    return sentence.strip()


def _first_sentence(text: str, max_words: int = 34) -> str:
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    cand = (m.group(1) if m else text).strip()
    words = cand.split()
    if len(words) > max_words:
        cand = " ".join(words[:max_words]).rstrip(",;:") + "…"
    return cand


CRISIS_REPLY = (
    "What you've written sounds like more than a hard day, and I want to be straight with you "
    "rather than literary: this is worth telling a person, not a book. If you are in danger right now, "
    "please contact your local emergency number or a crisis line in your country. If you can, reach "
    "someone you trust today — a friend, a family member, a counsellor — and say the sentence you "
    "wrote here out loud to them. I'm still here, and I'll keep listening, but I'm not a substitute "
    "for that call."
)


def compose(entry_text: str, matches, primary_theme: str | None,
            persona: str = DEFAULT_VOICE, crisis: bool = False,
            labels: list[str] | None = None) -> tuple[str, dict]:
    """Deterministic, passage-grounded reply. Used always for crisis, and as the fallback
    whenever the LLM is unavailable or produces an ungrounded quotation."""
    if crisis:
        return CRISIS_REPLY, {"source": "rule", "grounded": True, "passage_id": None}

    v = _voice(persona)

    if not matches:
        return (f"{v['open']} I don't want to hand you a quotation just to fill the silence — "
                f"nothing in what you wrote points at something I can honestly match. "
                f"Tell me a little more about what happened, or what today actually felt like, "
                f"and I'll look again."), \
               {"source": "rule", "grounded": True, "passage_id": None, "persona": v["name"]}

    m = matches[0]
    quote = _pick_sentence(m.text, labels)
    theme_line = f"On {primary_theme}, " if primary_theme else ""
    body = (
        f"{v['open']} {theme_line}there's a piece of writing that sits close to this: "
        f"\u201c{quote}\u201d — {m.book}, {m.author}. "
        f"{v['bridge']} {v['close']}"
    )
    return body, {"source": "rule", "grounded": True, "passage_id": m.passage_id,
                  "match_score": round(m.score, 3), "persona": v["name"]}


SYSTEM = (
    "You are Mirrora, a literary companion. Tone: warm, thoughtful, never relentlessly positive. "
    "Reply in 3-6 sentences. You may quote at most one passage, and only from the passage supplied; "
    "quote it exactly, or not at all. Do not diagnose, do not give advice lists, and do not claim the "
    "user's feeling is a lesson. End with one honest question."
)


def build_prompt(entry_text: str, matches, recent: list[dict] | None = None) -> str:
    lines = ["The user's check-in:", entry_text, ""]
    if matches:
        m = matches[0]
        lines += [f"Candidate passage ({m.book}, {m.author}):", m.text,
                  f"Why it matched: {'; '.join(m.explanation)}", ""]
    else:
        lines += ["No passage matched. Do not invent one.", ""]
    if recent:
        lines.append("Recent check-ins for continuity (do not quote them):")
        for r in recent[:3]:
            lines.append(f"- {r['created_at'][:10]}: {r['text'][:120]}")
    return "\n".join(lines)


def generate(entry_text: str, matches, primary_theme: str | None, llm=None,
             recent: list[dict] | None = None, crisis: bool = False,
             labels: list[str] | None = None,
             persona: str = DEFAULT_VOICE) -> tuple[str, dict]:
    """LLM if available, deterministic composer otherwise, with grounding enforced after."""
    if crisis or llm is None:
        return compose(entry_text, matches, primary_theme, crisis=crisis,
                       labels=labels, persona=persona)

    try:
        reply = llm(SYSTEM, build_prompt(entry_text, matches, recent))
    except Exception as exc:                      # never let a provider outage break the product
        body, meta = compose(entry_text, matches, primary_theme, labels=labels, persona=persona)
        meta["llm_error"] = str(exc)[:120]
        return body, meta

    g = validate_quotes(reply)
    if not g.ok:
        body, meta = compose(entry_text, matches, primary_theme, labels=labels, persona=persona)
        meta["grounding_rejected"] = g.violations
        return body, meta

    return reply, {"source": "llm", "grounded": True,
                   "passage_id": matches[0].passage_id if matches else None}
