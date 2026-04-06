#!/usr/bin/env python3
"""
Level-4 demo: LLM + MCP builds a rule-derived access table.

This script asks a local model to call MCP tools and generate a spreadsheet-like
table from deterministic permission checks.
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


USERS = ["alice", "bob", "john"]
ACTIONS = ["read", "write"]


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


def _short(text: Any, limit: int = 220) -> str:
    value = str(text)
    if len(value) > limit:
        return value[:limit] + "..."
    return value


def _infer_yes_no(text: str) -> str:
    head = text.strip().lower()
    if re.search(r"\byes\b", head):
        return "yes"
    if re.search(r"\bno\b", head):
        return "no"
    return "unknown"


def _markdown_table(rows: list[dict[str, str]]) -> str:
    headers = ["user", "can_read", "can_write", "evidence_summary"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row[h] for h in headers) + " |")
    return "\n".join(lines)


def run_demo(base_url: str, model: str, integration: str, api_key: str | None) -> None:
    endpoint = f"{base_url.rstrip('/')}/api/v1/chat"

    print("RULE TABLE AGENT + MCP DEMO")
    print("=" * 60)
    print(f"Model: {model}")
    print(f"Integration: {integration}")
    print(f"Endpoint: {endpoint}")
    print()

    rows: list[dict[str, str]] = []

    for user in USERS:
        evidence_parts: list[str] = []
        answers: dict[str, str] = {}
        print(f"User: {user}")

        for action in ACTIONS:
            raw_query = f"allowed({user}, {action})."
            prompt = (
                "Call query_prolog_raw exactly once with this query: "
                f"{raw_query} "
                "Then answer with YES or NO on the first line and one short evidence sentence."
            )
            print(f"  Prompt: {prompt}")

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
            verdict = _infer_yes_no(final_message)
            answers[action] = verdict
            evidence_parts.append(f"{action}: {final_message.replace('|', '/')}")

            if not tool_calls:
                print("    Tool calls: none (model did not use MCP tool)")
            else:
                print(f"    Tool calls: {len(tool_calls)}")
                for call in tool_calls:
                    tool = call.get("tool", "<unknown>")
                    arguments = json.dumps(call.get("arguments", {}), ensure_ascii=True)
                    output_summary = _short(call.get("output", ""))
                    print(f"      - {tool} {arguments}")
                    print(f"        output: {output_summary}")

            print(f"    Final answer: {final_message}")

        rows.append(
            {
                "user": user,
                "can_read": answers.get("read", "unknown"),
                "can_write": answers.get("write", "unknown"),
                "evidence_summary": " || ".join(evidence_parts),
            }
        )
        print("-" * 60)

    print("RULE-DERIVED TABLE (LLM + MCP)")
    print(_markdown_table(rows))
    print("-" * 60)

    summary_prompt = (
        "Use query_prolog to answer: Why does Bob fail permission checks in this knowledge base? "
        "Return a short deterministic explanation."
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
    print("If tool calls appear above, the model is overtly using deterministic logic.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run level-4 rule-table MCP demo via LM Studio API.")
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
    key = args.api_key or None

    try:
        run_demo(args.base_url, args.model, args.integration, key)
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
