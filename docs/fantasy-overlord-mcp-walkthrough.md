# Fantasy Overlord MCP Walkthrough

This is a chat-first simulation pattern for world state, locality, inventory,
conditions, and multi-hop inference.

Core idea:
- the LLM narrates and orchestrates
- deterministic predicates hold state
- you pause/resume by asserting or retracting facts
- multi-hop rules derive consequences

## Prerequisites

1. LM Studio running on `http://127.0.0.1:1234`
2. `mcp/prolog-reasoning` integration enabled
3. A local model loaded (for example `qwen/qwen3.5-9b`)

## Fast Capture (One Command)

Run:

```bash
python scripts/capture_fantasy_overlord_session.py --model qwen/qwen3.5-9b --out-dir docs/examples
```

Outputs:
- `docs/examples/fantasy-overlord-session.json`
- `docs/examples/fantasy-overlord-session.md`
- `docs/examples/fantasy-overlord-session.html`

## What This Demonstrates

1. **Night chain**: `time_of_day(night)` implies `asleep(C)` unless
   `insomnia(C)` or `status(C, guard_duty)`.
2. **Mobility chain**: `awake(C)` and `connected(From,To)` implies
   `can_move(C, To)`.
3. **Risk chain**: storm + docks exposure + low HP can lead to `high_risk(C)`
   when threat is present.
4. **Charm chain**: charm casting becomes valid only when locality and awake
   conditions are satisfied.

## Interactive Play Mode (Manual)

In chat, you can run a loop:

1. Query state (`query_rows awake(C).`, `query_rows high_risk(C).`)
2. Pause and edit facts (`assert_fact ...`, `retract_fact ...`)
3. Query again and compare
4. Continue turns

This gives you a "Sims-like" control loop with deterministic state transitions.
