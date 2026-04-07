#!/usr/bin/env python3
"""
Capture an Indie Launch War Room session using natural phrasing (not explicit tool commands).

Purpose:
- Demonstrate that users do not need to utter exact tool names.
- Measure how reliably the model still selects deterministic tools.

Outputs:
- JSON transcript
- Markdown transcript with tool-use validation table
- HTML transcript with per-step pass/fail badges
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
    "natural_preflight",
    "natural_reset",
    "natural_ingest",
    "natural_standup",
    "natural_cloud_incident",
    "natural_cert_incident",
    "natural_uncertain_note",
    "natural_recovery",
]

EXPECTED_TOOLS = {
    "natural_preflight": {"show_system_info", "list_known_facts"},
    "natural_reset": {"reset_kb"},
    "natural_ingest": {"bulk_assert_facts", "query_rows"},
    "natural_standup": {"query_rows"},
    "natural_cloud_incident": {"retract_fact", "assert_fact", "query_rows"},
    "natural_cert_incident": {"retract_fact", "assert_fact", "query_rows"},
    "natural_uncertain_note": {"classify_statement", "explain_error"},
    "natural_recovery": {"retract_fact", "assert_fact", "query_rows"},
}

FACTS = [
    "task(vertical_slice_lock).",
    "task(crash_triage_sweep).",
    "task(final_build_candidate).",
    "task(console_submission).",
    "task(platform_release_slot).",
    "task(launch_trailer_cut).",
    "task(press_kit_final).",
    "task(store_page_lock).",
    "task(localization_pack).",
    "task(streamer_preview_keys).",
    "task(day_one_patch).",
    "task(matchmaking_scale_test).",
    "task(community_faq_publish).",
    "task(embargo_briefing).",
    "task(global_launch).",
    "depends_on(crash_triage_sweep, vertical_slice_lock).",
    "depends_on(final_build_candidate, vertical_slice_lock).",
    "depends_on(final_build_candidate, crash_triage_sweep).",
    "depends_on(console_submission, final_build_candidate).",
    "depends_on(platform_release_slot, console_submission).",
    "depends_on(launch_trailer_cut, vertical_slice_lock).",
    "depends_on(press_kit_final, launch_trailer_cut).",
    "depends_on(store_page_lock, launch_trailer_cut).",
    "depends_on(store_page_lock, press_kit_final).",
    "depends_on(localization_pack, final_build_candidate).",
    "depends_on(streamer_preview_keys, platform_release_slot).",
    "depends_on(streamer_preview_keys, store_page_lock).",
    "depends_on(day_one_patch, final_build_candidate).",
    "depends_on(matchmaking_scale_test, final_build_candidate).",
    "depends_on(community_faq_publish, press_kit_final).",
    "depends_on(community_faq_publish, day_one_patch).",
    "depends_on(embargo_briefing, press_kit_final).",
    "depends_on(embargo_briefing, streamer_preview_keys).",
    "depends_on(global_launch, console_submission).",
    "depends_on(global_launch, day_one_patch).",
    "depends_on(global_launch, matchmaking_scale_test).",
    "depends_on(global_launch, store_page_lock).",
    "depends_on(global_launch, localization_pack).",
    "depends_on(global_launch, embargo_briefing).",
    "task_supplier(console_submission, console_cert_vendor).",
    "task_supplier(platform_release_slot, platform_ops_vendor).",
    "task_supplier(localization_pack, localization_vendor).",
    "task_supplier(matchmaking_scale_test, cloud_vendor).",
    "supplier_status(console_cert_vendor, on_time).",
    "supplier_status(platform_ops_vendor, on_time).",
    "supplier_status(localization_vendor, on_time).",
    "supplier_status(cloud_vendor, on_time).",
    "completed(vertical_slice_lock).",
    "completed(crash_triage_sweep).",
    "completed(launch_trailer_cut).",
    "completed(press_kit_final).",
    "milestone(platform_release_slot).",
    "milestone(embargo_briefing).",
    "milestone(global_launch).",
]


def _facts_block() -> str:
    return "\n".join(FACTS) + "\n"


def _user_prompt(step: str) -> str:
    prompts = {
        "natural_preflight": (
            "Hey, before we start, can you show me system info and what you factually know right now? "
            "Keep it short and grounded in the tool output."
        ),
        "natural_reset": (
            "Can we do a clean slate first so old runtime edits don't leak into this run? "
            "Please reset and confirm."
        ),
        "natural_ingest": (
            "Let's stand up a launch war-room board. Please load the following facts into working memory, "
            "then sanity-check counts for tasks, dependencies, supplier mapping/status, completed items, and milestones. "
            "If counts look off, say so clearly.\n\n"
            + _facts_block()
        ),
        "natural_standup": (
            "Morning standup view: what can start now, what's waiting, and do we have milestone risk yet? "
            "Please base it on the current board state, not guesses."
        ),
        "natural_cloud_incident": (
            "Update: cloud support slipped. Please update the board to reflect that vendor delay and show me "
            "what becomes blocked plus any milestone impact."
        ),
        "natural_cert_incident": (
            "Now certification looks delayed too. Reflect that status change and tell me the top launch-protection actions."
        ),
        "natural_uncertain_note": (
            "Producer note just came in: 'I think launch date might be June 3, but it is not locked yet.' "
            "Route that safely (don't force it as a hard fact). Also, explain this error text: "
            "Entity 'mystery_vendor' not in KB"
        ),
        "natural_recovery": (
            "Good news: both cloud and cert vendors are back on schedule. Also mark final_build_candidate, "
            "console_submission, and platform_release_slot completed. Then recalc ready/waiting/risk and summarize."
        ),
    }
    return prompts[step]


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
                "python scripts/capture_indie_launch_natural_session.py --validate\n"
                "Or pass --api-key directly."
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
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if not isinstance(text, str):
                continue
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
    return None


def _step_tool_report(transcript: dict[str, Any]) -> dict[str, dict[str, Any]]:
    report: dict[str, dict[str, Any]] = {}
    steps = transcript.get("steps", [])
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_name = str(step.get("step", ""))
        expected = EXPECTED_TOOLS.get(step_name, set())
        observed: set[str] = set()
        for call in step.get("tool_calls", []):
            if isinstance(call, dict):
                tool_name = call.get("tool")
                if isinstance(tool_name, str) and tool_name:
                    observed.add(tool_name)
        missing = sorted(expected - observed)
        report[step_name] = {
            "expected": sorted(expected),
            "observed": sorted(observed),
            "missing": missing,
            "pass": len(missing) == 0,
        }
    return report


def validate_transcript(transcript: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    steps = transcript.get("steps", [])
    if not isinstance(steps, list):
        return ["Transcript is missing a valid 'steps' list."]

    actual_order = [step.get("step") for step in steps if isinstance(step, dict)]
    if actual_order != STEP_NAMES:
        findings.append(f"Unexpected step order. Expected {STEP_NAMES}, got {actual_order}.")

    report = _step_tool_report(transcript)
    for step_name in STEP_NAMES:
        step = next((s for s in steps if isinstance(s, dict) and s.get("step") == step_name), None)
        if step is None:
            findings.append(f"Missing step '{step_name}'.")
            continue

        calls = step.get("tool_calls", [])
        if not isinstance(calls, list) or not calls:
            findings.append(f"Step '{step_name}' has no tool calls.")
        if not str(step.get("assistant_message", "")).strip():
            findings.append(f"Step '{step_name}' has an empty assistant reply.")

        step_rep = report.get(step_name, {})
        missing = step_rep.get("missing", [])
        if missing:
            findings.append(f"Step '{step_name}' missing expected tools: {missing}")

    uncertain_step = next(
        (s for s in steps if isinstance(s, dict) and s.get("step") == "natural_uncertain_note"),
        None,
    )
    if uncertain_step is not None:
        classify_calls = [
            c for c in uncertain_step.get("tool_calls", [])
            if isinstance(c, dict) and c.get("tool") == "classify_statement"
        ]
        if classify_calls:
            payload = _extract_tool_output_json(classify_calls[0].get("output"))
            if payload is not None and payload.get("can_persist_now") is not False:
                findings.append("Uncertain-note invariant failed: expected can_persist_now=false.")

    return findings


def _render_markdown(transcript: dict[str, Any]) -> str:
    tool_report = _step_tool_report(transcript)

    lines: list[str] = []
    lines.append("# Indie Launch War Room (Natural-Language Tooling Showcase)")
    lines.append("")
    lines.append(f"- Captured at: {transcript['captured_at']}")
    lines.append(f"- Model: `{transcript['model']}`")
    lines.append(f"- Integration: `{transcript['integration']}`")
    lines.append("")

    pass_count = sum(1 for name in STEP_NAMES if tool_report.get(name, {}).get("pass"))
    lines.append("## Tooling Robustness Summary")
    lines.append("")
    lines.append(f"- Step expectations met: `{pass_count}/{len(STEP_NAMES)}`")
    lines.append("")

    for step_name in STEP_NAMES:
        rep = tool_report.get(step_name, {"expected": [], "observed": [], "missing": [], "pass": False})
        badge = "PASS" if rep["pass"] else "MISS"
        lines.append(f"- `{step_name}`: **{badge}**")
        lines.append(f"  expected: `{', '.join(rep['expected'])}`")
        lines.append(f"  observed: `{', '.join(rep['observed'])}`")
        lines.append(f"  missing: `{', '.join(rep['missing']) if rep['missing'] else '(none)'}`")
        lines.append("")

    for step in transcript["steps"]:
        step_name = step["step"]
        rep = tool_report.get(step_name, {"pass": False, "expected": [], "observed": [], "missing": []})
        lines.append(f"## Step: {step_name}")
        lines.append("")
        lines.append(f"- Expected tools: `{', '.join(rep['expected'])}`")
        lines.append(f"- Observed tools: `{', '.join(rep['observed'])}`")
        lines.append(f"- Missing: `{', '.join(rep['missing']) if rep['missing'] else '(none)'}`")
        lines.append(f"- Step status: `{'PASS' if rep['pass'] else 'MISS'}`")
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


def _render_html(transcript: dict[str, Any]) -> str:
    tool_report = _step_tool_report(transcript)
    pass_count = sum(1 for name in STEP_NAMES if tool_report.get(name, {}).get("pass"))

    cards: list[str] = []
    for step in transcript["steps"]:
        step_name = step["step"]
        rep = tool_report.get(step_name, {"pass": False, "expected": [], "observed": [], "missing": []})
        status_cls = "ok" if rep["pass"] else "warn"
        status_text = "PASS" if rep["pass"] else "MISS"

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

        expect_html = html.escape(", ".join(rep["expected"]) if rep["expected"] else "(none)")
        observed_html = html.escape(", ".join(rep["observed"]) if rep["observed"] else "(none)")
        missing_html = html.escape(", ".join(rep["missing"]) if rep["missing"] else "(none)")

        cards.append(
            f"""
