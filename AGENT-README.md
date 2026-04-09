# AGENT README

Purpose: give any coding agent a fast, reliable path to become useful to its human in this repo.

## One-Minute Orientation

- Project spine: deterministic symbolic reasoning + MCP integration.
- Current test/doc marker: `115 passed`.
- Local-first behavior: runtime KB writes are process-local unless explicitly persisted by future write-path work.
- Pre-think is active research and runtime tooling, with policy boundaries enforced in `src/mcp_server.py`.

## Read In This Order (5 Minutes)

1. `README.md`
2. `docs/README.md`
3. `status.md`
4. `sessions.md`
5. `sessions/operator-brief.md`

Default scope rule:
- Do not read `sessions/parts/*` unless the human explicitly asks for historical context.

## First Commands

```powershell
python -m pytest tests -q
python scripts/check_docs_consistency.py
```

Optional smoke check:

```powershell
./scripts/onboarding_mcp_smoke.ps1
```

## MCP Setup Fast Path (LM Studio)

Use:
- `docs/lm-studio-mcp-guide.md`
- `docs/mcp-chat-playbooks.md`

Minimum server launch target:

```powershell
python src/mcp_server.py --stdio --kb-path prolog/core.pl
```

If LM Studio API auth is enabled, set:
- `LMSTUDIO_API_KEY`

## Where To Look For What

- Runtime behavior and tool contracts: `src/mcp_server.py`
- Deterministic engine: `src/engine/`
- Intake/classification: `src/parser/`, `src/validator/`
- Tests: `tests/`
- Scenario runners: `scripts/run_conversaton.py`, `scripts/run_scenario2_prethink_matrix.py`, `scripts/run_family_memory_ladder.py`
- Research specs and reports: `docs/research/`
- Published demos and docs hub: `docs/docs-hub.html`, `docs/examples/`

## Current Boundaries You Must Respect

- `classify_statement` is routing/proposal logic, not durable memory write.
- Runtime mutation tools (`assert_fact`, `bulk_assert_facts`, `retract_fact`, `reset_kb`) mutate process-local state.
- `docs/research/conversations/**` is local run output and is intentionally git-ignored.
- Publishable artifacts should go to tracked docs paths (for example `docs/examples/` and `docs/research/*.md`).

## Agent Workflow That Helps Humans Most

1. Verify baseline quickly (`pytest`, docs consistency).
2. Reproduce the user-visible issue or scenario.
3. Make the smallest coherent change set.
4. Re-run the relevant validation.
5. Update docs/session trackers when behavior or public surface changes.
6. Summarize outcomes in plain language with file pointers.

## Good First Contributions

- tighten MCP tool routing prompts and error handling
- improve scenario runner reliability under retries/timeouts
- publish clean, comparable benchmark reports
- improve docs-hub discoverability and onboarding quality

## If Unsure, Start Here

- Human asked for setup help: `docs/lm-studio-mcp-guide.md`
- Human asked for project understanding: `README.md` then `docs/README.md`
- Human asked for current priorities: `status.md`, `roadmap.md`, `sessions.md`
- Human asked for experiments: `docs/research/scenarios/README.md` and `scripts/` runners
