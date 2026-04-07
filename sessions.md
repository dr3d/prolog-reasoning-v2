# Prolog Reasoning v2 - Session Tracker

This file is a compact public summary of recent project state.

## Current Snapshot

- Last major track completed: Simulation-oriented MCP demos with visible internals, plus pre-thinker LoRA bootstrap scaffolding
- Current product direction: Core symbolic reliability first, with MVP editor treated as experimental
- Evaluator status: `prolog_baseline` 13/13, `ir_compiled` 13/13, `lm_only` 8/13 (improved from 6/13)
- Latest actions: Standardized capture UI copy controls to plain `copy`/`copied`, clarified pre-thinker architecture into two lanes (ontological routing + clarification eagerness), added a forward-looking clarification decision table (`docs/secondary/clarification-eagerness-decision-table.md`), added no-op `clarification_eagerness` policy surface (`src/mcp_server.py`, `kb_manifest.json`), and added a smoke invariant that uncertain classify steps do not auto-commit (`scripts/capture_mcp_surface_playbook_session.py` validation + MCP test coverage).
- Next priority: Keep onboarding smoke gates green, run clarification logic in log-only mode before enabling behavior changes, and continue building pre-thinker evaluation slices for routing accuracy and safe ingestion under ambiguity.

## Usage Notes

1. Keep this file short and current.
2. Keep this file focused on current state, not narrative history.
3. Long-form working notes can stay local and do not need to be published.
4. If long-form notes grow, split them in local-only files as `sessions/parts/YYYY-part-XX.md` (increment `XX` as needed).
