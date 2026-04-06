# Prolog Reasoning v2 — Session Tracker

This file is a compact public summary of recent project state.

## Current Snapshot

- Last major track completed: Chat-first MCP workflow hardening, clean tool alias rollout, transcript UX polish, and documentation reflow
- Current product direction: Core symbolic reliability first, with MVP editor treated as experimental
- Evaluator status: `prolog_baseline` 13/13, `ir_compiled` 13/13, `lm_only` 8/13 (improved from 6/13)
- Latest actions: Added user-facing MCP aliases (`query_logic`, `query_rows`, `assert_fact`, `bulk_assert_facts`, `retract_fact`, `reset_kb`) while keeping legacy `_raw` compatibility; updated LM Studio and playbook docs to prefer alias names; refreshed the captured CPM transcripts and HTML renderer with dark/light theme toggle plus copy buttons; added a realistic "daily ops" back-and-forth section to the canonical hospital playbook transcript; moved README quick-start flow to markdown-first guides before Python scripts; refreshed project status counts and guidance; confirmed no broken local markdown links across the repo.
- Next priority: Start knowledge-ingestion and revision engineering, especially statement typing, predicate mapping/canonicalization, tentative memory, correction cues, and explicit write-path design

## Usage Notes

1. Keep this file short and current.
2. Keep this file focused on current state, not narrative history.
3. Long-form working notes can stay local and do not need to be published.
