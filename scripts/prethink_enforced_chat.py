#!/usr/bin/env python3
"""
Pre-think enforced chat gateway for LM Studio.

This script enforces a pipeline:
  user input -> pre_think (when session-enabled) -> main model chat call

Why this exists:
- In UI-only tool mode, smaller models may skip tool calls.
- This gateway enforces pre_think in the orchestration layer instead of relying on model behavior.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from mcp_server import PrologMCPServer


DEFAULT_BASE_URL = "http://127.0.0.1:1234"
DEFAULT_MODEL = "qwen/qwen3.5-9b"
DEFAULT_INTEGRATION = "mcp/prolog-reasoning"
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_CONTEXT_LENGTH = 4000
DEFAULT_TEMPERATURE = 0.0


def _post_json(
    *,
    url: str,
    payload: Dict[str, Any],
    api_key: str | None,
    timeout_seconds: int,
) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url=url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    if api_key:
        request.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code}: {raw}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Connection error: {error}") from error


def _extract_message_text(response: Dict[str, Any]) -> str:
    items = response.get("output", [])
    if not isinstance(items, list):
        return ""
    parts: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        content = item.get("content")
        if isinstance(content, str) and content.strip():
            parts.append(content.strip())
            continue
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    text = block.get("text")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
    return "\n\n".join(parts).strip()


def _looks_like_prethink_toggle(text: str) -> bool:
    lowered = text.strip().lower()
    return ("prethink" in lowered) or ("pre-think" in lowered) or ("pre_think" in lowered)


def _session_enabled(server: PrologMCPServer) -> bool:
    state = server.show_pre_think_state(include_history=False)
    session = state.get("pre_think_session", {})
    return bool(session.get("enabled", False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enforced pre-think LM Studio chat gateway.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="LM Studio API base URL")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Main chat model")
    parser.add_argument("--integration", default=DEFAULT_INTEGRATION, help="MCP integration id")
    parser.add_argument("--kb-path", default="prolog/core.pl", help="KB path for local mcp_server instance")
    parser.add_argument("--api-key", default="", help="Optional LM Studio API key override")
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--context-length", type=int, default=DEFAULT_CONTEXT_LENGTH)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument(
        "--pre-think-handoff-mode",
        default="rewrite",
        choices=["rewrite", "answer_proxy"],
        help="Default handoff mode used when pre-think session is enabled.",
    )
    parser.add_argument(
        "--pre-think-kb-ingest-mode",
        default="none",
        choices=["none", "facts"],
        help="Default kb_ingest_mode used when pre-think session is enabled.",
    )
    parser.add_argument(
        "--disable-pre-think",
        action="store_true",
        help="Start with pre-think session disabled (raw passthrough until enabled).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_key = args.api_key.strip() or os.environ.get("LMSTUDIO_API_KEY", "").strip() or None

    server = PrologMCPServer(kb_path=args.kb_path)
    server.set_pre_think_session(
        enabled=not args.disable_pre_think,
        handoff_mode=args.pre_think_handoff_mode,
        kb_ingest_mode=args.pre_think_kb_ingest_mode,
    )

    endpoint = f"{args.base_url.rstrip('/')}/api/v1/chat"
    print("Pre-think enforced chat started.")
    print("Commands: /quit, /status, /prethink on, /prethink off")
    while True:
        try:
            user_text = input("you> ").strip()
        except EOFError:
            print()
            break
        if not user_text:
            continue
        if user_text in {"/quit", "/exit"}:
            break
        if user_text == "/status":
            state = server.show_pre_think_state(include_history=False)
            session = state.get("pre_think_session", {})
            print(
                "session> "
                f"enabled={session.get('enabled')} "
                f"handoff_mode={session.get('handoff_mode')} "
                f"kb_ingest_mode={session.get('kb_ingest_mode')}"
            )
            continue
        if user_text == "/prethink on":
            result = server.set_pre_think_session(enabled=True)
            print(f"session> {result.get('note')}")
            continue
        if user_text == "/prethink off":
            result = server.set_pre_think_session(enabled=False)
            print(f"session> {result.get('note')}")
            continue

        apply_pre_think = _session_enabled(server) or _looks_like_prethink_toggle(user_text)
        prompt_for_main = user_text

        if apply_pre_think:
            pre = server.pre_think(user_text)
            if pre.get("status") != "success":
                print(f"pre_think_error> {pre.get('message', pre)}")
            else:
                session_directive = pre.get("session_directive", {})
                if session_directive.get("detected"):
                    action = session_directive.get("action")
                    print(f"pre_think_session> directive applied: {action}")
                    # Do not forward pure mode-toggle directives to the main model.
                    continue
                prompt_for_main = str(pre.get("processed_utterance", user_text))
                print(f"pre_think> {prompt_for_main}")

        payload = {
            "model": args.model,
            "input": prompt_for_main,
            "temperature": float(args.temperature),
            "context_length": int(args.context_length),
            "integrations": [args.integration],
        }
        try:
            response = _post_json(
                url=endpoint,
                payload=payload,
                api_key=api_key,
                timeout_seconds=int(args.timeout_seconds),
            )
        except Exception as error:
            print(f"error> {error}")
            continue

        assistant_text = _extract_message_text(response) or "(empty response)"
        print(f"assistant> {assistant_text}")

    print("bye.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
