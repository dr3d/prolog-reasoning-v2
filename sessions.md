# Prolog Reasoning v2 - Session Tracker

This file is a compact public summary of recent project state.

## Current Snapshot

- Last major track completed: Simulation-oriented MCP demos with visible internals, plus pre-thinker LoRA bootstrap scaffolding
- Current product direction: Core symbolic reliability first, with MVP editor treated as experimental
- Evaluator status: `prolog_baseline` 13/13, `ir_compiled` 13/13, `lm_only` 8/13 (improved from 6/13)
- Latest actions: Hardened MCP tool-result semantics so deterministic `no_results` are no longer flagged as MCP errors (`src/mcp_server.py`), added a regression test (`tests/test_mcp_server.py`), and validated live Hermes/LM Studio behavior after `/reload-mcp`; removed the unused minimal-bundle artifacts (`MCP-MINIMAL.md`, `scripts/build_mcp_minimal_bundle.py`); retained fast Hermes MCP wiring guidance in `HERMES-AGENT-INSTALL.md` backed by `scripts/install_hermes_mcp.py`.
- Next priority: Continue pre-thinker data collection from reviewed live sessions while stabilizing chat-playbook reliability (especially prompt discipline after multi-tool query batches) before expanding write-path authority.

## Usage Notes

1. Keep this file short and current.
2. Keep this file focused on current state, not narrative history.
3. Long-form working notes can stay local and do not need to be published.
