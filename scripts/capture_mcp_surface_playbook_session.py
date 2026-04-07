#!/usr/bin/env python3
"""
Capture a compact MCP tool-surface playbook session via LM Studio API.

Goal:
- Exercise all canonical MCP tools at least once in one reproducible run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:1234"
DEFAULT_MODEL = "qwen/qwen3.5-9b"
DEFAULT_INTEGRATION = "mcp/prolog-reasoning"
STEP_NAMES = [
    "preflight",
    "reset",
    "seed",
    "rows",
    "logic",
    "nl_query",
    "classify",
    "explain",
    "cleanup",
]
REQUIRED_TOOLS = {
    "show_system_info",
    "list_known_facts",
    "reset_kb",
    "bulk_assert_facts",
    "assert_fact",
    "query_rows",
    "query_logic",
    "query_prolog",
    "classify_statement",
    "explain_error",
    "retract_fact",
}


def _post_json(url: str, payload: dict[str, Any], api_key: str | None) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url=url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    if api_key:
        request.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(request, timeout=480) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        if error.code == 401:
            raise RuntimeError(
                "HTTP 401 from LM Studio API. API auth appears enabled.\n"
                "Set LM Studio API token before running scripted captures.\n"
                "PowerShell example:\n"
                "$env:LMSTUDIO_API_KEY = \"<YOUR_LM_STUDIO_API_TOKEN>\"\n"
                "python scripts/capture_mcp_surface_playbook_session.py --validate\n"
                "Or pass --api-key directly."
            ) from error
        raise RuntimeError(f"HTTP {error.code}: {raw}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Connection error: {error}") from error


def _user_prompt(step: str) -> str:
    prompts = {
        "preflight": (
            "Use show_system_info and list_known_facts first.\n"
            "Then give a one-paragraph summary of what this MCP server can do."
        ),
        "reset": "Use ONLY reset_kb. Confirm success in one sentence.",
        "seed": (
            "Use bulk_assert_facts with these facts, then use assert_fact for one extra fact.\n"
            "Facts for bulk_assert_facts:\n"
            "task(alpha).\n"
            "task(beta).\n"
            "depends_on(beta, alpha).\n"
            "supplier_status(alpha_vendor, on_time).\n"
            "Then call assert_fact with:\n"
            "completed(alpha).\n"
        ),
        "rows": (
            "Use ONLY query_rows with this query:\n"
            "depends_on(Task, Prereq).\n"
            "Return rows and count."
        ),
        "logic": (
            "Use ONLY query_logic with this exact query:\n"
            "depends_on(beta, alpha).\n"
            "Return short answer and detailed answer."
        ),
        "nl_query": "Use ONLY query_prolog on: What task depends on alpha?",
        "classify": (
            "Use ONLY classify_statement on:\n"
            "Maybe my mother was Ann.\n"
            "Return classification fields only."
        ),
        "explain": (
            "Use ONLY explain_error with this error message:\n"
            "Entity 'charlie' not in KB\n"
            "Return the explanation and suggestions."
        ),
        "cleanup": (
            "Use ONLY these tools in order:\n"
            "1) retract_fact completed(alpha).\n"
            "2) reset_kb\n"
            "Confirm cleanup complete."
        ),
    }
    return prompts[step]


def _render_markdown(transcript: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# MCP Surface Playbook Session (Captured)")
    lines.append("")
    lines.append(f"- Captured at: {transcript['captured_at']}")
    lines.append(f"- Model: `{transcript['model']}`")
    lines.append(f"- Integration: `{transcript['integration']}`")
    lines.append("")

    for step in transcript["steps"]:
        lines.append(f"## Step: {step['step']}")
        lines.append("")
        lines.append("### User Prompt")
        lines.append("")
        lines.append("```text")
        lines.append(step["prompt"].rstrip())
        lines.append("```")
        lines.append("")
        lines.append("### Tool Calls")
        lines.append("")
        if not step["tool_calls"]:
            lines.append("- (none)")
        else:
            for call in step["tool_calls"]:
                lines.append(f"- `{call['tool']}` `{json.dumps(call['arguments'], ensure_ascii=True)}`")
        lines.append("")
        lines.append("### Assistant Reply")
        lines.append("")
        lines.append(step["assistant_message"].rstrip() or "(empty reply)")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _format_tool_output_preview(output_field: Any) -> str:
    if output_field is None:
        return "No output payload."

    payload = output_field
    if isinstance(output_field, str):
        try:
            payload = json.loads(output_field)
        except json.JSONDecodeError:
            return output_field

    if isinstance(payload, dict):
        for key in ("answer", "summary", "message", "explanation"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return json.dumps(payload, ensure_ascii=True, indent=2)

    if isinstance(payload, list):
        return json.dumps(payload, ensure_ascii=True, indent=2)

    return str(payload)


def _render_html(transcript: dict[str, Any]) -> str:
    sections: list[str] = []
    for step in transcript["steps"]:
        prompt_html = html.escape(step["prompt"].rstrip())
        reply_html = html.escape(step["assistant_message"].rstrip() or "(empty reply)")

        call_items: list[str] = []
        for call in step["tool_calls"]:
            tool_name = html.escape(str(call.get("tool", "")))
            args = html.escape(json.dumps(call.get("arguments", {}), ensure_ascii=True))
            preview = html.escape(_format_tool_output_preview(call.get("output")))
            call_items.append(
                "<li>"
                f"<div><code>{tool_name}</code> <code>{args}</code></div>"
                f"<details><summary>Output preview</summary><pre>{preview}</pre></details>"
                "</li>"
            )
        calls_html = "<ul>" + "".join(call_items) + "</ul>" if call_items else "<p>No tool calls.</p>"

        sections.append(
            f"""
