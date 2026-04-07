#!/usr/bin/env python3
"""
Capture an Indie Game Launch War Room MCP session via LM Studio API.

Outputs:
- JSON transcript with tool calls and messages
- Markdown transcript
- Styled HTML transcript suitable for sharing
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
    "ingest",
    "standup",
    "cdn_incident",
    "cert_incident",
    "clarify_intake",
    "recovery",
]
INGEST_EXPECTED_COUNTS = {
    "task(Task).": 15,
    "depends_on(Task, Prereq).": 24,
    "task_supplier(Task, Supplier).": 4,
    "supplier_status(Supplier, Status).": 4,
    "completed(Task).": 4,
    "milestone(M).": 3,
}
INGEST_EXPECTED_ASSERTED_COUNT = 62
REQUIRED_TOOLS = {
    "show_system_info",
    "list_known_facts",
    "reset_kb",
    "bulk_assert_facts",
    "query_rows",
    "query_logic",
    "assert_fact",
    "retract_fact",
    "classify_statement",
    "explain_error",
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
    "duration_days(crash_triage_sweep, 3).",
    "duration_days(final_build_candidate, 2).",
    "duration_days(console_submission, 4).",
    "duration_days(platform_release_slot, 2).",
    "duration_days(localization_pack, 5).",
    "duration_days(day_one_patch, 4).",
    "duration_days(matchmaking_scale_test, 3).",
    "duration_days(global_launch, 1).",
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


def _daily_ops_examples() -> list[dict[str, Any]]:
    return [
        {
            "title": "Coffee-Fueled Standup",
            "question": (
                "Morning all. I have exactly one coffee left and zero patience. "
                "What can we safely start right now, and what is still waiting?"
            ),
            "tool_calls": [
                {"tool": "query_rows", "arguments": {"query": "safe_to_start(Task)."}},
                {"tool": "query_rows", "arguments": {"query": "waiting_on(Task, Prereq)."}},
            ],
            "answer": (
                "Ready-now tasks surface immediately, and waiting tasks show concrete unmet prerequisites. "
                "You can assign owners directly from that deterministic list."
            ),
        },
        {
            "title": "What-If Vendor Shock",
            "question": (
                "Rumor says cloud load-test support might slip. If that happens, what milestones get hit first?"
            ),
            "tool_calls": [
                {"tool": "retract_fact", "arguments": {"fact": "supplier_status(cloud_vendor, on_time)."}},
                {"tool": "assert_fact", "arguments": {"fact": "supplier_status(cloud_vendor, delayed)."}},
                {"tool": "query_rows", "arguments": {"query": "blocked_task(Task, Supplier)."}},
                {"tool": "query_rows", "arguments": {"query": "delayed_milestone(Milestone, Supplier)."}},
            ],
            "answer": (
                "The chain moves from blocked supplier-backed tasks into milestone impact through dependency propagation. "
                "No guesswork needed."
            ),
        },
        {
            "title": "Uncertain Intake",
            "question": "I think launch date might be June 3? Not sure yet.",
            "tool_calls": [
                {"tool": "classify_statement", "arguments": {"text": "I think launch date might be June 3? Not sure yet."}},
            ],
            "answer": (
                "This should classify as tentative and avoid automatic persistence, creating room for clarification first."
            ),
        },
    ]


def _facts_block() -> str:
    return "\n".join(FACTS) + "\n"


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
                "python scripts/capture_indie_launch_warroom_session.py --validate\n"
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


def validate_transcript(transcript: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    steps = transcript.get("steps", [])
    if not isinstance(steps, list):
        return ["Transcript is missing a valid 'steps' list."]

    actual_order = [step.get("step") for step in steps if isinstance(step, dict)]
    if actual_order != STEP_NAMES:
        findings.append(f"Unexpected step order. Expected {STEP_NAMES}, got {actual_order}.")

    by_step: dict[str, dict[str, Any]] = {}
    seen_tools: set[str] = set()
    for step in steps:
        if isinstance(step, dict) and isinstance(step.get("step"), str):
            by_step[step["step"]] = step
            for call in step.get("tool_calls", []):
                if isinstance(call, dict):
                    tool_name = call.get("tool")
                    if isinstance(tool_name, str) and tool_name:
                        seen_tools.add(tool_name)

    for step_name in STEP_NAMES:
        step = by_step.get(step_name)
        if step is None:
            findings.append(f"Missing step '{step_name}'.")
            continue

        tool_calls = step.get("tool_calls", [])
        if not isinstance(tool_calls, list) or not tool_calls:
            findings.append(f"Step '{step_name}' has no tool calls.")

        if not str(step.get("assistant_message", "")).strip():
            findings.append(f"Step '{step_name}' has an empty assistant reply.")

    missing_tools = sorted(REQUIRED_TOOLS - seen_tools)
    if missing_tools:
        findings.append(f"Missing required tool usage: {missing_tools}")

    ingest_step = by_step.get("ingest")
    if ingest_step is not None:
        ingest_calls = ingest_step.get("tool_calls", [])
        if isinstance(ingest_calls, list):
            bulk_call = None
            for call in ingest_calls:
                if isinstance(call, dict) and call.get("tool") == "bulk_assert_facts":
                    bulk_call = call
                    break
            if bulk_call is None:
                findings.append("Ingest step did not call bulk_assert_facts.")
            else:
                bulk_json = _extract_tool_output_json(bulk_call.get("output"))
                if bulk_json is None:
                    findings.append("Ingest bulk_assert_facts output was not parseable JSON.")
                else:
                    asserted_count = bulk_json.get("asserted_count")
                    failed_count = bulk_json.get("failed_count")
                    if asserted_count != INGEST_EXPECTED_ASSERTED_COUNT:
                        findings.append(
                            f"Ingest asserted_count mismatch: expected {INGEST_EXPECTED_ASSERTED_COUNT}, got {asserted_count}."
                        )
                    if failed_count not in (0, None):
                        findings.append(f"Ingest failed_count should be 0, got {failed_count}.")

            for query, expected_rows in INGEST_EXPECTED_COUNTS.items():
                matching_call = None
                for call in ingest_calls:
                    if not isinstance(call, dict) or call.get("tool") != "query_rows":
                        continue
                    args = call.get("arguments", {})
                    if isinstance(args, dict) and args.get("query") == query:
                        matching_call = call
                        break
                if matching_call is None:
                    findings.append(f"Ingest step missing count query '{query}'.")
                    continue
                query_json = _extract_tool_output_json(matching_call.get("output"))
                if query_json is None:
                    findings.append(f"Ingest query output for '{query}' was not parseable JSON.")
                    continue
                actual_rows = query_json.get("num_rows")
                if actual_rows != expected_rows:
                    findings.append(
                        f"Ingest query '{query}' mismatch: expected {expected_rows} rows, got {actual_rows}."
                    )

    clarify_step = by_step.get("clarify_intake")
    if clarify_step is not None:
        tool_calls = clarify_step.get("tool_calls", [])
        classify_calls = [
            call
            for call in tool_calls
            if isinstance(call, dict) and call.get("tool") == "classify_statement"
        ]
        if not classify_calls:
            findings.append("Clarify step is missing classify_statement call.")
        else:
            classify_json = _extract_tool_output_json(classify_calls[0].get("output"))
            if classify_json is None:
                findings.append("Clarify step classify output was not parseable JSON.")
            else:
                if classify_json.get("can_persist_now") is not False:
                    findings.append("Clarify step expected can_persist_now=false for uncertain intake.")
                proposal = classify_json.get("proposal_check")
                if not isinstance(proposal, dict):
                    findings.append("Clarify step expected proposal_check in classify output.")
                elif proposal.get("status") not in {"needs_clarification", "reject"}:
                    findings.append("Clarify step proposal_check should be needs_clarification or reject.")

        write_tools = {"assert_fact", "bulk_assert_facts", "retract_fact", "reset_kb"}
        unexpected_writes = sorted(
            {
                call.get("tool")
                for call in tool_calls
                if isinstance(call, dict) and call.get("tool") in write_tools
            }
        )
        if unexpected_writes:
            findings.append(
                f"Clarify step must not call write tools: {unexpected_writes}"
            )

    return findings


def _user_prompt(step: str) -> str:
    prompts = {
        "preflight": (
            "Quick pulse check before we dive in. I am running on cold brew and optimism.\n"
            "Use show_system_info and list_known_facts first.\n"
            "Then summarize in one paragraph what this MCP setup can and cannot do today."
        ),
        "reset": "Use ONLY reset_kb. Confirm success in one sentence.",
        "ingest": (
            "We're kicking off an indie launch war room simulation.\n"
            "Use bulk_assert_facts with the full fact list below.\n"
            "Then run query_rows counts for:\n"
            "- task(Task).\n"
            "- depends_on(Task, Prereq).\n"
            "- task_supplier(Task, Supplier).\n"
            "- supplier_status(Supplier, Status).\n"
            "- completed(Task).\n"
            "- milestone(M).\n"
            "Expected counts:\n"
            "- task: 15\n"
            "- depends_on: 24\n"
            "- task_supplier: 4\n"
            "- supplier_status: 4\n"
            "- completed: 4\n"
            "- milestone: 3\n"
            "- asserted_count from bulk_assert_facts: 62\n"
            "If anything mismatches, stop and call it out clearly.\n\n"
            + _facts_block()
        ),
        "standup": (
            "Morning standup style, keep it practical.\n"
            "Use ONLY query_rows for these exact queries:\n"
            "- safe_to_start(Task).\n"
            "- waiting_on(Task, Prereq).\n"
            "- task_status(Task, Status).\n"
            "- delayed_milestone(Milestone, Supplier).\n"
            "Then use query_logic once on:\n"
            "depends_on(global_launch, console_submission).\n"
            "Return concise sections: ready now, blockers, waiting chain, milestone risk."
        ),
        "cdn_incident": (
            "Incident update: our cloud contact just pinged me and things look shaky.\n"
            "Use only these tools in order:\n"
            "1) retract_fact supplier_status(cloud_vendor, on_time).\n"
            "2) assert_fact supplier_status(cloud_vendor, delayed).\n"
            "3) query_rows blocked_task(Task, Supplier).\n"
            "4) query_rows delayed_milestone(Milestone, Supplier).\n"
            "5) query_rows task_status(Task, Status).\n"
            "Give me one short propagation narrative and two concrete mitigations."
        ),
        "cert_incident": (
            "Second incident, and yes this is one of those days.\n"
            "Use only these tools in order:\n"
            "1) retract_fact supplier_status(console_cert_vendor, on_time).\n"
            "2) assert_fact supplier_status(console_cert_vendor, delayed).\n"
            "3) query_rows blocked_task(Task, Supplier).\n"
            "4) query_rows delayed_milestone(Milestone, Supplier).\n"
            "5) query_rows waiting_on(Task, Prereq).\n"
            "6) query_logic delayed_milestone(global_launch, console_cert_vendor).\n"
            "Return top 3 interventions to protect global_launch."
        ),
        "clarify_intake": (
            "Incoming producer note in messy human form:\n"
            "\"I think launch date might be June 3, but it is not locked yet\"\n"
            "Use classify_statement on that text and report classification fields.\n"
            "Then use explain_error on:\n"
            "Entity 'mystery_vendor' not in KB\n"
            "Do not write any facts in this step."
        ),
        "recovery": (
            "Recovery pass. Assume we negotiated both vendors back on schedule.\n"
            "Use only these tools in order:\n"
            "1) retract_fact supplier_status(cloud_vendor, delayed).\n"
            "2) assert_fact supplier_status(cloud_vendor, on_time).\n"
            "3) retract_fact supplier_status(console_cert_vendor, delayed).\n"
            "4) assert_fact supplier_status(console_cert_vendor, on_time).\n"
            "5) assert_fact completed(final_build_candidate).\n"
            "6) assert_fact completed(console_submission).\n"
            "7) assert_fact completed(platform_release_slot).\n"
            "8) query_rows safe_to_start(Task).\n"
            "9) query_rows waiting_on(Task, Prereq).\n"
            "10) query_rows delayed_milestone(Milestone, Supplier).\n"
            "11) query_rows task_status(Task, Status).\n"
            "Close with: ready now, still waiting, remaining launch risk."
        ),
    }
    return prompts[step]


def _render_markdown(transcript: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Indie Game Launch War Room Session (Captured)")
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
    lines.append("These are intentionally conversational prompts that still map to deterministic tool calls.")
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

    daily_cards: list[str] = []
    for example in _daily_ops_examples():
        question_html = html.escape(example["question"])
        question_attr = html.escape(example["question"], quote=True)
        answer_html = html.escape(example["answer"])
        call_items = []
        for call in example["tool_calls"]:
            args = html.escape(json.dumps(call["arguments"], ensure_ascii=True))
            call_items.append(f"<li><code>{html.escape(call['tool'])}</code> <code>{args}</code></li>")
        tool_count = len(example["tool_calls"])
        calls_body = "<ul>" + "".join(call_items) + "</ul>"
        calls_html = (
            "<details class=\"toolbox tool-expando\">"
            f"<summary><span class=\"expando-title\">tool calls</span><span class=\"expando-count\">{tool_count}</span></summary>"
            f"{calls_body}"
            "</details>"
        )
        daily_cards.append(
            f"""
