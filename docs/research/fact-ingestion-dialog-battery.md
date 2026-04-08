# Fact Ingestion Dialog Battery

This ledger tracks multi-turn natural-language ingestion behavior, followed by deterministic KB checks.

Goal:
- measure whether a model writes grounded facts,
- avoids writing uncertain claims,
- and keeps behavior stable across steering profiles.

## Runner

```powershell
python scripts/run_fact_ingestion_dialog_battery.py --models qwen3.5-4b qwen/qwen3.5-9b qwen3.5-27b@q4_k_m
```

The runner appends compact run tables below and stores detailed per-scenario artifacts under:

`.tmp_fact_ingestion_dialog_battery/`

## Run 2026-04-07 22:10:56 UTC

| model | steering | scenario pass | kb checks | turn expectations | uncertain write violations | notes |
|---|---|---|---|---|---|---|
| qwen/qwen3.5-9b | strict_ingestion_v1 | 0/1 (0.0%) | 1/3 (33.3%) | 3/3 (100.0%) | 0 | review_failed_scenarios |

## Run 2026-04-07 22:13:28 UTC

| model | steering | scenario pass | kb checks | turn expectations | uncertain write violations | notes |
|---|---|---|---|---|---|---|
| qwen3.5-4b | loose_v1 | 1/4 (25.0%) | 6/12 (50.0%) | 8/10 (80.0%) | 1 | review_failed_scenarios |
| qwen3.5-4b | strict_ingestion_v1 | 1/4 (25.0%) | 8/12 (66.7%) | 8/10 (80.0%) | 0 | review_failed_scenarios |
| qwen/qwen3.5-9b | loose_v1 | 2/4 (50.0%) | 9/12 (75.0%) | 9/10 (90.0%) | 0 | review_failed_scenarios |
| qwen/qwen3.5-9b | strict_ingestion_v1 | 2/4 (50.0%) | 8/12 (66.7%) | 9/10 (90.0%) | 0 | review_failed_scenarios |
| qwen3.5-27b@q4_k_m | loose_v1 | 2/4 (50.0%) | 9/12 (75.0%) | 10/10 (100.0%) | 0 | review_failed_scenarios |
| qwen3.5-27b@q4_k_m | strict_ingestion_v1 | 2/4 (50.0%) | 9/12 (75.0%) | 9/10 (90.0%) | 0 | review_failed_scenarios |
