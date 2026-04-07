# Prolog Reasoning v2 - Session Tracker

This file is the fast-start state for coding agents.

## Agent Read Order

1. `README.md` (project thesis and runtime promises)
2. `docs/README.md` (docs map)
3. `status.md` and `roadmap.md` (what is complete vs next)
4. `sessions/README.md` and latest `sessions/parts/*` file (local narrative history)

## Current Snapshot (2026-04-07)

- Product direction: symbolic reliability first; editor remains experimental.
- Evaluator status: `prolog_baseline` 13/13, `ir_compiled` 13/13, `lm_only` 8/13.
- Test/doc marker: shared pass-count marker is `107 passed`.
- Latest completed track: PR1 proposal-check scaffolding and live MCP demo capture refresh.
- Current safety boundary: `classify_statement` returns deterministic `proposal_check` (`valid | needs_clarification | reject`) but does not perform durable KB writes.
- Next priority: expand model-scenario matrix coverage before PR2 guarded runtime writes.

## Canonical Pointers (Current)

- Write-path scaffold: `src/write_path/`, `data/predicate_registry.json`
- Matrix lane: `scripts/run_mcp_surface_model_matrix.py`, `docs/research/model-scenario-matrix.md`
- Onboarding smoke: `scripts/onboarding_mcp_smoke.ps1`
- Playbooks: `docs/mcp-chat-playbooks.md`
- Recent scenario captures:
  - `docs/examples/indie-launch-warroom-session.*`
  - `docs/examples/indie-launch-warroom-natural-session.*`
- Consistency guard: `scripts/check_docs_consistency.py`

## Session Notes Policy

1. Keep this file short and current.
2. Keep this file focused on actionable now-state, not narrative history.
3. Long-form notes stay local under `sessions/parts/`.
4. Long-form files are historical records and may mention artifacts that were removed later.
5. New parts should follow `sessions/parts/YYYY-part-XX.md`.
