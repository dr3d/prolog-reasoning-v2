# Training Modules

This folder is the low-friction learning track for the repo.

## Recommended Order

1. [01-llm-memory-magic.md](01-llm-memory-magic.md)
2. [02-knowledge-bases-101.md](02-knowledge-bases-101.md)
3. [03-learning-from-failures.md](03-learning-from-failures.md)
4. [04-lm-studio-mcp.md](04-lm-studio-mcp.md)
5. [05-constraint-graphics.md](05-constraint-graphics.md)
6. [06-how-the-editor-thinks.md](06-how-the-editor-thinks.md)
7. [07-reading-conflicts.md](07-reading-conflicts.md)

## Track Intent

The sequence is split into two arcs:

- Logic reliability arc (01-04)
- Constraint graphics arc (05-07)

### Logic reliability arc

This arc teaches:

- why LLM-only memory is not enough for durable fact work
- how to model facts/rules cleanly
- how to debug failures without guessing
- how to run deterministic tools in LM Studio via MCP

### Constraint graphics arc

This arc teaches:

- why constraints are a natural symbolic domain
- how deterministic solve loops behave
- how rollback and explicit conflict messages build trust

## What Is Current

The training content is aligned with current MCP alias tools:

- `query_logic`
- `query_rows`
- `assert_fact`
- `bulk_assert_facts`
- `retract_fact`
- `reset_kb`

Legacy `_raw` names still exist in the server for compatibility, but training
material now uses the alias surface.

## Related Docs

- [../docs/lm-studio-mcp-guide.md](../docs/lm-studio-mcp-guide.md)
- [../docs/mcp-chat-playbooks.md](../docs/mcp-chat-playbooks.md)
- [../docs/walkthrough-ladder.md](../docs/walkthrough-ladder.md)
- [../docs/fact-intake-pipeline.md](../docs/fact-intake-pipeline.md)

## Notes for Maintainers

When MCP or classifier capabilities change, update:

1. `04-lm-studio-mcp.md`
2. This `README.md`
3. Any examples that reference tool names or expected result shape
