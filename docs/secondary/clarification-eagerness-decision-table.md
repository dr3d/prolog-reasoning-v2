# Clarification Eagerness Decision Table

Status: Draft  
Owner: Core symbolic layer  
Date: 2026-04-07

This is a forward-looking routing/intake policy table.

Purpose:
- define deterministic action routing for uncertain candidate facts,
- keep write safety invariant explicit: uncertain facts are never auto-committed.

## Inputs

- `statement_confidence`: classifier/pre-thinker confidence in candidate fact shape.
- `manifest_match_score`: overlap with known ontology/predicate/entity surface.
- `clarification_eagerness`: policy knob in `[0.0, 1.0]`.

## Baseline Invariant

- if uncertainty remains, do not auto-commit.
- uncertain candidates may be clarified, staged as tentative, or skipped.

## Policy Bands

- Low eagerness: `0.0-0.29`
- Medium eagerness: `0.30-0.69`
- High eagerness: `0.70-1.00`

## Decision Table

| Statement confidence | Manifest match | Low eagerness | Medium eagerness | High eagerness |
|---|---|---|---|---|
| high (`>=0.85`) | high (`>=0.70`) | `assert` | `assert` | `assert` |
| medium (`0.60-0.84`) | high (`>=0.70`) | `tentative` | single targeted clarification, then `assert` on explicit confirm else `tentative` | targeted clarification loop (bounded), then `assert` on explicit confirm else `tentative` |
| low (`<0.60`) | high (`>=0.70`) | `tentative` or `none` | targeted clarification, else `tentative` | targeted clarification loop (bounded), else `tentative` |
| any | medium (`0.40-0.69`) | `none` | optional single clarification | bounded clarification loop, else `none` |
| any | low (`<0.40`) | `none` | `none` | `none` |

## Clarification Loop Limits

- one question at a time,
- maximum attempts per candidate (recommended: `1/2/3` for low/medium/high),
- explicit confirmation required for commit after clarification.

## Current Runtime Note

- default `clarification_eagerness` is `0.0` (no-op placeholder),
- current runtime behavior is unchanged by this key,
- this table is for planned routing/intake rollout.
