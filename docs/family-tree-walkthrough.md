# Family Tree Walkthrough (Level 1)

Status: Active  
Date: 2026-04-06

Canonical ladder:

- [walkthrough-ladder.md](walkthrough-ladder.md)

## Goal

Show pure deterministic relationship inference with no LLM in the loop.

## Run

```bash
python scripts/demonstrate_family_tree_tool.py
```

## What to Look For

- `ancestor` answers are rule-derived, not hard-coded
- sibling logic is consistent and repeatable
- reruns produce identical results

## Next

- Level 2: [family-tree-agent-mcp-walkthrough.md](family-tree-agent-mcp-walkthrough.md)
