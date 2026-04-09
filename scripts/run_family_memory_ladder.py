#!/usr/bin/env python3
"""
Run an ad-hoc family-memory ladder across fuzzy vs sharp memory modes.

Modes:
- fuzzy: no MCP integration (model relies on conversational context only)
- sharp: MCP integration with explicit Prolog tool usage guidance
- hybrid: MCP integration + required pre_think per turn (kb_ingest_mode=facts)
- hybrid_pressure: hybrid + large context ballast to induce fuzziness pressure

Outputs:
- per-mode transcripts (json, md, html)
- summary report (json, md)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from render_dialog_helpers import render_transcript_html


REPO_ROOT = SCRIPT_DIR.parent

DEFAULT_BASE_URL = "http://127.0.0.1:1234"
DEFAULT_INTEGRATION = "mcp/prolog-reasoning"
DEFAULT_MODEL = "qwen/qwen3.5-9b"
DEFAULT_ENV_FILE = ".env.local"
DEFAULT_OUT_ROOT = "docs/research/conversations/family-memory-ladder"
DEFAULT_CONTEXT_LENGTH = 4000
DEFAULT_TEMPERATURE = 0.0
DEFAULT_REQUEST_TIMEOUT_SECONDS = 240
DEFAULT_STEP_RETRIES = 3
DEFAULT_RETRY_DELAY_SECONDS = 2.0
DEFAULT_PRESSURE_STUFFING_CHARS = 3200

MODE_ORDER = ["fuzzy", "sharp", "hybrid", "hybrid_pressure"]


def _build_ladder() -> list[dict[str, Any]]:
    noise_block = (
        "Irrelevant sidebar: maintenance bay humming, weather chatter, inventory note, "
        "coffee spill report, and unrelated docking logs. Ignore this for family facts."
    )
    return [
        {
            "id": "t01_seed",
            "tier": 1,
            "turn_type": "statement",
            "utterance": (
                "Family ledger seed: Nora is parent of Ava. Liam is parent of Ava. "
                "Ava is parent of Owen. Owen is parent of Piper."
            ),
        },
        {
            "id": "q01_ancestors_piper_initial",
            "tier": 1,
            "turn_type": "probe",
            "utterance": "Who are Piper's ancestors right now?",
            "expected_all": ["owen", "ava", "nora", "liam"],
            "forbidden": [],
            "expect_truthy": None,
        },
        {
            "id": "t02_correction_parent_swap",
            "tier": 2,
            "turn_type": "statement",
            "utterance": (
                "Correction: Liam is not Ava's parent. Replace with Theo as Ava's parent."
            ),
        },
        {
            "id": "q02_parents_ava_after_correction",
            "tier": 2,
            "turn_type": "probe",
            "utterance": "After the correction, who are Ava's parents?",
            "expected_all": ["nora", "theo"],
            "forbidden": ["liam"],
            "expect_truthy": None,
        },
        {
            "id": "t03_tentative_noise",
            "tier": 3,
            "turn_type": "statement",
            "utterance": (
                "Tentative note only: maybe Olivia is Piper's parent, confidence low, "
                "not confirmed."
            ),
        },
        {
            "id": "q03_parent_piper_confirmed_only",
            "tier": 3,
            "turn_type": "probe",
            "utterance": "Using confirmed facts only, who is Piper's parent?",
            "expected_all": ["owen"],
            "forbidden": ["olivia"],
            "expect_truthy": None,
        },
        {
            "id": "t04_irrelevant_noise",
            "tier": 3,
            "turn_type": "statement",
            "utterance": noise_block,
        },
        {
            "id": "t05_branch_extension",
            "tier": 4,
            "turn_type": "statement",
            "utterance": "Theo is parent of Quinn. Quinn is parent of Rhea.",
        },
        {
            "id": "q04_ancestors_rhea",
            "tier": 4,
            "turn_type": "probe",
            "utterance": "Who are Rhea's ancestors?",
            "expected_all": ["quinn", "theo"],
            "forbidden": [],
            "expect_truthy": None,
        },
        {
            "id": "t06_additional_descendant",
            "tier": 4,
            "turn_type": "statement",
            "utterance": "Update: Owen is also parent of Una.",
        },
        {
            "id": "q05_descendants_ava",
            "tier": 4,
            "turn_type": "probe",
            "utterance": "List Ava's descendants now.",
            "expected_all": ["owen", "piper", "una"],
            "forbidden": [],
            "expect_truthy": None,
        },
        {
            "id": "q06_sibling_check",
            "tier": 4,
            "turn_type": "probe",
            "utterance": "Are Piper and Una siblings?",
            "expected_all": [],
            "forbidden": [],
            "expect_truthy": True,
        },
        {
            "id": "t07_branch_rewire",
            "tier": 5,
            "turn_type": "statement",
            "utterance": (
                "Second correction: Theo is not Quinn's parent. Replace with Mira as Quinn's parent."
            ),
        },
        {
            "id": "q07_ancestors_rhea_after_rewire",
            "tier": 5,
            "turn_type": "probe",
            "utterance": "After the second correction, who are Rhea's ancestors?",
            "expected_all": ["quinn", "mira"],
            "forbidden": ["theo"],
            "expect_truthy": None,
        },
        {
            "id": "q08_liam_removed_check",
            "tier": 5,
            "turn_type": "probe",
            "utterance": "Is Liam currently Ava's parent?",
            "expected_all": [],
            "forbidden": [],
            "expect_truthy": False,
        },
        {
            "id": "t08_tentative_new_claim",
            "tier": 6,
            "turn_type": "statement",
            "utterance": (
                "Tentative memo only: maybe Quinn is parent of Uma; confidence low and unverified."
            ),
        },
        {
            "id": "q09_uma_parent_confirmed",
            "tier": 6,
            "turn_type": "probe",
            "utterance": "Using confirmed facts only, does Uma have a recorded parent?",
            "expected_all": [],
            "forbidden": [],
            "expect_truthy": False,
        },
        {
            "id": "t09_deepen_mira_branch",
            "tier": 6,
            "turn_type": "statement",
            "utterance": "Extension: Rhea is parent of Sol.",
        },
        {
            "id": "q10_ancestors_sol",
            "tier": 6,
            "turn_type": "probe",
            "utterance": "Who are Sol's ancestors now?",
            "expected_all": ["rhea", "quinn", "mira"],
            "forbidden": ["theo"],
            "expect_truthy": None,
        },
        {
            "id": "t10_name_collision_noise",
            "tier": 6,
            "turn_type": "statement",
            "utterance": (
                "Noise only: inventory crate LIAM-42 and maintenance bot AVA-7 were moved. "
                "These are labels, not family members."
            ),
        },
        {
            "id": "q11_parents_ava_final",
            "tier": 6,
            "turn_type": "probe",
            "utterance": "Final check: who are Ava's parents?",
            "expected_all": ["nora", "theo"],
            "forbidden": ["liam"],
            "expect_truthy": None,
        },
        {
            "id": "q12_descendants_theo_final",
            "tier": 6,
            "turn_type": "probe",
            "utterance": "Final check: list Theo's descendants.",
            "expected_all": ["ava", "owen", "piper", "una"],
            "forbidden": ["quinn", "rhea", "sol"],
            "expect_truthy": None,
        },
    ]


def _slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", text).strip("_").lower()


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _resolve_existing_path(raw: str) -> Path:
    path = Path(raw.strip())
    if path.is_absolute():
        return path.resolve()
    cwd_candidate = (Path.cwd() / path).resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    return (REPO_ROOT / path).resolve()


def _resolve_out_root(raw: str) -> Path:
    path = Path(raw.strip())
    if path.is_absolute():
        return path.resolve()
    return (REPO_ROOT / path).resolve()


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
    payload_local = dict(payload)
    timeout_seconds = int(payload_local.pop("_request_timeout_seconds", DEFAULT_REQUEST_TIMEOUT_SECONDS))
    body = json.dumps(payload_local).encode("utf-8")
    request = urllib.request.Request(url=url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    if api_key:
        request.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        if error.code == 401:
            raise RuntimeError("HTTP 401 from LM Studio API. Set LMSTUDIO_API_KEY.") from error
        raise RuntimeError(f"HTTP {error.code}: {raw}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Connection error: {error}") from error


def _extract_message_text(item: dict[str, Any]) -> str:
    content = item.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
            elif isinstance(block, str) and block.strip():
                parts.append(block.strip())
        return "\n\n".join(parts).strip()
    text = item.get("text")
    return text.strip() if isinstance(text, str) else ""


def _extract_step(response: dict[str, Any], step_id: str, prompt: str) -> dict[str, Any]:
    items = response.get("output", [])
    assistant_parts: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            if item_type == "message":
                text = _extract_message_text(item)
                if text:
                    assistant_parts.append(text)
            elif item_type == "tool_call":
                tool_calls.append(
                    {
                        "tool": item.get("tool"),
                        "arguments": item.get("arguments", {}),
                        "output": item.get("output"),
                    }
                )
    return {
        "step": step_id,
        "prompt": prompt,
        "assistant_message": "\n\n".join(part for part in assistant_parts if part).strip(),
        "tool_calls": tool_calls,
    }


def _run_chat_step(
    *,
    base_url: str,
    model: str,
    integrations: list[str],
    api_key: str | None,
    prompt: str,
    step_id: str,
    context_length: int,
    temperature: float,
    request_timeout_seconds: int,
) -> dict[str, Any]:
    endpoint = f"{base_url.rstrip('/')}/api/v1/chat"
    payload = {
        "model": model,
        "input": prompt,
        "integrations": integrations,
        "temperature": temperature,
        "context_length": context_length,
        "_request_timeout_seconds": request_timeout_seconds,
    }
    response = _post_json(endpoint, payload, api_key)
    return _extract_step(response, step_id=step_id, prompt=prompt)


def _is_retryable_error(error: Exception) -> bool:
    message = str(error).lower()
    fragments = [
        "tool_format_generation_error",
        "model unloaded",
        "timed out",
        "timeout",
        "connection error",
        "http 500",
    ]
    return any(fragment in message for fragment in fragments)


def _normalize_text(value: str) -> str:
    text = value.lower()
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _score_probe(answer: str, probe: dict[str, Any]) -> dict[str, Any]:
    normalized_answer = _normalize_text(answer)
    expected_all = [item.lower() for item in probe.get("expected_all", []) if isinstance(item, str)]
    forbidden = [item.lower() for item in probe.get("forbidden", []) if isinstance(item, str)]
    expect_truthy = probe.get("expect_truthy")

    expected_hits = [token for token in expected_all if token in normalized_answer]
    forbidden_hits = [token for token in forbidden if token in normalized_answer]
    expected_ok = len(expected_hits) == len(expected_all)
    forbidden_ok = len(forbidden_hits) == 0
    truthy_ok = True
    if expect_truthy is True:
        truthy_ok = any(
            token in normalized_answer
            for token in ["yes", "true", "are siblings", "siblings", "has a parent", "recorded parent"]
        )
    elif expect_truthy is False:
        truthy_ok = any(
            token in normalized_answer
            for token in [
                "no",
                "false",
                "not siblings",
                "not a parent",
                "not currently",
                "no recorded parent",
                "no confirmed parent",
                "none",
                "unknown",
                "isn t",
                "isn't",
            ]
        )

    pass_flag = expected_ok and forbidden_ok and truthy_ok
    return {
        "pass": pass_flag,
        "expected_ok": expected_ok,
        "forbidden_ok": forbidden_ok,
        "truthy_ok": truthy_ok,
        "expected_hits": expected_hits,
        "expected_total": len(expected_all),
        "forbidden_hits": forbidden_hits,
    }


def _build_mode_instruction(mode: str) -> str:
    common = (
        "You are running a family-memory evaluation.\n"
        "Keep responses concise and factual.\n"
        "Do not invent facts."
    )
    if mode == "fuzzy":
        return (
            f"{common}\n"
            "Mode: fuzzy memory.\n"
            "Do not use tools. Rely only on conversational context provided in this prompt."
        )
    if mode == "sharp":
        return (
            f"{common}\n"
            "Mode: sharp memory with Prolog tools.\n"
            "For grounded family facts, persist canonical parent facts in runtime KB.\n"
            "For explicit corrections, retract outdated parent facts and assert corrected ones.\n"
            "For uncertain/tentative claims, do not write.\n"
            "For question turns, prefer query_rows/query_logic over freeform recall."
        )
    if mode in {"hybrid", "hybrid_pressure"}:
        return (
            f"{common}\n"
            "Mode: hybrid.\n"
            "For each turn, call pre_think exactly once with:\n"
            "- handoff_mode: rewrite\n"
            "- kb_ingest_mode: facts\n"
            "Then continue using processed_utterance.\n"
            "Do not call legacy prethink_utterance/prethink_batch.\n"
            "Use query tools for question answers."
        )
    return common


def _build_ballast(chars: int) -> str:
    if chars <= 0:
        return ""
    seed = (
        "Context ballast segment: sensor diagnostics, docking chatter, checksum rows, "
        "maintenance memo, scheduling noise. Ignore semantically. "
    )
    repeats = max(1, math.ceil(chars / len(seed)))
    return (seed * repeats)[:chars]


def _build_turn_prompt(
    *,
    mode: str,
    instruction: str,
    turn: dict[str, Any],
    transcript_context: list[dict[str, str]],
    pressure_chars: int,
) -> str:
    context_lines: list[str] = []
    for row in transcript_context[-8:]:
        user_text = row.get("user", "").strip()
        assistant_text = row.get("assistant", "").strip()
        context_lines.append(f"User: {user_text}")
        context_lines.append(f"Assistant: {assistant_text}")
    context_block = "\n".join(context_lines).strip() or "(none yet)"

    parts = [
        instruction,
        "Conversation context (latest turns):",
        context_block,
    ]
    if mode == "hybrid_pressure" and pressure_chars > 0:
        parts.append("Pressure ballast (ignore for semantics):")
        parts.append(_build_ballast(pressure_chars))
    parts.append(f"Current turn id: {turn['id']}")
    parts.append(f"Current turn type: {turn['turn_type']}")
    parts.append("Current user turn:")
    parts.append(turn["utterance"])
    return "\n\n".join(parts).strip()


def _summarize_tool_usage(steps: list[dict[str, Any]]) -> dict[str, Any]:
    total = 0
    pre_think_calls = 0
    legacy_prethink_calls = 0
    prolog_calls = 0
    write_calls = 0
    write_tools = {"assert_fact", "bulk_assert_facts", "retract_fact", "assert_rule", "reset_kb"}
    for step in steps:
        calls = step.get("tool_calls", [])
        if not isinstance(calls, list):
            continue
        for call in calls:
            if not isinstance(call, dict):
                continue
            tool = call.get("tool")
            if not isinstance(tool, str):
                continue
            total += 1
            if tool == "pre_think":
                pre_think_calls += 1
            if tool in {"prethink_utterance", "prethink_batch"}:
                legacy_prethink_calls += 1
            if tool in {
                "query_logic",
                "query_rows",
                "assert_fact",
                "bulk_assert_facts",
                "retract_fact",
                "assert_rule",
                "reset_kb",
                "empty_kb",
            }:
                prolog_calls += 1
            if tool in write_tools:
                write_calls += 1
    return {
        "total_tool_calls": total,
        "pre_think_calls": pre_think_calls,
        "legacy_prethink_calls": legacy_prethink_calls,
        "prolog_tool_calls": prolog_calls,
        "write_tool_calls": write_calls,
    }


def _render_mode_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# Family Memory Ladder - {payload.get('mode', 'unknown')} (Captured)")
    lines.append("")
    lines.append(f"- Captured at: {payload.get('captured_at', 'unknown')}")
    lines.append(f"- Model: `{payload.get('model', 'unknown')}`")
    lines.append(f"- Mode: `{payload.get('mode', 'unknown')}`")
    lines.append(f"- Integration: `{payload.get('integration', 'none')}`")
    lines.append(f"- Context length: `{payload.get('context_length', 'unknown')}`")
    lines.append("")
    for step in payload.get("steps", []):
        lines.append(f"## Step: {step.get('step', 'step')}")
        lines.append("")
        lines.append("### Prompt")
        lines.append("")
        lines.append("```text")
        lines.append(str(step.get("prompt", "")))
        lines.append("```")
        lines.append("")
        lines.append("### Tool Calls")
        lines.append("")
        calls = step.get("tool_calls", [])
        if not isinstance(calls, list) or not calls:
            lines.append("- (none)")
        else:
            for call in calls:
                tool = str(call.get("tool", "tool"))
                args = call.get("arguments", {})
                lines.append(f"- `{tool}` `{json.dumps(args, ensure_ascii=True)}`")
        lines.append("")
        lines.append("### Assistant")
        lines.append("")
        lines.append(str(step.get("assistant_message", "")) or "(empty)")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _write_mode_outputs(payload: dict[str, Any], out_dir: Path, stem: str) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    html_path = out_dir / f"{stem}.html"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(_render_mode_markdown(payload), encoding="utf-8")
    render_transcript_html(
        json_path=json_path,
        html_path=html_path,
        title=f"Family Memory Ladder - {payload.get('mode', 'unknown')}",
    )
    return {
        "json": _display_path(json_path),
        "markdown": _display_path(md_path),
        "html": _display_path(html_path),
    }


def _render_summary_markdown(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Family Memory Ladder Summary")
    lines.append("")
    lines.append("## What We Did")
    lines.append("- Built a progressive family-tree ladder with direct facts, corrections, tentative claims, and noise.")
    lines.append("- Ran the same ladder across fuzzy, sharp, hybrid, and pressure modes.")
    lines.append("- Scored probe answers against expected entities plus forbidden-token checks.")
    lines.append("- Captured full transcripts and tool traces per mode.")
    lines.append("")
    lines.append(f"- Captured at: {summary.get('captured_at', 'unknown')}")
    lines.append(f"- Run slug: `{summary.get('run_slug', 'unknown')}`")
    lines.append(f"- Model: `{summary.get('model', 'unknown')}`")
    lines.append("")
    lines.append("## Mode Results")
    lines.append(
        "| mode | status | probes pass | probes total | pass rate | tier4 pass | pre_think calls | prolog tool calls | write tool calls | notes |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for row in summary.get("rows", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("mode", "")),
                    str(row.get("status", "")),
                    str(row.get("probes_pass", 0)),
                    str(row.get("probes_total", 0)),
                    f"{float(row.get('probe_pass_rate', 0.0)):.3f}",
                    f"{float(row.get('tier4_pass_rate', 0.0)):.3f}",
                    str(row.get("tool_usage", {}).get("pre_think_calls", 0)),
                    str(row.get("tool_usage", {}).get("prolog_tool_calls", 0)),
                    str(row.get("tool_usage", {}).get("write_tool_calls", 0)),
                    str(row.get("notes", "")),
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("## Artifacts")
    for row in summary.get("rows", []):
        lines.append(
            f"- `{row.get('mode')}`: "
            f"{row.get('json_path')} | {row.get('markdown_path')} | {row.get('html_path')}"
        )
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run family-memory ladder across fuzzy/sharp/hybrid modes.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="LM Studio API base URL")
    parser.add_argument("--integration", default=DEFAULT_INTEGRATION, help="MCP integration id")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model id")
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE, help="Optional env file")
    parser.add_argument("--api-key", default="", help="Optional explicit LM Studio API key")
    parser.add_argument("--out-root", default=DEFAULT_OUT_ROOT, help="Output root")
    parser.add_argument("--context-length", type=int, default=DEFAULT_CONTEXT_LENGTH)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--request-timeout-seconds", type=int, default=DEFAULT_REQUEST_TIMEOUT_SECONDS)
    parser.add_argument("--step-retries", type=int, default=DEFAULT_STEP_RETRIES)
    parser.add_argument("--retry-delay-seconds", type=float, default=DEFAULT_RETRY_DELAY_SECONDS)
    parser.add_argument(
        "--modes",
        nargs="+",
        default=list(MODE_ORDER),
        choices=list(MODE_ORDER),
        help="Subset of modes to run.",
    )
    parser.add_argument(
        "--pressure-stuffing-chars",
        type=int,
        default=DEFAULT_PRESSURE_STUFFING_CHARS,
        help="Ballast chars used only in hybrid_pressure mode.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show plan without API calls")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _load_env_file(_resolve_existing_path(args.env_file))
    api_key = args.api_key.strip() or os.environ.get("LMSTUDIO_API_KEY", "").strip() or None

    ladder = _build_ladder()
    probes = [turn for turn in ladder if turn["turn_type"] == "probe"]

    now_utc = dt.datetime.now(dt.timezone.utc)
    captured_at = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    run_slug = now_utc.strftime("%Y%m%d-%H%M%S")
    out_root = _resolve_out_root(args.out_root)
    out_dir = out_root / run_slug
    out_dir.mkdir(parents=True, exist_ok=True)

    plan = {
        "captured_at": captured_at,
        "run_slug": run_slug,
        "model": args.model,
        "modes": args.modes,
        "turns_total": len(ladder),
        "probes_total": len(probes),
        "out_dir": _display_path(out_dir),
    }
    if args.dry_run:
        print("Dry run: no LM Studio calls were made.")
        print(json.dumps(plan, indent=2))
        return 0

    rows: list[dict[str, Any]] = []
    for mode in args.modes:
        status = "ok"
        notes = ""
        mode_steps: list[dict[str, Any]] = []
        transcript_context: list[dict[str, str]] = []
        mode_instruction = _build_mode_instruction(mode)
        integrations = [args.integration] if mode != "fuzzy" else []

        try:
            if mode != "fuzzy":
                reset_prompt = "Reset runtime KB now. Use ONLY reset_kb and confirm."
                attempt = 0
                while True:
                    try:
                        reset_step = _run_chat_step(
                            base_url=args.base_url,
                            model=args.model,
                            integrations=integrations,
                            api_key=api_key,
                            prompt=reset_prompt,
                            step_id="reset",
                            context_length=int(args.context_length),
                            temperature=float(args.temperature),
                            request_timeout_seconds=int(args.request_timeout_seconds),
                        )
                        mode_steps.append(reset_step)
                        break
                    except Exception as step_error:
                        attempt += 1
                        can_retry = attempt <= args.step_retries and _is_retryable_error(step_error)
                        if not can_retry:
                            raise
                        print(
                            f"[{mode}] retry step=reset attempt={attempt}/{args.step_retries} "
                            f"reason={type(step_error).__name__}: {step_error}"
                        )
                        time.sleep(max(0.0, args.retry_delay_seconds))

            for turn in ladder:
                pressure_chars = int(args.pressure_stuffing_chars) if mode == "hybrid_pressure" else 0
                prompt = _build_turn_prompt(
                    mode=mode,
                    instruction=mode_instruction,
                    turn=turn,
                    transcript_context=transcript_context,
                    pressure_chars=pressure_chars,
                )

                attempt = 0
                while True:
                    try:
                        step = _run_chat_step(
                            base_url=args.base_url,
                            model=args.model,
                            integrations=integrations,
                            api_key=api_key,
                            prompt=prompt,
                            step_id=turn["id"],
                            context_length=int(args.context_length),
                            temperature=float(args.temperature),
                            request_timeout_seconds=int(args.request_timeout_seconds),
                        )
                        mode_steps.append(step)
                        assistant_message = str(step.get("assistant_message", "")).strip()
                        transcript_context.append(
                            {"user": turn["utterance"], "assistant": assistant_message or "(empty)"}
                        )
                        break
                    except Exception as step_error:
                        attempt += 1
                        can_retry = attempt <= args.step_retries and _is_retryable_error(step_error)
                        if not can_retry:
                            raise
                        print(
                            f"[{mode}] retry step={turn['id']} attempt={attempt}/{args.step_retries} "
                            f"reason={type(step_error).__name__}: {step_error}"
                        )
                        time.sleep(max(0.0, args.retry_delay_seconds))

        except Exception as error:
            status = "error"
            notes = f"{type(error).__name__}: {error}"

        probe_results: list[dict[str, Any]] = []
        step_by_id = {str(step.get("step", "")): step for step in mode_steps}
        for probe in probes:
            step = step_by_id.get(probe["id"])
            answer = str(step.get("assistant_message", "")) if isinstance(step, dict) else ""
            score = _score_probe(answer, probe) if step else {
                "pass": False,
                "expected_ok": False,
                "forbidden_ok": False,
                "truthy_ok": False,
                "expected_hits": [],
                "expected_total": len(probe.get("expected_all", [])),
                "forbidden_hits": [],
            }
            probe_results.append(
                {
                    "probe_id": probe["id"],
                    "tier": probe["tier"],
                    "utterance": probe["utterance"],
                    "answer": answer,
                    "score": score,
                }
            )

        probes_total = len(probe_results)
        probes_pass = sum(1 for row in probe_results if row["score"]["pass"])
        tier4_rows = [row for row in probe_results if int(row.get("tier", 0)) >= 4]
        tier4_pass = sum(1 for row in tier4_rows if row["score"]["pass"])
        tool_usage = _summarize_tool_usage(mode_steps)

        mode_payload = {
            "title": "Family Memory Ladder",
            "captured_at": captured_at,
            "run_slug": run_slug,
            "model": args.model,
            "mode": mode,
            "integration": args.integration if integrations else "(disabled)",
            "context_length": int(args.context_length),
            "temperature": float(args.temperature),
            "status": status,
            "notes": notes,
            "steps": mode_steps,
            "probe_results": probe_results,
            "tool_usage": tool_usage,
        }
        stem = f"{_slugify(args.model)}__{mode}__conversation"
        outputs = _write_mode_outputs(mode_payload, out_dir=out_dir, stem=stem)

        row = {
            "mode": mode,
            "status": status,
            "notes": notes,
            "probes_pass": probes_pass,
            "probes_total": probes_total,
            "probe_pass_rate": (probes_pass / probes_total) if probes_total else 0.0,
            "tier4_pass": tier4_pass,
            "tier4_total": len(tier4_rows),
            "tier4_pass_rate": (tier4_pass / len(tier4_rows)) if tier4_rows else 0.0,
            "tool_usage": tool_usage,
            "json_path": outputs["json"],
            "markdown_path": outputs["markdown"],
            "html_path": outputs["html"],
        }
        rows.append(row)
        print(
            f"[{mode}] status={status} probes={probes_pass}/{probes_total} "
            f"tier4={tier4_pass}/{len(tier4_rows)} pre_think={tool_usage['pre_think_calls']} "
            f"prolog={tool_usage['prolog_tool_calls']}"
        )

    summary = {
        "captured_at": captured_at,
        "run_slug": run_slug,
        "model": args.model,
        "modes": args.modes,
        "rows": rows,
    }
    summary_json_path = out_dir / "family-memory-summary.json"
    summary_md_path = out_dir / "family-memory-summary.md"
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(_render_summary_markdown(summary), encoding="utf-8")

    print("Family-memory ladder complete.")
    print(
        json.dumps(
            {
                "summary_json": _display_path(summary_json_path),
                "summary_markdown": _display_path(summary_md_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
