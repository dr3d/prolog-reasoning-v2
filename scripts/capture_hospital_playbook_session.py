#!/usr/bin/env python3
"""
Capture a full CPM-like hospital playbook chat session via LM Studio API.

Outputs:
- JSON transcript with tool calls and messages
- Markdown transcript
- Styled HTML transcript suitable for screenshotting
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


def _daily_ops_examples() -> list[dict[str, Any]]:
    """Illustrative chat-first prompts that feel like live control-room use."""
    return [
        {
            "title": "Morning Standup",
            "question": "What can safely start this morning, and what is still waiting?",
            "tool_calls": [
                {"tool": "query_rows", "arguments": {"query": "safe_to_start(Task)."}},
                {"tool": "query_rows", "arguments": {"query": "waiting_on(Task, Prereq)."}},
            ],
            "answer": (
                "Ready now includes enclosure_glazing, roofing, and other tasks with satisfied prerequisites. "
                "Most downstream work is still waiting on interior_buildout and then regulatory_inspection."
            ),
        },
        {
            "title": "Supplier Delay Update",
            "question": "If the glass vendor is delayed today, what milestones are impacted first?",
            "tool_calls": [
                {"tool": "retract_fact", "arguments": {"fact": "supplier_status(glass_vendor, on_time)."}},
                {"tool": "assert_fact", "arguments": {"fact": "supplier_status(glass_vendor, delayed)."}},
                {"tool": "query_rows", "arguments": {"query": "blocked_task(Task, Supplier)."}},
                {"tool": "query_rows", "arguments": {"query": "delayed_milestone(Milestone, Supplier)."}},
            ],
            "answer": (
                "The first direct blocker is enclosure_glazing, and that propagates to regulatory_inspection, "
                "occupancy_permit, and go_live through the critical dependency chain."
            ),
        },
        {
            "title": "End-of-Day Recovery",
            "question": "We recovered glazing and completed rough-in items. What changed for tomorrow's plan?",
            "tool_calls": [
                {"tool": "retract_fact", "arguments": {"fact": "supplier_status(glass_vendor, delayed)."}},
                {"tool": "assert_fact", "arguments": {"fact": "supplier_status(glass_vendor, on_time)."}},
                {"tool": "assert_fact", "arguments": {"fact": "completed(enclosure_glazing)."}},
                {"tool": "assert_fact", "arguments": {"fact": "completed(mep_rough_in)."}},
                {"tool": "assert_fact", "arguments": {"fact": "completed(fireproofing)."}},
                {"tool": "query_rows", "arguments": {"query": "safe_to_start(Task)."}},
                {"tool": "query_rows", "arguments": {"query": "task_status(Task, Status)."}},
            ],
            "answer": (
                "The ready set expands and several previously waiting tasks move into executable status. "
                "Milestone risk decreases because no supplier remains in delayed state."
            ),
        },
    ]


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
        raise RuntimeError(f"HTTP {error.code}: {raw}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Connection error: {error}") from error


def _user_prompt(step: str) -> str:
    prompts = {
        "reset": (
            "Use ONLY reset_kb. Confirm success in one sentence."
        ),
        "ingest": (
            "Use bulk_assert_facts with the full fact list below.\n"
            "Then run query_rows counts for:\n"
            "- task(Task).\n"
            "- depends_on(Task, Prereq).\n"
            "- task_supplier(Task, Supplier).\n"
            "- supplier_status(Supplier, Status).\n"
            "- completed(Task).\n"
            "- milestone(M).\n"
            "Return the raw counts and stop if any count mismatches.\n\n"
            "task(site_prep).\n"
            "task(foundation).\n"
            "task(structural_frame).\n"
            "task(mep_rough_in).\n"
            "task(fireproofing).\n"
            "task(enclosure_glazing).\n"
            "task(roofing).\n"
            "task(interior_buildout).\n"
            "task(hvac_commissioning).\n"
            "task(medical_gas_cert).\n"
            "task(or_fitout).\n"
            "task(imaging_suite_install).\n"
            "task(it_network_core).\n"
            "task(regulatory_inspection).\n"
            "task(occupancy_permit).\n"
            "task(go_live).\n"
            "depends_on(foundation, site_prep).\n"
            "depends_on(structural_frame, foundation).\n"
            "depends_on(mep_rough_in, structural_frame).\n"
            "depends_on(fireproofing, structural_frame).\n"
            "depends_on(enclosure_glazing, structural_frame).\n"
            "depends_on(roofing, structural_frame).\n"
            "depends_on(interior_buildout, mep_rough_in).\n"
            "depends_on(interior_buildout, fireproofing).\n"
            "depends_on(hvac_commissioning, interior_buildout).\n"
            "depends_on(medical_gas_cert, interior_buildout).\n"
            "depends_on(or_fitout, medical_gas_cert).\n"
            "depends_on(imaging_suite_install, interior_buildout).\n"
            "depends_on(it_network_core, interior_buildout).\n"
            "depends_on(regulatory_inspection, hvac_commissioning).\n"
            "depends_on(regulatory_inspection, medical_gas_cert).\n"
            "depends_on(regulatory_inspection, it_network_core).\n"
            "depends_on(occupancy_permit, regulatory_inspection).\n"
            "depends_on(go_live, occupancy_permit).\n"
            "depends_on(go_live, or_fitout).\n"
            "depends_on(go_live, imaging_suite_install).\n"
            "duration_days(site_prep, 12).\n"
            "duration_days(foundation, 21).\n"
            "duration_days(structural_frame, 35).\n"
            "duration_days(interior_buildout, 40).\n"
            "duration_days(regulatory_inspection, 14).\n"
            "duration_days(occupancy_permit, 7).\n"
            "duration_days(go_live, 2).\n"
            "task_supplier(enclosure_glazing, glass_vendor).\n"
            "task_supplier(medical_gas_cert, medgas_vendor).\n"
            "task_supplier(imaging_suite_install, imaging_vendor).\n"
            "supplier_status(glass_vendor, on_time).\n"
            "supplier_status(medgas_vendor, on_time).\n"
            "supplier_status(imaging_vendor, on_time).\n"
            "completed(site_prep).\n"
            "completed(foundation).\n"
            "completed(structural_frame).\n"
            "milestone(regulatory_inspection).\n"
            "milestone(occupancy_permit).\n"
            "milestone(go_live).\n"
        ),
        "baseline": (
            "Use ONLY query_rows for these exact queries and return markdown tables plus row counts:\n"
            "- safe_to_start(Task).\n"
            "- waiting_on(Task, Prereq).\n"
            "- task_status(Task, Status).\n"
            "- delayed_milestone(Milestone, Supplier).\n"
            "Do not call query_prolog.\n"
        ),
        "shock_glass": (
            "Use only these tools in order:\n"
            "1) retract_fact supplier_status(glass_vendor, on_time).\n"
            "2) assert_fact supplier_status(glass_vendor, delayed).\n"
            "3) query_rows blocked_task(Task, Supplier).\n"
            "4) query_rows delayed_milestone(Milestone, Supplier).\n"
            "5) query_rows task_status(Task, Status).\n"
            "Return three tables and one short propagation narrative.\n"
        ),
        "shock_medgas": (
            "Use only these tools in order:\n"
            "1) retract_fact supplier_status(medgas_vendor, on_time).\n"
            "2) assert_fact supplier_status(medgas_vendor, delayed).\n"
            "3) query_rows blocked_task(Task, Supplier).\n"
            "4) query_rows delayed_milestone(Milestone, Supplier).\n"
            "5) query_rows waiting_on(Task, Prereq).\n"
            "Then provide top 3 interventions to protect go_live.\n"
        ),
        "recovery": (
            "Use only these tools in order:\n"
            "1) retract_fact supplier_status(glass_vendor, delayed).\n"
            "2) assert_fact supplier_status(glass_vendor, on_time).\n"
            "3) assert_fact completed(enclosure_glazing).\n"
            "4) assert_fact completed(mep_rough_in).\n"
            "5) assert_fact completed(fireproofing).\n"
            "6) query_rows safe_to_start(Task).\n"
            "7) query_rows waiting_on(Task, Prereq).\n"
            "8) query_rows delayed_milestone(Milestone, Supplier).\n"
            "Return sections: Ready now, Still waiting, Remaining milestone risks.\n"
        ),
    }
    return prompts[step]


def _render_markdown(transcript: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Hospital CPM Playbook Session (Captured)")
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

    lines.append("## Daily Ops Chat Snippets (Illustrative)")
    lines.append("")
    lines.append("These are realistic short prompts for day-to-day usage in chat mode.")
    lines.append("")
    for example in _daily_ops_examples():
        lines.append(f"### {example['title']}")
        lines.append("")
        lines.append("#### User Prompt")
        lines.append("")
        lines.append("```text")
        lines.append(example["question"])
        lines.append("```")
        lines.append("")
        lines.append("#### Tool Calls")
        lines.append("")
        for call in example["tool_calls"]:
            lines.append(f"- `{call['tool']}` `{json.dumps(call['arguments'], ensure_ascii=True)}`")
        lines.append("")
        lines.append("#### Assistant Reply")
        lines.append("")
        lines.append(example["answer"])
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _render_html(transcript: dict[str, Any]) -> str:
    card_blocks: list[str] = []
    for step in transcript["steps"]:
        prompt_html = html.escape(step["prompt"])
        prompt_attr = html.escape(step["prompt"], quote=True)
        reply_html = html.escape(step["assistant_message"] or "(empty reply)")

        call_items = []
        for call in step["tool_calls"]:
            args = html.escape(json.dumps(call["arguments"], ensure_ascii=True))
            call_items.append(f"<li><code>{html.escape(call['tool'])}</code> <code>{args}</code></li>")
        calls_html = "<ul>" + "".join(call_items) + "</ul>" if call_items else "<p>No tool calls.</p>"

        card_blocks.append(
            f"""
