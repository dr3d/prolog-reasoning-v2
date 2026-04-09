#!/usr/bin/env python3
"""
Interactive pre-think switchboard demo.

Purpose:
- Show session-level pre-think toggles in one place.
- Let you turn fact ingestion on/off and inspect resulting KB state.
- Avoid relying on main-model tool discipline while testing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from mcp_server import PrologMCPServer


HELP_TEXT = """\
Commands:
  /help
      Show this help.

  /status
      Show pre-think session state, model, history count, and ingest mode.

  /session on
  /session off
      Enable/disable session-level pre-think preference.

  /mode rewrite
  /mode answer_proxy
      Set session default pre-think handoff mode.

  /ingest on
  /ingest off
      Set session default KB ingest mode:
      on  -> kb_ingest_mode=facts
      off -> kb_ingest_mode=none

  /prethink <utterance>
      Run pre_think using current session defaults.

  /prethink_raw <utterance>
      Run pre_think with forced overrides:
      handoff_mode=rewrite, kb_ingest_mode=none

  /prethink_facts <utterance>
      Run pre_think with forced override:
      kb_ingest_mode=facts

  /query <prolog query>
      Run query_rows against runtime KB.
      Example: /query parent(zoe, X).

  /reset
      Reset runtime KB back to baseline core.pl.

  /empty
      Clear runtime KB to empty state.

  /demo
      Run a guided mini-flow:
      - reset
      - session on + ingest off
      - pre_think fact-like utterance (no ingestion)
      - query check
      - ingest on
      - pre_think fact-like utterance (ingestion enabled)
      - query check

  /quit
      Exit.
