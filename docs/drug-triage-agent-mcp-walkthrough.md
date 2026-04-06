# Drug Triage Agent Walkthrough (Level 6)

Status: Active  
Date: 2026-04-06

Canonical ladder:

- [walkthrough-ladder.md](walkthrough-ladder.md)

## Goal

Show an LLM orchestrating deterministic clinical triage through MCP tools.

## Run

```bash
python scripts/demonstrate_drug_triage_agent_mcp.py
```

Optional model override:

```bash
python scripts/demonstrate_drug_triage_agent_mcp.py --model qwen3.5-27b@q4_k_m
```

## What to Look For

- tool-backed candidate evaluation via `query_logic`
- deterministic status per drug candidate
- final summary still grounded in symbolic outputs

## Next

- Level 7: [fantasy-overlord-mcp-walkthrough.md](fantasy-overlord-mcp-walkthrough.md)
