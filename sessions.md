# Prolog Reasoning v2 - Session Tracker

This file is a compact public summary of recent project state.

## Current Snapshot

- Last major track completed: Simulation-oriented MCP demos with visible internals, plus pre-thinker LoRA bootstrap scaffolding
- Current product direction: Core symbolic reliability first, with MVP editor treated as experimental
- Evaluator status: `prolog_baseline` 13/13, `ir_compiled` 13/13, `lm_only` 8/13 (improved from 6/13)
- Latest actions: Re-ran the hospital CPM capture script against local LM Studio (`qwen/qwen3.5-9b`) with MCP integration and regenerated canonical artifacts in `docs/examples/`; fixed a broken local nav link in the generated transcript/template (`docs/examples/hospital-cpm-playbook-session.html`, `scripts/capture_hospital_playbook_session.py`) by correcting `./docs-hub.html` to `../docs-hub.html`; verified no further broken local links under `docs/*.html`.
- Next priority: Continue pre-thinker data collection from reviewed live sessions while stabilizing chat-playbook reliability (especially prompt discipline after multi-tool query batches) before expanding write-path authority.

## Usage Notes

1. Keep this file short and current.
2. Keep this file focused on current state, not narrative history.
3. Long-form working notes can stay local and do not need to be published.
