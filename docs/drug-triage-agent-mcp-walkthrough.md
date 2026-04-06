# Drug Triage Agent Walkthrough (Level 6)

Status: Draft  
Date: 2026-04-06

This walkthrough shows an LLM orchestrating deterministic clinical triage via
MCP tool calls.

The agent:

1. calls `query_prolog_raw` for each candidate drug
2. classifies each row as `contraindicated`, `caution`, or `safe`
3. asks for the final safe candidate set
4. returns a short human summary

## Prerequisites

1. LM Studio local server is running
2. `mcp/prolog-reasoning` integration is enabled
3. API token available if auth is enabled

Use either:

- env var: `LMSTUDIO_API_KEY`
- or `--api-key` argument

## Run It

```bash
python scripts/demonstrate_drug_triage_agent_mcp.py
```

Optional model override:

```bash
python scripts/demonstrate_drug_triage_agent_mcp.py --model qwen3.5-27b@q4_k_m
```

## Why It Matters

This is the split you wanted:

- LLM for orchestration and explanation
- symbolic engine for hard clinical rule consequences

That gives us answers that are both readable and reproducible.