<section class="step-card">
  <h2>{html.escape(step_name)} <span class="badge {status_cls}">{status_text}</span></h2>
  <div class="expect-box">
    <div><span class="k">expected:</span> <code>{expect_html}</code></div>
    <div><span class="k">observed:</span> <code>{observed_html}</code></div>
    <div><span class="k">missing:</span> <code>{missing_html}</code></div>
  </div>
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
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Indie Launch Natural-Language Tooling Showcase</title>
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
      --ok: #2f6b35;
      --warn: #8a5230;
    }}
    html[data-theme=\"dark\"] {{
      --bg: #171a1f;
      --panel: #1f252d;
      --ink: #e8edf2;
      --muted: #b7c1cc;
      --user: #3b2f23;
      --assistant: #21394d;
      --tool: #293229;
      --border: #3b4652;
      --ok: #95d89c;
      --warn: #f0bf96;
    }}
    body {{
      margin: 0;
      font-family: Georgia, \"Times New Roman\", serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.35;
    }}
    .wrap {{
      max-width: 1080px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1 {{ margin: 0 0 12px 0; font-size: 32px; }}
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
      font-family: \"Courier New\", monospace;
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
      font-family: \"Courier New\", monospace;
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
      font-family: \"Courier New\", monospace;
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 24px;
    }}
    .summary-box {{
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--panel);
      padding: 10px 12px;
      margin-bottom: 14px;
      font-family: \"Courier New\", monospace;
      font-size: 13px;
    }}
    .step-card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 16px;
      box-shadow: 0 1px 2px rgba(0,0,0,.04);
      padding: 16px;
      margin-bottom: 16px;
    }}
    h2 {{ margin: 0 0 10px 0; font-size: 21px; text-transform: none; }}
    .badge {{
      font-family: \"Courier New\", monospace;
      font-size: 11px;
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 2px 8px;
      vertical-align: middle;
    }}
    .badge.ok {{ color: var(--ok); }}
    .badge.warn {{ color: var(--warn); }}
    .expect-box {{
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 8px 10px;
      margin-bottom: 10px;
      font-family: \"Courier New\", monospace;
      font-size: 12px;
      background: color-mix(in srgb, var(--panel) 90%, var(--tool));
    }}
    .expect-box .k {{ color: var(--muted); text-transform: lowercase; }}
    .bubble {{
      border-radius: 14px;
      padding: 12px;
      margin-bottom: 12px;
      border: 1px solid var(--border);
    }}
    .bubble.user {{ background: var(--user); }}
    .bubble.assistant {{ background: var(--assistant); }}
    .bubble-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }}
    .label {{
      font-size: 11px;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 8px;
      font-family: \"Courier New\", monospace;
    }}
    .copy-btn {{
      border: 1px solid #b7a990;
      background: #fff4df;
      border-radius: 8px;
      color: #3e3a31;
      font-family: \"Courier New\", monospace;
      font-size: 11px;
      line-height: 1;
      padding: 4px 6px;
      cursor: pointer;
    }}
    .copy-btn:hover {{ background: #f8ebd2; }}
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
      font-family: \"Courier New\", monospace;
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
      font-family: \"Courier New\", monospace;
      font-size: 12px;
      color: var(--muted);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      text-transform: uppercase;
      letter-spacing: .08em;
    }}
    .tool-expando summary::-webkit-details-marker {{ display: none; }}
    .tool-expando > ul,
    .tool-expando > p {{
      margin: 0;
      padding: 0 10px 10px 20px;
    }}
    .tool-expando > p {{ padding-left: 10px; }}
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
      font-family: \"Courier New\", monospace;
      font-size: 13px;
    }}
    ul {{ margin: 0; padding-left: 20px; }}
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
  <div class=\"wrap\">
    <div class="topbar">
      <h1>Indie Launch Natural-Language Tooling Showcase</h1>
      <div class="topbar-right">
        <div class="nav-links">
          <a class="nav-link" href="https://dr3d.github.io/prolog-reasoning-v2/docs-hub.html">Back to Docs Hub</a>
          <a class="nav-link" href="https://github.com/dr3d/prolog-reasoning-v2">View Repo</a>
        </div>
        <button id="theme-toggle" class="theme-btn" aria-label="Toggle dark and light theme">theme: light</button>
      </div>
    </div>
    <div class=\"meta\">Captured: {html.escape(transcript['captured_at'])} | Model: {html.escape(transcript['model'])} | Integration: {html.escape(transcript['integration'])}</div>
    <div class=\"summary-box\">Step expectations met: {pass_count}/{len(STEP_NAMES)} (natural phrasing, not exact tool-name utterances)</div>
    {body}
  </div>
  <script>
    (() => {{
      const root = document.documentElement;
      const themeToggle = document.getElementById('theme-toggle');
      const storageKey = 'indie_launch_natural_theme';

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
    json_path = out_dir / "indie-launch-warroom-natural-session.json"
    md_path = out_dir / "indie-launch-warroom-natural-session.md"
    html_path = out_dir / "indie-launch-warroom-natural-session.html"

    json_path.write_text(json.dumps(transcript, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(transcript), encoding="utf-8")
    html_path.write_text(_render_html(transcript), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path), "html": str(html_path)}


def run_capture(
    base_url: str,
    model: str,
    integration: str,
    api_key: str | None,
    out_dir: Path,
    temperature: float,
) -> tuple[dict[str, Any], dict[str, str]]:
    endpoint = f"{base_url.rstrip('/')}/api/v1/chat"
    steps_out: list[dict[str, Any]] = []

    for step in STEP_NAMES:
        prompt = _user_prompt(step)
        payload = {
            "model": model,
            "input": prompt,
            "integrations": [integration],
            "temperature": temperature,
            "context_length": 16000,
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
        "temperature": temperature,
        "steps": steps_out,
        "tool_expectation_report": _step_tool_report({"steps": steps_out}),
    }
    return transcript, _write_outputs(transcript, out_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture natural-language indie launch session and validate tool-selection reliability."
    )
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
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature for the chat call.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("LMSTUDIO_API_KEY") or os.environ.get("OPENAI_API_KEY", ""),
        help="LM Studio API key. Defaults to LMSTUDIO_API_KEY, then OPENAI_API_KEY.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate transcript structure and expected tool selection behavior.",
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
            temperature=args.temperature,
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