<section class="step-card">
  <h2>{html.escape(example["title"])}</h2>
  <div class="bubble user">
    <div class="bubble-head">
      <div class="label">User</div>
      <button class="copy-btn" data-copy="{question_attr}" aria-label="Copy user prompt">copy</button>
    </div>
    <pre>{question_html}</pre>
  </div>
  {calls_html}
  <div class="bubble assistant"><div class="label">Assistant</div><pre>{answer_html}</pre></div>
</section>
""".strip()
        )

    body = "\n".join(cards)
    daily_body = "\n".join(daily_cards)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Indie Game Launch War Room Session</title>
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
      <h1>Indie Game Launch War Room Session</h1>
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
        <pre>These snippets intentionally mix normal human phrasing with deterministic tool use, so new users can see natural chat behavior without losing rigor.</pre>
      </div>
    </section>
    {daily_body}
  </div>
  <script>
    (() => {{
      const root = document.documentElement;
      const themeToggle = document.getElementById('theme-toggle');
      const storageKey = 'indie_launch_playbook_theme';

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
    json_path = out_dir / "indie-launch-warroom-session.json"
    md_path = out_dir / "indie-launch-warroom-session.md"
    html_path = out_dir / "indie-launch-warroom-session.html"

    json_path.write_text(json.dumps(transcript, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(transcript), encoding="utf-8")
    html_path.write_text(_render_html(transcript), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path), "html": str(html_path)}


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
        "steps": steps_out,
    }
    return transcript, _write_outputs(transcript, out_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture indie launch war-room session via LM Studio API.")
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
        help="Validate transcript structure and ingest/count invariants after capture/render.",
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
