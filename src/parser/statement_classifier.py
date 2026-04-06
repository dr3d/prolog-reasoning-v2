#!/usr/bin/env python3
"""
Deterministic statement classification for routing user utterances.

This is a lightweight control layer that sits before query execution.
It is intentionally rule-based so the system can make predictable routing
decisions even when a small language model is driving the interaction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class StatementKind(str, Enum):
    """High-level routing categories for user utterances."""

    QUERY = "query"
    HARD_FACT = "hard_fact"
    TENTATIVE_FACT = "tentative_fact"
    CORRECTION = "correction"
    PREFERENCE = "preference"
    SESSION_CONTEXT = "session_context"
    INSTRUCTION = "instruction"
    UNKNOWN = "unknown"


@dataclass
class StatementClassification:
    """Structured routing decision for a user utterance."""

    kind: StatementKind
    confidence: float
    needs_speaker_resolution: bool = False
    can_query_now: bool = False
    can_persist_now: bool = False
    suggested_operation: str = "none"
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to a model-friendly shape."""
        return {
            "kind": self.kind.value,
            "confidence": self.confidence,
            "needs_speaker_resolution": self.needs_speaker_resolution,
            "can_query_now": self.can_query_now,
            "can_persist_now": self.can_persist_now,
            "suggested_operation": self.suggested_operation,
            "reasons": self.reasons,
        }


QUESTION_PREFIXES = (
    "who",
    "what",
    "when",
    "where",
    "why",
    "how",
    "is",
    "are",
    "does",
    "do",
    "did",
    "can",
    "could",
    "will",
    "would",
    "should",
)

INSTRUCTION_QUERY_PREFIX_EXCLUSIONS = (
    "do not ",
    "don't ",
    "never ",
    "remember to ",
    "always ",
    "use ",
)

CORRECTION_CUES = (
    "actually",
    "i meant",
    "correction",
    "rather",
    "instead",
)

TENTATIVE_CUES = (
    "maybe",
    "might",
    "i think",
    "probably",
    "possibly",
    "not sure",
)

PREFERENCE_CUES = (
    "i like",
    "i prefer",
    "please",
    "call me",
    "keep responses",
    "keep your responses",
)

SESSION_CONTEXT_CUES = (
    "for this session",
    "in this project",
    "for now",
    "today i am",
)

INSTRUCTION_CUES = (
    "use ",
    "don't ",
    "do not ",
    "remember to ",
    "always ",
    "never ",
)

FIRST_PERSON_TOKENS = (" my ", " our ", " me ", " us ", " we ")

FACT_RELATION_CUES = (
    " is ",
    " was ",
    " are ",
    " works for ",
    " reports to ",
    " manager is ",
    " mother ",
    " father ",
    " parent ",
    " sibling ",
    " allergic to ",
)


class StatementClassifier:
    """Rule-based utterance classifier for query and ingestion routing."""

    def classify(self, text: str) -> StatementClassification:
        raw = (text or "").strip()
        lower = f" {raw.lower()} "
        reasons: List[str] = []

        if not raw:
            return StatementClassification(
                kind=StatementKind.UNKNOWN,
                confidence=0.0,
                reasons=["empty input"],
            )

        if self._looks_like_query(raw):
            reasons.append("question form detected")
            return StatementClassification(
                kind=StatementKind.QUERY,
                confidence=0.95,
                can_query_now=True,
                suggested_operation="query",
                reasons=reasons,
            )

        if self._contains_any(lower, CORRECTION_CUES):
            reasons.append("correction cue detected")
            return StatementClassification(
                kind=StatementKind.CORRECTION,
                confidence=0.9,
                suggested_operation="revise_memory",
                needs_speaker_resolution=self._needs_speaker_resolution(lower),
                reasons=reasons,
            )

        if self._contains_any(lower, PREFERENCE_CUES):
            reasons.append("preference cue detected")
            return StatementClassification(
                kind=StatementKind.PREFERENCE,
                confidence=0.82,
                suggested_operation="store_preference",
                needs_speaker_resolution=self._needs_speaker_resolution(lower),
                reasons=reasons,
            )

        if self._contains_any(lower, SESSION_CONTEXT_CUES):
            reasons.append("session-scoped context cue detected")
            return StatementClassification(
                kind=StatementKind.SESSION_CONTEXT,
                confidence=0.75,
                suggested_operation="store_session_context",
                needs_speaker_resolution=self._needs_speaker_resolution(lower),
                reasons=reasons,
            )

        if self._contains_any(lower, TENTATIVE_CUES):
            reasons.append("tentative language detected")
            return StatementClassification(
                kind=StatementKind.TENTATIVE_FACT,
                confidence=0.76,
                suggested_operation="store_tentative_fact",
                needs_speaker_resolution=self._needs_speaker_resolution(lower),
                reasons=reasons,
            )

        if self._looks_like_instruction(lower):
            reasons.append("instruction cue detected")
            return StatementClassification(
                kind=StatementKind.INSTRUCTION,
                confidence=0.72,
                suggested_operation="follow_instruction",
                needs_speaker_resolution=self._needs_speaker_resolution(lower),
                reasons=reasons,
            )

        if self._looks_like_declarative_fact(lower):
            reasons.append("declarative relation pattern detected")
            return StatementClassification(
                kind=StatementKind.HARD_FACT,
                confidence=0.81,
                suggested_operation="store_fact",
                needs_speaker_resolution=self._needs_speaker_resolution(lower),
                reasons=reasons,
            )

        return StatementClassification(
            kind=StatementKind.UNKNOWN,
            confidence=0.4,
            reasons=["no strong routing cues detected"],
        )

    def _looks_like_query(self, text: str) -> bool:
        stripped = text.strip().lower()
        if stripped.startswith(INSTRUCTION_QUERY_PREFIX_EXCLUSIONS):
            return False
        return stripped.endswith("?") or stripped.startswith(QUESTION_PREFIXES)

    def _looks_like_declarative_fact(self, lower: str) -> bool:
        return self._contains_any(lower, FACT_RELATION_CUES)

    def _looks_like_instruction(self, lower: str) -> bool:
        return self._contains_any(lower, INSTRUCTION_CUES)

    def _needs_speaker_resolution(self, lower: str) -> bool:
        return self._contains_any(lower, FIRST_PERSON_TOKENS)

    def _contains_any(self, haystack: str, needles: tuple[str, ...]) -> bool:
        return any(needle in haystack for needle in needles)
