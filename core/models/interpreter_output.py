"""Shared output schema for both interpreter paths (offline fallback and live Qwen).

Both offline_fallback() and live_qwen() MUST return an InterpreterOutput.
The evaluation harness (run_eval.py) consumes this and nothing else.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class EmotionTag:
    label: str
    intensity: int  # 1..5

    def __post_init__(self) -> None:
        if not (1 <= self.intensity <= 5):
            raise ValueError(f"intensity must be 1..5, got {self.intensity}")


@dataclass
class InterpreterOutput:
    # --- core extraction ---
    emotions: list[EmotionTag] = field(default_factory=list)
    situation: Optional[str] = None
    primary_theme: Optional[str] = None
    secondary_theme: Optional[str] = None

    # --- control signals ---
    abstained: bool = False
    rejected_ids: list[str] = field(default_factory=list)
    crisis_flagged: bool = False

    # --- debugging (never persisted in production) ---
    raw_output: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["emotions"] = [{"label": e.label, "intensity": e.intensity} for e in self.emotions]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "InterpreterOutput":
        return cls(
            emotions=[EmotionTag(**e) for e in d.get("emotions", [])],
            situation=d.get("situation"),
            primary_theme=d.get("primary_theme"),
            secondary_theme=d.get("secondary_theme"),
            abstained=bool(d.get("abstained", False)),
            rejected_ids=list(d.get("rejected_ids", [])),
            crisis_flagged=bool(d.get("crisis_flagged", False)),
            raw_output=d.get("raw_output"),
        )

    @classmethod
    def abstain(cls) -> "InterpreterOutput":
        """Convenience constructor for the vague-input path."""
        return cls(abstained=True, situation="unsupported_or_vague")

    @classmethod
    def crisis(cls) -> "InterpreterOutput":
        """Convenience constructor for the crisis path — no literary match."""
        return cls(crisis_flagged=True, situation="crisis", primary_theme=None, secondary_theme=None)