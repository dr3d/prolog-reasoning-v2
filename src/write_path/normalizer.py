#!/usr/bin/env python3
"""Deterministic parsing/normalization for candidate fact proposals."""

from __future__ import annotations

import re
from typing import Optional, Tuple


FIRST_PERSON_ALIASES = {"i", "me", "my", "we", "our", "us"}


def normalize_predicate_name(name: str) -> str:
    normalized = (name or "").strip().lower().replace("-", "_").replace(" ", "_")
    return re.sub(r"[^a-z0-9_]", "", normalized)


def normalize_entity_name(name: str) -> str:
    token = (name or "").strip().strip(".").strip("'").strip('"')
    token = token.lower()
    if token in FIRST_PERSON_ALIASES:
        return "<speaker>"
    token = token.replace("-", "_").replace(" ", "_")
    token = re.sub(r"[^a-z0-9_<>]", "", token)
    return token


def parse_prolog_fact(text: str) -> Optional[Tuple[str, list[str]]]:
    raw = (text or "").strip()
    match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\((.*)\)\.?$", raw)
    if not match:
        return None

    predicate = normalize_predicate_name(match.group(1))
    args_raw = match.group(2).strip()
    if not args_raw:
        return predicate, []

    parts = [part.strip() for part in args_raw.split(",")]
    if any(not part for part in parts):
        return None
    return predicate, [normalize_entity_name(part) for part in parts]


def parse_text_fact(text: str) -> Optional[Tuple[str, list[str], str]]:
    """
    Parse a small deterministic subset of fact-like utterances.

    Returns (predicate_alias, args, source_label) or None.
    """
    raw = (text or "").strip().rstrip(".")
    lower = raw.lower().strip()

    # Strip common tentative lead-ins so deterministic patterns still apply.
    for prefix in ("maybe ", "i think ", "probably ", "possibly "):
        if lower.startswith(prefix):
            lower = lower[len(prefix):].strip()
            break

    # "My mother was Ann" -> parent(ann, <speaker>)
    match = re.match(r"^(my|our)\s+(mother|father|parent)\s+(?:is|was)\s+(.+)$", lower)
    if match:
        subject = normalize_entity_name(match.group(3))
        return "parent", [subject, "<speaker>"], "text:family"

    # "alice is parent of bob" -> parent(alice, bob)
    match = re.match(r"^(.+)\s+is\s+parent\s+of\s+(.+)$", lower)
    if match:
        return "parent", [
            normalize_entity_name(match.group(1)),
            normalize_entity_name(match.group(2)),
        ], "text:family"

    # "john is allergic to peanuts" -> allergic_to(john, peanuts)
    match = re.match(r"^(.+)\s+is\s+allergic\s+to\s+(.+)$", lower)
    if match:
        return "allergic_to", [
            normalize_entity_name(match.group(1)),
            normalize_entity_name(match.group(2)),
        ], "text:clinical"

    return None
