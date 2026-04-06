#!/usr/bin/env python3
"""
Capture a fantasy multi-character simulation session via LM Studio + MCP.

Outputs:
- JSON transcript with tool calls and per-turn fact deltas
- Markdown transcript
- Styled HTML transcript with an "overlord" delta panel
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

DISPLAY_TOOL_ALIASES = {
    "query_prolog_raw": "query_logic",
    "query_prolog_rows_raw": "query_rows",
    "assert_fact_raw": "assert_fact",
    "bulk_assert_facts_raw": "bulk_assert_facts",
    "retract_fact_raw": "retract_fact",
    "reset_runtime_kb": "reset_kb",
}

FACTS = [
    "character(aria).",
    "character(borin).",
    "character(mara).",
    "character(silas).",
    "location(tower).",
    "location(market).",
    "location(docks).",
    "location(ruins).",
    "location(forest).",
    "connected(tower, market).",
    "connected(market, tower).",
    "connected(market, docks).",
    "connected(docks, market).",
    "connected(market, forest).",
    "connected(forest, market).",
    "connected(forest, ruins).",
    "connected(ruins, forest).",
    "at(aria, docks).",
    "at(borin, market).",
    "at(mara, ruins).",
    "at(silas, market).",
    "faction(aria, guild).",
    "faction(borin, guild).",
    "faction(mara, legion).",
    "faction(silas, rogue).",
    "has_item(aria, map_fragment).",
    "has_item(aria, copper_key).",
    "has_item(borin, ore_crate).",
    "has_item(borin, shield).",
    "has_item(mara, charm_scroll).",
    "has_item(silas, healing_herb).",
    "hp(aria, 8).",
    "hp(borin, 12).",
    "hp(mara, 10).",
    "hp(silas, 7).",
    "status(aria, normal).",
    "status(borin, normal).",
    "status(mara, normal).",
    "status(silas, normal).",
    "weather(clear).",
    "time_of_day(day).",
    "insomnia(silas).",
    "quest_active(relic_hunt).",
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


def _facts_block() -> str:
    return "\n".join(FACTS) + "\n"


def _user_prompt(step: str) -> str:
    prompts = {
        "reset": "Use ONLY reset_kb. Confirm success in one sentence.",
        "ingest": (
            "Use bulk_assert_facts with the full fact list below.\n"
            "Then verify counts with query_rows for:\n"
            "- character(C).\n"
            "- location(L).\n"
            "- at(C, L).\n"
            "- has_item(C, I).\n"
            "- connected(A, B).\n"
            "- status(C, S).\n"
            "Return row counts and stop if anything mismatches.\n\n"
            + _facts_block()
        ),
        "snapshot": (
            "Control-room baseline. Use query_rows only, then summarize in 5 bullets.\n"
            "Queries:\n"
            "1) at(C, L).\n"
            "2) has_item(C, I).\n"
            "3) awake(C).\n"
            "4) can_move(C, To).\n"
            "5) can_trade(A, B, L).\n"
            "6) high_risk(C).\n"
            "7) can_cast_charm(Caster, Target, L).\n"
            "Label each table."
        ),
        "storm_turn": (
            "Run this event turn in order:\n"
            "1) retract_fact time_of_day(day).\n"
            "2) assert_fact time_of_day(night).\n"
            "3) retract_fact weather(clear).\n"
            "4) assert_fact weather(storm).\n"
            "5) assert_fact status(aria, soaked).\n"
            "6) assert_fact status(silas, soaked).\n"
            "7) query_rows asleep(C).\n"
            "8) query_rows awake(C).\n"
            "9) query_rows exposed(C).\n"
            "10) query_rows high_risk(C).\n"
            "Then provide a short ops update and one immediate recommendation."
        ),
        "market_turn": (
            "Run this turn in order:\n"
            "1) retract_fact at(aria, docks).\n"
            "2) assert_fact at(aria, market).\n"
            "3) retract_fact has_item(silas, healing_herb).\n"
            "4) assert_fact has_item(aria, healing_herb).\n"
            "5) query_rows at(C, L).\n"
            "6) query_rows has_item(C, I).\n"
            "7) query_rows can_trade(A, B, L).\n"
            "8) query_rows high_risk(C).\n"
            "Report what changed in locality and inventory."
        ),
        "charm_turn": (
            "Pause and patch the world, then resume:\n"
            "1) query_rows can_cast_charm(Caster, Target, L).\n"
            "2) assert_fact insomnia(aria).\n"
            "3) assert_fact status(mara, guard_duty).\n"
            "4) retract_fact at(mara, ruins).\n"
            "5) assert_fact at(mara, market).\n"
            "6) query_rows can_cast_charm(Caster, Target, L).\n"
            "7) assert_fact charmed(aria, mara).\n"
            "8) query_rows charmed(Target, By).\n"
            "9) query_rows threatened(C).\n"
            "Explain which edit unlocked the charm interaction and why."
        ),
        "recovery_turn": (
            "Run recovery turn:\n"
            "1) retract_fact charmed(aria, mara).\n"
            "2) retract_fact status(mara, guard_duty).\n"
            "3) assert_fact status(mara, normal).\n"
            "4) retract_fact status(aria, soaked).\n"
            "5) assert_fact status(aria, normal).\n"
            "6) retract_fact status(silas, soaked).\n"
            "7) assert_fact status(silas, normal).\n"
            "8) retract_fact time_of_day(night).\n"
            "9) assert_fact time_of_day(day).\n"
            "10) query_rows awake(C).\n"
            "11) query_rows can_trade(A, B, L).\n"
            "12) query_rows high_risk(C).\n"
            "13) query_rows charmed(Target, By).\n"
            "Provide end-of-turn report: stable state, unresolved risks, next move."
        ),
    }
    return prompts[step]


def _extract_delta(tool_calls: list[dict[str, Any]]) -> dict[str, list[str]]:
    added: list[str] = []
    removed: list[str] = []
    for call in tool_calls:
        tool = call.get("tool", "")
        args = call.get("arguments", {})
        if not isinstance(args, dict):
            continue
        if tool in {"assert_fact", "assert_fact_raw"}:
            fact = str(args.get("fact", "")).strip()
            if fact:
                added.append(fact if fact.endswith(".") else fact + ".")
        elif tool in {"retract_fact", "retract_fact_raw"}:
            fact = str(args.get("fact", "")).strip()
            if fact:
                removed.append(fact if fact.endswith(".") else fact + ".")
        elif tool in {"bulk_assert_facts", "bulk_assert_facts_raw"}:
            for fact in args.get("facts", []):
                text = str(fact).strip()
                if text:
                    added.append(text if text.endswith(".") else text + ".")

    def _dedupe(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    return {"added": _dedupe(added), "removed": _dedupe(removed)}


def _display_tool_name(name: str) -> str:
    return DISPLAY_TOOL_ALIASES.get(name, name)


def _decode_tool_output(raw_output: Any) -> tuple[str, str]:
    """Return (summary, pretty_details) for a captured MCP tool output payload."""
    parsed: Any = raw_output
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except Exception:
            return ("unparsed output", parsed)

    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict) and "text" in parsed[0]:
        text_blob = str(parsed[0].get("text", ""))
        try:
            parsed = json.loads(text_blob)
        except Exception:
            return ("text output", text_blob)

    if isinstance(parsed, dict):
        status = str(parsed.get("status", "unknown"))
        result_type = str(parsed.get("result_type", "result"))
        predicate = str(parsed.get("predicate", ""))
        num_rows = parsed.get("num_rows")
        parts = [status, result_type]
        if predicate:
            parts.append(f"predicate={predicate}")
        if isinstance(num_rows, int):
            parts.append(f"rows={num_rows}")
        summary = " | ".join(parts)
        return (summary, json.dumps(parsed, indent=2))

    return ("raw output", json.dumps(parsed, indent=2) if not isinstance(parsed, str) else parsed)


def _render_markdown(transcript: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Fantasy Overlord Simulation Session (Captured)")
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
        if step["tool_calls"]:
            for call in step["tool_calls"]:
                lines.append(f"- `{_display_tool_name(call['tool'])}` `{json.dumps(call['arguments'], ensure_ascii=True)}`")
        else:
            lines.append("- (none)")
        lines.append("")
        lines.append("### Prolog Console")
        lines.append("")
        if step["tool_calls"]:
            for call in step["tool_calls"]:
                summary, details = _decode_tool_output(call.get("output"))
                lines.append(f"- `{_display_tool_name(call['tool'])}`: {summary}")
                lines.append("```json")
                lines.append(details.rstrip())
                lines.append("```")
        else:
            lines.append("- (none)")
        lines.append("")
        lines.append("### Overlord Delta")
        lines.append("")
        delta = step["delta"]
        lines.append(f"- Added facts: {len(delta['added'])}")
        lines.append(f"- Removed facts: {len(delta['removed'])}")
        if delta["added"]:
            lines.append("- Added:")
            for item in delta["added"]:
                lines.append(f"  - `{item}`")
        if delta["removed"]:
            lines.append("- Removed:")
            for item in delta["removed"]:
                lines.append(f"  - `{item}`")
        lines.append("")
        lines.append("### Assistant Reply")
        lines.append("")
        lines.append(step["assistant_message"].rstrip() or "(empty reply)")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_html(transcript: dict[str, Any]) -> str:
    cards: list[str] = []
    for step in transcript["steps"]:
        prompt_html = html.escape(step["prompt"])
        prompt_attr = html.escape(step["prompt"], quote=True)
        reply_html = html.escape(step["assistant_message"] or "(empty reply)")
        call_items = []
        console_items = []
        for call in step["tool_calls"]:
            args = html.escape(json.dumps(call["arguments"], ensure_ascii=True))
            displayed_tool = _display_tool_name(str(call["tool"]))
            call_items.append(f"<li><code>{html.escape(displayed_tool)}</code> <code>{args}</code></li>")
            summary, details = _decode_tool_output(call.get("output"))
            console_items.append(
                "<details class='console-item'>"
                f"<summary><code>{html.escape(displayed_tool)}</code> - {html.escape(summary)}</summary>"
                f"<pre>{html.escape(details)}</pre>"
                "</details>"
            )
        calls_html = "<ul>" + "".join(call_items) + "</ul>" if call_items else "<p>No tool calls.</p>"
        console_html = "".join(console_items) if console_items else "<p>No console output.</p>"

        added_items = "".join(f"<li><code>{html.escape(x)}</code></li>" for x in step["delta"]["added"])
        removed_items = "".join(f"<li><code>{html.escape(x)}</code></li>" for x in step["delta"]["removed"])
        delta_html = (
            "<div class='delta-grid'>"
            f"<div><div class='label'>Added ({len(step['delta']['added'])})</div><ul>{added_items or '<li>(none)</li>'}</ul></div>"
            f"<div><div class='label'>Removed ({len(step['delta']['removed'])})</div><ul>{removed_items or '<li>(none)</li>'}</ul></div>"
            "</div>"
        )

        cards.append(
            f"""