<section class="step-card">
  <h2>{html.escape(step["step"])}</h2>
  <div class="bubble user">
    <div class="bubble-head">
      <div class="label">User</div>
      <button class="copy-btn" data-copy="{prompt_attr}" aria-label="Copy user prompt">[copy]</button>
    </div>
    <pre>{prompt_html}</pre>
  </div>
  <div class="toolbox"><div class="label">Tool Calls</div>{calls_html}</div>
  <div class="bubble assistant"><div class="label">Assistant</div><pre>{reply_html}</pre></div>
</section>
""".strip()
        )

    body = "\n".join(card_blocks)
    daily_cards: list[str] = []
    for example in _daily_ops_examples():
        question_html = html.escape(example["question"])
        question_attr = html.escape(example["question"], quote=True)
        answer_html = html.escape(example["answer"])
        call_items = []
        for call in example["tool_calls"]:
            args = html.escape(json.dumps(call["arguments"], ensure_ascii=True))
            call_items.append(f"<li><code>{html.escape(call['tool'])}</code> <code>{args}</code></li>")
        calls_html = "<ul>" + "".join(call_items) + "</ul>"
        daily_cards.append(
            f"""
<section class="step-card">
  <h2>{html.escape(example["title"])}</h2>
  <div class="bubble user">
    <div class="bubble-head">
      <div class="label">User</div>
      <button class="copy-btn" data-copy="{question_attr}" aria-label="Copy user prompt">[copy]</button>
    </div>
    <pre>{question_html}</pre>
  </div>
  <div class="toolbox"><div class="label">Tool Calls</div>{calls_html}</div>
  <div class="bubble assistant"><div class="label">Assistant</div><pre>{answer_html}</pre></div>
