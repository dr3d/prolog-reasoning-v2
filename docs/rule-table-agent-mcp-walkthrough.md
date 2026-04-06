# Rule-Derived Table Agent Walkthrough (Level 4)

Status: Draft  
Date: 2026-04-06

This walkthrough shows an LLM using MCP tools to build a rule-derived
spreadsheet-style table.

Level 3 produced deterministic table rows directly from Python.
Level 4 asks the model to call tools and then compose the table.

## What You Will See

For each prompt, the script prints:

- MCP tool calls (`query_prolog_raw` and related calls)
- tool arguments
- tool output summary
- final model answer

If tool calls appear and the model emits a table, this is overt LLM+logic
cooperation rather than freehand generation.

## Prerequisites

1. LM Studio local server is running
2. `mcp/prolog-reasoning` is enabled and healthy
3. If auth is enabled, provide an API key

Use either:

- env var: `LMSTUDIO_API_KEY`
- or `--api-key` argument

## Run It

From the repo root:

```bash
python scripts/demonstrate_rule_table_agent_mcp.py
```

Optional model override:

```bash
python scripts/demonstrate_rule_table_agent_mcp.py --model qwen3.5-27b@q4_k_m
```

## Prompt Shape

The demo asks the model to:

1. call `query_prolog_raw` for each `(user, action)` permission check
2. return a short yes/no verdict plus evidence for each check
3. assemble a markdown table from those deterministic checks
4. explain Bob's permission failure via an additional tool-backed query

Why raw query in Level 4:

- the natural-language parser is intentionally lightweight in this repo
- raw predicate checks avoid parser ambiguity for table cells
- the model still orchestrates tool use and presentation, while the symbolic
  layer supplies deterministic truth

Current default scenario uses users:

- `alice`
- `bob`
- `john`

## Why This Matters

This is a practical "agent coprocessor" pattern:

- model handles orchestration and presentation
- symbolic layer handles truth and consequences

That pairing is exactly what this project is trying to make easy.

## Level Ladder

- Level 1: [family-tree-walkthrough.md](family-tree-walkthrough.md)
- Level 2: [family-tree-agent-mcp-walkthrough.md](family-tree-agent-mcp-walkthrough.md)
- Level 3: [rule-table-walkthrough.md](rule-table-walkthrough.md)
- Level 4: this doc
