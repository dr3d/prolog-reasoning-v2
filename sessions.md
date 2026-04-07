# Prolog Reasoning v2 - Session Tracker

This file is a compact public summary of recent project state.

## Current Snapshot

- Last major track completed: Simulation-oriented MCP demos with visible internals, plus pre-thinker LoRA bootstrap scaffolding
- Current product direction: Core symbolic reliability first, with MVP editor treated as experimental
- Evaluator status: `prolog_baseline` 13/13, `ir_compiled` 13/13, `lm_only` 8/13 (improved from 6/13)
- Latest actions: Hidden legacy `_raw` tool aliases from MCP discovery while keeping backward-compatible call support, added a third validated onboarding gate for surface coverage (`scripts/capture_mcp_surface_playbook_session.py --validate`), extended the one-command smoke runner (`scripts/onboarding_mcp_smoke.ps1`) to run hospital + fantasy + surface, updated onboarding docs with an interactive MCP surface playbook, completed a tracked-file secret/PII scrub pass before cloud push (no obvious live API keys found), and added an LP-LM comparison note with online references only (`docs/research/lp-lm-comparison.md`).
- Next priority: Keep all three onboarding smoke gates green in CI/local pre-push flow and convert LP-LM comparison takeaways into parser-contract evaluation slices while continuing pre-thinker data collection before expanding write-path authority.

## Usage Notes

1. Keep this file short and current.
2. Keep this file focused on current state, not narrative history.
3. Long-form working notes can stay local and do not need to be published.
4. If long-form notes grow, split them in local-only files as `sessions/parts/YYYY-part-XX.md` (increment `XX` as needed).
