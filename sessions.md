# Prolog Reasoning v2 - Session Tracker

This file is the fast-start state for coding agents.

## Agent Read Order

1. `AGENT-README.md` (fast onboarding and MCP setup path)
2. `README.md` (project thesis and runtime promises)
3. `docs/README.md` (docs map)
4. `status.md` and `roadmap.md` (what is complete vs next)
5. `sessions/operator-brief.md` (active handoff and current priorities)

Default scope rule:
- Do not read `sessions/parts/*` by default.
- Open historical long-form notes only when explicitly requested by the operator.

## Current Snapshot (2026-04-09)

- Product direction: symbolic reliability first; editor remains experimental.
- Evaluator status: `prolog_baseline` 13/13, `ir_compiled` 13/13, `lm_only` 8/13.
- Test/doc marker: shared pass-count marker is `115 passed`.
- Latest completed track: `scenario-2` (Archive of Kestrel-9) added with integrated question battery (`37` prompts), and executed against the Qwen trio via `run_conversaton.py`.
- Latest completed benchmark track: harder family-memory ladder run (`12` probes; corrections + rewiring + distractors) consolidated across `fuzzy`, `sharp`, `hybrid`, and `hybrid_pressure`.
- Latest maintenance pass: runner hardened for transient LM Studio faults (per-step retries, configurable request timeout, partial artifact write-on-error).
- Latest docs publication pass: docs-hub now includes a Family Memory Ladder demo card plus two published session HTML captures.
- Current safety boundary: `classify_statement` returns deterministic `proposal_check` (`valid | needs_clarification | reject`) but does not perform durable KB writes.
- Artifact boundary: raw run captures under `docs/research/conversations/**` are intentionally local-only (git-ignored); publish-safe summaries and selected showcase HTML live under tracked docs paths.
- Next priority: improve long-run stability for full scenario batteries (timeouts/tool-format failures) and keep rotating stronger showcase captures into fixed docs-hub slots.

## Canonical Pointers (Current)

- Write-path scaffold: `src/write_path/`, `data/predicate_registry.json`
- Matrix lane: `scripts/run_mcp_surface_model_matrix.py`, `docs/research/model-scenario-matrix.md`
- Fact-ingestion dialog battery: `scripts/run_fact_ingestion_dialog_battery.py`, `data/fact_extraction/fact_ingestion_dialog_battery_v1.json`, `docs/research/fact-ingestion-dialog-battery.md`
- Buried-fact extraction matrix: `scripts/run_fact_extraction_steering_matrix.py`, `data/fact_extraction/buried_facts_corpus_v1.json`, `docs/research/fact-extraction-steering-matrix.md`
- Scenario pipeline: `docs/research/scenarios/README.md`, `docs/research/scenarios/scenario-1.md`, `docs/research/scenarios/scenario-2.md`, `scripts/run_conversaton.py`, `docs/research/conversations/<scenario>/<timestamp>/*.{json,md,html}`
- Latest scenario-2 run artifacts: `docs/research/conversations/scenario-2/20260408-171233/*`
- Family ladder runner: `scripts/run_family_memory_ladder.py`
- Family ladder report: `docs/research/family-memory-ladder-qwen9b-2026-04-09.md`
- Family ladder publish-safe summary: `docs/research/family-memory-ladder-qwen9b-2026-04-09-summary.{md,json}`
- Family ladder published showcase HTML: `docs/examples/family-memory-ladder-hybrid-session.html`, `docs/examples/family-memory-ladder-hybrid-pressure-session.html`
- Family ladder local raw captures: `docs/research/conversations/family-memory-ladder/<timestamp>/*`
- Shared conversation HTML renderer: `scripts/render_dialog_json_html.py`, `scripts/templates/dialog-session-page.template.html`, `scripts/templates/dialog-themes/*.css`
- Renderer helpers: `scripts/render_dialog_helpers.py`, `scripts/render_examples_sessions_html.py`
- Research ledger HTML renderer: `scripts/render_research_ledgers_html.py`, `scripts/templates/research-ledger-page.template.html`
- Onboarding smoke: `scripts/onboarding_mcp_smoke.ps1`
- Playbooks: `docs/mcp-chat-playbooks.md`
- Recent scenario captures:
  - `docs/examples/indie-launch-warroom-session.*`
  - `docs/examples/indie-launch-warroom-natural-session.*`
- Consistency guard: `scripts/check_docs_consistency.py`

## Historical (Open Only On Request)

- Legacy run pack: `docs/research/legacy/runs/dialog-battery-20260407-221328/*.html`
- Research archive: `docs/research/legacy/README.md`

## Session Notes Policy

1. Keep this file short and current.
2. Keep this file focused on actionable now-state, not narrative history.
3. Long-form notes stay local under `sessions/parts/`.
4. Long-form files are historical records and may mention artifacts that were removed later.
5. New parts should follow `sessions/parts/YYYY-part-XX.md`.
6. Treat `sessions/parts/*` as archival context, not default planning input.
