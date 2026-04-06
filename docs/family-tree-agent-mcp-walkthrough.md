# Family Tree Agent Walkthrough (Level 2)

Status: Draft  
Date: 2026-04-05

This walkthrough shows an LLM overtly using the Prolog reasoning MCP tool.

Level 1 was pure engine usage.
Level 2 is the same logic idea, but now the model calls tools through LM Studio.

## What You Will See

The script sends prompts to LM Studio and asks the model to use MCP tools such
as:

- `query_prolog`
- `classify_statement`

For each prompt, it prints:

- the tool call(s)
- the tool arguments
- the tool output summary
- the final model response

If tool calls appear, the model is explicitly using deterministic logic instead
of only freehand text generation.

## Prerequisites

1. LM Studio local server is running
2. `mcp/prolog-reasoning` is enabled and healthy
3. If auth is enabled, an API key is available

You can provide the key either by:

- env var: `LMSTUDIO_API_KEY`
- script flag: `--api-key`

## Run It

From the repo root:

```bash
python scripts/demonstrate_family_tree_agent_mcp.py
```

Optional flags:

```bash
python scripts/demonstrate_family_tree_agent_mcp.py \
  --model qwen3.5-4b \
  --integration mcp/prolog-reasoning \
  --base-url http://127.0.0.1:1234
```

## What The Prompts Do

The script runs four prompts:

1. `Use query_prolog to answer: Who is John's parent?`
2. `Use query_prolog to answer: Is John an ancestor of Bob?`
3. `Use query_prolog to answer: Who is Alice's parent?`
4. `Use classify_statement on: My mother was Ann.`

This gives both:

- classic relationship inference
- statement-typing behavior for intake

## Why This Is Useful

This is the first practical "agent + logic tool" loop:

- model chooses a tool
- tool returns deterministic structure
- model responds using that structure

That is exactly the operational pattern this project is designed for.

## Level 1 vs Level 2

- Level 1: [family-tree-walkthrough.md](family-tree-walkthrough.md)
  - pure deterministic engine
  - no LLM in the loop

- Level 2: this doc
  - LLM + MCP integration
  - overt tool use shown in output

## Next Step

After this, a good next walkthrough is:

- access-control checks through MCP
- rule-derived table generation (spreadsheet-style)
