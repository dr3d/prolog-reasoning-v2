# Prolog Reasoning v2 - Session Tracker

This file is the fast-start state for coding agents.

## Agent Read Order

1. `README.md` (project thesis and runtime promises)
2. `docs/README.md` (docs map)
3. `status.md` and `roadmap.md` (what is complete vs next)
4. `sessions/README.md` and latest `sessions/parts/*` file (local narrative history)

## Current Snapshot (2026-04-08)

- Product direction: symbolic reliability first; editor remains experimental.
- Evaluator status: `prolog_baseline` 13/13, `ir_compiled` 13/13, `lm_only` 8/13.
- Test/doc marker: shared pass-count marker is `108 passed`.
- Latest completed track: research lane reorganized around `scenarios/` + `conversations/`, with reusable runner `scripts/run_conversaton.py` supporting single-model and Qwen battery runs to JSON+MD+HTML outputs.
- Latest maintenance pass: docs/research archive split completed, temporary run cruft removed, tracked-file secret scan clean, and capture scripts hardened so `render_dialog_helpers` imports work under pytest module loading.
- Current safety boundary: `classify_statement` returns deterministic `proposal_check` (`valid | needs_clarification | reject`) but does not perform durable KB writes.
- Next priority: run additional scenarios through the new battery runner and publish selected HTML artifacts through docs hub / GitHub Pages links.

## Canonical Pointers (Current)

- Write-path scaffold: `src/write_path/`, `data/predicate_registry.json`
- Matrix lane: `scripts/run_mcp_surface_model_matrix.py`, `docs/research/model-scenario-matrix.md`
- Fact-ingestion dialog battery: `scripts/run_fact_ingestion_dialog_battery.py`, `data/fact_extraction/fact_ingestion_dialog_battery_v1.json`, `docs/research/fact-ingestion-dialog-battery.md`
- Buried-fact extraction matrix: `scripts/run_fact_extraction_steering_matrix.py`, `data/fact_extraction/buried_facts_corpus_v1.json`, `docs/research/fact-extraction-steering-matrix.md`
- Scenario pipeline: `docs/research/scenarios/README.md`, `docs/research/scenarios/scenario-1.md`, `scripts/run_conversaton.py`, `docs/research/conversations/<scenario>/<timestamp>/*.{json,md,html}`
- Shared conversation HTML renderer: `scripts/render_dialog_json_html.py`, `scripts/templates/dialog-session-page.template.html`, `scripts/templates/dialog-themes/*.css`
- Renderer helpers: `scripts/render_dialog_helpers.py`, `scripts/render_examples_sessions_html.py`
- Research ledger HTML renderer: `scripts/render_research_ledgers_html.py`, `scripts/templates/research-ledger-page.template.html`
- Published dialog-battery HTML pack: `docs/research/legacy/runs/dialog-battery-20260407-221328/*.html`
- Research archive: `docs/research/legacy/README.md`
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
