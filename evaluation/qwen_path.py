"""Live Qwen interpreter path.

Reads DASHSCOPE_API_KEY from the environment. Never hardcodes the key.
Returns InterpreterOutput or raises on parse failure (the harness counts
parse failures against Qwen).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from openai import OpenAI

from core.models.interpreter_output import EmotionTag, InterpreterOutput

BASE = Path(__file__).resolve().parent
TAXONOMY = json.loads((BASE / "taxonomy.json").read_text(encoding="utf-8"))

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
        if not key:
            raise RuntimeError("neither DASHSCOPE_API_KEY nor QWEN_API_KEY is set")
        _client = OpenAI(
            api_key=key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    return _client


EXTRACTION_PROMPT = """You are the interpretation layer of a literary-companion app.
Read the user's check-in and return ONLY a JSON object matching this schema:

{
  "emotions": [{"label": "<one of: __EMOTIONS__>", "intensity": 1-5}],
  "situation": "<one of: __SITUATIONS__> or null",
  "primary_theme": "<one of: __THEMES__> or null",
  "secondary_theme": "<one of: __THEMES__> or null",
  "abstained": true|false,
  "rejected_ids": ["<verbatim ids from provided_ids that are NOT in the emotion list>"],
  "crisis_flagged": true|false
}

VALIDATION RULE (must be applied exactly):
- Take the list `provided_ids` below.
- For EACH id in that list, check whether it appears EXACTLY in the emotion list above.
- If it does NOT appear exactly, add it to `rejected_ids`, copied verbatim.
- Do not add anything else to `rejected_ids`. Do not omit any invalid id.
- If `provided_ids` is empty, `rejected_ids` must be `[]`.

OTHER RULES:
- Rejecting an id does NOT mean abstaining. If the text still conveys a real
  feeling (e.g. "I feel hopeful about tomorrow"), extract it normally and
  ALSO list the invalid ids in rejected_ids.
- Only use emotion labels from the list. Do not invent labels.
- If the text is too vague to classify, set abstained=true and emotions=[].
- If the text contains self-harm or suicidal content, set crisis_flagged=true
  and primary_theme=null.
- Do not force emotions the text does not support. If envy is only mild,
  use intensity 2, or omit it.
- Output JSON only. No prose, no markdown fences.
- `emotions` must ONLY contain labels from the emotions list above.
  Themes and situations are DIFFERENT vocabularies — never put a theme
  like "courage" or a situation like "work_stress" in emotions.

Example A:
provided_ids = ["joyful_42", "hopeful_99"]
Text: "I feel really joyful_42 and a bit hopeful_99 about tomorrow."
Output:
{
  "emotions": [{"label": "hope", "intensity": 3}],
  "situation": null,
  "primary_theme": null,
  "secondary_theme": null,
  "abstained": false,
  "rejected_ids": ["joyful_42", "hopeful_99"],
  "crisis_flagged": false
}

Example B:
provided_ids = ["joy", "hopeful_99"]
"joy" IS an allowed emotion; "hopeful_99" is not.
Output: "rejected_ids": ["hopeful_99"]

Example: "My sister moved out last month and the flat is very quiet now."
Output:
{
  "emotions": [{"label": "loneliness", "intensity": 3}, {"label": "sadness", "intensity": 2}],
  "situation": "grief",
  "primary_theme": "loss",
  "secondary_theme": "belonging"
}

Example C:
provided_ids = []
Output: "rejected_ids": []

provided_ids = __PROVIDED_IDS__

User check-in:
__TEXT__
"""


def live_qwen(text: str, provided_ids: list[str] | None = None) -> InterpreterOutput:
    provided_ids = provided_ids or []
    prompt = (
    EXTRACTION_PROMPT
    .replace("__EMOTIONS__", ", ".join(TAXONOMY["emotions"]))
    .replace("__SITUATIONS__", ", ".join(TAXONOMY["situations"]))
    .replace("__THEMES__", ", ".join(TAXONOMY["themes"]))
    .replace("__PROVIDED_IDS__", json.dumps(provided_ids))
    .replace("__TEXT__", text)
     )
    resp = _get_client().chat.completions.create(
        model="qwen-plus",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=400,
    )
    raw = resp.choices[0].message.content or ""

    # Strip markdown fences if the model added them.
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").lstrip("json").strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Qwen returned non-JSON: {raw[:200]}") from exc

    # --- deterministic ID validation (do NOT trust the model for this) ---
    valid_emotions = set(TAXONOMY["emotions"])
    expected_rejected = [i for i in provided_ids if i not in valid_emotions]
    model_rejected = list(parsed.get("rejected_ids", []))
    if set(model_rejected) != set(expected_rejected):
        print(f"[qwen_path] rejected_ids mismatch: model={model_rejected} expected={expected_rejected}")
    parsed["rejected_ids"] = expected_rejected  # override with the computed truth
    parsed.pop("_model_rejected_ids", None)      # never sent to InterpreterOutput

    # --- validate emotion labels against the taxonomy ---
    for e in parsed.get("emotions", []):
        if e.get("label") not in valid_emotions:
            raise ValueError(f"Qwen returned unknown emotion label: {e.get('label')}")

    # --- build the output object AFTER all overrides ---
    out = InterpreterOutput.from_dict(parsed)
    out.raw_output = raw
    return out