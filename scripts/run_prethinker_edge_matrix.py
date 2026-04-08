#!/usr/bin/env python3
"""
Run a phrasing edge-case matrix against the MCP pre-thinker tool.

This script is for fast research iteration:
- feed controlled utterance variants
- capture structured pre-thinker assessments
- score agreement on expected routing fields
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from mcp_server import PrologMCPServer


DEFAULT_DATASET = "data/fact_extraction/prethinker_edge_cases_v1.json"
DEFAULT_OUT_ROOT = ".tmp_prethinker_edge_matrix"
DEFAULT_BASE_URL = "http://127.0.0.1:1234"
DEFAULT_MODEL = "qwen3.5-4b"
DEFAULT_ENV_FILE = ".env.local"
DEFAULT_KB_PATH = "prolog/core.pl"
DEFAULT_TIMEOUT_SECONDS = 120


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


def _load_dataset(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Dataset must be a JSON object.")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Dataset must include non-empty 'cases' list.")
    return payload


def _as_bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _as_text_or_none(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text if text else None
    return None


def _eval_field(expected: Any, observed: Any) -> bool | None:
    if expected is None:
        return None
    return expected == observed


def _render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Pre-Thinker Edge Matrix")
    lines.append("")
    lines.append(f"- Captured at: {report.get('captured_at')}")
    lines.append(f"- Model: `{report.get('model')}`")
    lines.append(f"- Dataset: `{report.get('dataset_path')}`")
    lines.append(f"- Cases: `{report.get('total_cases')}`")
    lines.append(
        f"- Overall pass: `{report.get('overall_pass_count')}` / `{report.get('total_cases')}`"
    )
    lines.append(
        f"- Assessment valid: `{report.get('assessment_valid_count')}` / `{report.get('total_cases')}`"
    )
    lines.append(
        f"- Fallback used: `{report.get('fallback_count')}` / `{report.get('total_cases')}`"
    )
    lines.append(
        f"- Write candidates: `{report.get('write_candidate_count')}` / `{report.get('total_cases')}`"
    )
    lines.append(
        f"- Write-ready now: `{report.get('write_ready_count')}` / `{report.get('total_cases')}`"
    )
    lines.append("")
    lines.append(
        "| id | source | expected kind | observed kind | expected persist | observed persist | "
        "expected clarify | observed clarify | expected write_now | observed write_now | "
        "proposal status | assessment valid | fallback | case pass |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for row in report.get("rows", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("id", "")),
                    str(row.get("assessment_source", "")),
                    str(row.get("expected_kind", "")),
                    str(row.get("observed_kind", "")),
                    str(row.get("expected_can_persist_now", "")),
                    str(row.get("observed_can_persist_now", "")),
                    str(row.get("expected_needs_clarification", "")),
                    str(row.get("observed_needs_clarification", "")),
                    str(row.get("expected_can_write_now", "")),
                    str(row.get("observed_can_write_now", "")),
                    str(row.get("observed_proposal_status", "")),
                    str(row.get("assessment_valid", "")),
                    str(row.get("fallback_used", "")),
                    str(row.get("case_pass", "")),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run pre-thinker phrasing edge matrix and emit JSON + Markdown report."
    )
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Edge-case dataset JSON path")
    parser.add_argument("--out-root", default=DEFAULT_OUT_ROOT, help="Output root")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="LM Studio API base URL")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Pre-thinker model id")
    parser.add_argument("--api-key", default="", help="Optional explicit API key")
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE, help="Optional env file")
    parser.add_argument("--kb-path", default=DEFAULT_KB_PATH, help="KB path for MCP server init")
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Pre-thinker request timeout seconds",
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=0,
        help="Limit number of cases for quick iteration (0 = all).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _load_env_file(Path(args.env_file))

    dataset_path = (REPO_ROOT / args.dataset).resolve() if not Path(args.dataset).is_absolute() else Path(args.dataset).resolve()
    out_root = (REPO_ROOT / args.out_root).resolve() if not Path(args.out_root).is_absolute() else Path(args.out_root).resolve()
    dataset = _load_dataset(dataset_path)
    all_cases = dataset.get("cases", [])
    cases = all_cases[: args.max_cases] if args.max_cases and args.max_cases > 0 else all_cases

    server = PrologMCPServer(kb_path=args.kb_path)
    server.prethinker_base_url = args.base_url
    server.prethinker_model = args.model
    server.prethinker_api_key = (
        args.api_key.strip()
        or os.environ.get("PRETHINKER_API_KEY", "").strip()
        or os.environ.get("LMSTUDIO_API_KEY", "").strip()
        or os.environ.get("OPENAI_API_KEY", "").strip()
        or None
    )
    server.prethinker_timeout_seconds = int(args.timeout_seconds)

    now_utc = dt.datetime.now(dt.timezone.utc)
    run_slug = now_utc.strftime("%Y%m%d-%H%M%S")
    run_dir = out_root / f"prethinker_edge_{run_slug}"
    run_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for idx, raw_case in enumerate(cases, start=1):
        case = raw_case if isinstance(raw_case, dict) else {}
        case_id = str(case.get("id") or f"case_{idx:02d}")
        text = str(case.get("text", "")).strip()
        narrative_context = str(case.get("narrative_context", "")).strip()
        expected = case.get("expected", {})
        expected = expected if isinstance(expected, dict) else {}

        result = server.prethink_utterance(
            text=text,
            narrative_context=narrative_context,
            model=args.model,
        )
        model_assessment = result.get("model_assessment", {})
        model_assessment = model_assessment if isinstance(model_assessment, dict) else {}
        final_assessment = result.get("assessment", {})
        final_assessment = final_assessment if isinstance(final_assessment, dict) else {}
        assessment_valid = bool(result.get("assessment_valid", False))
        fallback_used = bool(result.get("fallback_used", False))
        assessment_source = str(result.get("assessment_source", "model"))
        assessment_for_scoring = model_assessment if assessment_valid else {}
        kb_projection = result.get("kb_projection", {})
        kb_projection = kb_projection if isinstance(kb_projection, dict) else {}

        expected_kind = expected.get("kind")
        expected_can_persist_now = _as_bool_or_none(expected.get("can_persist_now"))
        expected_needs_clarification = _as_bool_or_none(expected.get("needs_clarification"))
        expected_can_write_now = _as_bool_or_none(expected.get("can_write_now"))
        expected_proposal_status = _as_text_or_none(expected.get("proposal_status"))
        observed_kind = assessment_for_scoring.get("kind")
        observed_can_persist_now = _as_bool_or_none(assessment_for_scoring.get("can_persist_now"))
        observed_needs_clarification = _as_bool_or_none(assessment_for_scoring.get("needs_clarification"))
        observed_can_write_now = _as_bool_or_none(kb_projection.get("can_write_now"))
        observed_proposal_status = _as_text_or_none(kb_projection.get("proposal_status"))
        final_kind = final_assessment.get("kind")

        kind_ok = _eval_field(expected_kind, observed_kind)
        persist_ok = _eval_field(expected_can_persist_now, observed_can_persist_now)
        clarification_ok = _eval_field(expected_needs_clarification, observed_needs_clarification)
        write_ready_ok = _eval_field(expected_can_write_now, observed_can_write_now)
        proposal_status_ok = _eval_field(expected_proposal_status, observed_proposal_status)
        checks = [
            check
            for check in [kind_ok, persist_ok, clarification_ok, write_ready_ok, proposal_status_ok]
            if check is not None
        ]
        case_pass = assessment_valid and (all(checks) if checks else True)

        row = {
            "id": case_id,
            "text": text,
            "narrative_context": narrative_context,
            "assessment_source": assessment_source,
            "fallback_used": fallback_used,
            "expected_kind": expected_kind,
            "expected_can_persist_now": expected_can_persist_now,
            "expected_needs_clarification": expected_needs_clarification,
            "expected_can_write_now": expected_can_write_now,
            "expected_proposal_status": expected_proposal_status,
            "observed_kind": observed_kind,
            "observed_can_persist_now": observed_can_persist_now,
            "observed_needs_clarification": observed_needs_clarification,
            "observed_can_write_now": observed_can_write_now,
            "observed_proposal_status": observed_proposal_status,
            "final_kind": final_kind,
            "kind_ok": kind_ok,
            "persist_ok": persist_ok,
            "clarification_ok": clarification_ok,
            "write_ready_ok": write_ready_ok,
            "proposal_status_ok": proposal_status_ok,
            "assessment_valid": assessment_valid,
            "validation_errors": result.get("validation_errors", []),
            "case_pass": case_pass,
            "model_assessment": model_assessment,
            "final_assessment": final_assessment,
            "baseline_assessment": result.get("baseline_assessment", {}),
            "agreement_with_baseline": result.get("agreement_with_baseline", {}),
            "kb_projection": kb_projection,
            "assistant_message": result.get("assistant_message", ""),
            "raw_response": result.get("raw_response", {}),
        }
        rows.append(row)
        print(
            f"[{case_id}] valid={assessment_valid} fallback={fallback_used} pass={case_pass} "
            f"model_kind={observed_kind} final_kind={final_kind} "
            f"persist={observed_can_persist_now} clarify={observed_needs_clarification} "
            f"write_now={observed_can_write_now} proposal={observed_proposal_status}"
        )

    total_cases = len(rows)
    overall_pass_count = sum(1 for row in rows if row.get("case_pass"))
    assessment_valid_count = sum(1 for row in rows if row.get("assessment_valid"))
    fallback_count = sum(1 for row in rows if row.get("fallback_used"))
    write_candidate_count = sum(
        1
        for row in rows
        if isinstance(row.get("kb_projection"), dict)
        and row["kb_projection"].get("should_attempt_write") is True
    )
    write_ready_count = sum(
        1
        for row in rows
        if isinstance(row.get("kb_projection"), dict)
        and row["kb_projection"].get("can_write_now") is True
    )
    kind_checks = [row["kind_ok"] for row in rows if row.get("kind_ok") is not None]
    persist_checks = [row["persist_ok"] for row in rows if row.get("persist_ok") is not None]
    clarification_checks = [
        row["clarification_ok"] for row in rows if row.get("clarification_ok") is not None
    ]
    write_ready_checks = [
        row["write_ready_ok"] for row in rows if row.get("write_ready_ok") is not None
    ]

    report = {
        "captured_at": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "run_slug": run_slug,
        "model": args.model,
        "base_url": args.base_url,
        "dataset_path": str(dataset_path),
        "total_cases": total_cases,
        "overall_pass_count": overall_pass_count,
        "assessment_valid_count": assessment_valid_count,
        "fallback_count": fallback_count,
        "write_candidate_count": write_candidate_count,
        "write_ready_count": write_ready_count,
        "kind_accuracy": (sum(1 for check in kind_checks if check) / len(kind_checks)) if kind_checks else None,
        "persist_accuracy": (sum(1 for check in persist_checks if check) / len(persist_checks)) if persist_checks else None,
        "clarification_accuracy": (
            sum(1 for check in clarification_checks if check) / len(clarification_checks)
        ) if clarification_checks else None,
        "write_ready_accuracy": (
            sum(1 for check in write_ready_checks if check) / len(write_ready_checks)
        ) if write_ready_checks else None,
        "rows": rows,
    }

    model_slug = _slugify(args.model)
    json_path = run_dir / f"{model_slug}__prethinker-edge.json"
    md_path = run_dir / f"{model_slug}__prethinker-edge.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")

    print("Pre-thinker edge matrix complete.")
    print(json.dumps({"json": str(json_path), "markdown": str(md_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
