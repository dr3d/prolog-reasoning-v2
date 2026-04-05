# Prolog Reasoning v2 — Session Tracker

This file is now a compact index. Full narrative history lives in session parts.

## Current Snapshot

- Last major track completed: Evaluator hardening + core engine fixes + repeated-run statistics
- Current product direction: Constraint-based graphic editor MVP (graphical spreadsheet for layout rules) + core symbolic layer improvements
- Evaluator status: `prolog_baseline` 13/13, `ir_compiled` 13/13, `lm_only` 8/13 (improved from 6/13)
- Latest actions: Fixed lm_only to preserve user-supplied rules; added Wilson CI + timing stats; fixed engine variable collision bug; implemented findall/3
- Next priority: Roadmap based on external critique (Gemini); candidate projects include temporal logic, multi-session isolation, soft-fail buffer zone, fact auditor

## Session History (Long Form)

- [Session Log Structure](docs/sessions/README.md)
- [2026 Part 01](docs/sessions/parts/2026-part-01.md)

## Usage Notes

1. Keep this file short and current.
2. Add detailed session write-ups to `docs/sessions/parts/`.
3. Start a new part file when the active part becomes unwieldy.
