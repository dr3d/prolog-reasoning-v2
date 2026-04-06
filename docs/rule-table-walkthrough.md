# Rule-Derived Table Walkthrough (Level 3)

Status: Draft  
Date: 2026-04-05

This walkthrough shows a practical "agent + logic tool" outcome:
build spreadsheet-style rows from rules instead of guessing cells.

## What You Will See

The demo computes a table for users:

- `alice`
- `bob`
- `john`

with derived columns:

- role(s)
- derived permissions
- `can_read`
- `can_write`
- `violation_flag`

The rows come from symbolic inference, not ad-hoc text generation.

## Run It

From the repo root:

```bash
python scripts/demonstrate_rule_table_tool.py
```

## What The Demo Uses

It relies on the existing agent-skill knowledge base and rule:

```prolog
role(alice, admin).
permission(admin, read).
permission(admin, write).
allowed(User, Action) :- role(User, Role), permission(Role, Action).
```

Then it resolves:

- `role(User, Role)`
- `allowed(User, Action)`

for each user and materializes deterministic table rows.

## Why This Is Level 3

Level 1 showed pure engine reasoning.
Level 2 showed LLM + MCP tool calls.
Level 3 shows a direct business-style output:

- rule-derived table / spreadsheet view
- deterministic compliance-like flags
- reproducible outputs from the same facts and rules

## What To Notice

1. The table is computed, not written by guesswork.
2. If rules change, rows update deterministically.
3. This pattern generalizes to policy sheets, eligibility tables, and access reports.

## Suggested Next Variation

Change the fact set and rerun:

- add `role(bob, admin)` and watch rows change
- remove `permission(admin, write)` and watch `violation_flag` flip

That is the value proposition of symbolic derivation in a shape people already
understand.