<section class="step-card">
  <h2>{html.escape(step["step"])}</h2>
  <div class="step-layout">
    <div>
      <div class="bubble user">
        <div class="bubble-head">
          <div class="label">User</div>
          <button class="copy-btn" data-copy="{prompt_attr}" aria-label="Copy user prompt">[copy]</button>
        </div>
        <pre>{prompt_html}</pre>
      </div>
      <div class="toolbox"><div class="label">Tool Calls</div>{calls_html}</div>
      <div class="overlord"><div class="label">Overlord Delta</div>{delta_html}</div>
      <div class="bubble assistant"><div class="label">Assistant</div><pre>{reply_html}</pre></div>
    </div>
    <aside class="console-pane">
      <div class="label">Prolog Console</div>
      {console_html}
    </aside>
  </div>
</section>
""".strip()
        )

    body = "\n".join(cards)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Fantasy Overlord Simulation Session</title>
  <style>
    :root {{
      --bg: #e2ddd3;
      --panel: #ebe6dd;
      --ink: #21201c;
      --muted: #5d584f;
      --user: #ddd1bf;
      --assistant: #cbd8e6;
      --tool: #d7e2d4;
      --delta: #e5d3d1;
      --border: #c1b8a9;
      --good: #2d6631;
      --bad: #8b3131;
    }}
    html[data-theme="dark"] {{
      --bg: #151920;
      --panel: #1f2530;
      --ink: #e8edf3;
      --muted: #b4c0cc;
      --user: #3d3125;
      --assistant: #22384f;
      --tool: #293626;
      --delta: #3a2828;
      --border: #3a4654;
      --good: #9fe0a6;
      --bad: #ff8f8f;
    }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.35;
    }}
    .wrap {{
      max-width: 1160px;
      margin: 0 auto;
      padding: 24px;
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
    h1 {{
      margin: 0 0 8px 0;
      font-size: 34px;
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
      margin-top: 4px;
    }}
    .meta {{
      font-family: "Courier New", monospace;
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 16px;
    }}
    .legend {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 10px 12px;
      margin-bottom: 14px;
      font-family: "Courier New", monospace;
      font-size: 12px;
      color: var(--muted);
    }}
    .step-card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 14px;
      margin-bottom: 14px;
    }}
    h2 {{
      margin: 0 0 10px 0;
      font-size: 22px;
    }}
    .bubble, .toolbox, .overlord {{
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 10px;
      margin-bottom: 10px;
    }}
    .bubble.user {{ background: var(--user); }}
    .bubble.assistant {{ background: var(--assistant); }}
    .toolbox {{ background: var(--tool); font-family: "Courier New", monospace; font-size: 13px; }}
    .overlord {{ background: var(--delta); }}
    .step-layout {{
      display: grid;
      grid-template-columns: minmax(0, 2fr) minmax(290px, 1fr);
      gap: 12px;
      align-items: start;
    }}
    .console-pane {{
      background: color-mix(in srgb, var(--panel) 90%, black);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 10px;
      max-height: 640px;
      overflow: auto;
      position: sticky;
      top: 12px;
    }}
    .console-item {{
      border: 1px solid var(--border);
      border-radius: 8px;
      margin-bottom: 8px;
      background: color-mix(in srgb, var(--panel) 94%, black);
    }}
    .console-item summary {{
      padding: 8px 10px;
      cursor: pointer;
      font-family: "Courier New", monospace;
      font-size: 12px;
      color: var(--ink);
    }}
    .console-item pre {{
      margin: 0;
      padding: 0 10px 10px 10px;
      font-size: 12px;
    }}
    .label {{
      font-size: 11px;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: var(--muted);
      font-family: "Courier New", monospace;
      margin-bottom: 8px;
    }}
    .bubble-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 6px;
    }}
    .copy-btn {{
      border: 1px solid var(--border);
      background: #fff4df;
      border-radius: 8px;
      color: #3d372d;
      font-family: "Courier New", monospace;
      font-size: 12px;
      line-height: 1;
      padding: 6px 8px;
      cursor: pointer;
    }}
    .copy-btn.copied {{
      background: #dff0d8;
      color: #2f5f2f;
    }}
    .delta-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      font-family: "Courier New", monospace;
      font-size: 12px;
    }}
    .delta-grid ul {{
      margin: 0;
      padding-left: 16px;
      max-height: 180px;
      overflow: auto;
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
    @media (max-width: 900px) {{
      .delta-grid {{
        grid-template-columns: 1fr;
      }}
      .step-layout {{
        grid-template-columns: 1fr;
      }}
      .console-pane {{
        position: static;
        max-height: none;
      }}
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
      <h1>Fantasy Overlord Simulation Session</h1>
      <div class="topbar-right">
        <div class="nav-links">
          <a class="nav-link" href="./docs-hub.html">Back to Docs Hub</a>
          <a class="nav-link" href="https://github.com/dr3d/prolog-reasoning-v2">View Repo</a>
        </div>
        <button id="theme-toggle" class="theme-btn" aria-label="Toggle dark and light theme">theme: light</button>
      </div>
    </div>
    <div class="meta">Captured: {html.escape(transcript["captured_at"])} | Model: {html.escape(transcript["model"])} | Integration: {html.escape(transcript["integration"])}</div>
    <div class="legend">Overlord view: every step captures user instruction, tool calls, and a deterministic fact delta extracted from assert/retract operations.</div>
    {body}
  </div>
  <script>
    (() => {{
      const root = document.documentElement;
      const toggle = document.getElementById('theme-toggle');
      const key = 'fantasy_overlord_theme';
      const setTheme = (theme) => {{
        root.setAttribute('data-theme', theme);
        if (toggle) {{
          toggle.textContent = theme === 'dark' ? 'theme: dark' : 'theme: light';
        }}
      }};
      const stored = window.localStorage.getItem(key);
      if (stored === 'dark' || stored === 'light') {{
        setTheme(stored);
      }} else {{
        const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        setTheme(prefersDark ? 'dark' : 'light');
      }}
      if (toggle) {{
        toggle.addEventListener('click', () => {{
          const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
          setTheme(next);
          window.localStorage.setItem(key, next);
        }});
      }}
      const buttons = document.querySelectorAll('.copy-btn');
      for (const button of buttons) {{
        button.addEventListener('click', async () => {{
          const before = '[copy]';
          const text = button.getAttribute('data-copy') || '';
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
    json_path = out_dir / "fantasy-overlord-session.json"
    md_path = out_dir / "fantasy-overlord-session.md"
    html_path = out_dir / "fantasy-overlord-session.html"
    json_path.write_text(json.dumps(transcript, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(transcript), encoding="utf-8")
    html_path.write_text(_render_html(transcript), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path), "html": str(html_path)}


def run_capture(base_url: str, model: str, integration: str, api_key: str | None, out_dir: Path) -> dict[str, str]:
    endpoint = f"{base_url.rstrip('/')}/api/v1/chat"
    step_names = ["reset", "ingest", "snapshot", "storm_turn", "market_turn", "charm_turn", "recovery_turn"]
    steps: list[dict[str, Any]] = []
    for step in step_names:
        prompt = _user_prompt(step)
        payload = {
            "model": model,
            "input": prompt,
            "integrations": [integration],
            "temperature": 0,
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
        steps.append(
            {
                "step": step,
                "prompt": prompt,
                "tool_calls": tool_calls,
                "delta": _extract_delta(tool_calls),
                "assistant_message": assistant_message,
            }
        )

    transcript = {
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "model": model,
        "integration": integration,
        "steps": steps,
    }
    return _write_outputs(transcript, out_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture fantasy overlord simulation session via LM Studio API.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="LM Studio API base URL")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model id from LM Studio /v1/models")
    parser.add_argument("--integration", default=DEFAULT_INTEGRATION, help="MCP integration id")
    parser.add_argument("--out-dir", default="docs/examples", help="Output directory for transcript artifacts")
    parser.add_argument("--input-json", default="", help="Render markdown/html from an existing transcript JSON.")
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
