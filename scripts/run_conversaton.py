#!/usr/bin/env python3
"""
Run a reusable conversation capture against LM Studio + MCP and emit:
- JSON transcript
- Markdown transcript
- HTML transcript

Input modes:
1) Scenario markdown (default), e.g. docs/research/scenarios/scenario-1.md
   - Uses section 6 for story input
   - Uses section 7 and optionally section 8 for prompts
2) JSON plan with a `steps` list, where each step has a `prompt`
   (and optional `id` / `step`)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import traceback
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
DEFAULT_BATTERY_MODELS = [
    "qwen3.5-4b",
    "qwen/qwen3.5-9b",
    "qwen3.5-27b@q4_k_m",
]
DEFAULT_ENV_FILE = ".env.local"
DEFAULT_CONVERSATION_FILE = "docs/research/scenarios/scenario-1.md"
DEFAULT_OUT_ROOT = "docs/research/conversations"
DEFAULT_CONTEXT_LENGTH = 8000
DEFAULT_TEMPERATURE = 0.0

DEFAULT_RESET_PROMPT = "Reset runtime KB now. Use ONLY reset_kb and confirm."
DEFAULT_INGESTION_PREFIX = (
    "You are operating with MCP tools enabled.\n"
    "Task: build a runtime knowledge base from the scenario below.\n"
    "Store grounded facts/rules only. Avoid unsupported inventions.\n"
    "After ingestion, confirm what you persisted."
)


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

    repo_candidate = (REPO_ROOT / path).resolve()
    if repo_candidate.exists():
        return repo_candidate

    return cwd_candidate


def _resolve_out_root(raw: str) -> Path:
    value = raw.strip()
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (REPO_ROOT / path).resolve()


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


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
        with urllib.request.urlopen(request, timeout=900) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        if error.code == 401:
            raise RuntimeError(
                "HTTP 401 from LM Studio API. Set LMSTUDIO_API_KEY or pass --api-key."
            ) from error
        if error.code == 400 and "plugin_connection_error" in raw:
            raise RuntimeError(
                "LM Studio MCP integration failed to stay up.\n"
                "Check mcp/prolog-reasoning integration health and retry.\n"
                f"Raw error: {raw}"
            ) from error
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
    if isinstance(text, str):
        return text.strip()
    return ""


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
                message_text = _extract_message_text(item)
                if message_text:
                    assistant_parts.append(message_text)
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
    integration: str,
    api_key: str | None,
    prompt: str,
    step_id: str,
    context_length: int,
    temperature: float,
) -> dict[str, Any]:
    endpoint = f"{base_url.rstrip('/')}/api/v1/chat"
    payload = {
        "model": model,
        "input": prompt,
        "integrations": [integration],
        "temperature": temperature,
        "context_length": context_length,
    }
    response = _post_json(endpoint, payload, api_key)
    return _extract_step(response, step_id=step_id, prompt=prompt)


def _extract_section(markdown: str, section_num: int, next_section_num: int) -> str:
    start_match = re.search(rf"(?m)^##\s*{section_num}\)[^\n]*\n", markdown)
    if not start_match:
        return ""
    start_idx = start_match.end()
    end_match = re.search(rf"(?m)^##\s*{next_section_num}\)[^\n]*\n", markdown[start_idx:])
    end_idx = start_idx + end_match.start() if end_match else len(markdown)
    section = markdown[start_idx:end_idx].strip()
    section = re.sub(r"^\s*---\s*", "", section, count=1)
    return section.strip()


def _extract_prompts(section_text: str) -> list[str]:
    prompts: list[str] = []
    for line in section_text.splitlines():
        stripped = line.strip()
        match = re.search(r'\*\*Prompt(?: [AB])?:\*\*\s*"(.+?)"\s*$', stripped)
        if match:
            prompt = match.group(1).strip()
            if prompt:
                prompts.append(prompt)
    return prompts


def _extract_title_from_markdown(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            if title:
                return title
    return fallback


def _build_plan_from_markdown(
    *,
    path: Path,
    markdown: str,
    skip_stress_prompts: bool,
    skip_reset: bool,
    skip_story_ingestion: bool,
) -> dict[str, Any]:
    title = _extract_title_from_markdown(markdown, fallback=path.stem)
    run_id = _slugify(path.stem)
    story_section = _extract_section(markdown, section_num=6, next_section_num=7)
    deep_section = _extract_section(markdown, section_num=7, next_section_num=8)
    stress_section = _extract_section(markdown, section_num=8, next_section_num=9)

    deep_prompts = _extract_prompts(deep_section)
    stress_prompts = [] if skip_stress_prompts else _extract_prompts(stress_section)
    prompts = deep_prompts + stress_prompts

    steps: list[dict[str, str]] = []
    if not skip_reset:
        steps.append({"id": "reset", "prompt": DEFAULT_RESET_PROMPT})

    if story_section and not skip_story_ingestion:
        story_prompt = f"{DEFAULT_INGESTION_PREFIX}\n\n{story_section}"
        steps.append({"id": "story_ingestion", "prompt": story_prompt})

    for index, prompt in enumerate(prompts, start=1):
        steps.append({"id": f"q{index:02d}", "prompt": prompt})

    if not steps:
        raise ValueError(
            f"No conversation steps extracted from markdown file: {path}. "
            "Expected sectioned scenario markdown or use JSON plan mode."
        )

    return {
        "title": title,
        "run_id": run_id,
        "source_mode": "scenario_markdown",
        "source_path": _display_path(path),
        "steps": steps,
    }


def _build_plan_from_json(
    *,
    path: Path,
    payload: dict[str, Any],
    prepend_reset: bool,
) -> dict[str, Any]:
    title_raw = _coerce_text(payload.get("title")).strip()
    run_id_raw = _coerce_text(payload.get("run_id")).strip()
    title = title_raw or path.stem
    run_id = _slugify(run_id_raw or path.stem)

    raw_steps = payload.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError(f"JSON plan requires non-empty 'steps' array: {path}")

    steps: list[dict[str, str]] = []
    if prepend_reset:
        steps.append({"id": "reset", "prompt": DEFAULT_RESET_PROMPT})

    for index, raw in enumerate(raw_steps, start=1):
        if isinstance(raw, str):
            prompt = raw.strip()
            step_id = f"turn_{index:02d}"
        elif isinstance(raw, dict):
            prompt = _coerce_text(raw.get("prompt") or raw.get("input")).strip()
            step_id = _coerce_text(raw.get("id") or raw.get("step")).strip() or f"turn_{index:02d}"
        else:
            continue

        if not prompt:
            continue
        steps.append({"id": _slugify(step_id) or f"turn_{index:02d}", "prompt": prompt})

    if not steps:
        raise ValueError(f"JSON plan had no usable prompt steps: {path}")

    return {
        "title": title,
        "run_id": run_id,
        "source_mode": "json_plan",
        "source_path": _display_path(path),
        "steps": steps,
    }


def _load_conversation_plan(args: argparse.Namespace, source_path: Path) -> dict[str, Any]:
    input_mode = args.input_mode
    if input_mode == "auto":
        input_mode = "json_plan" if source_path.suffix.lower() == ".json" else "scenario_markdown"

    if input_mode == "json_plan":
        payload = json.loads(source_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError(f"JSON plan must be an object: {source_path}")
        return _build_plan_from_json(
            path=source_path,
            payload=payload,
            prepend_reset=args.prepend_reset and not args.skip_reset,
        )

    markdown = source_path.read_text(encoding="utf-8-sig")
    return _build_plan_from_markdown(
        path=source_path,
        markdown=markdown,
        skip_stress_prompts=args.skip_stress_prompts,
        skip_reset=args.skip_reset,
        skip_story_ingestion=args.skip_story_ingestion,
    )


def _render_markdown_transcript(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# {payload.get('title', 'Conversation')} (Captured)")
    lines.append("")
    lines.append(f"- Captured at: {payload.get('captured_at', 'unknown')}")
    lines.append(f"- Model: `{payload.get('model', 'unknown')}`")
    lines.append(f"- Integration: `{payload.get('integration', 'unknown')}`")
    lines.append(f"- Source mode: `{payload.get('source_mode', 'unknown')}`")
    lines.append(f"- Source file: `{payload.get('source_path', 'unknown')}`")
    lines.append("")

    steps = payload.get("steps", [])
    if not isinstance(steps, list):
        steps = []

    for step in steps:
        if not isinstance(step, dict):
            continue
        step_name = _coerce_text(step.get("step")).strip() or "step"
        prompt = _coerce_text(step.get("prompt")).rstrip()
        assistant_message = _coerce_text(step.get("assistant_message")).rstrip() or "(empty reply)"
        tool_calls = step.get("tool_calls", [])
        if not isinstance(tool_calls, list):
            tool_calls = []

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
        if not tool_calls:
            lines.append("- (none)")
        else:
            for call in tool_calls:
                if not isinstance(call, dict):
                    continue
                tool = _coerce_text(call.get("tool")) or "tool"
                arguments = call.get("arguments", {})
                lines.append(f"- `{tool}` `{json.dumps(arguments, ensure_ascii=True)}`")
        lines.append("")
        lines.append("### Assistant Reply")
        lines.append("")
        lines.append(assistant_message)
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _write_outputs(payload: dict[str, Any], out_dir: Path, model_slug: str) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    base_name = f"{model_slug}__conversation"
    json_path = out_dir / f"{base_name}.json"
    md_path = out_dir / f"{base_name}.md"
    html_path = out_dir / f"{base_name}.html"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown_transcript(payload), encoding="utf-8")
    render_transcript_html(
        json_path=json_path,
        html_path=html_path,
        title=_coerce_text(payload.get("title")) or "Conversation",
    )

    return {
        "json": _display_path(json_path),
        "markdown": _display_path(md_path),
        "html": _display_path(html_path),
    }


def _render_summary_markdown(summary_payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Conversation Model Battery Summary")
    lines.append("")
    lines.append(f"- Captured at: {summary_payload.get('captured_at', 'unknown')}")
    lines.append(f"- Run id: `{summary_payload.get('run_id', 'unknown')}`")
    lines.append(f"- Run slug: `{summary_payload.get('run_slug', 'unknown')}`")
    lines.append(f"- Source mode: `{summary_payload.get('source_mode', 'unknown')}`")
    lines.append(f"- Source file: `{summary_payload.get('source_path', 'unknown')}`")
    lines.append(f"- Integration: `{summary_payload.get('integration', 'unknown')}`")
    lines.append("")
    lines.append("| model | status | steps | tool calls | duration s | json | markdown | html | notes |")
    lines.append("|---|---|---:|---:|---:|---|---|---|---|")

    runs = summary_payload.get("runs", [])
    if not isinstance(runs, list):
        runs = []

    for run in runs:
        if not isinstance(run, dict):
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    str(run.get("model", "")),
                    str(run.get("status", "")),
                    str(run.get("steps_total", 0)),
                    str(run.get("tool_calls_total", 0)),
                    str(run.get("duration_seconds", "")),
                    str(run.get("json_path", "")),
                    str(run.get("markdown_path", "")),
                    str(run.get("html_path", "")),
                    str(run.get("notes", "")),
                ]
            )
            + " |"
        )

    lines.append("")
    lines.append(
        f"- Successes: `{summary_payload.get('success_count', 0)}` / `{summary_payload.get('model_count', 0)}`"
    )
    lines.append(f"- Failures: `{summary_payload.get('failure_count', 0)}`")
    return "\n".join(lines).strip() + "\n"


def _write_battery_summary(out_dir: Path, summary_payload: dict[str, Any]) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "matrix-summary.json"
    md_path = out_dir / "matrix-summary.md"
    json_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    md_path.write_text(_render_summary_markdown(summary_payload), encoding="utf-8")
    return {"json": _display_path(json_path), "markdown": _display_path(md_path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a generic conversation capture and write JSON/MD/HTML artifacts."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="LM Studio API base URL")
    parser.add_argument("--integration", default=DEFAULT_INTEGRATION, help="MCP integration id")
    parser.add_argument(
        "--model",
        default="",
        help="Optional single-model override. If set, it replaces battery models.",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=list(DEFAULT_BATTERY_MODELS),
        help="Model list for battery mode (defaults to local Qwen trio).",
    )
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE, help="Optional env file")
    parser.add_argument("--api-key", default="", help="Optional explicit LM Studio API key")
    parser.add_argument(
        "--conversation-file",
        default=DEFAULT_CONVERSATION_FILE,
        help="Conversation input path (scenario markdown or JSON plan).",
    )
    parser.add_argument(
        "--story-doc",
        default="",
        help="Alias for --conversation-file (backward compatibility).",
    )
    parser.add_argument(
        "--input-mode",
        default="auto",
        choices=["auto", "scenario_markdown", "json_plan"],
        help="Input parser mode.",
    )
    parser.add_argument("--run-id", default="", help="Optional run id override.")
    parser.add_argument("--out-root", default=DEFAULT_OUT_ROOT, help="Artifact output root.")
    parser.add_argument("--context-length", type=int, default=DEFAULT_CONTEXT_LENGTH)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument(
        "--skip-stress-prompts",
        action="store_true",
        help="Markdown mode only: skip section 8 prompts.",
    )
    parser.add_argument(
        "--skip-reset",
        action="store_true",
        help="Do not auto-prepend reset step.",
    )
    parser.add_argument(
        "--prepend-reset",
        action="store_true",
        help="JSON mode only: prepend reset step before plan steps.",
    )
    parser.add_argument(
        "--skip-story-ingestion",
        action="store_true",
        help="Markdown mode only: skip auto story-ingestion step.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse input and print run metadata without LM Studio calls.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Battery mode: continue remaining models when one fails.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _load_env_file(Path(args.env_file))
    api_key = args.api_key.strip() or os.environ.get("LMSTUDIO_API_KEY", "").strip() or None

    source_raw = args.story_doc.strip() or args.conversation_file.strip()
    if not source_raw:
        raise ValueError("Provide --conversation-file (or --story-doc alias).")
    source_path = _resolve_existing_path(source_raw)
    if not source_path.exists():
        raise FileNotFoundError(f"Conversation input file not found: {source_path}")

    plan = _load_conversation_plan(args, source_path=source_path)
    run_id = _slugify(args.run_id.strip()) or _slugify(plan.get("run_id", "")) or "conversation"
    model_override = args.model.strip()
    models = [model_override] if model_override else list(args.models)

    now_utc = dt.datetime.now(dt.timezone.utc)
    run_slug = now_utc.strftime("%Y%m%d-%H%M%S")
    captured_at = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    out_root = _resolve_out_root(args.out_root)
    out_dir = out_root / run_id / run_slug

    if args.dry_run:
        preview = {
            "title": plan.get("title"),
            "run_id": run_id,
            "source_mode": plan.get("source_mode"),
            "source_path": plan.get("source_path"),
            "steps_total": len(plan.get("steps", [])),
            "models": models,
            "model_count": len(models),
            "out_dir": _display_path(out_dir),
            "file_prefixes": [f"{_slugify(model)}__conversation" for model in models],
        }
        print("Dry run: no LM Studio calls were made.")
        print(json.dumps(preview, indent=2))
        return 0

    run_rows: list[dict[str, Any]] = []
    for model in models:
        model_slug = _slugify(model)
        started = dt.datetime.now(dt.timezone.utc)
        steps_out: list[dict[str, Any]] = []
        notes = ""
        outputs: dict[str, str] = {}
        status = "ok"
        try:
            for step in plan["steps"]:
                step_id = _coerce_text(step.get("id")).strip() or f"step_{len(steps_out)+1:02d}"
                prompt = _coerce_text(step.get("prompt")).strip()
                if not prompt:
                    continue
                steps_out.append(
                    _run_chat_step(
                        base_url=args.base_url,
                        model=model,
                        integration=args.integration,
                        api_key=api_key,
                        prompt=prompt,
                        step_id=step_id,
                        context_length=args.context_length,
                        temperature=args.temperature,
                    )
                )

            payload = {
                "title": plan.get("title") or "Conversation",
                "captured_at": captured_at,
                "run_slug": run_slug,
                "run_id": run_id,
                "model": model,
                "integration": args.integration,
                "context_length": args.context_length,
                "temperature": args.temperature,
                "source_mode": plan.get("source_mode"),
                "source_path": plan.get("source_path"),
                "steps": steps_out,
            }
            outputs = _write_outputs(payload, out_dir=out_dir, model_slug=model_slug)
        except Exception as error:
            status = "error"
            notes = f"{type(error).__name__}: {error}"
            if not args.continue_on_error:
                raise
            traceback.print_exc()

        finished = dt.datetime.now(dt.timezone.utc)
        duration_seconds = round((finished - started).total_seconds(), 3)
        tool_calls_total = sum(
            len(step.get("tool_calls", []))
            for step in steps_out
            if isinstance(step, dict) and isinstance(step.get("tool_calls"), list)
        )
        row = {
            "model": model,
            "model_slug": model_slug,
            "status": status,
            "steps_total": len(steps_out),
            "tool_calls_total": tool_calls_total,
            "duration_seconds": duration_seconds,
            "json_path": outputs.get("json", ""),
            "markdown_path": outputs.get("markdown", ""),
            "html_path": outputs.get("html", ""),
            "notes": notes,
        }
        run_rows.append(row)
        print(
            f"[{model}] status={status} steps={row['steps_total']} "
            f"tool_calls={row['tool_calls_total']} duration_s={duration_seconds}"
        )

    success_count = sum(1 for row in run_rows if row.get("status") == "ok")
    failure_count = sum(1 for row in run_rows if row.get("status") != "ok")
    summary_payload = {
        "captured_at": captured_at,
        "run_slug": run_slug,
        "run_id": run_id,
        "title": plan.get("title") or "Conversation",
        "source_mode": plan.get("source_mode"),
        "source_path": plan.get("source_path"),
        "integration": args.integration,
        "context_length": args.context_length,
        "temperature": args.temperature,
        "model_count": len(models),
        "success_count": success_count,
        "failure_count": failure_count,
        "runs": run_rows,
    }
    summary_paths = _write_battery_summary(out_dir=out_dir, summary_payload=summary_payload)

    print("Capture complete.")
    print(json.dumps(summary_paths, indent=2))
    if failure_count:
        print(f"Completed with failures: {failure_count}/{len(models)}")
        return 2
    print(f"Completed all models: {success_count}/{len(models)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
