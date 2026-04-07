# Model Scenario Matrix

This ledger tracks repeatable MCP scenario runs across model sizes and families.

Primary goal: measure logic-ingestion behavior, especially whether a model treats
text as a candidate fact under known predicates instead of drifting into generic
chat narration.

## Focus Metrics

- `validation`: whether the scripted scenario satisfied structural invariants.
- `tools`: required tool coverage count (`11/11` expected for this scenario).
- `classify kind`: output kind from `classify_statement`.
- `candidate predicate`: canonical predicate inferred by deterministic proposal-check.
- `fact recognition`: `yes` when the classify step looked fact-like and produced
  a deterministic candidate predicate with proposal status in
  `valid | needs_clarification`.
- `can persist now`: should remain `false` for uncertain first-person statements.
- `proposal status`: deterministic proposal gate status.
- `classify writes`: should remain `none` during classify step.
- `nl result`: high-level query outcome marker (`status/result_type`).

## How To Run

```powershell
python scripts/run_mcp_surface_model_matrix.py --models qwen3.5-4b qwen/qwen3.5-9b qwen3.5-27b@q4_k_m
```

The runner stores per-model raw captures under `.tmp_model_matrix/` and appends
compact rows to this file.

## Run 2026-04-07 15:56:14 UTC

| model | validation | tools | classify kind | candidate predicate | fact recognition | can persist now | proposal status | classify writes | nl result | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| qwen3.5-4b | pass | 11/11 | tentative_fact | parent | yes | False | needs_clarification | none | no_results/no_result | none |
| qwen/qwen3.5-9b | pass | 11/11 | tentative_fact | parent | yes | False | needs_clarification | none | no_results/no_result | none |
| qwen3.5-27b@q4_k_m | pass | 11/11 | tentative_fact | parent | yes | False | needs_clarification | none | no_results/no_result | none |
