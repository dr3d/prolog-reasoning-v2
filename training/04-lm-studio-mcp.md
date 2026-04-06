---
layout: post
title: "Local LLM Integration with MCP"
description: "Run deterministic logic tools from LM Studio chat."
level: "Beginner"
domain: "LLM Tools and Integration"
duration: "15 minutes"
---

# Local LLM Integration with MCP

This lesson shows the practical setup path for using this repo as a local MCP
tool server.

## Learning Objectives

By the end, you should be able to:

- configure LM Studio to launch the MCP server
- verify tool availability
- run query and table workflows from chat
- understand runtime write/reset behavior for what-if scenarios

## What MCP Gives You Here

In this repo, MCP gives your chat model access to deterministic tool calls.

Common tools:

- `query_prolog` (NL query path)
- `query_logic` (literal Prolog query)
- `query_rows` (table-style variable bindings)
- `assert_fact`, `bulk_assert_facts`, `retract_fact`, `reset_kb`
- `classify_statement`, `list_known_facts`, `explain_error`, `show_system_info`

Legacy `_raw` tool names are still accepted for compatibility, but the alias
names above are preferred.

## Setup

## 1. Install dependencies

```bash
pip install -r requirements.txt
```

## 2. Configure LM Studio `mcp.json`

Use placeholders, not hardcoded personal paths:

```json
{
  "mcpServers": {
    "prolog-reasoning": {
      "command": "<PYTHON_EXE>",
      "args": [
        "<REPO_ROOT>\\src\\mcp_server.py",
        "--stdio",
        "--kb-path",
        "<REPO_ROOT>\\prolog\\core.pl"
      ],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

Notes:

- `<PYTHON_EXE>` should be the interpreter where requirements were installed.
- `<REPO_ROOT>` should be your local clone path.
- LM Studio owns the stdio process after integration is enabled.

## 3. Verify in chat

Start a fresh LM Studio chat and paste:

```text
Use show_system_info and list_known_facts first.
Confirm query_logic, query_rows, assert_fact, bulk_assert_facts, retract_fact, and reset_kb are available.
Then wait.
```

If those tool names appear and calls succeed, the setup is working.

## First Practical Pattern

For deterministic table/report use, prefer:

- `query_rows` over free-form narrative answers

For scenario state changes:

- `assert_fact` / `retract_fact` for edits
- `reset_kb` to restore baseline runtime state

## Common Issues

### Red warning icon in LM Studio integration

Usually one of:

- bad `command` path
- bad `args` path to `mcp_server.py`
- Python environment missing repo dependencies

Restart LM Studio after config updates.

### Tool calls succeed, but results look empty

Likely causes:

- runtime KB was reset and not re-ingested
- you queried derived predicates before loading prerequisite facts

Use count checks with `query_rows` on base predicates before derived queries.

## Suggested Next Reads

- `docs/lm-studio-mcp-guide.md`
- `docs/mcp-chat-playbooks.md`
- `docs/family-tree-agent-mcp-walkthrough.md`
- `docs/rule-table-agent-mcp-walkthrough.md`

## Key Takeaways

1. MCP turns the symbolic layer into callable tools in normal chat flow.
2. Alias tool names are the clean default surface.
3. Deterministic query/table paths are the safest backbone for live reporting.
4. Runtime fact edits are useful for simulations, with `reset_kb` as a safety rail.