<section class="card">
  <h2>Step: {html.escape(step["step"])}</h2>
  <div class="label">User Prompt</div>
  <pre class="prompt">{prompt_html}</pre>
  <div class="label">Tool Calls</div>
  {calls_html}
  <div class="label">Assistant Reply</div>
  <pre class="reply">{reply_html}</pre>
</section>
""".strip()
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MCP Surface Playbook Session</title>
  <style>
    :root {{
      --bg: #f3f5f7;
      --card: #ffffff;
      --ink: #12212c;
      --muted: #4c5a64;
      --border: #d5dee4;
      --accent: #0f5f7c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Tahoma, sans-serif;
      background: var(--bg);
      color: var(--ink);
    }}
    .wrap {{
      max-width: 1080px;
      margin: 0 auto;
      padding: 20px 16px 40px;
    }}
    h1 {{ margin: 0 0 8px; font-size: 1.55rem; }}
    .meta {{ color: var(--muted); margin-bottom: 18px; }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px;
      margin-bottom: 14px;
    }}
    h2 {{ margin: 0 0 10px; font-size: 1.05rem; color: var(--accent); }}
    .label {{
      font-size: 0.8rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
      margin: 10px 0 6px;
    }}
    pre {{
      margin: 0;
      background: #f9fbfc;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }}
    ul {{ margin: 6px 0 0 18px; padding: 0; }}
    li {{ margin-bottom: 10px; }}
    code {{
      font-family: Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 0.9rem;
    }}
    details {{ margin-top: 6px; }}
    summary {{ cursor: pointer; color: var(--accent); }}
  </style>
</head>
<body>
  <main class="wrap">
    <h1>MCP Surface Playbook Session (Captured)</h1>
    <div class="meta">Captured: {html.escape(transcript["captured_at"])} | Model: {html.escape(transcript["model"])} | Integration: {html.escape(transcript["integration"])}</div>
    {"".join(sections)}
  </main>
</body>
</html>
"""


