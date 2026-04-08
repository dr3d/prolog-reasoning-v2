# Family Tree Agent Walkthrough (Level 2)

Status: Active  
Date: 2026-04-06

Canonical ladder:

- [walkthrough-ladder.md](walkthrough-ladder.md)

## Goal

Show an LLM calling MCP tools for family-relationship queries and statement typing.

## Run

```bash
python scripts/demonstrate_family_tree_agent_mcp.py
```

Optional:

```bash
python scripts/demonstrate_family_tree_agent_mcp.py --model qwen3.5-4b --integration mcp/prolog-reasoning --base-url http://127.0.0.1:1234
```

## What to Look For

- visible MCP tool calls (`query_logic`, `classify_statement`)
- deterministic tool output feeding final model response
- clear separation between query answering and candidate-fact typing

## Next

- Level 3: [rule-table-walkthrough.md](rule-table-walkthrough.md)
