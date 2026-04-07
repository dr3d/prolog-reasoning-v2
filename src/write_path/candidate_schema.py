#!/usr/bin/env python3
"""Schemas for write-path proposal checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


PROPOSAL_STATUSES = {"valid", "needs_clarification", "reject"}


@dataclass
class CandidateFact:
    """Normalized candidate fact proposal."""

    canonical_predicate: str
    arguments: List[str]
    normalized_fact: str
    source: str = "text"
    raw_predicate: Optional[str] = None


@dataclass
class ProposalCheckResult:
    """Deterministic validation output for a candidate fact."""

    status: str
    issues: List[str] = field(default_factory=list)
    candidate: Optional[CandidateFact] = None
    reasoning: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        payload = {
            "status": self.status,
            "issues": self.issues,
            "reasoning": self.reasoning,
        }
        if self.candidate is not None:
            payload["candidate"] = {
                "canonical_predicate": self.candidate.canonical_predicate,
                "arguments": self.candidate.arguments,
                "normalized_fact": self.candidate.normalized_fact,
                "source": self.candidate.source,
                "raw_predicate": self.candidate.raw_predicate,
            }
        return payload
