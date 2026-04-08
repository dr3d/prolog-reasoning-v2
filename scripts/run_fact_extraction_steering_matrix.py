#!/usr/bin/env python3
"""
Run a local fact-extraction steering matrix against LM Studio-hosted models.

This script evaluates how well models can be steered to:
- extract canonical predicate facts from natural prose
- attach uncertainty and clarification markers for risky claims
- avoid inventing unsupported facts
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:1234"
DEFAULT_OUT_ROOT = ".tmp_fact_extraction_matrix"
DEFAULT_ENV_FILE = ".env.local"
DEFAULT_DATASET = "data/fact_extraction/buried_facts_corpus_v1.json"
DEFAULT_PREDICATE_REGISTRY = "data/predicate_registry.json"
DEFAULT_LEDGER = "docs/research/fact-extraction-steering-matrix.md"
DEFAULT_MODELS = [
    "qwen3.5-4b",
    "qwen/qwen3.5-9b",
    "qwen3.5-27b@q4_k_m",
]
DEFAULT_PROMPT_SETS = ["baseline_v1", "strict_v1"]
PROMPT_SET_VERSION = "2026-04-07-v1"


BASELINE_SYSTEM_PROMPT = """You extract symbolic facts from text.
Return JSON only.
Use evidence from the passage.
"""


STRICT_SYSTEM_PROMPT = """You are a conservative symbolic fact extractor.
Output JSON only and never output markdown.
Use only predicates provided by the user.
If a claim is hedged, rumored, unresolved, or speaker-grounding is missing:
- set certainty to "uncertain"
- set needs_clarification to true
- provide a short clarification_reason
Only extract claims directly supported by the passage.
"""


def _slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", text).strip("_").lower()


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


def _post_json(url: str, payload: dict[str, Any], api_key: str | None) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url=url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    if api_key:
        request.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        if error.code == 401:
            raise RuntimeError(
                "HTTP 401 from LM Studio API. API auth appears enabled.\n"
                "Set LM Studio token in LMSTUDIO_API_KEY or pass --api-key."
            ) from error
        raise RuntimeError(f"HTTP {error.code}: {raw}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Connection error: {error}") from error


def _extract_message_content(response: dict[str, Any]) -> str:
    # LM Studio /api/v1/chat shape
    output_items = response.get("output")
    if isinstance(output_items, list):
        messages = [
            item.get("content")
            for item in output_items
            if isinstance(item, dict) and item.get("type") == "message"
        ]
        for content in reversed(messages):
            if isinstance(content, str) and content.strip():
                return content

    # OpenAI-style /v1/chat/completions shape
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(item, str):
                parts.append(item)
        joined = "\n".join(parts).strip()
        if joined:
            return joined
    reasoning = message.get("reasoning_content")
    if isinstance(reasoning, str):
        return reasoning
    return ""


def _extract_json_blob(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if not stripped:
        return None

    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        candidate = stripped[start : end + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return None
    return None


def _normalize_token(value: Any) -> str:
    if value is None:
        return ""
    token = str(value).strip().lower()
    token = token.replace("-", "_").replace(" ", "_")
    token = re.sub(r"[^a-z0-9_<>\[\]:./]+", "_", token)
    token = re.sub(r"_+", "_", token).strip("_")
    return token


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def _to_confidence(value: Any) -> float:
    try:
        conf = float(value)
    except (TypeError, ValueError):
        return 0.0
    if conf < 0.0:
        return 0.0
    if conf > 1.0:
        return 1.0
    return conf


def _normalize_fact(raw: dict[str, Any]) -> dict[str, Any] | None:
    predicate = _normalize_token(raw.get("predicate"))
    arguments_raw = raw.get("arguments")

    if not predicate:
        return None

    arguments: list[str] = []
    if isinstance(arguments_raw, list):
        arguments = [_normalize_token(item) for item in arguments_raw]
    elif isinstance(arguments_raw, str):
        arguments = [_normalize_token(arguments_raw)]
    elif "subject" in raw or "object" in raw:
        subj = _normalize_token(raw.get("subject"))
        obj = _normalize_token(raw.get("object"))
        arguments = [subj] + ([obj] if obj else [])

    arguments = [arg for arg in arguments if arg]
    certainty = str(raw.get("certainty", "")).strip().lower()
    needs_clarification = _to_bool(raw.get("needs_clarification"))
    if certainty not in {"certain", "uncertain"}:
        certainty = "uncertain" if needs_clarification else "certain"

    return {
        "predicate": predicate,
        "arguments": arguments,
        "certainty": certainty,
        "needs_clarification": needs_clarification,
        "clarification_reason": str(raw.get("clarification_reason", "")).strip(),
        "confidence": _to_confidence(raw.get("confidence", 0.0)),
        "evidence_quote": str(
            raw.get("evidence_quote", raw.get("evidence_text", raw.get("evidence", "")))
        ).strip(),
        "raw_relation_text": str(raw.get("raw_relation_text", "")).strip(),
    }


def _fact_key(fact: dict[str, Any]) -> tuple[str, ...]:
    return tuple([fact["predicate"]] + list(fact["arguments"]))


def _validate_fact_shape(
    fact: dict[str, Any],
    arity_by_predicate: dict[str, int],
) -> tuple[bool, str]:
    predicate = fact["predicate"]
    args = fact["arguments"]
    if predicate not in arity_by_predicate:
        return False, "invalid_predicate"
    if len(args) != arity_by_predicate[predicate]:
        return False, "invalid_arity"
    return True, ""


def _safe_div(n: float, d: float) -> float:
    return (n / d) if d else 0.0


def _build_prompt(
    prompt_set: str,
    doc_id: str,
    passage: str,
    predicate_registry: dict[str, Any],
) -> tuple[str, str]:
    if prompt_set not in {"baseline_v1", "strict_v1"}:
        raise ValueError(f"Unsupported prompt set: {prompt_set}")

    system_prompt = BASELINE_SYSTEM_PROMPT if prompt_set == "baseline_v1" else STRICT_SYSTEM_PROMPT

    preds = predicate_registry.get("predicates", {})
    lines: list[str] = []
    for name, spec in preds.items():
        if not isinstance(spec, dict):
            continue
        arity = spec.get("arity", "?")
        aliases = spec.get("aliases", [])
        alias_str = ", ".join([str(a) for a in aliases]) if isinstance(aliases, list) else ""
        lines.append(f"- {name} / arity {arity} / aliases: {alias_str}")

    guardrail_block = ""
    if prompt_set == "strict_v1":
        guardrail_block = (
            "Strict guardrails:\n"
            "1) Use only listed predicates.\n"
            "2) Normalize entities to lowercase snake_case.\n"
            "3) For unresolved speaker references, use placeholder <speaker>.\n"
            "4) For uncertain or hedged claims, set certainty=uncertain and needs_clarification=true.\n"
            "5) Do not output instructions/preferences as facts.\n"
            "6) Evidence quote must be a direct substring from the passage.\n"
        )

    user_prompt = (
        f"Document ID: {doc_id}\n\n"
        "Allowed predicates:\n"
        + "\n".join(lines)
        + "\n\n"
        + guardrail_block
        + (
            "Return JSON object with this exact shape:\n"
            "{\n"
            "  \"document_id\": \"...\",\n"
            "  \"facts\": [\n"
            "    {\n"
            "      \"predicate\": \"...\",\n"
            "      \"arguments\": [\"...\"],\n"
            "      \"certainty\": \"certain|uncertain\",\n"
            "      \"confidence\": 0.0,\n"
            "      \"needs_clarification\": false,\n"
            "      \"clarification_reason\": \"\",\n"
            "      \"evidence_quote\": \"\",\n"
            "      \"raw_relation_text\": \"\"\n"
            "    }\n"
            "  ],\n"
            "  \"ignored_claims\": [\"...\"]\n"
            "}\n\n"
            "Passage:\n"
            f"{passage}\n"
        )
    )
    return system_prompt, user_prompt


def _score_document(
    document: dict[str, Any],
    predicted_facts: list[dict[str, Any]],
    arity_by_predicate: dict[str, int],
) -> dict[str, Any]:
    expected_raw = document.get("expected_facts", [])
    expected_facts = [
        fact
        for fact in (
            _normalize_fact(item) for item in expected_raw if isinstance(item, dict)
        )
        if fact is not None
    ]

    valid_predicted: list[dict[str, Any]] = []
    invalid_predicate = 0
    invalid_arity = 0
    evidence_supported = 0

    text_lower = str(document.get("text", "")).lower()
    for fact in predicted_facts:
        ok, reason = _validate_fact_shape(fact, arity_by_predicate)
        if not ok:
            if reason == "invalid_predicate":
                invalid_predicate += 1
            elif reason == "invalid_arity":
                invalid_arity += 1
            continue
        valid_predicted.append(fact)
        evidence = fact.get("evidence_quote", "").strip()
        if evidence and evidence.lower() in text_lower:
            evidence_supported += 1

    expected_counter = collections.Counter([_fact_key(fact) for fact in expected_facts])
    predicted_counter = collections.Counter([_fact_key(fact) for fact in valid_predicted])

    tp = 0
    for key, exp_count in expected_counter.items():
        tp += min(exp_count, predicted_counter.get(key, 0))
    fp = sum(predicted_counter.values()) - tp
    fn = sum(expected_counter.values()) - tp

    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)

    expected_by_key = {_fact_key(f): f for f in expected_facts}
    predicted_by_key = {_fact_key(f): f for f in valid_predicted}
    matched_keys = set(expected_by_key).intersection(predicted_by_key)

    uncertainty_matches = 0
    certainty_matches = 0
    expected_uncertain_total = 0
    uncertain_recall_hits = 0
    overconfident_errors = 0
    unnecessary_clarification = 0

    for key, expected in expected_by_key.items():
        if expected.get("needs_clarification"):
            expected_uncertain_total += 1
        predicted = predicted_by_key.get(key)
        if not predicted:
            continue
        if predicted.get("needs_clarification") == expected.get("needs_clarification"):
            uncertainty_matches += 1
        if predicted.get("certainty") == expected.get("certainty"):
            certainty_matches += 1
        if expected.get("needs_clarification") and predicted.get("needs_clarification"):
            uncertain_recall_hits += 1
        if expected.get("needs_clarification") and not predicted.get("needs_clarification"):
            overconfident_errors += 1
        if (not expected.get("needs_clarification")) and predicted.get("needs_clarification"):
            unnecessary_clarification += 1

    uncertainty_accuracy = _safe_div(uncertainty_matches, len(matched_keys))
    certainty_accuracy = _safe_div(certainty_matches, len(matched_keys))
    uncertain_recall = _safe_div(uncertain_recall_hits, expected_uncertain_total)
    evidence_support_rate = _safe_div(evidence_supported, len(valid_predicted))

    return {
        "document_id": document.get("id"),
        "expected_count": len(expected_facts),
        "predicted_count": len(valid_predicted),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "matched_keys": len(matched_keys),
        "uncertainty_accuracy": uncertainty_accuracy,
        "certainty_accuracy": certainty_accuracy,
        "uncertain_recall": uncertain_recall,
        "evidence_support_rate": evidence_support_rate,
        "invalid_predicate": invalid_predicate,
        "invalid_arity": invalid_arity,
        "overconfident_errors": overconfident_errors,
        "unnecessary_clarification": unnecessary_clarification,
    }


def _aggregate_scores(doc_scores: list[dict[str, Any]], parse_failures: int) -> dict[str, Any]:
    tp = sum(int(score.get("tp", 0)) for score in doc_scores)
    fp = sum(int(score.get("fp", 0)) for score in doc_scores)
    fn = sum(int(score.get("fn", 0)) for score in doc_scores)
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)

    uncertainty_accuracy = _safe_div(
        sum(float(score.get("uncertainty_accuracy", 0.0)) for score in doc_scores),
        len(doc_scores),
    )
    uncertain_recall = _safe_div(
        sum(float(score.get("uncertain_recall", 0.0)) for score in doc_scores),
        len(doc_scores),
    )
    evidence_support_rate = _safe_div(
        sum(float(score.get("evidence_support_rate", 0.0)) for score in doc_scores),
        len(doc_scores),
    )
    invalid_predicate = sum(int(score.get("invalid_predicate", 0)) for score in doc_scores)
    invalid_arity = sum(int(score.get("invalid_arity", 0)) for score in doc_scores)
    overconfident_errors = sum(int(score.get("overconfident_errors", 0)) for score in doc_scores)
    unnecessary_clarification = sum(
        int(score.get("unnecessary_clarification", 0)) for score in doc_scores
    )

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "uncertainty_accuracy": uncertainty_accuracy,
        "uncertain_recall": uncertain_recall,
        "evidence_support_rate": evidence_support_rate,
        "invalid_predicate": invalid_predicate,
        "invalid_arity": invalid_arity,
        "overconfident_errors": overconfident_errors,
        "unnecessary_clarification": unnecessary_clarification,
        "parse_failures": parse_failures,
        "docs_scored": len(doc_scores),
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def _format_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _ensure_ledger(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "# Fact Extraction Steering Matrix\n\n"
            "Tracks local LM Studio runs for buried-fact extraction quality.\n\n"
            "Each run compares models and prompt sets on one synthetic corpus.\n"
        ),
        encoding="utf-8",
    )


def _append_ledger(path: Path, run_label: str, rows: list[dict[str, Any]]) -> None:
    _ensure_ledger(path)
    lines: list[str] = []
    lines.append("")
    lines.append(f"## Run {run_label}")
    lines.append("")
    lines.append(
        "| model | prompt set | docs | precision | recall | f1 | uncertainty acc | uncertain recall | evidence support | invalid predicate | invalid arity | parse failures | overconfident | notes |"
    )
    lines.append(
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"
    )
    for row in rows:
        summary = row["summary"]
        note = "ok"
        if int(summary.get("parse_failures", 0)) > 0:
            note = "parse_failures_present"
        lines.append(
            "| "
            + " | ".join(
                [
                    row["model"],
                    row["prompt_set"],
                    str(summary.get("docs_scored")),
                    _format_pct(float(summary.get("precision", 0.0))),
                    _format_pct(float(summary.get("recall", 0.0))),
                    _format_pct(float(summary.get("f1", 0.0))),
                    _format_pct(float(summary.get("uncertainty_accuracy", 0.0))),
                    _format_pct(float(summary.get("uncertain_recall", 0.0))),
                    _format_pct(float(summary.get("evidence_support_rate", 0.0))),
                    str(summary.get("invalid_predicate")),
                    str(summary.get("invalid_arity")),
                    str(summary.get("parse_failures")),
                    str(summary.get("overconfident_errors")),
                    note,
                ]
            )
            + " |"
        )
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def _load_dataset(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Dataset must be a JSON object.")
    docs = payload.get("documents")
    if not isinstance(docs, list) or not docs:
        raise ValueError("Dataset 'documents' must be a non-empty list.")
    return payload


def _load_predicate_registry(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("predicates"), dict):
        raise ValueError("Predicate registry missing 'predicates' map.")
    return payload


def _arity_map(registry: dict[str, Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    predicates = registry.get("predicates", {})
    for name, spec in predicates.items():
        if not isinstance(name, str) or not isinstance(spec, dict):
            continue
        arity = spec.get("arity")
        if isinstance(arity, int):
            result[_normalize_token(name)] = arity
    return result


def _call_model(
    *,
    base_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    api_key: str | None,
    temperature: float,
    max_tokens: int,
    context_length: int,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "input": f"{system_prompt}\n\n{user_prompt}",
        "temperature": temperature,
        "context_length": context_length,
    }
    url = base_url.rstrip("/") + "/api/v1/chat"
    return _post_json(url, payload, api_key)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run buried-fact extraction steering experiments across local LM Studio models."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="LM Studio API base URL")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS, help="Model IDs to evaluate")
    parser.add_argument(
        "--prompt-sets",
        nargs="+",
        default=DEFAULT_PROMPT_SETS,
        help="Prompt strategy names (baseline_v1 strict_v1)",
    )
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Dataset JSON path")
    parser.add_argument(
        "--predicate-registry",
        default=DEFAULT_PREDICATE_REGISTRY,
        help="Predicate registry JSON path",
    )
    parser.add_argument("--out-root", default=DEFAULT_OUT_ROOT, help="Output root for run artifacts")
    parser.add_argument("--ledger", default=DEFAULT_LEDGER, help="Ledger markdown path")
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE, help="Optional .env file")
    parser.add_argument("--api-key", default="", help="Optional explicit LM Studio API key")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature")
    parser.add_argument("--max-tokens", type=int, default=1200, help="Completion token limit")
    parser.add_argument(
        "--context-length",
        type=int,
        default=4000,
        help="Requested LM Studio context length per prompt.",
    )
    parser.add_argument("--max-docs", type=int, default=0, help="Limit docs per run (0 = all)")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and emit prompts only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _load_env_file(Path(args.env_file))

    api_key = args.api_key.strip() or os.environ.get("LMSTUDIO_API_KEY", "").strip() or None
    dataset_path = Path(args.dataset)
    registry_path = Path(args.predicate_registry)
    out_root = Path(args.out_root)
    ledger_path = Path(args.ledger)

    dataset = _load_dataset(dataset_path)
    registry = _load_predicate_registry(registry_path)
    arity_by_predicate = _arity_map(registry)

    docs = dataset.get("documents", [])
    if args.max_docs and args.max_docs > 0:
        docs = docs[: args.max_docs]

    now_utc = dt.datetime.now(dt.timezone.utc)
    run_label = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    run_slug = now_utc.strftime("%Y%m%d-%H%M%S")
    run_dir = out_root / f"fact_extract_{run_slug}"
    run_dir.mkdir(parents=True, exist_ok=True)

    matrix_rows: list[dict[str, Any]] = []
    for model in args.models:
        for prompt_set in args.prompt_sets:
            doc_records: list[dict[str, Any]] = []
            parse_failures = 0

            for document in docs:
                doc_id = str(document.get("id", "unknown_doc"))
                text = str(document.get("text", ""))
                system_prompt, user_prompt = _build_prompt(prompt_set, doc_id, text, registry)

                if args.dry_run:
                    doc_records.append(
                        {
                            "document_id": doc_id,
                            "prompt_set": prompt_set,
                            "model": model,
                            "request": {"system": system_prompt, "user": user_prompt},
                            "response_text": "",
                            "parse_ok": False,
                            "predicted_facts": [],
                            "doc_score": _score_document(document, [], arity_by_predicate),
                        }
                    )
                    parse_failures += 1
                    continue

                response = _call_model(
                    base_url=args.base_url,
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    api_key=api_key,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                    context_length=args.context_length,
                )

                response_text = _extract_message_content(response)
                payload = _extract_json_blob(response_text)
                facts_raw = payload.get("facts", []) if isinstance(payload, dict) else []
                predicted_facts = [
                    fact
                    for fact in (
                        _normalize_fact(item) for item in facts_raw if isinstance(item, dict)
                    )
                    if fact is not None
                ]
                parse_ok = isinstance(payload, dict) and isinstance(payload.get("facts"), list)
                if not parse_ok:
                    parse_failures += 1

                doc_score = _score_document(document, predicted_facts, arity_by_predicate)
                doc_records.append(
                    {
                        "document_id": doc_id,
                        "prompt_set": prompt_set,
                        "model": model,
                        "response_text": response_text,
                        "raw_response": response,
                        "parsed_payload": payload,
                        "parse_ok": parse_ok,
                        "predicted_facts": predicted_facts,
                        "doc_score": doc_score,
                    }
                )

            doc_scores = [record["doc_score"] for record in doc_records]
            summary = _aggregate_scores(doc_scores, parse_failures)

            run_payload = {
                "captured_at": run_label,
                "run_slug": run_slug,
                "prompt_set_version": PROMPT_SET_VERSION,
                "dataset_id": dataset.get("dataset_id"),
                "dataset_spec_version": dataset.get("spec_version"),
                "model": model,
                "prompt_set": prompt_set,
                "summary": summary,
                "documents": doc_records,
            }
            out_file = run_dir / f"{_slugify(model)}__{prompt_set}.json"
            _write_json(out_file, run_payload)

            matrix_rows.append(
                {
                    "model": model,
                    "prompt_set": prompt_set,
                    "summary": summary,
                    "artifact": str(out_file),
                }
            )
            print(
                f"[{model} | {prompt_set}] "
                f"f1={summary['f1']:.3f} "
                f"uncert_acc={summary['uncertainty_accuracy']:.3f} "
                f"parse_failures={summary['parse_failures']}"
            )

    matrix_summary = {
        "captured_at": run_label,
        "run_slug": run_slug,
        "prompt_set_version": PROMPT_SET_VERSION,
        "dataset_id": dataset.get("dataset_id"),
        "rows": matrix_rows,
    }
    _write_json(run_dir / "matrix-summary.json", matrix_summary)
    _append_ledger(ledger_path, run_label, matrix_rows)

    print(f"Wrote run artifacts to: {run_dir}")
    print(f"Updated ledger: {ledger_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
