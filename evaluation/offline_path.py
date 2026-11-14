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
    r"\b(ending it all|kill myself|suicide|self[- ]harm|don'?t see the point)\b",
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
    "peer_comparison": ["feed", "promoted", "falling behind", "朋友们"],
    "performing_wellness": ["doing great", "pretending", "posted about", "morning routine"],
    "crisis": ["ending it all", "kill myself"],
    "grief": ["passed", "grandmother", "funeral"],
    "creative_block": ["blank page", "staring", "write"],
    "relationship_conflict": ["partner", "we barely talked"],
    "work_stress": ["deadlines", "meeting", "work"],
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
    if not emotions and situation is None and len(text.split()) < 15:
        out = InterpreterOutput.abstain()
        out.rejected_ids = rejected
        out.raw_output = "offline:abstain"
        return out

    theme = _find_label(text, THEME_HINTS)
    secondary = None
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