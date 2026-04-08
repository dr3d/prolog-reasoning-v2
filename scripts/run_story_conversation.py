#!/usr/bin/env python3
"""
Backward-compatible wrapper.

Use `scripts/run_conversaton.py` for the generic conversation runner.
"""

from __future__ import annotations

from run_conversaton import main


if __name__ == "__main__":
    raise SystemExit(main())
