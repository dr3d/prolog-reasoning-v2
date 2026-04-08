# Fact Extraction Steering Matrix

Tracks local LM Studio runs for buried-fact extraction quality.

Each run compares models and prompt sets on one synthetic corpus.

## Run 2026-04-07 21:48:50 UTC

| model | prompt set | docs | precision | recall | f1 | uncertainty acc | uncertain recall | evidence support | invalid predicate | invalid arity | parse failures | overconfident | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen/qwen3.5-9b | strict_v1 | 2 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0 | 0 | 0 | 0 | ok |

## Run 2026-04-07 21:51:04 UTC

| model | prompt set | docs | precision | recall | f1 | uncertainty acc | uncertain recall | evidence support | invalid predicate | invalid arity | parse failures | overconfident | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen/qwen3.5-9b | strict_v1 | 2 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0 | 0 | 2 | 0 | parse_failures_present |

## Run 2026-04-07 22:12:24 UTC

| model | prompt set | docs | precision | recall | f1 | uncertainty acc | uncertain recall | evidence support | invalid predicate | invalid arity | parse failures | overconfident | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen/qwen3.5-9b | strict_v1 | 2 | 100.0% | 50.0% | 66.7% | 50.0% | 50.0% | 50.0% | 0 | 0 | 1 | 0 | parse_failures_present |

## Run 2026-04-07 22:21:46 UTC

| model | prompt set | docs | precision | recall | f1 | uncertainty acc | uncertain recall | evidence support | invalid predicate | invalid arity | parse failures | overconfident | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen3.5-4b | baseline_v1 | 8 | 100.0% | 44.4% | 61.5% | 50.0% | 37.5% | 50.0% | 0 | 0 | 4 | 0 | parse_failures_present |
| qwen3.5-4b | strict_v1 | 8 | 100.0% | 44.4% | 61.5% | 37.5% | 25.0% | 37.5% | 0 | 0 | 5 | 0 | parse_failures_present |
| qwen/qwen3.5-9b | baseline_v1 | 8 | 100.0% | 55.6% | 71.4% | 62.5% | 50.0% | 62.5% | 0 | 0 | 3 | 0 | parse_failures_present |
| qwen/qwen3.5-9b | strict_v1 | 8 | 100.0% | 66.7% | 80.0% | 62.5% | 37.5% | 62.5% | 0 | 0 | 3 | 0 | parse_failures_present |
| qwen3.5-27b@q4_k_m | baseline_v1 | 8 | 100.0% | 66.7% | 80.0% | 54.2% | 12.5% | 62.5% | 0 | 0 | 3 | 2 | parse_failures_present |
| qwen3.5-27b@q4_k_m | strict_v1 | 8 | 100.0% | 77.8% | 87.5% | 75.0% | 50.0% | 75.0% | 0 | 0 | 2 | 0 | parse_failures_present |
