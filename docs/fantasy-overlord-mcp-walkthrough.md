# Fantasy Overlord MCP Walkthrough (Level 7)

Status: Active  
Date: 2026-04-06

Canonical ladder:

- [walkthrough-ladder.md](walkthrough-ladder.md)

## Goal

Demonstrate pause/edit/resume world-state control with multi-hop deterministic consequences.

## Fast Capture

```bash
python scripts/capture_fantasy_overlord_session.py --model qwen/qwen3.5-9b --validate --out-dir docs/examples
```

Expected success signal:

- `Validation passed.`

Outputs:

- `docs/examples/fantasy-overlord-session.json`
- `docs/examples/fantasy-overlord-session.md`
- `docs/examples/fantasy-overlord-session.html`

## What to Look For

- turn-by-turn fact deltas from assert/retract operations
- rule chains for sleep, mobility, threat, and charm gating
- side-panel Prolog console view in HTML transcript

## Manual Play Loop

1. query state (`query_rows awake(C).`, `query_rows high_risk(C).`)
2. edit state (`assert_fact ...`, `retract_fact ...`)
3. query again and compare
4. continue turns
