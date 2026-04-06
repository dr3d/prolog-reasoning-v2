# Rule-Derived Table Agent Walkthrough (Level 4)

Status: Active  
Date: 2026-04-06

Canonical ladder:

- [walkthrough-ladder.md](walkthrough-ladder.md)

## Goal

Show an LLM orchestrating deterministic table construction through MCP tool calls.

## Run

```bash
python scripts/demonstrate_rule_table_agent_mcp.py
```

Optional model override:

```bash
python scripts/demonstrate_rule_table_agent_mcp.py --model qwen3.5-27b@q4_k_m
```

## What to Look For

- repeated `query_logic` calls for `(user, action)` checks
- table assembly built from tool outputs
- model handles narration/presentation while symbolic layer supplies truth

## Next

- Level 5: [drug-triage-walkthrough.md](drug-triage-walkthrough.md)
