#!/usr/bin/env python3
"""
Bootstrap weak-label pre-thinker datasets from captured transcript JSON files.

Input format: transcript JSON files like docs/examples/*-session.json with:
- captured_at
- model
- integration
- steps: [{ step, prompt, ... }, ...]

Output:
- flat JSONL (text + target)
- chat JSONL (messages + target)
- metadata JSON summary
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from parser.statement_classifier import StatementClassifier


SYSTEM_PROMPT = (
    "You are a stateless pre-thinker classifier for symbolic routing. "
    "Return JSON only with keys: kind, confidence, needs_speaker_resolution, "
    "can_query_now, can_persist_now, suggested_operation, reasons."
)

LINE_PREFIX_RE = re.compile(r"^\s*(?:[-*]\s+|\d+[\)\.:]\s*)")


@dataclass
class Candidate:
    text: str
    source_file: str
    step: str
    mode: str


def _normalize_text(text: str) -> str:
    text = text.strip()
    text = LINE_PREFIX_RE.sub("", text).strip()
    return re.sub(r"\s+", " ", text)


def _looks_like_fact_blob(text: str) -> bool:
    # Heuristic: long blocks packed with predicate(...) lines are not good
    # natural utterance samples for statement routing.
    if text.count(").") >= 8:
        return True
    if len(text) > 700 and text.count("\n") > 10:
        return True
    return False


def _split_prompt(prompt: str, min_len: int, max_len: int) -> list[str]:
    if not prompt.strip():
        return []

    candidates: list[str] = []

    # Keep full prompt if moderate size and not a fact blob.
    if min_len <= len(prompt) <= max_len and not _looks_like_fact_blob(prompt):
        candidates.append(_normalize_text(prompt))

    # Also split by lines and keep compact intent lines.
    for raw_line in prompt.splitlines():
        line = _normalize_text(raw_line)
        if not line:
            continue
        if len(line) < min_len or len(line) > max_len:
            continue
        if _looks_like_fact_blob(line):
            continue
        candidates.append(line)

    deduped: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        if item and item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _read_transcript(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _collect_candidates(
    transcript_paths: list[Path],
    min_len: int,
    max_len: int,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen_global: set[str] = set()

    for transcript_path in transcript_paths:
        data = _read_transcript(transcript_path)
        steps = data.get("steps", [])
        for step in steps:
            step_name = str(step.get("step", "unknown_step"))
            prompt = str(step.get("prompt", ""))
            for text in _split_prompt(prompt, min_len=min_len, max_len=max_len):
                if text in seen_global:
                    continue
                seen_global.add(text)
                candidates.append(
                    Candidate(
                        text=text,
                        source_file=str(transcript_path.as_posix()),
                        step=step_name,
                        mode="prompt",
                    )
                )
    return candidates


def _flat_record(index: int, split: str, candidate: Candidate, target: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"transcript_{split}_{index:04d}",
        "split": split,
        "text": candidate.text,
        "target": target,
        "source": "transcript_bootstrap_v1",
        "label_quality": "weak_label_rule_baseline",
        "metadata": {
            "source_file": candidate.source_file,
            "step": candidate.step,
            "mode": candidate.mode,
        },
    }


def _chat_record(index: int, split: str, candidate: Candidate, target: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"transcript_{split}_{index:04d}",
        "split": split,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": candidate.text},
            {"role": "assistant", "content": json.dumps(target, ensure_ascii=True)},
        ],
        "target": target,
        "source": "transcript_bootstrap_v1",
        "label_quality": "weak_label_rule_baseline",
        "metadata": {
            "source_file": candidate.source_file,
            "step": candidate.step,
            "mode": candidate.mode,
        },
    }


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def _split_records(
    candidates: list[Candidate],
    train_ratio: float,
    dev_ratio: float,
) -> dict[str, list[Candidate]]:
    total = len(candidates)
    train_count = int(total * train_ratio)
    dev_count = int(total * dev_ratio)
    train = candidates[:train_count]
    dev = candidates[train_count : train_count + dev_count]
    test = candidates[train_count + dev_count :]
    return {"train": train, "dev": dev, "test": test}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap pre-thinker labels from transcript prompts.")
    parser.add_argument(
        "--inputs",
        nargs="*",
        default=[
            "docs/examples/hospital-cpm-playbook-session.json",
            "docs/examples/fantasy-overlord-session.json",
        ],
        help="Transcript JSON files to ingest.",
    )
    parser.add_argument("--out-dir", default="data/prethinker", help="Output directory.")
    parser.add_argument("--prefix", default="transcript_bootstrap", help="Output filename prefix.")
    parser.add_argument("--min-len", type=int, default=14, help="Minimum candidate text length.")
    parser.add_argument("--max-len", type=int, default=280, help="Maximum candidate text length.")
    parser.add_argument("--train-ratio", type=float, default=0.7, help="Train split ratio.")
    parser.add_argument("--dev-ratio", type=float, default=0.15, help="Dev split ratio.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    transcript_paths = [Path(item) for item in args.inputs if Path(item).exists()]
    if not transcript_paths:
        raise RuntimeError("No transcript input files found.")

    classifier = StatementClassifier()
    candidates = _collect_candidates(
        transcript_paths=transcript_paths,
        min_len=args.min_len,
        max_len=args.max_len,
    )
    if not candidates:
        raise RuntimeError("No usable utterance candidates extracted from transcript inputs.")

    split_candidates = _split_records(
        candidates=candidates,
        train_ratio=args.train_ratio,
        dev_ratio=args.dev_ratio,
    )

    out_dir = Path(args.out_dir)
    summary_counts: dict[str, dict[str, int]] = {}

    for split_name, rows in split_candidates.items():
        flat_records: list[dict[str, Any]] = []
        chat_records: list[dict[str, Any]] = []
        kind_counts: dict[str, int] = {}

        for index, candidate in enumerate(rows, start=1):
            target = classifier.classify(candidate.text).to_dict()
            kind = target.get("kind", "unknown")
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
            flat_records.append(_flat_record(index, split_name, candidate, target))
            chat_records.append(_chat_record(index, split_name, candidate, target))

        _write_jsonl(out_dir / f"{args.prefix}_{split_name}_flat.jsonl", flat_records)
        _write_jsonl(out_dir / f"{args.prefix}_{split_name}_chat.jsonl", chat_records)
        summary_counts[split_name] = dict(sorted(kind_counts.items()))

    metadata = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_files": [str(path.as_posix()) for path in transcript_paths],
        "total_candidates": len(candidates),
        "split_sizes": {k: len(v) for k, v in split_candidates.items()},
        "kind_counts_by_split": summary_counts,
        "note": (
            "Labels are generated by the deterministic rule classifier as weak labels. "
            "Review and correct before using as gold data."
        ),
    }
    metadata_path = out_dir / f"{args.prefix}_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print("Transcript bootstrap dataset written.")
    print(
        json.dumps(
            {
                "out_dir": str(out_dir),
                "metadata": str(metadata_path),
                "total_candidates": len(candidates),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
