# Family Memory Ladder Summary (Publish-Safe)

- Captured at: 2026-04-09 04:38:00 UTC
- Report date: 2026-04-09
- Model: `qwen/qwen3.5-9b`
- Consolidated from runs: `20260409-040159` + `20260409-043209`

## Results Table

| mode | status | probes pass | probes total | pass rate | tier4+ pass | pre_think calls | prolog calls | write calls | source run |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| fuzzy | ok | 10 | 12 | 0.833 | 0.778 | 0 | 0 | 0 | `20260409-040159` |
| sharp | ok | 9 | 12 | 0.750 | 0.667 | 0 | 31 | 9 | `20260409-040159` |
| hybrid | ok | 10 | 12 | 0.833 | 0.778 | 24 | 35 | 8 | `20260409-040159` |
| hybrid_pressure | ok | 10 | 12 | 0.833 | 0.778 | 33 | 38 | 8 | `20260409-043209` |

## Interpretation

- `hybrid` matched `fuzzy` top-line score while maintaining tool-grounded auditability.
- `sharp` had higher write/query activity but lower score in this pass.
- `hybrid_pressure` held steady under context ballast with higher tool traffic.

## Publication Note

Full per-turn transcripts and raw run artifacts are kept local under `docs/research/conversations/**` and are intentionally excluded from git to keep published docs lightweight.
