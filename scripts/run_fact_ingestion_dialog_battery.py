#!/usr/bin/env python3
"""
Run a multi-turn fact-ingestion battery through LM Studio MCP integration.

For each scenario:
1) reset runtime KB
2) execute natural-language turns
3) run deterministic post-check queries against the same MCP session path
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:1234"
DEFAULT_INTEGRATION = "mcp/prolog-reasoning"
DEFAULT_MODELS = [
    "qwen3.5-4b",
    "qwen/qwen3.5-9b",
    "qwen3.5-27b@q4_k_m",
]
DEFAULT_STEERING_PROFILES = ["loose_v1", "strict_ingestion_v1"]
DEFAULT_BATTERY_PATH = "data/fact_extraction/fact_ingestion_dialog_battery_v1.json"
DEFAULT_ENV_FILE = ".env.local"
DEFAULT_OUT_ROOT = ".tmp_fact_ingestion_dialog_battery"
DEFAULT_LEDGER = "docs/research/fact-ingestion-dialog-battery.md"

WRITE_TOOLS = {
    "assert_fact",
    "bulk_assert_facts",
    "retract_fact",
    "assert_rule",
    "reset_kb",
}


STEERING_PREFIX = {
    "loose_v1": (
        "You are operating with MCP tools enabled. Use tools when useful, keep answers grounded, "
        "and avoid inventing facts."
    ),
    "strict_ingestion_v1": (
        "You are operating with MCP tools enabled. Strict ingestion policy:\n"
        "1) Persist only clearly grounded facts.\n"
        "2) For uncertain/hedged/speaker-unresolved claims, call classify_statement and do not write facts.\n"
        "3) Ignore style instructions as non-facts.\n"
        "4) Prefer canonical predicates and deterministic behavior.\n"
    ),
}


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
                "HTTP 401 from LM Studio API. Set LMSTUDIO_API_KEY or pass --api-key."
            ) from error
        if error.code == 400 and "plugin_connection_error" in raw:
            raise RuntimeError(
                "LM Studio integration error for mcp/prolog-reasoning.\n"
                "The MCP plugin process did not stay up.\n"
                "Check LM Studio integration health, then retry.\n"
                f"Raw error: {raw}"
            ) from error
        raise RuntimeError(f"HTTP {error.code}: {raw}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Connection error: {error}") from error


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


def _extract_step(response: dict[str, Any], step_id: str, prompt: str) -> dict[str, Any]:
    items = response.get("output", [])
    tool_calls: list[dict[str, Any]] = []
    assistant_message = ""
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "tool_call":
                tool_calls.append(
                    {
                        "tool": item.get("tool"),
                        "arguments": item.get("arguments", {}),
                        "output": item.get("output"),
                    }
                )
            elif item.get("type") == "message":
                content = item.get("content")
                if isinstance(content, str):
                    assistant_message = content
    return {
        "step": step_id,
        "prompt": prompt,
        "tool_calls": tool_calls,
        "assistant_message": assistant_message,
    }


def _run_chat_step(
    *,
    base_url: str,
    model: str,
    integration: str,
    api_key: str | None,
    prompt: str,
    step_id: str,
    context_length: int,
) -> dict[str, Any]:
    endpoint = f"{base_url.rstrip('/')}/api/v1/chat"
    payload = {
        "model": model,
        "input": prompt,
        "integrations": [integration],
        "temperature": 0,
        "context_length": context_length,
    }
    response = _post_json(endpoint, payload, api_key)
    return _extract_step(response, step_id=step_id, prompt=prompt)


def _evaluate_turn_expectations(turn_spec: dict[str, Any], step: dict[str, Any]) -> dict[str, Any]:
    observed = {
        str(call.get("tool"))
        for call in step.get("tool_calls", [])
        if isinstance(call, dict) and isinstance(call.get("tool"), str)
    }
    expected_any = {
        str(tool) for tool in turn_spec.get("expected_any_tools", []) if isinstance(tool, str)
    }
    forbidden = {
        str(tool) for tool in turn_spec.get("forbidden_tools", []) if isinstance(tool, str)
    }
    expected_any_ok = True if not expected_any else bool(observed.intersection(expected_any))
    forbidden_ok = len(observed.intersection(forbidden)) == 0
    turn_type = str(turn_spec.get("turn_type", ""))
    uncertain_write_violation = turn_type == "uncertain" and bool(observed.intersection(WRITE_TOOLS))
    return {
        "observed_tools": sorted(observed),
        "expected_any_tools": sorted(expected_any),
        "forbidden_tools": sorted(forbidden),
        "expected_any_ok": expected_any_ok,
        "forbidden_ok": forbidden_ok,
        "uncertain_write_violation": uncertain_write_violation,
        "pass": expected_any_ok and forbidden_ok and not uncertain_write_violation,
    }


def _verify_query_exists(
    *,
    base_url: str,
    model: str,
    integration: str,
    api_key: str | None,
    query: str,
    expect_present: bool,
    step_id: str,
    context_length: int,
) -> dict[str, Any]:
    prompt = (
        "Verification step. Use ONLY query_rows with this exact query and no other tools:\n"
        f"{query}\n"
        "Then return one short sentence."
    )
    step = _run_chat_step(
        base_url=base_url,
        model=model,
        integration=integration,
        api_key=api_key,
        prompt=prompt,
        step_id=step_id,
        context_length=context_length,
    )
    row_call = None
    for call in step.get("tool_calls", []):
        if isinstance(call, dict) and call.get("tool") == "query_rows":
            row_call = call
            break
    payload = _extract_tool_output_json(row_call.get("output") if row_call else None) or {}
    status = payload.get("status")
    num_rows = payload.get("num_rows")
    try:
        count = int(num_rows)
    except (TypeError, ValueError):
        count = 0
    exists = status == "success" and count > 0
    ok = exists if expect_present else (not exists)
    return {
        "query": query,
        "expect_present": expect_present,
        "ok": ok,
        "exists": exists,
        "status": status,
        "num_rows": count,
        "step": step,
    }


def _ensure_ledger(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "# Fact Ingestion Dialog Battery\n\n"
            "Tracks multi-turn ingestion behavior and post-run KB outcomes across models and steering profiles.\n"
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
        "| model | steering | scenario pass | kb checks | turn expectations | uncertain write violations | notes |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for row in rows:
        summary = row["summary"]
        note = "ok"
        if summary.get("scenario_pass_rate", 0.0) < 1.0:
            note = "review_failed_scenarios"
        lines.append(
            "| "
            + " | ".join(
                [
                    row["model"],
                    row["steering_profile"],
                    f"{summary['scenario_passes']}/{summary['scenarios_total']} ({summary['scenario_pass_rate'] * 100:.1f}%)",
                    f"{summary['kb_checks_pass']}/{summary['kb_checks_total']} ({summary['kb_check_accuracy'] * 100:.1f}%)",
                    f"{summary['turn_expectations_pass']}/{summary['turn_expectations_total']} ({summary['turn_expectation_accuracy'] * 100:.1f}%)",
                    str(summary["uncertain_write_violations"]),
                    note,
                ]
            )
            + " |"
        )
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_battery(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Battery file must be a JSON object.")
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("Battery file requires a non-empty 'scenarios' list.")
    return payload


def _run_single_scenario(
    *,
    base_url: str,
    model: str,
    integration: str,
    api_key: str | None,
    steering_profile: str,
    scenario: dict[str, Any],
    context_length: int,
) -> dict[str, Any]:
    scenario_id = str(scenario.get("id", "unknown"))
    steps: list[dict[str, Any]] = []

    reset_prompt = "Reset runtime KB now. Use ONLY reset_kb and confirm."
    reset_step = _run_chat_step(
        base_url=base_url,
        model=model,
        integration=integration,
        api_key=api_key,
        prompt=reset_prompt,
        step_id=f"{scenario_id}:reset",
        context_length=context_length,
    )
    steps.append(reset_step)

    turn_evals: list[dict[str, Any]] = []
    turns = scenario.get("turns", [])
    if not isinstance(turns, list):
        turns = []

    for turn in turns:
        if not isinstance(turn, dict):
            continue
        turn_id = str(turn.get("id", "turn"))
        user_prompt = str(turn.get("prompt", "")).strip()
        full_prompt = f"{STEERING_PREFIX[steering_profile]}\n\nUser turn:\n{user_prompt}"
        step = _run_chat_step(
            base_url=base_url,
            model=model,
            integration=integration,
            api_key=api_key,
            prompt=full_prompt,
            step_id=f"{scenario_id}:{turn_id}",
            context_length=context_length,
        )
        steps.append(step)
        evaluation = _evaluate_turn_expectations(turn, step)
        turn_evals.append(
            {
                "turn_id": turn_id,
                "turn_type": turn.get("turn_type"),
                "prompt": user_prompt,
                "evaluation": evaluation,
            }
        )

    verification_results: list[dict[str, Any]] = []
    present_queries = scenario.get("assert_present_queries", [])
    absent_queries = scenario.get("assert_absent_queries", [])

    for idx, query in enumerate(present_queries):
        if not isinstance(query, str):
            continue
        result = _verify_query_exists(
            base_url=base_url,
            model=model,
            integration=integration,
            api_key=api_key,
            query=query,
            expect_present=True,
            step_id=f"{scenario_id}:verify_present_{idx+1}",
            context_length=context_length,
        )
        verification_results.append(result)
        steps.append(result["step"])

    for idx, query in enumerate(absent_queries):
        if not isinstance(query, str):
            continue
        result = _verify_query_exists(
            base_url=base_url,
            model=model,
            integration=integration,
            api_key=api_key,
            query=query,
            expect_present=False,
            step_id=f"{scenario_id}:verify_absent_{idx+1}",
            context_length=context_length,
        )
        verification_results.append(result)
        steps.append(result["step"])

    turn_total = len(turn_evals)
    turn_pass = sum(1 for item in turn_evals if item["evaluation"]["pass"])
    uncertain_write_violations = sum(
        1 for item in turn_evals if item["evaluation"]["uncertain_write_violation"]
    )
    checks_total = len(verification_results)
    checks_pass = sum(1 for item in verification_results if item["ok"])

    scenario_pass = (turn_pass == turn_total) and (checks_pass == checks_total)
    return {
        "scenario_id": scenario_id,
        "description": scenario.get("description", ""),
        "scenario_pass": scenario_pass,
        "turns_total": turn_total,
        "turns_pass": turn_pass,
        "uncertain_write_violations": uncertain_write_violations,
        "kb_checks_total": checks_total,
        "kb_checks_pass": checks_pass,
        "turn_evaluations": turn_evals,
        "verification_results": verification_results,
        "steps": steps,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run fact-ingestion dialog battery and verify final KB state."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="LM Studio API base URL")
    parser.add_argument("--integration", default=DEFAULT_INTEGRATION, help="MCP integration id")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS, help="Model ids")
    parser.add_argument(
        "--steering-profiles",
        nargs="+",
        default=DEFAULT_STEERING_PROFILES,
        help="Steering profiles to evaluate",
    )
    parser.add_argument("--battery", default=DEFAULT_BATTERY_PATH, help="Scenario battery JSON")
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE, help="Optional env file")
    parser.add_argument("--api-key", default="", help="Optional explicit LM Studio API key")
    parser.add_argument("--out-root", default=DEFAULT_OUT_ROOT, help="Output root for artifacts")
    parser.add_argument("--ledger", default=DEFAULT_LEDGER, help="Ledger markdown path")
    parser.add_argument("--max-scenarios", type=int, default=0, help="Limit scenarios (0 = all)")
    parser.add_argument(
        "--context-length",
        type=int,
        default=4000,
        help="Requested LM Studio context length for each chat call.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate config only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _load_env_file(Path(args.env_file))
    api_key = args.api_key.strip() or os.environ.get("LMSTUDIO_API_KEY", "").strip() or None

    battery = _load_battery(Path(args.battery))
    scenarios = battery.get("scenarios", [])
    if args.max_scenarios and args.max_scenarios > 0:
        scenarios = scenarios[: args.max_scenarios]

    for profile in args.steering_profiles:
        if profile not in STEERING_PREFIX:
            raise ValueError(f"Unsupported steering profile: {profile}")

    now_utc = dt.datetime.now(dt.timezone.utc)
    run_label = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    run_slug = now_utc.strftime("%Y%m%d-%H%M%S")
    run_dir = Path(args.out_root) / f"dialog_battery_{run_slug}"
    run_dir.mkdir(parents=True, exist_ok=True)

    ledger_rows: list[dict[str, Any]] = []

    for model in args.models:
        for profile in args.steering_profiles:
            if args.dry_run:
                summary = {
                    "scenario_passes": 0,
                    "scenarios_total": len(scenarios),
                    "scenario_pass_rate": 0.0,
                    "kb_checks_pass": 0,
                    "kb_checks_total": 0,
                    "kb_check_accuracy": 0.0,
                    "turn_expectations_pass": 0,
                    "turn_expectations_total": 0,
                    "turn_expectation_accuracy": 0.0,
                    "uncertain_write_violations": 0,
                    "dry_run": True,
                }
                ledger_rows.append(
                    {"model": model, "steering_profile": profile, "summary": summary}
                )
                continue

            scenario_records: list[dict[str, Any]] = []
            for scenario in scenarios:
                record = _run_single_scenario(
                    base_url=args.base_url,
                    model=model,
                    integration=args.integration,
                    api_key=api_key,
                    steering_profile=profile,
                    scenario=scenario,
                    context_length=args.context_length,
                )
                scenario_records.append(record)

            scenarios_total = len(scenario_records)
            scenario_passes = sum(1 for s in scenario_records if s["scenario_pass"])
            kb_checks_total = sum(int(s["kb_checks_total"]) for s in scenario_records)
            kb_checks_pass = sum(int(s["kb_checks_pass"]) for s in scenario_records)
            turn_expect_total = sum(int(s["turns_total"]) for s in scenario_records)
            turn_expect_pass = sum(int(s["turns_pass"]) for s in scenario_records)
            uncertain_write_violations = sum(
                int(s["uncertain_write_violations"]) for s in scenario_records
            )

            summary = {
                "scenario_passes": scenario_passes,
                "scenarios_total": scenarios_total,
                "scenario_pass_rate": (scenario_passes / scenarios_total) if scenarios_total else 0.0,
                "kb_checks_pass": kb_checks_pass,
                "kb_checks_total": kb_checks_total,
                "kb_check_accuracy": (kb_checks_pass / kb_checks_total) if kb_checks_total else 0.0,
                "turn_expectations_pass": turn_expect_pass,
                "turn_expectations_total": turn_expect_total,
                "turn_expectation_accuracy": (
                    turn_expect_pass / turn_expect_total if turn_expect_total else 0.0
                ),
                "uncertain_write_violations": uncertain_write_violations,
            }

            payload = {
                "captured_at": run_label,
                "run_slug": run_slug,
                "battery_id": battery.get("battery_id"),
                "battery_version": battery.get("version"),
                "model": model,
                "steering_profile": profile,
                "summary": summary,
                "scenarios": scenario_records,
            }
            out_file = run_dir / f"{_slugify(model)}__{profile}.json"
            _write_json(out_file, payload)
            print(
                f"[{model} | {profile}] "
                f"scenario_pass={summary['scenario_passes']}/{summary['scenarios_total']} "
                f"kb={summary['kb_checks_pass']}/{summary['kb_checks_total']} "
                f"turns={summary['turn_expectations_pass']}/{summary['turn_expectations_total']} "
                f"uncertain_write_violations={summary['uncertain_write_violations']}"
            )

            ledger_rows.append(
                {
                    "model": model,
                    "steering_profile": profile,
                    "summary": summary,
                    "artifact": str(out_file),
                }
            )

    summary_payload = {
        "captured_at": run_label,
        "run_slug": run_slug,
        "battery_id": battery.get("battery_id"),
        "rows": ledger_rows,
    }
    _write_json(run_dir / "matrix-summary.json", summary_payload)
    _append_ledger(Path(args.ledger), run_label, ledger_rows)

    print(f"Wrote run artifacts to: {run_dir}")
    print(f"Updated ledger: {args.ledger}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
