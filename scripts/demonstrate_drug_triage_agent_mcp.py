#!/usr/bin/env python3
"""
Level-6 demo: LLM + MCP produces deterministic clinical triage.

The model orchestrates tool calls and summarizes results; the symbolic layer
decides risk status through explicit rules.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:1234"
DEFAULT_MODEL = "qwen3.5-4b"
DEFAULT_INTEGRATION = "mcp/prolog-reasoning"

PATIENT = "alice"
CANDIDATE_DRUGS = ["acetaminophen", "naproxen", "amoxicillin", "clopidogrel"]


def _post_json(url: str, payload: dict[str, Any], api_key: str | None) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url=url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    if api_key:
        request.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code}: {raw}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Connection error: {error}") from error


def _extract_message(items: list[dict[str, Any]]) -> str:
    messages = [item.get("content", "").strip() for item in items if item.get("type") == "message"]
    messages = [message for message in messages if message]
    return messages[-1] if messages else "(no assistant message produced)"


def _extract_tool_calls(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if item.get("type") == "tool_call"]


def _short(text: Any, limit: int = 240) -> str:
    value = str(text)
    return value if len(value) <= limit else value[:limit] + "..."


def _infer_status(text: str) -> str:
    lowered = text.lower()
    if "contraindicated" in lowered:
        return "contraindicated"
    if "caution" in lowered:
        return "caution"
    if "safe" in lowered:
        return "safe"
    return "unknown"


def _markdown_table(rows: list[dict[str, str]]) -> str:
    headers = ["patient", "candidate_drug", "status", "agent_evidence"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row[h] for h in headers) + " |")
    return "\n".join(lines)


def run_demo(base_url: str, model: str, integration: str, api_key: str | None) -> None:
    endpoint = f"{base_url.rstrip('/')}/api/v1/chat"

    print("CLINICAL TRIAGE AGENT + MCP DEMO")
    print("=" * 60)
    print(f"Model: {model}")
    print(f"Integration: {integration}")
    print(f"Endpoint: {endpoint}")
    print()

    rows: list[dict[str, str]] = []
    for drug in CANDIDATE_DRUGS:
        prompt = (
            "Call query_logic exactly once with this query: "
            f"triage({PATIENT}, {drug}, Status, Reason). "
            "If no result exists, mark SAFE. "
            "Return one line in this format: STATUS=<value>; REASON=<short reason>."
        )
        print(f"Prompt ({drug}): {prompt}")

        payload = {
            "model": model,
            "input": prompt,
            "integrations": [integration],
            "temperature": 0,
            "context_length": 8000,
        }
        response = _post_json(endpoint, payload, api_key)
        items = response.get("output", [])
        tool_calls = _extract_tool_calls(items)
        final_message = _extract_message(items)
        status = _infer_status(final_message)

        if not tool_calls:
            print("  Tool calls: none (model did not use MCP tool)")
        else:
            print(f"  Tool calls: {len(tool_calls)}")
            for call in tool_calls:
                print(f"    - {call.get('tool', '<unknown>')} {json.dumps(call.get('arguments', {}), ensure_ascii=True)}")
                print(f"      output: {_short(call.get('output', ''))}")

        print(f"  Final answer: {final_message}")
        print("-" * 60)

        rows.append(
            {
                "patient": PATIENT,
                "candidate_drug": drug,
                "status": status,
                "agent_evidence": final_message.replace("|", "/"),
            }
        )

    print("TRIAGE TABLE (LLM + MCP)")
    print(_markdown_table(rows))
    print("-" * 60)

    summary_prompt = (
        f"Use query_logic with safe_candidate({PATIENT}, Drug). "
        "Then answer in two sentences: which option is safest and why."
    )
    print("Summary prompt:")
    print(f"  {summary_prompt}")
    payload = {
        "model": model,
        "input": summary_prompt,
        "integrations": [integration],
        "temperature": 0,
        "context_length": 8000,
    }
    response = _post_json(endpoint, payload, api_key)
    items = response.get("output", [])
    tool_calls = _extract_tool_calls(items)
    final_message = _extract_message(items)

    if tool_calls:
        print(f"Summary tool calls: {len(tool_calls)}")
    else:
        print("Summary tool calls: none")
    print("Summary answer:")
    print(final_message)

    print()
    print("Demo complete.")
    print("If MCP tool calls appear, the model is using deterministic triage rules.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run clinical-triage MCP demo via LM Studio API.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="LM Studio API base URL")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model id from LM Studio /v1/models")
    parser.add_argument("--integration", default=DEFAULT_INTEGRATION, help="MCP integration id")
    parser.add_argument(
        "--api-key",
        default=os.environ.get("LMSTUDIO_API_KEY", ""),
        help="LM Studio API key. Defaults to LMSTUDIO_API_KEY env var.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_key = args.api_key or None

    try:
        run_demo(args.base_url, args.model, args.integration, api_key)
        return 0
    except Exception as error:
        print("Demo failed:")
        print(f"  {error}")
        print()
        print("Tips:")
        print("  - Make sure LM Studio server is running.")
        print("  - Make sure mcp/prolog-reasoning is enabled.")
        print("  - If auth is enabled, set LMSTUDIO_API_KEY or pass --api-key.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
