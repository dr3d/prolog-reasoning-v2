#!/usr/bin/env python3
"""
Level-2 family tree demo: LLM + MCP tool use.

This script calls LM Studio's chat API and asks a model to explicitly use the
prolog-reasoning MCP integration for family-tree questions.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:1234"
DEFAULT_MODEL = "qwen3.5-4b"
DEFAULT_INTEGRATION = "mcp/prolog-reasoning"


PROMPTS = [
    "Use query_logic to answer with this exact query: parent(john, X).",
    "Use query_logic to answer with this exact query: ancestor(john, bob).",
    "Use query_logic to answer with this exact query: parent(X, alice).",
    "Use classify_statement on: My mother was Ann.",
]


def _post_json(url: str, payload: dict[str, Any], api_key: str | None) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url=url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    if api_key:
        request.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code}: {raw}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Connection error: {error}") from error


def _extract_message(output_items: list[dict[str, Any]]) -> str:
    messages = [item.get("content", "").strip() for item in output_items if item.get("type") == "message"]
    messages = [message for message in messages if message]
    if messages:
        return messages[-1]
    return "(no assistant message produced)"


def _extract_tool_calls(output_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in output_items if item.get("type") == "tool_call"]


def _summarize_tool_output(raw_output: Any) -> str:
    text = str(raw_output)
    if len(text) > 220:
        return text[:220] + "..."
    return text


def run_demo(base_url: str, model: str, integration: str, api_key: str | None) -> None:
    endpoint = f"{base_url.rstrip('/')}/api/v1/chat"

    print("FAMILY TREE AGENT + MCP DEMO")
    print("=" * 60)
    print(f"Model: {model}")
    print(f"Integration: {integration}")
    print(f"Endpoint: {endpoint}")
    print()

    for index, prompt in enumerate(PROMPTS, start=1):
        print(f"{index}. Prompt")
        print(f"   {prompt}")

        payload = {
            "model": model,
            "input": prompt,
            "integrations": [integration],
            "temperature": 0,
            "context_length": 8000,
        }

        response = _post_json(endpoint, payload, api_key)
        output_items = response.get("output", [])
        tool_calls = _extract_tool_calls(output_items)
        final_message = _extract_message(output_items)

        if not tool_calls:
            print("   Tool calls: none (model did not use MCP tool)")
        else:
            print(f"   Tool calls: {len(tool_calls)}")
            for tool_call in tool_calls:
                tool = tool_call.get("tool", "<unknown>")
                arguments = json.dumps(tool_call.get("arguments", {}), ensure_ascii=True)
                summary = _summarize_tool_output(tool_call.get("output", ""))
                print(f"     - {tool} {arguments}")
                print(f"       output: {summary}")

        print("   Final answer:")
        print(f"   {final_message}")
        print("-" * 60)

    print("Demo complete.")
    print("If tool calls appear above, the model is overtly using deterministic logic.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run level-2 family-tree MCP demo via LM Studio API.")
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
