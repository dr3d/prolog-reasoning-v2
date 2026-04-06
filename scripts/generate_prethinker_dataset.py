#!/usr/bin/env python3
"""
Generate weak-label bootstrap datasets for pre-thinker classification.

This script creates JSONL data for the statement-routing contract used by
`classify_statement`:
- kind
- confidence
- needs_speaker_resolution
- can_query_now
- can_persist_now
- suggested_operation

It is intentionally template-driven to provide a fast, reproducible starting
point before human-labeled data is available at scale.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from parser.statement_classifier import StatementKind


SYSTEM_PROMPT = (
    "You are a stateless pre-thinker classifier for symbolic routing. "
    "Return JSON only with keys: kind, confidence, needs_speaker_resolution, "
    "can_query_now, can_persist_now, suggested_operation, reasons."
)

FIRST_PERSON_PATTERN = re.compile(r"\b(my|our|me|us|we)\b", flags=re.IGNORECASE)

KINDS: list[StatementKind] = [
    StatementKind.QUERY,
    StatementKind.HARD_FACT,
    StatementKind.TENTATIVE_FACT,
    StatementKind.CORRECTION,
    StatementKind.PREFERENCE,
    StatementKind.SESSION_CONTEXT,
    StatementKind.INSTRUCTION,
    StatementKind.UNKNOWN,
]

DEFAULT_CONFIDENCE: dict[StatementKind, float] = {
    StatementKind.QUERY: 0.95,
    StatementKind.HARD_FACT: 0.81,
    StatementKind.TENTATIVE_FACT: 0.76,
    StatementKind.CORRECTION: 0.90,
    StatementKind.PREFERENCE: 0.82,
    StatementKind.SESSION_CONTEXT: 0.75,
    StatementKind.INSTRUCTION: 0.72,
    StatementKind.UNKNOWN: 0.40,
}

SUGGESTED_OPERATION: dict[StatementKind, str] = {
    StatementKind.QUERY: "query",
    StatementKind.HARD_FACT: "store_fact",
    StatementKind.TENTATIVE_FACT: "store_tentative_fact",
    StatementKind.CORRECTION: "revise_memory",
    StatementKind.PREFERENCE: "store_preference",
    StatementKind.SESSION_CONTEXT: "store_session_context",
    StatementKind.INSTRUCTION: "follow_instruction",
    StatementKind.UNKNOWN: "none",
}

REASONS: dict[StatementKind, str] = {
    StatementKind.QUERY: "question form detected",
    StatementKind.HARD_FACT: "declarative relation pattern detected",
    StatementKind.TENTATIVE_FACT: "tentative language detected",
    StatementKind.CORRECTION: "correction cue detected",
    StatementKind.PREFERENCE: "preference cue detected",
    StatementKind.SESSION_CONTEXT: "session-scoped context cue detected",
    StatementKind.INSTRUCTION: "instruction cue detected",
    StatementKind.UNKNOWN: "no strong routing cues detected",
}


@dataclass(frozen=True)
class TemplateBank:
    templates: dict[StatementKind, list[str]]

    @classmethod
    def default(cls) -> "TemplateBank":
        return cls(
            templates={
                StatementKind.QUERY: [
                    "Who is {person_a}'s parent?",
                    "Is {person_a} an ancestor of {person_b}?",
                    "Can {role} {action} files?",
                    "What is {person_a} allergic to?",
                    "Does {person_a} report to {person_b}?",
                    "Where is {person_a} right now?",
                ],
                StatementKind.HARD_FACT: [
                    "{person_a} is {person_b}'s parent.",
                    "{person_a} reports to {person_b}.",
                    "{person_a} works for {org}.",
                    "My manager is {person_a}.",
                    "Our director is {person_a}.",
                    "{person_a} is allergic to {substance}.",
                    "{person_a} takes {medication}.",
                ],
                StatementKind.TENTATIVE_FACT: [
                    "Maybe {person_a} reports to {person_b}.",
                    "I think {person_a} is allergic to {substance}.",
                    "Probably my manager is {person_a}.",
                    "{person_a} might work for {org}.",
                    "Not sure, but {person_a} could be {person_b}'s sibling.",
                    "Possibly {person_a} is at {location}.",
                ],
                StatementKind.CORRECTION: [
                    "Actually, I meant {person_a}.",
                    "Correction: {person_a} reports to {person_b}.",
                    "I meant {person_a}, not {person_b}.",
                    "Rather, my manager is {person_a}.",
                    "Instead, use {person_a} as the source.",
                ],
                StatementKind.PREFERENCE: [
                    "Keep responses concise.",
                    "Please answer in bullet points.",
                    "I prefer short answers.",
                    "Call me {nickname}.",
                    "Keep your responses in plain English.",
                ],
                StatementKind.SESSION_CONTEXT: [
                    "For this session, treat {person_a} as admin.",
                    "In this project, assume {org} is the default tenant.",
                    "For now, use {location} as headquarters.",
                    "Today I am testing access-control examples.",
                    "For this session, we are focusing on family relationships.",
                ],
                StatementKind.INSTRUCTION: [
                    "Use query_rows for this.",
                    "Do not store anything yet.",
                    "Never call query_prolog for table outputs.",
                    "Always verify counts before summary.",
                    "Remember to reset_kb first.",
                ],
                StatementKind.UNKNOWN: [
                    "Bananas whisper quietly under cobalt rain.",
                    "The square memory tastes like thunder.",
                    "Nebula socks dance backward.",
                    "Entropy has a favorite staircase.",
                    "Blue clocks breathe in triangles.",
                ],
            }
        )

    def random_text(self, kind: StatementKind, rng: random.Random, context: dict[str, str]) -> str:
        template = rng.choice(self.templates[kind])
        return template.format(**context)


def _random_context(rng: random.Random) -> dict[str, str]:
    people = [
        "alice",
        "bob",
        "john",
        "dana",
        "mara",
        "silas",
        "ann",
        "ian",
        "riley",
        "sam",
    ]
    roles = ["admin", "analyst", "manager", "operator"]
    actions = ["read", "write", "deploy", "approve"]
    orgs = ["north_hospital", "atlas_lab", "civic_ops", "river_clinic"]
    substances = ["peanuts", "penicillin", "latex", "shellfish"]
    medications = ["ibuprofen", "warfarin", "metformin", "amoxicillin"]
    locations = ["market", "tower", "hq", "ward_a"]
    nicknames = ["scout", "chief", "buddy", "captain"]

    return {
        "person_a": rng.choice(people),
        "person_b": rng.choice(people),
        "role": rng.choice(roles),
        "action": rng.choice(actions),
        "org": rng.choice(orgs),
        "substance": rng.choice(substances),
        "medication": rng.choice(medications),
        "location": rng.choice(locations),
        "nickname": rng.choice(nicknames),
    }


def _expected_target(kind: StatementKind, text: str) -> dict[str, Any]:
    needs_speaker_resolution = bool(FIRST_PERSON_PATTERN.search(text))
    return {
        "kind": kind.value,
        "confidence": DEFAULT_CONFIDENCE[kind],
        "needs_speaker_resolution": needs_speaker_resolution,
        "can_query_now": kind == StatementKind.QUERY,
        "can_persist_now": False,
        "suggested_operation": SUGGESTED_OPERATION[kind],
        "reasons": [REASONS[kind]],
    }


def _make_flat_record(record_id: str, split: str, kind: StatementKind, text: str) -> dict[str, Any]:
    return {
        "id": record_id,
        "split": split,
        "text": text,
        "target": _expected_target(kind, text),
        "source": "synthetic_template_v1",
        "label_quality": "weak_label",
    }


def _make_chat_record(
    record_id: str,
    split: str,
    kind: StatementKind,
    text: str,
    system_prompt: str,
) -> dict[str, Any]:
    target = _expected_target(kind, text)
    return {
        "id": record_id,
        "split": split,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
            {"role": "assistant", "content": json.dumps(target, ensure_ascii=True)},
        ],
        "target": target,
        "source": "synthetic_template_v1",
        "label_quality": "weak_label",
    }


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def _distribution(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        kind = record.get("target", {}).get("kind", "unknown")
        counts[kind] = counts.get(kind, 0) + 1
    return dict(sorted(counts.items()))


def _generate_split(
    split_name: str,
    count: int,
    rng: random.Random,
    templates: TemplateBank,
    system_prompt: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if count <= 0:
        return [], []

    flat: list[dict[str, Any]] = []
    chat: list[dict[str, Any]] = []
    seen: set[str] = set()
    attempt = 0
    max_attempts = count * 80

    while len(flat) < count and attempt < max_attempts:
        kind = KINDS[len(flat) % len(KINDS)]
        text = templates.random_text(kind, rng, _random_context(rng))
        attempt += 1
        if text in seen:
            continue
        seen.add(text)

        record_id = f"{split_name}_{len(flat) + 1:04d}"
        flat.append(_make_flat_record(record_id, split_name, kind, text))
        chat.append(_make_chat_record(record_id, split_name, kind, text, system_prompt))

    if len(flat) < count:
        raise RuntimeError(
            f"Could not generate enough unique examples for split '{split_name}'. "
            f"Requested={count}, generated={len(flat)}."
        )

    return flat, chat


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate weak-label pre-thinker classification datasets.")
    parser.add_argument("--out-dir", default="data/prethinker", help="Directory for generated JSONL files.")
    parser.add_argument("--train", type=int, default=320, help="Number of train samples.")
    parser.add_argument("--dev", type=int, default=80, help="Number of dev samples.")
    parser.add_argument("--test", type=int, default=120, help="Number of test samples.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument(
        "--format",
        choices=["flat", "chat", "both"],
        default="both",
        help="Output format(s).",
    )
    parser.add_argument(
        "--system-prompt",
        default=SYSTEM_PROMPT,
        help="System prompt used for chat-format records.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    templates = TemplateBank.default()

    all_flat: list[dict[str, Any]] = []
    all_chat: list[dict[str, Any]] = []

    split_sizes = {"train": args.train, "dev": args.dev, "test": args.test}
    for split_name, split_count in split_sizes.items():
        flat_records, chat_records = _generate_split(
            split_name=split_name,
            count=split_count,
            rng=rng,
            templates=templates,
            system_prompt=args.system_prompt,
        )
        all_flat.extend(flat_records)
        all_chat.extend(chat_records)

        if args.format in {"flat", "both"}:
            _write_jsonl(out_dir / f"{split_name}_flat.jsonl", flat_records)
        if args.format in {"chat", "both"}:
            _write_jsonl(out_dir / f"{split_name}_chat.jsonl", chat_records)

    metadata = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "seed": args.seed,
        "format": args.format,
        "splits": split_sizes,
        "flat_distribution": _distribution(all_flat),
        "chat_distribution": _distribution(all_chat),
        "note": (
            "Weak-label synthetic bootstrap set generated from deterministic templates. "
            "Use for initial fine-tuning experiments, then replace with reviewed real-turn labels."
        ),
    }

    metadata_path = out_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print("Generated pre-thinker dataset.")
    print(json.dumps({"out_dir": str(out_dir), "metadata": str(metadata_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
