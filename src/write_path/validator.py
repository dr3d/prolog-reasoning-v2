#!/usr/bin/env python3
"""Deterministic proposal validation for candidate fact writes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .candidate_schema import CandidateFact, ProposalCheckResult
from .normalizer import normalize_predicate_name, parse_prolog_fact, parse_text_fact


FACTISH_KINDS = {"hard_fact", "tentative_fact", "correction"}


class PredicateProposalValidator:
    """Validate candidate fact proposals against a deterministic predicate registry."""

    def __init__(self, registry_path: str):
        self.registry_path = Path(registry_path)
        self.registry = self._load_registry(self.registry_path)
        self.alias_to_canonical = self._build_alias_map(self.registry)

    def _load_registry(self, registry_path: Path) -> Dict[str, Any]:
        payload = json.loads(registry_path.read_text(encoding="utf-8-sig"))
        predicates = payload.get("predicates")
        if not isinstance(predicates, dict):
            raise ValueError("Invalid predicate registry: missing predicates object")
        return payload

    def _build_alias_map(self, registry: Dict[str, Any]) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        for canonical, meta in registry["predicates"].items():
            canonical_name = normalize_predicate_name(canonical)
            mapping[canonical_name] = canonical_name
            for alias in meta.get("aliases", []):
                alias_name = normalize_predicate_name(str(alias))
                if alias_name:
                    mapping[alias_name] = canonical_name
        return mapping

    def _resolve_canonical(self, predicate_name: str) -> Optional[str]:
        return self.alias_to_canonical.get(normalize_predicate_name(predicate_name))

    def _build_fact_text(self, predicate: str, arguments: list[str]) -> str:
        return f"{predicate}({', '.join(arguments)})."

    def evaluate(
        self,
        text: str,
        *,
        kind: str,
        needs_speaker_resolution: bool,
    ) -> dict:
        parsed_source = "unknown"
        parsed = parse_prolog_fact(text)
        if parsed is None:
            text_parsed = parse_text_fact(text)
            if kind not in FACTISH_KINDS:
                return ProposalCheckResult(
                    status="reject",
                    issues=[f"statement kind '{kind}' is not fact-like for write proposals"],
                    reasoning=["non-fact classification kinds are rejected in PR1 proposal-check"],
                ).to_dict()
            if text_parsed is None:
                return ProposalCheckResult(
                    status="needs_clarification",
                    issues=["could not parse a deterministic candidate fact from text"],
                    reasoning=["parser currently handles a small controlled subset of fact patterns"],
                ).to_dict()
            raw_predicate, arguments, parsed_source = text_parsed
        else:
            raw_predicate, arguments = parsed
            parsed_source = "prolog_literal"

        canonical = self._resolve_canonical(raw_predicate)
        if canonical is None:
            return ProposalCheckResult(
                status="needs_clarification",
                issues=[f"unknown predicate alias '{raw_predicate}'"],
                reasoning=["predicate alias not found in deterministic registry"],
            ).to_dict()

        predicate_meta = self.registry["predicates"][canonical]
        expected_arity = int(predicate_meta.get("arity", 0))
        if len(arguments) != expected_arity:
            return ProposalCheckResult(
                status="needs_clarification",
                issues=[
                    f"arity mismatch for '{canonical}': expected {expected_arity}, got {len(arguments)}"
                ],
                reasoning=["candidate rejected pending argument clarification"],
            ).to_dict()

        if any(not arg for arg in arguments):
            return ProposalCheckResult(
                status="reject",
                issues=["empty argument after normalization"],
                reasoning=["normalized arguments must be non-empty"],
            ).to_dict()

        status = "valid"
        issues: list[str] = []
        reasoning = ["predicate and arity validated against deterministic registry"]
        if needs_speaker_resolution and "<speaker>" in arguments:
            status = "needs_clarification"
            issues.append("speaker identity is unresolved")
            reasoning.append("candidate contains <speaker> and requires explicit grounding before persistence")

        candidate = CandidateFact(
            canonical_predicate=canonical,
            arguments=arguments,
            normalized_fact=self._build_fact_text(canonical, arguments),
            source=parsed_source,
            raw_predicate=raw_predicate,
        )
        return ProposalCheckResult(
            status=status,
            issues=issues,
            candidate=candidate,
            reasoning=reasoning,
        ).to_dict()