def _write_outputs(transcript: dict[str, Any], out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "mcp-surface-playbook-session.json"
    md_path = out_dir / "mcp-surface-playbook-session.md"
    html_path = out_dir / "mcp-surface-playbook-session.html"
    json_path.write_text(json.dumps(transcript, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(transcript), encoding="utf-8")
    html_path.write_text(_render_html(transcript), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path), "html": str(html_path)}


def validate_transcript(transcript: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    steps = transcript.get("steps", [])
    if not isinstance(steps, list):
        return ["Transcript is missing a valid 'steps' list."]

    actual_order = [step.get("step") for step in steps if isinstance(step, dict)]
    if actual_order != STEP_NAMES:
        findings.append(f"Unexpected step order. Expected {STEP_NAMES}, got {actual_order}.")

    seen_tools: set[str] = set()
    for step_name in STEP_NAMES:
        step = next((s for s in steps if isinstance(s, dict) and s.get("step") == step_name), None)
        if step is None:
            findings.append(f"Missing step '{step_name}'.")
            continue

        tool_calls = step.get("tool_calls", [])
        if not isinstance(tool_calls, list) or not tool_calls:
            findings.append(f"Step '{step_name}' has no tool calls.")
            continue

        for call in tool_calls:
            if isinstance(call, dict):
                tool_name = call.get("tool")
                if isinstance(tool_name, str) and tool_name:
                    seen_tools.add(tool_name)

        if not str(step.get("assistant_message", "")).strip():
            findings.append(f"Step '{step_name}' has an empty assistant reply.")

    missing_tools = sorted(REQUIRED_TOOLS - seen_tools)
    if missing_tools:
        findings.append(f"Missing required tool usage: {missing_tools}")

    return findings


def run_capture(
    base_url: str, model: str, integration: str, api_key: str | None, out_dir: Path
) -> tuple[dict[str, Any], dict[str, str]]:
    endpoint = f"{base_url.rstrip('/')}/api/v1/chat"
    steps_out: list[dict[str, Any]] = []

    for step in STEP_NAMES:
        prompt = _user_prompt(step)
        payload = {
            "model": model,
            "input": prompt,
            "integrations": [integration],
            "temperature": 0,
            "context_length": 12000,
        }
        response = _post_json(endpoint, payload, api_key)
        items = response.get("output", [])

        tool_calls = []
        for item in items:
            if item.get("type") == "tool_call":
                tool_calls.append(
                    {
                        "tool": item.get("tool"),
                        "arguments": item.get("arguments", {}),
                        "output": item.get("output"),
                    }
                )

        messages = [item.get("content", "") for item in items if item.get("type") == "message"]
        assistant_message = messages[-1] if messages else ""

        steps_out.append(
            {
                "step": step,
                "prompt": prompt,
                "tool_calls": tool_calls,
                "assistant_message": assistant_message,
            }
        )

    transcript = {
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "model": model,
        "integration": integration,
        "steps": steps_out,
    }
    return transcript, _write_outputs(transcript, out_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture MCP surface playbook session via LM Studio API.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="LM Studio API base URL")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model id from LM Studio /v1/models")
    parser.add_argument("--integration", default=DEFAULT_INTEGRATION, help="MCP integration id")
    parser.add_argument("--out-dir", default="docs/examples", help="Output directory for transcript artifacts")
    parser.add_argument(
        "--input-json",
        default="",
        help="Optional: render markdown from an existing transcript JSON instead of calling the API.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("LMSTUDIO_API_KEY") or os.environ.get("OPENAI_API_KEY", ""),
        help="LM Studio API key. Defaults to LMSTUDIO_API_KEY, then OPENAI_API_KEY.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate transcript structure and required tool coverage after capture/render.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)

    if args.input_json:
        transcript = json.loads(Path(args.input_json).read_text(encoding="utf-8-sig"))
        outputs = _write_outputs(transcript, out_dir)
    else:
        api_key = args.api_key or None
        transcript, outputs = run_capture(
            base_url=args.base_url,
            model=args.model,
            integration=args.integration,
            api_key=api_key,
            out_dir=out_dir,
        )

    if args.validate:
        findings = validate_transcript(transcript)
        if findings:
            print("Validation failed:")
            for finding in findings:
                print(f"- {finding}")
            return 2
        print("Validation passed.")

    print("Capture complete.")
    print(json.dumps(outputs, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
