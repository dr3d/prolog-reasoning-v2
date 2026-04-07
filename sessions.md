# Prolog Reasoning v2 - Session Tracker

This file is a compact public summary of recent project state.

## Current Snapshot

- Last major track completed: Simulation-oriented MCP demos with visible internals, plus pre-thinker LoRA bootstrap scaffolding
- Current product direction: Core symbolic reliability first, with MVP editor treated as experimental
- Evaluator status: `prolog_baseline` 13/13, `ir_compiled` 13/13, `lm_only` 8/13 (improved from 6/13)
- Latest actions: Added PR1 write-path proposal-check scaffolding (`src/write_path/` + `data/predicate_registry.json`) and wired `classify_statement` to return deterministic `proposal_check` (`valid | needs_clarification | reject`) without mutating behavior; expanded unit coverage for normalization/alias/arity/fact-shape cases, exercised the MCP surface live against local LM Studio (`127.0.0.1:1234`, `qwen/qwen3.5-9b`) with validation pass, updated pass-count markers to `107 passed`, added a new live-captured indie launch war-room scenario (`scripts/capture_indie_launch_warroom_session.py` + `docs/examples/indie-launch-warroom-session.*`) with conversational prompts and onboarding smoke integration, updated all transcript templates so green Tool Calls panels are collapsed expandos by default, published a natural-language robustness capture showing honest tool-selection reliability (`5/8` step expectations met) in `docs/examples/indie-launch-warroom-natural-session.*`, established a repo-level `prototypes/` workspace scaffold with explicit status lanes (`experimental`, `active`, `archived`), aligned docs/playbook markup with canonical GitHub Pages links for rendered HTML demo sharing, clarified acronym usage by spelling out `CPM` as `Critical Path Method` in key onboarding docs, added a model-scenario matrix runner (`scripts/run_mcp_surface_model_matrix.py`) plus tracked ledger (`docs/research/model-scenario-matrix.md`), and refreshed canonical MCP surface capture artifacts to the latest `qwen3.5-27b@q4_k_m` run.
- Next priority: Expand model-matrix coverage across additional scenarios to surface fact-recognition and tool-selection weak spots before PR2 guarded runtime writes.

## Usage Notes

1. Keep this file short and current.
2. Keep this file focused on current state, not narrative history.
3. Long-form working notes can stay local and do not need to be published.
4. If long-form notes grow, split them in local-only files as `sessions/parts/YYYY-part-XX.md` (increment `XX` as needed).
