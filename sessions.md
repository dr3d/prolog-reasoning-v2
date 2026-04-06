# Prolog Reasoning v2 - Session Tracker

This file is a compact public summary of recent project state.

## Current Snapshot

- Last major track completed: Simulation-oriented MCP demos with visible internals, plus docs hub hardening
- Current product direction: Core symbolic reliability first, with MVP editor treated as experimental
- Evaluator status: `prolog_baseline` 13/13, `ir_compiled` 13/13, `lm_only` 8/13 (improved from 6/13)
- Latest actions: Added a styled `docs/index.html` docs hub (GitHub Pages-friendly) and top-level transcript pages; added a fantasy multi-character simulation capture flow (`scripts/capture_fantasy_overlord_session.py`) with pause/resume fact edits and multi-hop rule effects; expanded deterministic simulation predicates (`asleep`, `awake`, `can_move`, `can_trade`, `threatened`, `high_risk`, `can_cast_charm`, etc.) and exposed them through MCP metadata; generated and published fantasy transcript artifacts (`docs/fantasy-overlord-session.html` plus `docs/examples/*`); added a visible "Prolog Console" side panel in the fantasy HTML transcript so viewers can inspect raw tool outputs per turn; normalized `_raw` tool display names to clean aliases in rendered transcripts; aligned Level 4/6 walkthroughs and demo prompts to prefer alias tool names (`query_logic`, `query_rows`) over legacy `_raw` naming; completed a docs taxonomy pass that moved non-core docs into `docs/research/`, `docs/secondary/`, `docs/prototypes/`, and `docs/legacy/`; consolidated overlapping intake/memory/write narrative docs into one canonical spec (`docs/fact-intake-pipeline.md`) and trimmed scenario overlap by making `docs/uses-and-scenarios.md` primary with a short research appendix; consolidated level walkthroughs into a canonical ladder (`docs/walkthrough-ladder.md`) with thin per-level pages; added persistent nav links (`Back to Docs Hub`, `View Repo`) to transcript HTML templates and current published HTML outputs.
- Next priority: Start knowledge-ingestion and revision engineering, especially statement typing, predicate mapping/canonicalization, tentative memory, correction cues, and explicit write-path design, while extending the simulation pattern into interactive pause/edit/resume demos.

## Usage Notes

1. Keep this file short and current.
2. Keep this file focused on current state, not narrative history.
3. Long-form working notes can stay local and do not need to be published.
