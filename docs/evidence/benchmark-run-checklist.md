# Benchmark Run Checklist

Status: Operational checklist
Purpose: Run reproducible benchmark passes and avoid metric drift.

## Pre-Run

- [ ] Confirm working tree state and note commit hash.
- [ ] Activate the intended Python environment.
- [ ] Record machine and OS details.
- [ ] Clear or archive old run outputs if needed.

## Data and Scenario Setup

- [ ] Regenerate benchmark dataset:
  - python data/benchmark.py
- [ ] Confirm test case count and domain summary.
- [ ] Verify any scenario-specific config files.

## Core Evaluations

- [ ] Run evaluation script:
  - python data/evaluate.py
- [ ] Confirm output artifact exists:
  - data/evaluation_report.json
- [ ] Capture console output logs for audit.

## Test Integrity Checks

- [ ] Run engine tests:
  - pytest tests/test_engine.py -v
- [ ] Run semantic tests:
  - pytest tests/test_semantic.py -v
- [ ] Run failure explanation tests:
  - pytest tests/test_failures.py -v

## Baseline Discipline

- [ ] Symbolic baseline result is captured.
- [ ] Neuro-symbolic pipeline result is captured.
- [ ] LLM-only baseline is either captured or explicitly marked unavailable.
- [ ] Any missing baseline is documented with reason.

## Metrics QA

- [ ] Accuracy definition matches methods appendix.
- [ ] Latency unit and sampling window are documented.
- [ ] Pass/fail logic is unchanged from previous run or explicitly noted.
- [ ] Variance or repeated-run policy is documented.

## Failure Taxonomy QA

- [ ] Failure classes used by translator are listed.
- [ ] At least one representative example per failure class is logged.
- [ ] Suggested remediation text is present for each class.

## Post-Run Packaging

- [ ] Save run bundle to dated folder under data/results (recommended).
- [ ] Update claim-to-evidence matrix with new artifacts.
- [ ] Update methods appendix with run-specific details.
- [ ] Mark any unresolved anomalies and next actions.

## Release Gate

Do not publish new numbers unless all are true:

- [ ] Methods are documented.
- [ ] Artifacts are saved and traceable.
- [ ] Baselines are present or explicitly justified.
- [ ] Caveats are disclosed.
