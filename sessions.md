# Prolog Reasoning v2 — Session Tracker

This file is a compact public summary of recent project state.

## Current Snapshot

- Last major track completed: LM Studio MCP integration hardening, response polish, coverage expansion, and external-agent skill/install framing
- Current product direction: Core symbolic reliability first, with MVP editor treated as experimental
- Evaluator status: `prolog_baseline` 13/13, `ir_compiled` 13/13, `lm_only` 8/13 (improved from 6/13)
- Latest actions: Reframed README around deterministic reliability for LLM agents; added the "Memories are timestamped. Facts are not." thesis line; added a new memory-and-inference infographic and linked it from README; hardened and polished the MCP server for LM Studio with initialize/ping/tool-call support, JSON-safe result wrapping, clearer query/error/list responses, and verified all four exposed tools in a live LM Studio session; added 8 focused MCP server tests and brought the public test count to `68 passed`; added a repo-root `SKILL.md` to help external agents treat the project as a deterministic memory/reasoning layer; added separate Hermes and OpenClaw agent-install playbooks plus ingestion test prompts, with Hermes using a static prefill shim and OpenClaw leaning on native skill indexing; drafted a write-path spec covering mutation operations, pre-write backup, journal semantics, and context-scoped writes; added a deterministic `classify_statement` MCP tool with test coverage and brought the public test count to `72 passed`; exercised that tool through LM Studio's native `api/v1/chat` endpoint across multiple local models and published the comparison in `docs/lmstudio-classifier-matrix.md`; removed stale handoff/review/evidence docs and stopped tracking generated evaluation output; kept constraint editor work explicitly in the experimental lane
- Next priority: Start knowledge-ingestion and revision engineering, especially statement typing, tentative memory, correction cues, and explicit write-path design

## Usage Notes

1. Keep this file short and current.
2. Keep this file focused on current state, not narrative history.
3. Long-form working notes can stay local and do not need to be published.
