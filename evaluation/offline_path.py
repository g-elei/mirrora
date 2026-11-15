"""Offline fallback interpreter path.

Returns InterpreterOutput. No network calls. This is the baseline
that live Qwen must beat on the frozen 11-scenario evaluation set.
"""
from __future__ import annotations

import re
from typing import Optional

from core.models.interpreter_output import EmotionTag, InterpreterOutput

# --- crisis phrases (deterministic, must not miss) ---
CRISIS_PATTERNS = [
    r"\b(ending it all|ending it|kill myself|killing myself|suicide|self[- ]harm|"
    r"hurt myself|harm myself|take my (own )?life|want to die|wish i (was|were) dead|"
    r"better off dead|better off without me|no reason to (live|go on)|nothing to live for)\b",
    r"\b(don'?t|do not) want to (be here|live|exist|wake up)\b",
    r"(不想活|想死|自杀|结束生命|没有活下去的意义)",
]

# A check-in that states a feeling then contradicts it is describing a mask, not a mood.
# Tagging the cheerful words literally is the topic-proximity failure this project exists
# to avoid, so contrast is required before the rule fires.
MASKING_CUES = [
    "told everyone", "doing great", "doing fine", "pretending", "pretend to be",
    "say i'm fine", "say i am fine", "i'm fine", "im fine", "holding it together",
    "nobody knows", "no one knows", "nobody know", "posted about", "morning routine",
    "look fine", "seem fine", "act like",
]

# --- minimal keyword -> emotion rules (replace/extend with your heuristic) ---
EMOTION_KEYWORDS = {
    "envy": ["falling behind", "everyone else", "jealous", "羡慕"],
    "self_doubt": ["not good enough", "wrong with me", "怀疑自己", "不够好"],
    "confusion": ["don't know", "迷茫", "lost", "unsure"],
    "sadness": ["sad", "crying", "passed", "emptier", "难过"],
    "loneliness": ["lonely", "miles apart", "alone", "孤独"],
    "frustration": ["frustrated", "relentless", "staring", "frustrated"],
    "exhaustion": ["exhausted", "crying in the bathroom", "can't keep", "累"],
    "shame": ["pretending", "ashamed", "embarrassed"],
    "pride": ["proud", "spoke up", "finally"],
    "joy": ["happy", "great", "开心"],
    "relief": ["relieved", "finally"],
    "hope": ["hopeful", "tomorrow", "希望"],
    "love": ["love", "grandmother", "partner", "爱"],
}

SITUATION_HINTS = {
    "peer_comparison": ["feed", "promoted", "falling behind", "朋友们", "everyone else",
                        "everyone did", "better than me", "left behind", "ahead of me",
                        "compared with", "effortless"],
    "performing_wellness": ["doing great", "pretending", "posted about", "morning routine"],
    "crisis": ["ending it all", "kill myself"],
    "grief": ["passed", "grandmother", "funeral"],
    "creative_block": ["blank page", "staring", "write"],
    "relationship_conflict": ["partner", "we barely talked"],
    "work_stress": ["deadlines", "meeting", "work"],
}

# Situation -> theme fallback (Phase 1 §5.2). Used only when no theme was inferred from
# wording, so a recognised situation still reaches the matcher with a primary theme.
SITUATION_THEMES = {
    "peer_comparison": ("ambition", "identity"),
    "performing_wellness": ("identity", "belonging"),
    "work_stress": ("failure", "ambition"),
    "relationship_conflict": ("love", "belonging"),
    "grief": ("loss", "love"),
    "creative_block": ("meaning", "failure"),
    "health_worry": ("fear", "fear"),
    "financial_stress": ("fear", "responsibility"),
    "identity_question": ("identity", "meaning"),
}

THEME_HINTS = {
    "ambition": ["promoted", "falling behind", "edge"],
    "identity": ["wrong with me", "who i am", "方向"],
    "loss": ["passed", "grandmother"],
    "love": ["partner", "grandmother", "love"],
    "failure": ["deadlines", "blank page", "lost my edge"],
    "meaning": ["point", "blank page"],
    "courage": ["spoke up", "shaking"],
    "fear": ["pretending", "scared"],
    "belonging": ["miles apart", "same room"],
}


def _find_emotions(text: str) -> list[EmotionTag]:
    out: list[EmotionTag] = []
    lowered = text.lower()
    for label, keywords in EMOTION_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in lowered)
        if hits:
            intensity = min(5, 2 + hits)
            out.append(EmotionTag(label=label, intensity=intensity))
    return out


def _find_label(text: str, hints: dict[str, list[str]]) -> Optional[str]:
    lowered = text.lower()
    best: Optional[str] = None
    best_hits = 0
    for label, keywords in hints.items():
        hits = sum(1 for kw in keywords if kw in lowered)
        if hits > best_hits:
            best, best_hits = label, hits
    return best


def offline_fallback(text: str, provided_ids: list[str] | None = None) -> InterpreterOutput:
    provided_ids = provided_ids or []

    # 1. Crisis takes precedence over everything.
    for pattern in CRISIS_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            out = InterpreterOutput.crisis()
            out.emotions = _find_emotions(text)
            out.raw_output = "offline:crisis"
            return out

    # 2. Reject ids not present in the taxonomy.
    from pathlib import Path
    import json
    tax_path = Path(__file__).resolve().parent / "taxonomy.json"
    valid = set(json.loads(tax_path.read_text(encoding="utf-8"))["emotions"])
    rejected = [i for i in provided_ids if i not in valid]

    # 3. Vague input -> abstain.
    emotions = _find_emotions(text)
    situation = _find_label(text, SITUATION_HINTS)

    # Masking: a stated feeling immediately contradicted. Drop the surface positives and
    # name what the concealment itself costs.
    lowered = text.lower()
    if any(c in lowered for c in MASKING_CUES) and any(
            c in lowered for c in (" but ", "though", "however", "yet ", "even though", "actually")):
        situation = "performing_wellness"
        emotions = [e for e in emotions if e.label not in {"joy", "pride", "relief", "hope", "gratitude"}]
        have = {e.label for e in emotions}
        for label, inten in (("exhaustion", 3), ("loneliness", 3), ("shame", 2)):
            if label not in have:
                emotions.append(EmotionTag(label=label, intensity=inten))
    if not emotions and situation is None and len(text.split()) < 15:
        out = InterpreterOutput.abstain()
        out.rejected_ids = rejected
        out.raw_output = "offline:abstain"
        return out

    theme = _find_label(text, THEME_HINTS)
    secondary = None
    if theme is None and situation in SITUATION_THEMES:
        theme, secondary = SITUATION_THEMES[situation]
    remaining = {k: v for k, v in THEME_HINTS.items() if k != theme}
    secondary = _find_label(text, remaining) if remaining else None

    return InterpreterOutput(
        emotions=emotions,
        situation=situation,
        primary_theme=theme,
        secondary_theme=secondary,
        rejected_ids=rejected,
        raw_output="offline",
    )