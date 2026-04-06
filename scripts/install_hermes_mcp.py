#!/usr/bin/env python3
"""
Install/update prolog-reasoning-v2 MCP config for Hermes.

Assumptions:
- The repo is already cloned locally.
- Hermes reads config from ~/.hermes/config.yaml (or a custom path).

This script:
1) Detects repo root (or accepts --repo-root).
2) Creates/updates a server entry under top-level `mcp_servers:`.
3) Creates a timestamped backup before modifying existing config.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _is_top_level_key(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith("#") and _indent(line) == 0 and stripped.endswith(":")


def _build_server_block(
    server_name: str,
    python_exe: Path,
    repo_root: Path,
    enabled: bool,
) -> list[str]:
    mcp_server = repo_root / "src" / "mcp_server.py"
    kb_path = repo_root / "prolog" / "core.pl"

    return [
        f"  {server_name}:\n",
        f'    command: "{python_exe}"\n',
        "    args:\n",
        f'      - "{mcp_server}"\n',
        '      - "--stdio"\n',
        '      - "--kb-path"\n',
        f'      - "{kb_path}"\n',
        "    env:\n",
        '      PYTHONIOENCODING: "utf-8"\n',
        f"    enabled: {'true' if enabled else 'false'}\n",
    ]


def _find_mcp_servers_section(lines: list[str]) -> tuple[int | None, int | None]:
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "mcp_servers:" and _indent(line) == 0:
            start = i
            break
    if start is None:
        return None, None

    end = len(lines)
    for j in range(start + 1, len(lines)):
        if _is_top_level_key(lines[j]):
            end = j
            break
    return start, end


def _find_server_entry(lines: list[str], section_start: int, section_end: int, server_name: str) -> tuple[int | None, int | None]:
    needle = f"{server_name}:"
    start = None
    for i in range(section_start + 1, section_end):
        if lines[i].strip() == needle and _indent(lines[i]) == 2:
            start = i
            break
    if start is None:
        return None, None

    end = section_end
    for j in range(start + 1, section_end):
        stripped = lines[j].strip()
        if stripped and not stripped.startswith("#") and _indent(lines[j]) <= 2:
            end = j
            break
    return start, end


def _upsert_mcp_server(
    original: str,
    server_name: str,
    python_exe: Path,
    repo_root: Path,
    enabled: bool,
) -> str:
    lines = original.splitlines(keepends=True)
    if not lines:
        lines = []

    server_block = _build_server_block(
        server_name=server_name,
        python_exe=python_exe,
        repo_root=repo_root,
        enabled=enabled,
    )

    section_start, section_end = _find_mcp_servers_section(lines)

    if section_start is None:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] = lines[-1] + "\n"
        if lines and lines[-1].strip():
            lines.append("\n")
        lines.append("mcp_servers:\n")
        lines.extend(server_block)
        return "".join(lines)

    server_start, server_end = _find_server_entry(
        lines=lines,
        section_start=section_start,
        section_end=section_end,
        server_name=server_name,
    )

    if server_start is not None:
        lines[server_start:server_end] = server_block
        return "".join(lines)

    insert_at = section_end
    if insert_at > 0 and lines[insert_at - 1].strip():
        server_block = ["\n"] + server_block
    lines[insert_at:insert_at] = server_block
    return "".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install/update prolog-reasoning MCP server in Hermes config.")
    parser.add_argument(
        "--config",
        default="~/.hermes/config.yaml",
        help="Path to Hermes config.yaml",
    )
    parser.add_argument(
        "--repo-root",
        default="",
        help="Repo root path (defaults to script's parent repo).",
    )
    parser.add_argument(
        "--python-exe",
        default=sys.executable,
        help="Python interpreter Hermes should use for mcp_server.py",
    )
    parser.add_argument(
        "--server-name",
        default="prolog_reasoning",
        help="Server key under mcp_servers (default: prolog_reasoning)",
    )
    parser.add_argument(
        "--disable",
        action="store_true",
        help="Write enabled: false for the server entry",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print result instead of writing file",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve() if args.repo_root else Path(__file__).resolve().parent.parent
    config_path = Path(args.config).expanduser().resolve()
    python_exe = Path(args.python_exe).expanduser().resolve()

    mcp_server_path = repo_root / "src" / "mcp_server.py"
    kb_path = repo_root / "prolog" / "core.pl"
    if not mcp_server_path.exists():
        raise FileNotFoundError(f"Missing mcp server file: {mcp_server_path}")
    if not kb_path.exists():
        raise FileNotFoundError(f"Missing KB file: {kb_path}")

    config_path.parent.mkdir(parents=True, exist_ok=True)
    original = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    updated = _upsert_mcp_server(
        original=original,
        server_name=args.server_name,
        python_exe=python_exe,
        repo_root=repo_root,
        enabled=not args.disable,
    )

    if args.dry_run:
        print(updated)
        return 0

    if config_path.exists():
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = config_path.with_suffix(f".yaml.bak.{stamp}")
        backup_path.write_text(original, encoding="utf-8")
        backup_note = str(backup_path)
    else:
        backup_note = None

    config_path.write_text(updated, encoding="utf-8")

    print("Hermes MCP config updated.")
    print(f"Config: {config_path}")
    if backup_note:
        print(f"Backup: {backup_note}")
    print("Next step: restart Hermes or run /reload-mcp in an active Hermes chat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
