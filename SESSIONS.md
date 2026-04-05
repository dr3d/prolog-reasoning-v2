# Prolog Reasoning v2 — Session Tracker

This file is a compact public summary of recent project state.

## Current Snapshot

- Last major track completed: Evaluator hardening + core engine fixes + repeated-run statistics
- Current product direction: Constraint-based graphic editor MVP (graphical spreadsheet for layout rules) + core symbolic layer improvements
- Evaluator status: `prolog_baseline` 13/13, `ir_compiled` 13/13, `lm_only` 8/13 (improved from 6/13)
- Latest actions: Fixed lm_only to preserve user-supplied rules; added Wilson CI + timing stats; fixed engine variable collision bug; implemented findall/3
- Next priority: Roadmap based on external critique (Gemini); candidate projects include temporal logic, multi-session isolation, soft-fail buffer zone, fact auditor

## Usage Notes

1. Keep this file short and current.
2. Keep this file focused on current state, not narrative history.
3. Long-form working notes can stay local and do not need to be published.
