#!/usr/bin/env python3
"""
Lightweight docs consistency checks for common drift regressions.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def main() -> int:
    findings: list[str] = []

    def forbid(rel_path: str, phrase: str, reason: str) -> None:
        text = _read(rel_path)
        if phrase in text:
            findings.append(
                f"{rel_path}: found forbidden phrase {phrase!r} ({reason})"
            )

    readme_text = _read("README.md")
    status_text = _read("status.md")
    docs_readme_text = _read("docs/README.md")
    sessions_text = _read("sessions.md")
    operator_brief_text = _read("sessions/operator-brief.md")

    pass_pattern = re.compile(r"(\d+)\s+passed")
    readme_match = pass_pattern.search(readme_text)
    status_match = pass_pattern.search(status_text)
    if not readme_match:
        findings.append("README.md: missing '<N> passed' marker.")
    if not status_match:
        findings.append("status.md: missing '<N> passed' marker.")
    if readme_match and status_match and readme_match.group(1) != status_match.group(1):
        findings.append(
            "README.md and status.md disagree on passing test count "
            f"({readme_match.group(1)} vs {status_match.group(1)})."
        )

    if "(sessions/)" in docs_readme_text or "(sessions/README.md)" in docs_readme_text:
        findings.append(
            "docs/README.md contains broken in-docs sessions links. "
            "Use local-only wording plus ../sessions.md."
        )

    if "latest `sessions/parts/*` file" in sessions_text:
        findings.append(
            "sessions.md read order still includes long-form historical notes by default. "
            "Keep default flow focused on current-state docs."
        )

    if "Then open:" in operator_brief_text and "`sessions/parts/" in operator_brief_text:
        findings.append(
            "sessions/operator-brief.md still directs agents into long-form history by default. "
            "Historical parts should be opt-in/on-request only."
        )

    for rel in (
        "docs/lm-studio-mcp-guide.md",
        "HERMES-AGENT-INSTALL.md",
        "OPENCLAW-AGENT-INSTALL.md",
    ):
        forbid(rel, "all 4 tools", "tool surface expanded beyond 4")
        forbid(rel, "four tools", "tool surface expanded beyond 4")

    forbid(
        "docs/lm-studio-mcp-guide.md",
        "known_relationships",
        "list_known_facts now returns supported_predicates",
    )
    forbid(
        "SKILL.md",
        "does not expose a fact-writing tool",
        "MCP exposes runtime fact mutation tools",
    )

    if findings:
        print("Docs consistency check failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("Docs consistency check passed.")
    if readme_match:
        print(f"Shared pass-count marker: {readme_match.group(1)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
