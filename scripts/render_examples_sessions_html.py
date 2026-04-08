#!/usr/bin/env python3
"""
Re-render docs/examples session HTML files from JSON using the centralized dialog renderer.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "scripts/render_dialog_json_html.py"
EXAMPLES_DIR = ROOT / "docs/examples"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Re-render docs/examples/*-session.json to HTML via the shared renderer."
    )
    parser.add_argument(
        "--theme",
        default="standard",
        choices=["standard", "telegram", "imessage"],
        help="Theme to use for output HTML.",
    )
    parser.add_argument(
        "--pattern",
        default="*-session.json",
        help="Glob pattern for input JSON files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cmd = [
        sys.executable,
        str(RENDERER),
        "--input",
        str(EXAMPLES_DIR),
        "--pattern",
        args.pattern,
        "--in-place",
        "--theme",
        args.theme,
    ]
    completed = subprocess.run(cmd, cwd=str(ROOT))
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
