# Claim-to-Evidence Matrix

Status: Working matrix
Purpose: Prevent unsupported claims from reaching docs or presentations.

Use one row per externally visible claim.

## Rules

- If no evidence exists, mark claim as Internal Observation or Hypothesis.
- Do not publish quantitative claims without method + artifact links.
- Every metric claim must reference a run output and test context.

## Matrix

| Claim ID | Claim Text | Claim Type | Evidence Artifact(s) | Method Reference | Current Status | Caveats |
|---|---|---|---|---|---|---|
| C-001 | Symbolic baseline accuracy is 30.77 percent on benchmark set (4/13) | Quantitative | data/evaluation_report.json, data/results/2026-04-05-evidence/evaluate.log | docs/evidence/METHODS_APPENDIX_2026-04-05.md | Available | Single run only; no variance/confidence interval yet |
| C-002 | Semantic validator catches Y percent of unsupported queries before reasoning | Quantitative | data/results/2026-04-05-evidence/test_semantic.log | docs/evidence/METHODS_APPENDIX_2026-04-05.md | Pending instrumentation | Need explicit catch-rate metric and denominator definition |
| C-003 | Failure explanations improve retry success by Z percent | Quantitative | Retry experiment logs (to be added) | docs/evidence/METHODS_APPENDIX_2026-04-05.md | Not started | Requires controlled before/after retry protocol |
| C-004 | Core engine behavior is stable across current test suite (21/21 passing) | Verification | data/results/2026-04-05-evidence/test_engine.log | docs/evidence/METHODS_APPENDIX_2026-04-05.md | Available | Stability only within covered behaviors |
| C-005 | Semantic parsing and validation workflow handles common family/access intents (17/17 passing) | Verification | data/results/2026-04-05-evidence/test_semantic.log | docs/evidence/METHODS_APPENDIX_2026-04-05.md | Available | Coverage does not imply full domain generalization |
| C-006 | Failure translator returns actionable guidance for common failure classes (16/16 passing) | Verification | data/results/2026-04-05-evidence/test_failures.log | docs/evidence/METHODS_APPENDIX_2026-04-05.md | Available | Actionability not yet user-study validated |
| C-007 | Local-first stack is practical for constrained domain reasoning | Mixed | data/evaluation_report.json, data/results/2026-04-05-evidence/*.log | docs/evidence/METHODS_APPENDIX_2026-04-05.md | Internal observation | Workload and hardware sensitive; baselines incomplete |

## Status Definitions

- Available: Evidence exists now and is traceable.
- Pending measurement: Pipeline exists but current values not pinned.
- Not started: Protocol or instrumentation missing.
- Internal observation: Reasonable claim, not yet formally measured.
- Hypothesis: Forward-looking claim requiring validation.

## Publication Gate

Before publishing docs with claims:

- [ ] Each claim has a row in this matrix.
- [ ] Each quantitative claim has artifact + method link.
- [ ] Each forward-looking claim is tagged as hypothesis.
- [ ] Caveats are written in plain language.
