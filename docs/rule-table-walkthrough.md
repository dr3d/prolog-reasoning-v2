# Rule-Derived Table Walkthrough (Level 3)

Status: Active  
Date: 2026-04-06

Canonical ladder:

- [walkthrough-ladder.md](walkthrough-ladder.md)

## Goal

Show deterministic table/report generation from rules with no LLM dependency.

## Run

```bash
python scripts/demonstrate_rule_table_tool.py
```

## What to Look For

- table rows are computed from rules, not guessed
- changes in facts/rules propagate deterministically into row outputs
- this pattern maps directly to access reports and compliance tables

## Next

- Level 4: [rule-table-agent-mcp-walkthrough.md](rule-table-agent-mcp-walkthrough.md)
