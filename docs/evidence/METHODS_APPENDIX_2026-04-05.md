# Methods Appendix: Evidence Run 2026-04-05

Status: Completed run log
Purpose: Record exact execution context and outputs for current benchmark and test pass.

## 1. Study Metadata

- Study title: Initial evidence bundle run
- Date run: 2026-04-05
- Commit hash: cb69500
- Author: Repository maintainer + Copilot execution support
- Environment owner: Local workstation

## 2. Environment and Hardware

- OS: Microsoft Windows NT 10.0.26200.0
- PowerShell: 5.1.26100.8115
- CPU: Intel(R) Core(TM) Ultra 9 285K
- RAM: 68407275520 bytes (~63.7 GiB)
- Python: 3.12.11 (venv)
- Execution mode: Local

## 3. Code Paths Used

- Dataset generation: data/benchmark.py
- Evaluation execution: data/evaluate.py
- Engine correctness tests: tests/test_engine.py
- Semantic pipeline tests: tests/test_semantic.py
- Failure explanation tests: tests/test_failures.py

## 4. Dataset Definition (Current Run)

- Dataset file: data/benchmark.json
- Number of test cases: 13
- Domain distribution:
  - family: 6
  - access: 3
  - constraint: 2
  - inference: 2
- Inclusion/exclusion criteria: As currently hardcoded in BenchmarkDataset._build_tests

## 5. Experimental Conditions Executed

1. Symbolic baseline
- Condition name: prolog_baseline
- Source: data/evaluate.py
- Result: 4 passed, 9 failed, total 13
- Accuracy: 0.3076923076923077 (30.77 percent)

2. Neuro-symbolic pipeline
- Condition name: ir_compiled
- Result: Not executed in current evaluate.py flow
- Status: Placeholder field only

3. LLM-only baseline
- Condition name: lm_only
- Result: Not executed in current evaluate.py flow
- Status: Placeholder field only

## 6. Metrics and Definitions Used in This Run

- Accuracy: passed / total in evaluate.py
- Pass criterion: (len(solutions) > 0) equals expected_answer
- Tests run summary: 13 (from evaluation_report summary)
- Latency: per-test elapsed values recorded, currently 0.0 at reported precision

## 7. Procedure and Commands

1. Generate dataset
- d:/_PROJECTS/prolog-reasoning-v2/.venv/Scripts/python.exe data/benchmark.py

2. Run evaluation
- d:/_PROJECTS/prolog-reasoning-v2/.venv/Scripts/python.exe data/evaluate.py

3. Run test suites
- d:/_PROJECTS/prolog-reasoning-v2/.venv/Scripts/python.exe -m pytest tests/test_engine.py -v
- d:/_PROJECTS/prolog-reasoning-v2/.venv/Scripts/python.exe -m pytest tests/test_semantic.py -v
- d:/_PROJECTS/prolog-reasoning-v2/.venv/Scripts/python.exe -m pytest tests/test_failures.py -v

## 8. Artifacts Produced

Primary:
- data/evaluation_report.json

Run logs:
- data/results/2026-04-05-evidence/benchmark.log
- data/results/2026-04-05-evidence/evaluate.log
- data/results/2026-04-05-evidence/test_engine.log
- data/results/2026-04-05-evidence/test_semantic.log
- data/results/2026-04-05-evidence/test_failures.log

## 9. Test Suite Outcomes

- tests/test_engine.py: 21 passed
- tests/test_semantic.py: 17 passed
- tests/test_failures.py: 16 passed
- Total: 54 passed, 0 failed

## 10. Known Issues and Caveats

- Current evaluator baseline accuracy is low (30.77 percent), indicating mismatch between benchmark expectations and loaded rule context in baseline mode.
- ir_compiled and lm_only conditions are not yet implemented in evaluator output.
- Confidence intervals, repeated-run variance, and outlier policy were not applied in this first run.

## 11. Immediate Next Actions

1. Implement ir_compiled and lm_only execution paths in data/evaluate.py.
2. Add repeated-run support (N runs per condition) and variance reporting.
3. Increase timing precision or sampling method for meaningful latency reporting.
4. Investigate baseline failures by category (family recursion, access rule expansion, built-in arithmetic/negation handling).
