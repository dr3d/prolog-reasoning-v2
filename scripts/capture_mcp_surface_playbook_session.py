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

from render_dialog_helpers import render_transcript_html


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
        "nl_query": (
            "Use ONLY query_logic with this exact query:\n"
            "depends_on(Task, alpha).\n"
            "Return short answer, then list matching Task values."
        ),
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


def _extract_tool_output_json(output_field: Any) -> dict[str, Any] | None:
    """Decode LM Studio tool-call output payload into a dict when possible."""
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


def _render_html(transcript: dict[str, Any]) -> str:
    cards: list[str] = []
    for step in transcript["steps"]:
        prompt_html = html.escape(step["prompt"].rstrip())
        prompt_attr = html.escape(step["prompt"], quote=True)
        reply_html = html.escape(step["assistant_message"].rstrip() or "(empty reply)")

        tool_items: list[str] = []
        for call in step["tool_calls"]:
            args = html.escape(json.dumps(call.get("arguments", {}), ensure_ascii=True))
            tool_items.append(
                f"<li><code>{html.escape(str(call.get('tool', '')))}</code> <code>{args}</code></li>"
            )
        tool_count = len(step["tool_calls"])
        calls_body = "<ul>" + "".join(tool_items) + "</ul>" if tool_items else "<p>No tool calls.</p>"
        calls_html = (
            "<details class=\"toolbox tool-expando\">"
            f"<summary><span class=\"expando-title\">tool calls</span><span class=\"expando-count\">{tool_count}</span></summary>"
            f"{calls_body}"
            "</details>"
        )

        cards.append(
            f"""
<section class="step-card">
  <h2>{html.escape(step["step"])}</h2>
  <div class="bubble user">
    <div class="bubble-head">
      <div class="label">User</div>
      <button class="copy-btn" data-copy="{prompt_attr}" aria-label="Copy user prompt">copy</button>
    </div>
    <pre>{prompt_html}</pre>
  </div>
  {calls_html}
  <div class="bubble assistant"><div class="label">Assistant</div><pre>{reply_html}</pre></div>
</section>
""".strip()
        )

    body = "\n".join(cards)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>MCP Surface Playbook Session</title>
  <style>
    :root {{
      --bg: #e3ddd2;
      --panel: #ece7de;
      --ink: #201f1b;
      --muted: #59544d;
      --user: #decfba;
      --assistant: #cedbe6;
      --tool: #d9dfd3;
      --border: #c2b9aa;
    }}
    html[data-theme="dark"] {{
      --bg: #171a1f;
      --panel: #1f252d;
      --ink: #e8edf2;
      --muted: #b7c1cc;
      --user: #3b2f23;
      --assistant: #21394d;
      --tool: #293229;
      --border: #3b4652;
    }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.35;
    }}
    .wrap {{
      max-width: 1080px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1 {{
      margin: 0 0 12px 0;
      font-size: 34px;
    }}
    .topbar {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
    }}
    .topbar-right {{
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 8px;
    }}
    .nav-links {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }}
    .nav-link {{
      border: 1px solid var(--border);
      background: var(--panel);
      border-radius: 9px;
      color: var(--ink);
      font-family: "Courier New", monospace;
      font-size: 12px;
      line-height: 1;
      padding: 7px 10px;
      text-decoration: none;
      white-space: nowrap;
    }}
    .nav-link:hover {{
      filter: brightness(1.06);
    }}
    .theme-btn {{
      border: 1px solid var(--border);
      background: var(--panel);
      border-radius: 10px;
      color: var(--ink);
      font-family: "Courier New", monospace;
      font-size: 12px;
      line-height: 1;
      padding: 8px 10px;
      cursor: pointer;
      white-space: nowrap;
      margin-top: 4px;
    }}
    .theme-btn:hover {{
      filter: brightness(1.06);
    }}
    .meta {{
      font-family: "Courier New", monospace;
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 24px;
    }}
    .step-card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 16px;
      box-shadow: 0 1px 2px rgba(0,0,0,.04);
      padding: 16px;
      margin-bottom: 16px;
    }}
    h2 {{
      margin: 0 0 12px 0;
      font-size: 22px;
      text-transform: capitalize;
    }}
    .bubble {{
      border-radius: 14px;
      padding: 12px;
      margin-bottom: 12px;
      border: 1px solid var(--border);
    }}
    .bubble-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }}
    .bubble.user {{ background: var(--user); }}
    .bubble.assistant {{ background: var(--assistant); }}
    .copy-btn {{
      border: 1px solid #b7a990;
      background: #fff4df;
      border-radius: 8px;
      color: #3e3a31;
      font-family: "Courier New", monospace;
      font-size: 11px;
      line-height: 1;
      padding: 4px 6px;
      cursor: pointer;
    }}
    .copy-btn:hover {{
      background: #f8ebd2;
    }}
    .copy-btn.copied {{
      border-color: #7e9e73;
      background: #e5f0dd;
      color: #2f5130;
    }}
    .label {{
      font-size: 11px;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 8px;
      font-family: "Courier New", monospace;
    }}
    .toolbox {{
      background: var(--tool);
      border-radius: 14px;
      padding: 12px;
      margin-bottom: 12px;
      border: 1px solid var(--border);
      font-family: "Courier New", monospace;
      font-size: 13px;
    }}
    .tool-expando {{
      border: 1px solid var(--border);
      border-radius: 10px;
      background: color-mix(in srgb, var(--tool) 88%, var(--panel));
      padding: 0;
    }}
    .tool-expando summary {{
      cursor: pointer;
      list-style: none;
      padding: 8px 10px;
      font-family: "Courier New", monospace;
      font-size: 12px;
      color: var(--muted);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      text-transform: uppercase;
      letter-spacing: .08em;
    }}
    .tool-expando summary::-webkit-details-marker {{
      display: none;
    }}
    .tool-expando > ul,
    .tool-expando > p {{
      margin: 0;
      padding: 0 10px 10px 20px;
    }}
    .tool-expando > p {{
      padding-left: 10px;
    }}
    .expando-count {{
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 1px 7px;
      font-size: 11px;
      letter-spacing: 0;
      text-transform: none;
      color: var(--ink);
      background: var(--panel);
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: "Courier New", monospace;
      font-size: 13px;
    }}
    ul {{
      margin: 0;
      padding-left: 20px;
    }}
    @media (max-width: 760px) {{
      .topbar {{
        flex-direction: column;
      }}
      .topbar-right {{
        width: 100%;
        align-items: flex-start;
      }}
      .nav-links {{
        justify-content: flex-start;
      }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <h1>MCP Surface Playbook Session</h1>
      <div class="topbar-right">
        <div class="nav-links">
          <a class="nav-link" href="https://dr3d.github.io/prolog-reasoning/docs-hub.html">Back to Docs Hub</a>
          <a class="nav-link" href="https://github.com/dr3d/prolog-reasoning">View Repo</a>
        </div>
        <button id="theme-toggle" class="theme-btn" aria-label="Toggle dark and light theme">theme: light</button>
      </div>
    </div>
    <div class="meta">Captured: {html.escape(transcript["captured_at"])} | Model: {html.escape(transcript["model"])} | Integration: {html.escape(transcript["integration"])}</div>
    {body}
  </div>
  <script>
    (() => {{
      const root = document.documentElement;
      const themeToggle = document.getElementById('theme-toggle');
      const storageKey = 'surface_playbook_theme';

      const setTheme = (theme) => {{
        root.setAttribute('data-theme', theme);
        if (themeToggle) {{
          themeToggle.textContent = theme === 'dark' ? 'theme: dark' : 'theme: light';
        }}
      }};

      const stored = window.localStorage.getItem(storageKey);
      if (stored === 'dark' || stored === 'light') {{
        setTheme(stored);
      }} else {{
        const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        setTheme(prefersDark ? 'dark' : 'light');
      }}

      if (themeToggle) {{
        themeToggle.addEventListener('click', () => {{
          const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
          setTheme(next);
          window.localStorage.setItem(storageKey, next);
        }});
      }}

      const buttons = document.querySelectorAll('.copy-btn');
      for (const button of buttons) {{
        button.addEventListener('click', async () => {{
          const text = button.getAttribute('data-copy') || '';
          const before = 'copy';
          try {{
            await navigator.clipboard.writeText(text);
            button.textContent = 'copied';
            button.classList.add('copied');
          }} catch (error) {{
            button.textContent = 'copy-failed';
          }}
          window.setTimeout(() => {{
            button.textContent = before;
            button.classList.remove('copied');
          }}, 1200);
        }});
      }}
    }})();
  </script>
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
    render_transcript_html(
        json_path=json_path,
        html_path=html_path,
        title="MCP Surface Playbook Session",
    )
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

    # Smoke invariant: uncertain candidate facts must not auto-commit.
    classify_step = next(
        (s for s in steps if isinstance(s, dict) and s.get("step") == "classify"),
        None,
    )
    if classify_step is not None:
        classify_calls = [
            c for c in classify_step.get("tool_calls", [])
            if isinstance(c, dict) and c.get("tool") == "classify_statement"
        ]
        if not classify_calls:
            findings.append("Classify step is missing classify_statement call.")
        else:
            classify_payload = _extract_tool_output_json(classify_calls[0].get("output"))
            if classify_payload is None:
                findings.append("Classify step output was not parseable JSON.")
            else:
                if classify_payload.get("can_persist_now") is not False:
                    findings.append(
                        "Invariant failed: uncertain classify step must return can_persist_now=false."
                    )
                if classify_payload.get("kind") != "tentative_fact":
                    findings.append(
                        "Invariant failed: classify step expected kind='tentative_fact'."
                    )

        write_tools = {"assert_fact", "bulk_assert_facts", "retract_fact", "reset_kb"}
        unexpected_writes = sorted({
            c.get("tool")
            for c in classify_step.get("tool_calls", [])
            if isinstance(c, dict) and c.get("tool") in write_tools
        })
        if unexpected_writes:
            findings.append(
                f"Invariant failed: classify step must not call write tools: {unexpected_writes}"
            )

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
        help="Optional: render markdown/html from an existing transcript JSON instead of calling the API.",
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
