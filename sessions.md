# Prolog Reasoning v2 - Session Tracker

This file is a compact public summary of recent project state.

## Current Snapshot

- Last major track completed: Simulation-oriented MCP demos with visible internals, plus pre-thinker LoRA bootstrap scaffolding
- Current product direction: Core symbolic reliability first, with MVP editor treated as experimental
- Evaluator status: `prolog_baseline` 13/13, `ir_compiled` 13/13, `lm_only` 8/13 (improved from 6/13)
- Latest actions: Switched the architecture diagram to a top-down runtime/control layout (`architecture.md`), ran a docs consistency sweep to remove stale tool-count and schema wording, aligned install guides/skill docs with the real MCP surface, corrected public pass-count markers to `95 passed`, and added `scripts/check_docs_consistency.py` as a lightweight regression guard.
- Next priority: Keep onboarding smoke gates green, keep docs/examples and install playbooks synchronized with live MCP behavior, and continue pre-thinker evaluation slices for routing accuracy and safe ingestion under ambiguity.

## Usage Notes

1. Keep this file short and current.
2. Keep this file focused on current state, not narrative history.
3. Long-form working notes can stay local and do not need to be published.
4. If long-form notes grow, split them in local-only files as `sessions/parts/YYYY-part-XX.md` (increment `XX` as needed).