</section>
""".strip()
        )
    daily_body = "\n".join(daily_cards)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Hospital CPM Playbook Session</title>
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
      font-size: 12px;
      line-height: 1;
      padding: 6px 8px;
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
    .toolbox {{
      background: var(--tool);
      border-radius: 14px;
      padding: 12px;
      margin-bottom: 12px;
      border: 1px solid var(--border);
      font-family: "Courier New", monospace;
      font-size: 13px;
    }}
    .label {{
      font-size: 11px;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 8px;
      font-family: "Courier New", monospace;
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
      <h1>Hospital CPM Playbook Session</h1>
      <div class="topbar-right">
        <div class="nav-links">
          <a class="nav-link" href="../docs-hub.html">Back to Docs Hub</a>
          <a class="nav-link" href="https://github.com/dr3d/prolog-reasoning-v2">View Repo</a>
        </div>
        <button id="theme-toggle" class="theme-btn" aria-label="Toggle dark and light theme">theme: light</button>
      </div>
    </div>
    <div class="meta">Captured: {html.escape(transcript["captured_at"])} | Model: {html.escape(transcript["model"])} | Integration: {html.escape(transcript["integration"])}</div>
    {body}
    <section class="step-card">
      <h2>Daily Ops Chat Snippets (Illustrative)</h2>
      <div class="bubble assistant">
        <div class="label">Note</div>
        <pre>This section is intentionally conversational. It shows believable day-to-day prompts and reports, not test harness steps.</pre>
      </div>
    </section>
    {daily_body}
  </div>
  <script>
    (() => {{
      const root = document.documentElement;
      const themeToggle = document.getElementById('theme-toggle');
      const storageKey = 'cpm_playbook_theme';

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
          const before = '[copy]';
          try {{
            await navigator.clipboard.writeText(text);
            button.textContent = '[copied]';
            button.classList.add('copied');
          }} catch (error) {{
            button.textContent = '[copy-failed]';
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
    json_path = out_dir / "hospital-cpm-playbook-session.json"
    md_path = out_dir / "hospital-cpm-playbook-session.md"
    html_path = out_dir / "hospital-cpm-playbook-session.html"

    json_path.write_text(json.dumps(transcript, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(transcript), encoding="utf-8")
    html_path.write_text(_render_html(transcript), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path), "html": str(html_path)}


def run_capture(base_url: str, model: str, integration: str, api_key: str | None, out_dir: Path) -> dict[str, Any]:
    endpoint = f"{base_url.rstrip('/')}/api/v1/chat"

    step_names = ["reset", "ingest", "baseline", "shock_glass", "shock_medgas", "recovery"]
    steps_out: list[dict[str, Any]] = []

    for step in step_names:
        prompt = _user_prompt(step)
        payload = {
            "model": model,
            "input": prompt,
            "integrations": [integration],
            "temperature": 0,
            "context_length": 14000,
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
    return _write_outputs(transcript, out_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture hospital CPM playbook session via LM Studio API.")
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
        default=os.environ.get("LMSTUDIO_API_KEY", ""),
        help="LM Studio API key. Defaults to LMSTUDIO_API_KEY.",
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
        outputs = run_capture(
            base_url=args.base_url,
            model=args.model,
            integration=args.integration,
            api_key=api_key,
            out_dir=out_dir,
        )

    print("Capture complete.")
    print(json.dumps(outputs, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
