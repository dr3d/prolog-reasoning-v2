# Prolog Reasoning v2 — Session Tracker

This file is a compact public summary of recent project state.

## Current Snapshot

- Last major track completed: LM Studio MCP integration hardening, response polish, and coverage expansion
- Current product direction: Core symbolic reliability first, with MVP editor treated as experimental
- Evaluator status: `prolog_baseline` 13/13, `ir_compiled` 13/13, `lm_only` 8/13 (improved from 6/13)
- Latest actions: Reframed README around deterministic reliability for LLM agents; added the "Memories are timestamped. Facts are not." thesis line; added a new memory-and-inference infographic and linked it from README; hardened and polished the MCP server for LM Studio with initialize/ping/tool-call support, JSON-safe result wrapping, clearer query/error/list responses, and verified all four exposed tools in a live LM Studio session; added 8 focused MCP server tests and brought the public test count to `68 passed`; kept constraint editor work explicitly in the experimental lane
- Next priority: Implement Tier 1 roadmap items (temporal logic, dependency split, multi-session isolation) and start ontology-context routing prototype

## Usage Notes

1. Keep this file short and current.
2. Keep this file focused on current state, not narrative history.
3. Long-form working notes can stay local and do not need to be published.
