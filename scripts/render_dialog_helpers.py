#!/usr/bin/env python3
"""
Shared helper to render transcript JSON into HTML via the centralized dialog renderer.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
RENDERER = SCRIPTS_DIR / "render_dialog_json_html.py"


def render_transcript_html(
    *,
    json_path: Path,
    html_path: Path,
    title: str,
    theme: str = "standard",
    docs_hub_link: str = "https://dr3d.github.io/prolog-reasoning/docs-hub.html",
    repo_link: str = "https://github.com/dr3d/prolog-reasoning",
) -> None:
    cmd = [
        sys.executable,
        str(RENDERER),
        "--input",
        str(json_path),
        "--output",
        str(html_path),
        "--theme",
        theme,
        "--title",
        title,
        "--docs-hub-link",
        docs_hub_link,
        "--repo-link",
        repo_link,
    ]
    subprocess.run(cmd, cwd=str(REPO_ROOT), check=True)