"""


def _pretty(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=True)


def _session_snapshot(server: PrologMCPServer) -> dict[str, Any]:
    state = server.show_pre_think_state(include_history=False)
    session = state.get("pre_think_session", {})
    return {
        "enabled": session.get("enabled"),
        "handoff_mode": session.get("handoff_mode"),
        "kb_ingest_mode": session.get("kb_ingest_mode"),
        "model": state.get("pre_think_model"),
        "history_turns": state.get("history_turns"),
        "history_path": state.get("pre_think_history_path"),
    }


def _print_session(server: PrologMCPServer) -> None:
    print(_pretty(_session_snapshot(server)))


def _set_session(
    server: PrologMCPServer,
    *,
    enabled: bool | None = None,
    handoff_mode: str | None = None,
    kb_ingest_mode: str | None = None,
) -> dict[str, Any]:
    snap = _session_snapshot(server)
    enabled_final = snap["enabled"] if enabled is None else enabled
    handoff_final = snap["handoff_mode"] if handoff_mode is None else handoff_mode
    ingest_final = snap["kb_ingest_mode"] if kb_ingest_mode is None else kb_ingest_mode
    return server.set_pre_think_session(
        enabled=enabled_final,
        handoff_mode=handoff_final,
        kb_ingest_mode=ingest_final,
    )


def _print_prethink_result(result: dict[str, Any]) -> None:
    keys = [
        "status",
        "result_type",
        "input_utterance",
        "processed_utterance",
        "handoff_mode",
        "kb_ingest_mode",
        "requested_candidate_facts",
        "attempted_candidate_facts",
        "ingested_facts_count",
        "ingested_facts",
        "rejected_candidate_facts_count",
        "rejected_candidate_facts",
        "normalization_reason",
        "fallback_used",
        "session_directive",
    ]
    slim = {key: result.get(key) for key in keys if key in result}
    print(_pretty(slim))


def _run_demo(server: PrologMCPServer) -> None:
    print("\n[demo] reset_kb")
    print(_pretty(server.reset_kb()))

    print("\n[demo] session on, mode=rewrite, ingest=none")
    print(_pretty(server.set_pre_think_session(enabled=True, handoff_mode="rewrite", kb_ingest_mode="none")))

    utterance_no_ingest = "Data point: Zoe is parent of Yara."
    print(f"\n[demo] pre_think (ingest OFF): {utterance_no_ingest}")
    result_a = server.pre_think(utterance_no_ingest)
    _print_prethink_result(result_a)

    print("\n[demo] query check: parent(zoe, X).")
    print(_pretty(server.query_rows("parent(zoe, X).")))

    print("\n[demo] ingest ON")
    print(_pretty(_set_session(server, kb_ingest_mode="facts")))

    utterance_ingest = "Fact candidate: Zoe is parent of Yara and Yara is parent of Niko."
    print(f"\n[demo] pre_think (ingest ON): {utterance_ingest}")
    result_b = server.pre_think(utterance_ingest)
    _print_prethink_result(result_b)

    print("\n[demo] query check: parent(zoe, X).")
    print(_pretty(server.query_rows("parent(zoe, X).")))
    print("\n[demo] query check: parent(yara, X).")
    print(_pretty(server.query_rows("parent(yara, X).")))

    print("\n[demo] final session snapshot")
    _print_session(server)
    print("")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive pre-think switchboard demo.")
    parser.add_argument("--kb-path", default="prolog/core.pl", help="Path to baseline KB")
    parser.add_argument(
        "--disable-at-start",
        action="store_true",
        help="Start with session-level pre-think disabled.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demo flow once and exit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    server = PrologMCPServer(kb_path=args.kb_path)
    server.set_pre_think_session(
        enabled=not args.disable_at_start,
        handoff_mode="rewrite",
        kb_ingest_mode="none",
    )

    if args.demo:
        _run_demo(server)
        return 0

    print("Pre-think switchboard ready.")
    print("Use /help for commands.\n")
    _print_session(server)

    while True:
        try:
            raw = input("\npt-switch> ").strip()
        except EOFError:
            print("")
            break
        if not raw:
            continue
        if raw in {"/quit", "/exit"}:
            break
        if raw == "/help":
            print(HELP_TEXT)
            continue
        if raw == "/status":
            _print_session(server)
            continue
        if raw == "/reset":
            print(_pretty(server.reset_kb()))
            continue
        if raw == "/empty":
            print(_pretty(server.empty_kb()))
            continue
        if raw == "/demo":
            _run_demo(server)
            continue

        if raw.startswith("/session "):
            value = raw.split(" ", 1)[1].strip().lower()
            if value not in {"on", "off"}:
                print("Use: /session on|off")
                continue
            result = _set_session(server, enabled=(value == "on"))
            print(_pretty(result))
            continue

        if raw.startswith("/mode "):
            value = raw.split(" ", 1)[1].strip().lower()
            if value not in {"rewrite", "answer_proxy"}:
                print("Use: /mode rewrite|answer_proxy")
                continue
            result = _set_session(server, handoff_mode=value)
            print(_pretty(result))
            continue

        if raw.startswith("/ingest "):
            value = raw.split(" ", 1)[1].strip().lower()
            if value not in {"on", "off"}:
                print("Use: /ingest on|off")
                continue
            mode = "facts" if value == "on" else "none"
            result = _set_session(server, kb_ingest_mode=mode)
            print(_pretty(result))
            continue

        if raw.startswith("/query "):
            query = raw.split(" ", 1)[1].strip()
            print(_pretty(server.query_rows(query)))
            continue

        if raw.startswith("/prethink_raw "):
            utterance = raw.split(" ", 1)[1].strip()
            result = server.pre_think(
                utterance,
                handoff_mode="rewrite",
                kb_ingest_mode="none",
            )
            _print_prethink_result(result)
            continue

        if raw.startswith("/prethink_facts "):
            utterance = raw.split(" ", 1)[1].strip()
            result = server.pre_think(
                utterance,
                kb_ingest_mode="facts",
            )
            _print_prethink_result(result)
            continue

        if raw.startswith("/prethink "):
            utterance = raw.split(" ", 1)[1].strip()
            result = server.pre_think(utterance)
            _print_prethink_result(result)
            continue

        print("Unknown command. Use /help.")

    print("bye.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
