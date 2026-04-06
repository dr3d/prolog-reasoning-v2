#!/usr/bin/env python3
"""
Evaluate the deterministic StatementClassifier against a labeled JSONL dataset.

Accepted record shapes:
1) Flat records with:
   - text
   - target: { kind, suggested_operation, needs_speaker_resolution, ... }

2) Chat records with:
   - messages (includes user text)
   - target
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from parser.statement_classifier import StatementClassifier


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _extract_user_text(record: dict[str, Any]) -> str:
    text = record.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()

    messages = record.get("messages", [])
    if isinstance(messages, list):
        for message in messages:
            if message.get("role") == "user" and isinstance(message.get("content"), str):
                content = message["content"].strip()
                if content:
                    return content
    raise ValueError("Could not extract user text from record.")


def _extract_target(record: dict[str, Any]) -> dict[str, Any]:
    target = record.get("target")
    if isinstance(target, dict) and target.get("kind"):
        return target
    raise ValueError("Record is missing target classification object.")


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _f1(precision: float, recall: float) -> float:
    return _safe_div(2 * precision * recall, precision + recall)


def _summarize_per_kind(true_labels: list[str], pred_labels: list[str]) -> dict[str, dict[str, float]]:
    labels = sorted(set(true_labels) | set(pred_labels))
    summary: dict[str, dict[str, float]] = {}

    for label in labels:
        tp = sum(1 for t, p in zip(true_labels, pred_labels) if t == label and p == label)
        fp = sum(1 for t, p in zip(true_labels, pred_labels) if t != label and p == label)
        fn = sum(1 for t, p in zip(true_labels, pred_labels) if t == label and p != label)
        support = sum(1 for t in true_labels if t == label)

        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        summary[label] = {
            "support": support,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(_f1(precision, recall), 4),
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }

    return summary


def _confusion_matrix(true_labels: list[str], pred_labels: list[str]) -> dict[str, dict[str, int]]:
    labels = sorted(set(true_labels) | set(pred_labels))
    matrix: dict[str, dict[str, int]] = {
        label: {other: 0 for other in labels} for label in labels
    }
    for truth, pred in zip(true_labels, pred_labels):
        matrix[truth][pred] += 1
    return matrix


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate StatementClassifier on labeled JSONL records.")
    parser.add_argument(
        "--input",
        default="data/prethinker/test_flat.jsonl",
        help="Path to JSONL dataset.",
    )
    parser.add_argument(
        "--report",
        default="data/prethinker/rule_classifier_eval.json",
        help="Path to write JSON report.",
    )
    parser.add_argument(
        "--predictions-jsonl",
        default="",
        help="Optional path to write per-example predictions.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    report_path = Path(args.report)
    predictions_path = Path(args.predictions_jsonl) if args.predictions_jsonl else None

    records = _read_jsonl(input_path)
    if not records:
        raise RuntimeError(f"No records found in {input_path}")

    classifier = StatementClassifier()

    true_kind: list[str] = []
    pred_kind: list[str] = []
    op_match = 0
    speaker_match = 0
    prediction_rows: list[dict[str, Any]] = []

    for index, record in enumerate(records, start=1):
        text = _extract_user_text(record)
        target = _extract_target(record)
        pred = classifier.classify(text).to_dict()

        true_kind.append(target["kind"])
        pred_kind.append(pred["kind"])

        if target.get("suggested_operation") == pred.get("suggested_operation"):
            op_match += 1
        if bool(target.get("needs_speaker_resolution")) == bool(pred.get("needs_speaker_resolution")):
            speaker_match += 1

        prediction_rows.append(
            {
                "index": index,
                "id": record.get("id", f"row_{index:04d}"),
                "text": text,
                "target": target,
                "prediction": pred,
                "kind_match": target["kind"] == pred["kind"],
                "operation_match": target.get("suggested_operation") == pred.get("suggested_operation"),
            }
        )

    total = len(records)
    kind_accuracy = _safe_div(sum(1 for t, p in zip(true_kind, pred_kind) if t == p), total)
    op_accuracy = _safe_div(op_match, total)
    speaker_accuracy = _safe_div(speaker_match, total)

    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "input_path": str(input_path),
        "total_examples": total,
        "overall": {
            "kind_accuracy": round(kind_accuracy, 4),
            "suggested_operation_accuracy": round(op_accuracy, 4),
            "needs_speaker_resolution_accuracy": round(speaker_accuracy, 4),
        },
        "per_kind": _summarize_per_kind(true_kind, pred_kind),
        "confusion_matrix": _confusion_matrix(true_kind, pred_kind),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if predictions_path:
        predictions_path.parent.mkdir(parents=True, exist_ok=True)
        with predictions_path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in prediction_rows:
                handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    print("Evaluation complete.")
    print(json.dumps({"report": str(report_path), "kind_accuracy": round(kind_accuracy, 4)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
