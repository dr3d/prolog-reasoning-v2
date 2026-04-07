# Indie Launch War Room MCP Walkthrough

Status: Active  
Date: 2026-04-07

Canonical ladder:

- [walkthrough-ladder.md](walkthrough-ladder.md)

## Goal

Demonstrate a realistic launch control-room chat where deterministic logic tracks task readiness, supplier shocks, and recovery actions.

## Fast Capture

```bash
python scripts/capture_indie_launch_warroom_session.py --model qwen/qwen3.5-9b --validate --out-dir docs/examples
```

Expected success signal:

- `Validation passed.`

Outputs:

- `docs/examples/indie-launch-warroom-session.json`
- `docs/examples/indie-launch-warroom-session.md`
- `docs/examples/indie-launch-warroom-session.html`

## What to Look For

- conversational prompts with deterministic tool calls
- dependency-chain impact after supplier delay updates
- uncertain intake classification that does not auto-persist
- explicit recovery pass that recalculates ready/waiting/risk state

## Manual Play Loop

1. ingest baseline facts (`bulk_assert_facts`)
2. query readiness and waiting chains (`query_rows`)
3. inject incidents (`retract_fact`, `assert_fact`)
4. classify uncertain notes (`classify_statement`)
5. recover and re-check milestone risk
