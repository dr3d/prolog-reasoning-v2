# Methods Appendix Template

Status: Template
Purpose: Document exactly how each published metric was produced.

## 1. Study Metadata

- Study title:
- Date run:
- Commit hash:
- Author(s):
- Environment owner:

## 2. Environment and Hardware

- OS and version:
- CPU model and cores:
- RAM:
- Python version:
- Dependency lock reference:
- Execution mode: local / CI

## 3. Code Paths Used

- Dataset generation: data/benchmark.py
- Evaluation execution: data/evaluate.py
- Engine correctness tests: tests/test_engine.py
- Semantic tests: tests/test_semantic.py
- Failure translation tests: tests/test_failures.py

## 4. Dataset Definition

- Dataset file:
- Number of test cases:
- Domains covered:
- Inclusion criteria:
- Exclusion criteria:
- Labeling assumptions:

## 5. Experimental Conditions

For each condition, list exact configuration:

1. Symbolic baseline
- Description:
- Inputs:
- Runtime settings:

2. Neuro-symbolic pipeline
- Description:
- Inputs:
- Validator settings:
- Failure translator settings:

3. LLM-only baseline (if available)
- Description:
- Model:
- Prompt mode:
- Temperature:
- Other decoding settings:

## 6. Metrics and Definitions

For each metric, include formula and interpretation.

- Accuracy:
- Pass/fail criterion:
- Latency:
- Error guidance quality (if human-rated):
- Recovery rate after guidance:

## 7. Procedure

1. Regenerate benchmark dataset:
- python data/benchmark.py

2. Run evaluation:
- python data/evaluate.py

3. Run tests:
- pytest tests/test_engine.py -v
- pytest tests/test_semantic.py -v
- pytest tests/test_failures.py -v

4. Archive artifacts:
- data/evaluation_report.json
- Console output logs
- Methods appendix version

## 8. Statistical Reporting

- Number of runs per condition:
- Mean and variance:
- Confidence interval method:
- Outlier handling:

## 9. Validity Threats

- Internal validity risks:
- External validity risks:
- Construct validity risks:

## 10. Reproducibility Checklist

- [ ] Commit hash recorded
- [ ] Environment recorded
- [ ] Dataset version recorded
- [ ] Commands recorded
- [ ] Raw outputs archived
- [ ] Metrics definitions included
- [ ] Known limitations stated

## 11. Claim Traceability

List each public claim and point to its evidence package.

- Claim ID:
- Claim text:
- Evidence file(s):
- Caveats:
