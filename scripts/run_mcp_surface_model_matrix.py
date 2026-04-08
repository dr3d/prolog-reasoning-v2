#!/usr/bin/env python3
"""
Run the MCP surface playbook across multiple models and record compact metrics.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any

from capture_mcp_surface_playbook_session import (
    REQUIRED_TOOLS,
    run_capture,
    validate_transcript,
)


DEFAULT_BASE_URL = "http://127.0.0.1:1234"
DEFAULT_INTEGRATION = "mcp/prolog-reasoning"
DEFAULT_OUT_ROOT = ".tmp_model_matrix"
DEFAULT_LEDGER = "docs/research/model-scenario-matrix.md"
DEFAULT_ENV_FILE = ".env.local"
DEFAULT_MODELS = [
    "qwen3.5-4b",
    "qwen/qwen3.5-9b",
    "qwen3.5-27b@q4_k_m",
]


def _slugify_model(model: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", model).strip("_").lower()


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


def _extract_tool_output_json(output_field: Any) -> dict[str, Any] | None:
    if output_field is None:
        return None

    payload: Any = output_field
    if isinstance(output_field, str):
        try:
            payload = json.loads(output_field)
        except json.JSONDecodeError:
            return None

    if isinstance(payload, dict):
        return payload

    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    try:
                        parsed = json.loads(text)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(parsed, dict):
                        return parsed
            elif isinstance(item, str):
                try:
                    parsed = json.loads(item)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    return parsed

    return None


def _find_step(transcript: dict[str, Any], step_name: str) -> dict[str, Any] | None:
    for step in transcript.get("steps", []):
        if isinstance(step, dict) and step.get("step") == step_name:
            return step
    return None


def _find_tool_call(step: dict[str, Any] | None, tool_name: str) -> dict[str, Any] | None:
    if not isinstance(step, dict):
        return None
    for call in step.get("tool_calls", []):
        if isinstance(call, dict) and call.get("tool") == tool_name:
            return call
    return None


def summarize_transcript(transcript: dict[str, Any], findings: list[str]) -> dict[str, Any]:
    seen_tools: set[str] = set()
    for step in transcript.get("steps", []):
        if not isinstance(step, dict):
            continue
        for call in step.get("tool_calls", []):
            if isinstance(call, dict):
                tool = call.get("tool")
                if isinstance(tool, str) and tool:
                    seen_tools.add(tool)

    required_total = len(REQUIRED_TOOLS)
    required_seen = len(REQUIRED_TOOLS.intersection(seen_tools))
    missing_required = sorted(REQUIRED_TOOLS - seen_tools)

    classify_step = _find_step(transcript, "classify")
    classify_call = _find_tool_call(classify_step, "classify_statement")
    classify_payload = _extract_tool_output_json(
        classify_call.get("output") if classify_call else None
    ) or {}
    proposal_check = classify_payload.get("proposal_check") or {}
    classify_kind = classify_payload.get("kind")
    classify_can_persist_now = classify_payload.get("can_persist_now")
    classify_proposal_status = proposal_check.get("status")
    candidate = proposal_check.get("candidate") or {}
    classify_candidate_predicate = candidate.get("canonical_predicate")
    classify_fact_recognition_ok = (
        classify_kind in {"hard_fact", "tentative_fact", "correction"}
        and classify_proposal_status in {"valid", "needs_clarification"}
        and isinstance(classify_candidate_predicate, str)
        and bool(classify_candidate_predicate)
    )

    write_tools = {"assert_fact", "bulk_assert_facts", "retract_fact", "reset_kb"}
    classify_write_tools = sorted({
        call.get("tool")
        for call in (classify_step or {}).get("tool_calls", [])
        if isinstance(call, dict) and call.get("tool") in write_tools
    })

    nl_step = _find_step(transcript, "nl_query")
    nl_call = _find_tool_call(nl_step, "query_logic")
    nl_payload = _extract_tool_output_json(nl_call.get("output") if nl_call else None) or {}
    nl_result_status = nl_payload.get("status")
    nl_result_type = nl_payload.get("result_type")

    return {
        "captured_at": transcript.get("captured_at"),
        "validation_pass": len(findings) == 0,
        "validation_findings": findings,
        "required_tools_seen": f"{required_seen}/{required_total}",
        "missing_required_tools": missing_required,
        "classify_kind": classify_kind,
        "classify_can_persist_now": classify_can_persist_now,
        "classify_proposal_status": classify_proposal_status,
        "classify_candidate_predicate": classify_candidate_predicate,
        "classify_fact_recognition_ok": classify_fact_recognition_ok,
        "classify_write_tools": classify_write_tools,
        "nl_query_result_status": nl_result_status,
        "nl_query_result_type": nl_result_type,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _ensure_ledger_file(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "# Model Scenario Matrix\n\n"
            "Compact matrix for MCP scenario runs across model families.\n\n"
            "Each run appends a small table with validation and behavior markers.\n"
        ),
        encoding="utf-8",
    )


def _append_ledger(path: Path, run_label: str, rows: list[dict[str, Any]]) -> None:
    _ensure_ledger_file(path)

    lines: list[str] = []
    lines.append("")
    lines.append(f"## Run {run_label}")
    lines.append("")
    lines.append(
        "| model | validation | tools | classify kind | candidate predicate | fact recognition | can persist now | proposal status | classify writes | nl result | notes |"
    )
    lines.append(
        "|---|---|---|---|---|---|---|---|---|---|---|"
    )

    for row in rows:
        summary = row["summary"]
        findings = summary.get("validation_findings", [])
        note = findings[0] if findings else "none"
        classify_writes = (
            ", ".join(summary.get("classify_write_tools", []))
            if summary.get("classify_write_tools")
            else "none"
        )
        nl_result = f"{summary.get('nl_query_result_status')}/{summary.get('nl_query_result_type')}"
        lines.append(
            "| "
            + " | ".join(
                [
                    row["model"],
                    "pass" if summary.get("validation_pass") else "fail",
                    str(summary.get("required_tools_seen")),
                    str(summary.get("classify_kind")),
                    str(summary.get("classify_candidate_predicate")),
                    "yes" if summary.get("classify_fact_recognition_ok") else "no",
                    str(summary.get("classify_can_persist_now")),
                    str(summary.get("classify_proposal_status")),
                    classify_writes,
                    nl_result,
                    note.replace("|", "/"),
                ]
            )
            + " |"
        )

    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run MCP surface playbook capture across models and write a compact matrix."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="LM Studio API base URL")
    parser.add_argument("--integration", default=DEFAULT_INTEGRATION, help="MCP integration id")
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        help="Model ids to run (space-separated).",
    )
    parser.add_argument("--out-root", default=DEFAULT_OUT_ROOT, help="Output root for run artifacts")
    parser.add_argument(
        "--env-file",
        default=DEFAULT_ENV_FILE,
        help="Optional env file to load LMSTUDIO_API_KEY from when not already set.",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="Optional explicit LM Studio API key. Defaults to env resolution.",
    )
    parser.add_argument(
        "--ledger",
        default=DEFAULT_LEDGER,
        help="Markdown ledger file to append matrix run rows.",
    )
    parser.add_argument(
        "--skip-ledger",
        action="store_true",
        help="Do not append markdown run summary rows.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _load_env_file(Path(args.env_file))
    api_key = args.api_key or os.environ.get("LMSTUDIO_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print(
            "Missing LM Studio API key. Set LMSTUDIO_API_KEY, pass --api-key, or put it in .env.local."
        )
        return 2

    run_label = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    out_root = Path(args.out_root)
    run_stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_root = out_root / f"mcp_surface_{run_stamp}"

    rows: list[dict[str, Any]] = []
    for model in args.models:
        model_slug = _slugify_model(model)
        model_out = run_root / model_slug
        print(f"[matrix] running model={model} -> {model_out}")
        try:
            transcript, outputs = run_capture(
                base_url=args.base_url,
                model=model,
                integration=args.integration,
                api_key=api_key,
                out_dir=model_out,
            )
            findings = validate_transcript(transcript)
            summary = summarize_transcript(transcript, findings)
            row = {
                "model": model,
                "outputs": outputs,
                "summary": summary,
            }
        except Exception as exc:
            row = {
                "model": model,
                "outputs": {},
                "summary": {
                    "captured_at": None,
                    "validation_pass": False,
                    "validation_findings": [f"runtime_error: {exc}"],
                    "required_tools_seen": "0/11",
                    "missing_required_tools": sorted(REQUIRED_TOOLS),
                    "classify_kind": None,
                    "classify_can_persist_now": None,
                    "classify_proposal_status": None,
                    "classify_write_tools": [],
                    "nl_query_result_status": None,
                    "nl_query_result_type": None,
                },
            }
        rows.append(row)

    combined = {
        "scenario": "mcp-surface-playbook-session",
        "run_label": run_label,
        "base_url": args.base_url,
        "integration": args.integration,
        "rows": rows,
    }
    combined_path = run_root / "matrix-summary.json"
    _write_json(combined_path, combined)

    if not args.skip_ledger:
        _append_ledger(Path(args.ledger), run_label, rows)

    print("Matrix run complete.")
    print(json.dumps({"run_root": str(run_root), "summary": str(combined_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
