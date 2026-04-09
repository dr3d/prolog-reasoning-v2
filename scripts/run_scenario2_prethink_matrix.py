#!/usr/bin/env python3
"""
Run Scenario-2 with a pre-think A/B stress matrix and lightweight grading.

Matrix rows per model:
1) baseline_off  -> no pre_think tool usage requested
2) baseline_on   -> pre_think required before each non-reset turn
3) stuffed_off   -> heavy prompt ballast, pre_think disabled
4) stuffed_on    -> heavy prompt ballast, pre_think required

Outputs:
- per-run JSON transcript
- per-run Markdown transcript
- matrix-summary JSON + Markdown
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
DEFAULT_ENV_FILE = ".env.local"
DEFAULT_SCENARIO_FILE = "docs/research/scenarios/scenario-2.md"
DEFAULT_OUT_ROOT = "docs/research/conversations"
DEFAULT_MODELS = [
    "qwen3.5-4b",
    "qwen/qwen3.5-9b",
]
DEFAULT_NORMAL_CONTEXT_LENGTH = 4000
DEFAULT_STUFFED_CONTEXT_LENGTH = 4000
DEFAULT_STUFFING_CHARS = 24000
DEFAULT_TEMPERATURE = 0.0
DEFAULT_REQUEST_TIMEOUT_SECONDS = 300
DEFAULT_PRE_THINK_HANDOFF_MODE = "process"
DEFAULT_STEP_RETRIES = 2
DEFAULT_RETRY_DELAY_SECONDS = 3.0

DEFAULT_RESET_PROMPT = "Reset runtime KB now. Use ONLY reset_kb and confirm."
DEFAULT_INGESTION_PREFIX = (
    "You are operating with MCP tools enabled.\n"
    "Task: build a runtime knowledge base from the scenario below.\n"
    "Store grounded facts/rules only. Avoid unsupported inventions.\n"
    "After ingestion, confirm what you persisted."
)

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "by",
    "does",
    "for",
    "from",
    "has",
    "have",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "there",
    "this",
    "to",
    "was",
    "were",
    "with",
}

PROLOG_TOOL_NAMES = {
    "query_logic",
    "query_rows",
    "assert_fact",
    "bulk_assert_facts",
    "retract_fact",
    "assert_rule",
    "reset_kb",
    "kb_empty",
    "list_known_facts",
    "explain_error",
    "classify_statement",
}


def _slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", text).strip("_").lower()


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _resolve_existing_path(raw: str) -> Path:
    value = raw.strip()
    path = Path(value)
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
    request_timeout_seconds = int(
        payload_local.pop("_request_timeout_seconds", DEFAULT_REQUEST_TIMEOUT_SECONDS)
    )
    body = json.dumps(payload_local).encode("utf-8")
    request = urllib.request.Request(url=url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    if api_key:
        request.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(request, timeout=request_timeout_seconds) as response:
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
            if item.get("type") == "message":
                text = _extract_message_text(item)
                if text:
                    assistant_parts.append(text)
            elif item.get("type") == "tool_call":
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
    integration: str,
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
        "integrations": [integration],
        "temperature": temperature,
        "context_length": context_length,
        "_request_timeout_seconds": request_timeout_seconds,
    }
    response = _post_json(endpoint, payload, api_key)
    return _extract_step(response, step_id=step_id, prompt=prompt)


def _is_retryable_error(error: Exception) -> bool:
    message = str(error).lower()
    retryable_fragments = [
        "tool_format_generation_error",
        "model unloaded",
        "timed out",
        "timeout",
        "connection error",
        "http 500",
    ]
    return any(fragment in message for fragment in retryable_fragments)


def _extract_section(markdown: str, section_num: int, next_section_num: int) -> str:
    start_match = re.search(rf"(?m)^##\s*{section_num}\)[^\n]*\n", markdown)
    if not start_match:
        return ""
    start_idx = start_match.end()
    end_match = re.search(rf"(?m)^##\s*{next_section_num}\)[^\n]*\n", markdown[start_idx:])
    end_idx = start_idx + end_match.start() if end_match else len(markdown)
    section = markdown[start_idx:end_idx].strip()
    return re.sub(r"^\s*---\s*", "", section, count=1).strip()


def _extract_title_from_markdown(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            if title:
                return title
    return fallback


def _parse_question_battery(markdown: str) -> list[dict[str, Any]]:
    section7 = _extract_section(markdown, section_num=7, next_section_num=8)
    if not section7:
        return []
    pattern = re.compile(r"(?m)^####\s+(Q[^\n]+)\s*$")
    matches = list(pattern.finditer(section7))
    questions: list[dict[str, Any]] = []
    for index, match in enumerate(matches, start=1):
        qid = match.group(1).strip()
        start = match.end()
        end = matches[index].start() if index < len(matches) else len(section7)
        block = section7[start:end]
        prompt_match = re.search(r'\*\*Prompt(?: [AB])?:\*\*\s*"(.+?)"\s*$', block, re.MULTILINE)
        expected_match = re.search(r"(?ms)\*\*Expected:\*\*\s*(.+)$", block)
        prompt = prompt_match.group(1).strip() if prompt_match else ""
        expected_block = expected_match.group(1).strip() if expected_match else ""
        expected_lines: list[str] = []
        for raw_line in expected_block.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#### ") or line.startswith("### "):
                continue
            if line.startswith("- "):
                expected_lines.append(line[2:].strip())
        if prompt:
            questions.append(
                {
                    "index": index,
                    "id": qid,
                    "step_id": f"q{index:02d}",
                    "prompt": prompt,
                    "expected": expected_lines,
                }
            )
    return questions


def _normalize_text(value: str) -> str:
    text = value.lower()
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokens(value: str) -> list[str]:
    return [token for token in _normalize_text(value).split() if token]


def _token_hit_score(expected_line: str, response_text: str) -> float:
    expected_tokens = [
        token
        for token in _tokens(expected_line)
        if token not in STOP_WORDS and len(token) > 1
    ]
    if not expected_tokens:
        return 1.0
    response_tokens = set(_tokens(response_text))
    if not response_tokens:
        return 0.0
    hits = sum(1 for token in expected_tokens if token in response_tokens)
    return hits / len(expected_tokens)


def _grade_answer(response_text: str, expected_lines: list[str]) -> dict[str, Any]:
    normalized_response = _normalize_text(response_text)
    matches: list[dict[str, Any]] = []
    for line in expected_lines:
        normalized_line = _normalize_text(line)
        substring_match = bool(normalized_line) and normalized_line in normalized_response
        score = _token_hit_score(line, response_text)
        matched = substring_match or score >= 0.55
        matches.append(
            {
                "expected_line": line,
                "matched": matched,
                "token_hit_score": round(score, 4),
            }
        )
    total = len(matches)
    matched_count = sum(1 for item in matches if item["matched"])
    line_recall = (matched_count / total) if total else 0.0
    return {
        "expected_lines_total": total,
        "matched_lines": matched_count,
        "line_recall": round(line_recall, 4),
        "matches": matches,
    }


def _build_ballast(chars: int) -> str:
    if chars <= 0:
        return ""
    seed = (
        "Ballast block for context pressure testing only. "
        "Ignore this block for task semantics. "
        "Token ballast sequence. "
    )
    repeats = max(1, math.ceil(chars / len(seed)))
    text = (seed * repeats)[:chars]
    return text


def _compose_prompt(
    *,
    raw_prompt: str,
    require_pre_think: bool,
    stuffing_chars: int,
    pre_think_handoff_mode: str,
    pre_think_kb_ingest_mode: str,
) -> str:
    if require_pre_think:
        ingest_instruction = (
            "Pass argument `kb_ingest_mode` with value `facts` in that tool call.\n"
            if pre_think_kb_ingest_mode == "facts"
            else ""
        )
        if pre_think_handoff_mode == "verbatim_say":
            mode_header = (
                "Run mode: pre-think REQUIRED.\n"
                "Call tool `pre_think` exactly once using the full raw utterance below.\n"
                "Pass argument `handoff_mode` with value `answer_proxy` in that tool call.\n"
                f"{ingest_instruction}"
                "After the tool returns, output ONLY the returned `processed_utterance` verbatim.\n"
                "Do not reinterpret it. Do not add commentary. Do not call any other tools.\n"
                "Do not call legacy `prethink_utterance` or `prethink_batch`."
            )
        else:
            mode_header = (
                "Run mode: pre-think REQUIRED.\n"
                "Before answering, call tool `pre_think` exactly once using the full raw utterance below.\n"
                f"{ingest_instruction}"
                "Then continue using the returned `processed_utterance` as the working utterance.\n"
                "Do not call legacy `prethink_utterance` or `prethink_batch`."
            )
    else:
        mode_header = (
            "Run mode: pre-think DISABLED. "
            "Do not call `pre_think`, `prethink_utterance`, or `prethink_batch`."
        )
    parts = [mode_header]
    if stuffing_chars > 0:
        parts.append("Context ballast (ignore for semantics):")
        parts.append(_build_ballast(stuffing_chars))
    parts.append("Raw user utterance:")
    parts.append(raw_prompt)
    return "\n\n".join(parts).strip()


def _render_markdown_transcript(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# {payload.get('title', 'Scenario Run')} (Captured)")
    lines.append("")
    lines.append(f"- Captured at: {payload.get('captured_at', 'unknown')}")
    lines.append(f"- Model: `{payload.get('model', 'unknown')}`")
    lines.append(f"- Condition: `{payload.get('condition_id', 'unknown')}`")
    lines.append(f"- Integration: `{payload.get('integration', 'unknown')}`")
    lines.append(f"- Source file: `{payload.get('source_path', 'unknown')}`")
    lines.append(f"- Context length: `{payload.get('context_length', 'unknown')}`")
    lines.append(f"- Stuffing chars: `{payload.get('stuffing_chars', 0)}`")
    lines.append("")
    for step in payload.get("steps", []):
        step_name = str(step.get("step", "step"))
        prompt = str(step.get("prompt", ""))
        assistant_message = str(step.get("assistant_message", "")) or "(empty reply)"
        tool_calls = step.get("tool_calls", [])
        lines.append(f"## Step: {step_name}")
        lines.append("")
        lines.append("### User Prompt")
        lines.append("")
        lines.append("```text")
        lines.append(prompt)
        lines.append("```")
        lines.append("")
        lines.append("### Tool Calls")
        lines.append("")
        if not isinstance(tool_calls, list) or not tool_calls:
            lines.append("- (none)")
        else:
            for call in tool_calls:
                if not isinstance(call, dict):
                    continue
                tool_name = str(call.get("tool", "tool"))
                arguments = call.get("arguments", {})
                lines.append(f"- `{tool_name}` `{json.dumps(arguments, ensure_ascii=True)}`")
        lines.append("")
        lines.append("### Assistant Reply")
        lines.append("")
        lines.append(assistant_message)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _write_run_outputs(payload: dict[str, Any], out_dir: Path, stem: str) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    html_path = out_dir / f"{stem}.html"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown_transcript(payload), encoding="utf-8")
    render_transcript_html(
        json_path=json_path,
        html_path=html_path,
        title=str(payload.get("title", "Scenario Run")),
    )
    return {
        "json": _display_path(json_path),
        "markdown": _display_path(md_path),
        "html": _display_path(html_path),
    }


def _extract_tool_name(call: Any) -> str:
    if isinstance(call, dict):
        tool = call.get("tool")
        if isinstance(tool, str):
            return tool
    return ""


def _summarize_tools(steps: list[dict[str, Any]]) -> dict[str, Any]:
    non_reset_steps = [step for step in steps if step.get("step") != "reset"]
    pre_think_steps = 0
    legacy_prethink_calls = 0
    prolog_tool_calls = 0
    total_tool_calls = 0
    for step in non_reset_steps:
        calls = step.get("tool_calls", [])
        if not isinstance(calls, list):
            continue
        step_used_pre_think = False
        for call in calls:
            tool = _extract_tool_name(call)
            if not tool:
                continue
            total_tool_calls += 1
            if tool == "pre_think":
                step_used_pre_think = True
            if tool in {"prethink_utterance", "prethink_batch"}:
                legacy_prethink_calls += 1
            if tool in PROLOG_TOOL_NAMES:
                prolog_tool_calls += 1
        if step_used_pre_think:
            pre_think_steps += 1
    pre_think_coverage = (
        pre_think_steps / len(non_reset_steps) if non_reset_steps else 0.0
    )
    return {
        "non_reset_steps": len(non_reset_steps),
        "pre_think_steps": pre_think_steps,
        "pre_think_coverage": round(pre_think_coverage, 4),
        "legacy_prethink_calls": legacy_prethink_calls,
        "prolog_tool_calls": prolog_tool_calls,
        "total_tool_calls": total_tool_calls,
    }


def _render_matrix_markdown(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Scenario-2 Pre-Think Matrix Summary")
    lines.append("")
    lines.append(f"- Captured at: {summary.get('captured_at', 'unknown')}")
    lines.append(f"- Run slug: `{summary.get('run_slug', 'unknown')}`")
    lines.append(f"- Scenario: `{summary.get('scenario_path', 'unknown')}`")
    lines.append(f"- Integration: `{summary.get('integration', 'unknown')}`")
    lines.append("")
    lines.append(
        "| model | condition | status | question avg recall | q>=0.70 | pre_think coverage | "
        "legacy prethink calls | prolog tool calls | total tool calls | json | markdown | html | notes |"
    )
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---|---|")
    for row in summary.get("rows", []):
        grade = row.get("grade", {})
        tools = row.get("tool_summary", {})
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("model", "")),
                    str(row.get("condition_id", "")),
                    str(row.get("status", "")),
                    f"{float(grade.get('average_line_recall', 0.0)):.3f}",
                    str(grade.get("questions_meeting_threshold", 0)),
                    f"{float(tools.get('pre_think_coverage', 0.0)):.3f}",
                    str(tools.get("legacy_prethink_calls", 0)),
                    str(tools.get("prolog_tool_calls", 0)),
                    str(tools.get("total_tool_calls", 0)),
                    str(row.get("json_path", "")),
                    str(row.get("markdown_path", "")),
                    str(row.get("html_path", "")),
                    str(row.get("notes", "")),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Scenario-2 pre-think A/B matrix with lightweight grading."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="LM Studio API base URL")
    parser.add_argument("--integration", default=DEFAULT_INTEGRATION, help="MCP integration id")
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE, help="Optional env file")
    parser.add_argument("--api-key", default="", help="Optional explicit LM Studio API key")
    parser.add_argument(
        "--scenario-file",
        default=DEFAULT_SCENARIO_FILE,
        help="Scenario markdown path (expects section 6 story + section 7 question battery).",
    )
    parser.add_argument("--out-root", default=DEFAULT_OUT_ROOT, help="Artifact output root")
    parser.add_argument(
        "--models",
        nargs="+",
        default=list(DEFAULT_MODELS),
        help="Model list to run.",
    )
    parser.add_argument(
        "--normal-context-length",
        type=int,
        default=DEFAULT_NORMAL_CONTEXT_LENGTH,
        help="Context length for baseline_off and baseline_on.",
    )
    parser.add_argument(
        "--stuffed-context-length",
        type=int,
        default=DEFAULT_STUFFED_CONTEXT_LENGTH,
        help="Context length for stuffed_off and stuffed_on.",
    )
    parser.add_argument(
        "--stuffing-chars",
        type=int,
        default=DEFAULT_STUFFING_CHARS,
        help="Prompt ballast characters for stuffed_* conditions.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help="Chat temperature.",
    )
    parser.add_argument(
        "--request-timeout-seconds",
        type=int,
        default=DEFAULT_REQUEST_TIMEOUT_SECONDS,
        help="Per-step request timeout in seconds.",
    )
    parser.add_argument(
        "--step-retries",
        type=int,
        default=DEFAULT_STEP_RETRIES,
        help="Retry count per step for transient LM Studio/tool-call failures.",
    )
    parser.add_argument(
        "--retry-delay-seconds",
        type=float,
        default=DEFAULT_RETRY_DELAY_SECONDS,
        help="Delay between per-step retries.",
    )
    parser.add_argument(
        "--conditions",
        nargs="+",
        default=["baseline_off", "baseline_on", "stuffed_off", "stuffed_on"],
        choices=["baseline_off", "baseline_on", "stuffed_off", "stuffed_on"],
        help="Subset of matrix conditions to run.",
    )
    parser.add_argument(
        "--question-threshold",
        type=float,
        default=0.70,
        help="Threshold used for q>=threshold count.",
    )
    parser.add_argument(
        "--max-questions",
        type=int,
        default=0,
        help="Limit number of question battery prompts after story ingestion (0 = all).",
    )
    parser.add_argument(
        "--question-ids",
        nargs="+",
        default=[],
        help="Optional specific question ids/step ids to run (for example Q1.1 Q2.1 q03).",
    )
    parser.add_argument(
        "--pre-think-handoff-mode",
        choices=["process", "verbatim_say"],
        default=DEFAULT_PRE_THINK_HANDOFF_MODE,
        help=(
            "When pre-think is enabled: "
            "`process` => model continues reasoning from processed utterance; "
            "`verbatim_say` => model outputs processed utterance verbatim."
        ),
    )
    parser.add_argument(
        "--pre-think-kb-ingest-mode",
        choices=["none", "facts"],
        default="none",
        help="When pre-think is enabled, request kb_ingest_mode for pre_think tool calls.",
    )
    parser.add_argument(
        "--pre-think-on-story",
        action="store_true",
        help="When set, pre-think is also required for the story_ingestion turn.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show matrix plan only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _load_env_file(_resolve_existing_path(args.env_file))
    api_key = args.api_key.strip() or os.environ.get("LMSTUDIO_API_KEY", "").strip() or None

    scenario_path = _resolve_existing_path(args.scenario_file)
    if not scenario_path.exists():
        raise FileNotFoundError(f"Scenario file not found: {scenario_path}")
    markdown = scenario_path.read_text(encoding="utf-8-sig")
    title = _extract_title_from_markdown(markdown, fallback=scenario_path.stem)
    story_section = _extract_section(markdown, section_num=6, next_section_num=7)
    questions = _parse_question_battery(markdown)
    if not story_section:
        raise ValueError("Scenario missing section 6 story block.")
    if not questions:
        raise ValueError("Scenario missing section 7 question battery.")

    selected_questions = list(questions)
    if args.question_ids:
        wanted = {item.strip().lower() for item in args.question_ids if item.strip()}
        selected_questions = [
            question
            for question in selected_questions
            if question["id"].lower() in wanted or question["step_id"].lower() in wanted
        ]
        if not selected_questions:
            raise ValueError(
                "No matching questions found for --question-ids. "
                f"Available ids include: {[q['id'] for q in questions[:8]]} ..."
            )
    if args.max_questions and args.max_questions > 0:
        selected_questions = selected_questions[: args.max_questions]
    if not selected_questions:
        raise ValueError("Question selection resolved to zero prompts.")

    base_steps: list[dict[str, Any]] = [{"id": "reset", "raw_prompt": DEFAULT_RESET_PROMPT}]
    base_steps.append(
        {
            "id": "story_ingestion",
            "raw_prompt": f"{DEFAULT_INGESTION_PREFIX}\n\n{story_section}",
        }
    )
    for question in selected_questions:
        base_steps.append({"id": question["step_id"], "raw_prompt": question["prompt"]})

    condition_map = {
        "baseline_off": {
            "require_pre_think": False,
            "stuffing_chars": 0,
            "context_length": int(args.normal_context_length),
        },
        "baseline_on": {
            "require_pre_think": True,
            "stuffing_chars": 0,
            "context_length": int(args.normal_context_length),
        },
        "stuffed_off": {
            "require_pre_think": False,
            "stuffing_chars": max(0, int(args.stuffing_chars)),
            "context_length": int(args.stuffed_context_length),
        },
        "stuffed_on": {
            "require_pre_think": True,
            "stuffing_chars": max(0, int(args.stuffing_chars)),
            "context_length": int(args.stuffed_context_length),
        },
    }

    now_utc = dt.datetime.now(dt.timezone.utc)
    run_slug = now_utc.strftime("%Y%m%d-%H%M%S")
    captured_at = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    out_root = _resolve_out_root(args.out_root)
    run_id = "scenario-2-prethink-matrix"
    out_dir = out_root / run_id / run_slug
    out_dir.mkdir(parents=True, exist_ok=True)

    matrix_plan = {
        "captured_at": captured_at,
        "run_slug": run_slug,
        "scenario_path": _display_path(scenario_path),
        "models": args.models,
        "conditions": args.conditions,
        "steps_total": len(base_steps),
        "questions_total": len(selected_questions),
        "questions_total_in_scenario": len(questions),
        "question_ids": [q["id"] for q in selected_questions],
        "pre_think_handoff_mode": args.pre_think_handoff_mode,
        "pre_think_kb_ingest_mode": args.pre_think_kb_ingest_mode,
        "pre_think_on_story": bool(args.pre_think_on_story),
        "out_dir": _display_path(out_dir),
    }
    if args.dry_run:
        print("Dry run: no LM Studio calls were made.")
        print(json.dumps(matrix_plan, indent=2))
        return 0

    rows: list[dict[str, Any]] = []
    question_by_step = {question["step_id"]: question for question in selected_questions}
    for model in args.models:
        for condition_id in args.conditions:
            cfg = condition_map[condition_id]
            require_pre_think = bool(cfg["require_pre_think"])
            stuffing_chars = int(cfg["stuffing_chars"])
            context_length = int(cfg["context_length"])
            steps_out: list[dict[str, Any]] = []
            notes = ""
            status = "ok"

            try:
                for step in base_steps:
                    step_id = step["id"]
                    raw_prompt = step["raw_prompt"]
                    if step_id == "reset":
                        prompt = raw_prompt
                    else:
                        require_pre_think_for_step = require_pre_think and (
                            step_id != "story_ingestion" or args.pre_think_on_story
                        )
                        prompt = _compose_prompt(
                            raw_prompt=raw_prompt,
                            require_pre_think=require_pre_think_for_step,
                            stuffing_chars=stuffing_chars,
                            pre_think_handoff_mode=args.pre_think_handoff_mode,
                            pre_think_kb_ingest_mode=args.pre_think_kb_ingest_mode,
                        )
                    attempt = 0
                    while True:
                        try:
                            steps_out.append(
                                _run_chat_step(
                                    base_url=args.base_url,
                                    model=model,
                                    integration=args.integration,
                                    api_key=api_key,
                                    prompt=prompt,
                                    step_id=step_id,
                                    context_length=context_length,
                                    temperature=float(args.temperature),
                                    request_timeout_seconds=int(args.request_timeout_seconds),
                                )
                            )
                            break
                        except Exception as step_error:
                            attempt += 1
                            can_retry = attempt <= args.step_retries and _is_retryable_error(step_error)
                            if not can_retry:
                                raise
                            print(
                                f"[{model} | {condition_id}] retry step={step_id} "
                                f"attempt={attempt}/{args.step_retries} "
                                f"reason={type(step_error).__name__}: {step_error}"
                            )
                            time.sleep(max(0.0, args.retry_delay_seconds))
            except Exception as error:
                status = "error"
                notes = f"{type(error).__name__}: {error}"

            graded_questions: list[dict[str, Any]] = []
            for step in steps_out:
                step_id = str(step.get("step", ""))
                question = question_by_step.get(step_id)
                if not question:
                    continue
                answer = str(step.get("assistant_message", ""))
                grade = _grade_answer(answer, list(question.get("expected", [])))
                graded_questions.append(
                    {
                        "question_id": question["id"],
                        "step_id": step_id,
                        "prompt": question["prompt"],
                        "grade": grade,
                    }
                )

            recalls = [
                float(item["grade"].get("line_recall", 0.0))
                for item in graded_questions
                if isinstance(item, dict)
            ]
            avg_recall = (sum(recalls) / len(recalls)) if recalls else 0.0
            threshold = float(args.question_threshold)
            q_threshold_hits = sum(1 for score in recalls if score >= threshold)

            tool_summary = _summarize_tools(steps_out)
            payload = {
                "title": title,
                "captured_at": captured_at,
                "run_slug": run_slug,
                "run_id": run_id,
                "model": model,
                "condition_id": condition_id,
                "require_pre_think": require_pre_think,
                "pre_think_on_story": bool(args.pre_think_on_story),
                "stuffing_chars": stuffing_chars,
                "pre_think_handoff_mode": args.pre_think_handoff_mode,
                "pre_think_kb_ingest_mode": args.pre_think_kb_ingest_mode,
                "integration": args.integration,
                "context_length": context_length,
                "temperature": float(args.temperature),
                "source_mode": "scenario_markdown",
                "source_path": _display_path(scenario_path),
                "status": status,
                "notes": notes,
                "steps": steps_out,
                "grade": {
                    "questions_total": len(graded_questions),
                    "average_line_recall": round(avg_recall, 4),
                    "question_threshold": threshold,
                    "questions_meeting_threshold": q_threshold_hits,
                    "per_question": graded_questions,
                },
                "tool_summary": tool_summary,
            }
            stem = f"{_slugify(model)}__{condition_id}__conversation"
            outputs = _write_run_outputs(payload, out_dir=out_dir, stem=stem)
            row = {
                "model": model,
                "condition_id": condition_id,
                "status": status,
                "notes": notes,
                "grade": payload["grade"],
                "tool_summary": tool_summary,
                "json_path": outputs["json"],
                "markdown_path": outputs["markdown"],
                "html_path": outputs["html"],
            }
            rows.append(row)
            print(
                f"[{model} | {condition_id}] status={status} "
                f"avg_recall={row['grade']['average_line_recall']} "
                f"q>=thr={row['grade']['questions_meeting_threshold']} "
                f"pre_think_coverage={tool_summary['pre_think_coverage']}"
            )

    summary = {
        "captured_at": captured_at,
        "run_slug": run_slug,
        "run_id": run_id,
        "scenario_path": _display_path(scenario_path),
        "integration": args.integration,
        "pre_think_handoff_mode": args.pre_think_handoff_mode,
        "pre_think_kb_ingest_mode": args.pre_think_kb_ingest_mode,
        "pre_think_on_story": bool(args.pre_think_on_story),
        "question_ids": [q["id"] for q in selected_questions],
        "rows": rows,
    }
    summary_json = out_dir / "matrix-summary.json"
    summary_md = out_dir / "matrix-summary.md"
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md.write_text(_render_matrix_markdown(summary), encoding="utf-8")

    print("Scenario-2 pre-think matrix complete.")
    print(
        json.dumps(
            {
                "summary_json": _display_path(summary_json),
                "summary_markdown": _display_path(summary_md),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
