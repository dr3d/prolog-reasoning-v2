# Fact-Ingestion Benchmark Matrix Spec

Status: Draft  
Owner: Core symbolic + intake track  
Last updated: 2026-04-07

This spec defines a repeatable benchmark matrix for one question:

Can a model reliably recognize when language is a candidate symbolic fact, under known predicates, without over-asserting uncertain or unresolved claims?

The matrix is designed for local-first runs through the existing MCP capture flow and should produce compact, comparable artifacts across models.

## 1) Scope

In scope:

- fact-ish utterance recognition (`hard_fact`, `tentative_fact`, `correction`)
- predicate recognition against a deterministic registry
- argument extraction quality
- unresolved reference handling (especially `<speaker>`)
- write-discipline signals (`classify_statement` must not mutate state)
- query-vs-ingestion routing boundaries

Out of scope (for this benchmark):

- long multi-turn memory durability
- advanced ontology routing (secondary track)
- retrieval quality from external stores

## 2) Benchmark Unit

One benchmark row is:

- one model id
- one scenario id
- one deterministic run (fixed prompt/script order)
- one scored output record

Rows are append-only in a ledger, with raw run artifacts stored locally in `.tmp_*` during comparison windows.

## 3) Scenario Matrix Dimensions

Each scenario is tagged across these dimensions:

1. Predicate familiarity:
- `known_predicate`
- `alias_of_known`
- `unknown_predicate`

2. Certainty shape:
- `explicit`
- `tentative`
- `correction`
- `instructional_non_fact`

3. Reference resolution:
- `fully_grounded`
- `needs_speaker_resolution`
- `ambiguous_entity`

4. Form:
- `natural_text`
- `prolog_literal`
- `noisy_hybrid`

5. Expected operation lane:
- `query_only`
- `classify_only`
- `classify_then_manual_write`

## 4) Minimum Scenario Set (v1)

Use at least these 12 scenarios per model:

1. `S01_known_hard_fact`: `My mother is Ann.`
2. `S02_known_tentative`: `Maybe my mother was Ann.`
3. `S03_known_correction`: `Actually, I meant Alice.`
4. `S04_instruction_non_fact`: `Keep responses concise.`
5. `S05_query_only`: `Who is John's parent?`
6. `S06_alias_resolution`: `Ann is mom of Scott.`
7. `S07_unknown_predicate`: `Ann mentors Scott.`
8. `S08_arity_mismatch_like`: `parent(ann).`
9. `S09_grounded_prolog_literal`: `parent(ann, scott).`
10. `S10_speaker_unresolved`: `Our father was Bob.`
11. `S11_ambiguous_entity`: `The manager reports to Chris.` (no grounding for manager entity)
12. `S12_noisy_hybrid`: `I think maybe parent(ann, me)???`

## 5) Canonical Scoring Fields

Each row should include these fields:

- `run_id`
- `timestamp_utc`
- `model`
- `scenario_id`
- `validation` (`pass|fail`)
- `required_tools_called` (count/expected)
- `classify_kind`
- `classify_confidence`
- `proposal_status` (`valid|needs_clarification|reject|missing`)
- `candidate_predicate`
- `candidate_arguments`
- `needs_speaker_resolution`
- `can_persist_now`
- `classify_write_side_effect` (`none|detected`)
- `query_status_marker` (`success|validation_error|no_result|n/a`)
- `fact_recognition` (`yes|partial|no`)
- `failure_bucket` (see section 7)
- `notes`

## 6) Derived Metrics (Model-Level)

Aggregate over all scenarios per model:

- `fact_recognition_rate` = `% rows with fact_recognition=yes` for fact-ish scenarios
- `predicate_match_rate` = `% rows with expected canonical predicate`
- `safe_abstention_rate` = `% unknown/ambiguous scenarios yielding needs_clarification or reject`
- `speaker_safety_rate` = `% speaker-unresolved scenarios with can_persist_now=false`
- `write_discipline_rate` = `% classify steps with no mutation side effects`
- `routing_accuracy` = `% rows with expected classify kind family`

## 7) Failure Buckets

Use exactly one primary bucket per failed row:

- `F1_kind_misroute`: wrong high-level kind
- `F2_predicate_miss`: candidate predicate missing/wrong
- `F3_argument_parse_error`: argument extraction/normalization failure
- `F4_resolution_safety`: unresolved references not flagged safely
- `F5_overcommit_persist`: can_persist_now true when unsafe
- `F6_undercommit`: clear hard fact rejected without reason
- `F7_tooling_protocol`: wrong/missing required tools
- `F8_unexpected_write`: classify path mutation detected

## 8) Pass/Fail Gates

Per-model benchmark pass requires all hard gates:

1. `write_discipline_rate = 100%`
2. `speaker_safety_rate = 100%`
3. `safe_abstention_rate >= 90%`
4. `routing_accuracy >= 85%`

Soft target gates (tracked, not blocking):

1. `predicate_match_rate >= 85%`
2. `fact_recognition_rate >= 85%`

## 9) Artifact Contract

For each matrix run, keep:

- raw session capture per scenario (`json`, optional `md/html`)
- machine summary `matrix-summary.json`
- append row(s) to ledger markdown table

Suggested local output root:

` .tmp_model_matrix/fact_ingestion_<timestamp>/ `

When publishing canonical snapshots, promote only:

- latest ledger markdown under `docs/research/`
- any explicitly chosen example artifacts under `docs/examples/`

## 10) Execution Protocol

1. Choose model set (for example `4b`, `9b`, `27b@q4`).
2. Run scripted scenarios in fixed order.
3. Validate required-tool usage per scenario.
4. Parse classify/proposal fields into normalized scoring schema.
5. Compute derived metrics and gate outcomes.
6. Append compact results to ledger.
7. Keep `.tmp_*` during active comparison; prune after decisions.

## 11) Mapping to Current Repo Assets

Current assets already cover part of this:

- baseline scenario ledger: `docs/research/model-scenario-matrix.md`
- matrix runner: `scripts/run_mcp_surface_model_matrix.py`
- capture harness: `scripts/capture_mcp_surface_playbook_session.py`
- intake contract: `docs/fact-intake-pipeline.md`
- write proposal validator: `src/write_path/validator.py`

This spec extends those assets from one scenario slice to a proper scenario matrix with consistent scoring.

## 12) Versioning Rules

- Bump `spec_version` when scoring fields or gate definitions change.
- Do not rewrite old rows; append new rows with new version tag.
- If prompt wording changes, record `prompt_set_version` to keep comparisons honest.

## 13) Next Implementation Steps

1. Add `scenario_id` coverage beyond the current single MCP surface session.
2. Extend `scripts/run_mcp_surface_model_matrix.py` to emit all scoring fields in section 5.
3. Add failure bucket assignment logic for deterministic triage.
4. Create a canonical ledger page (`docs/research/fact-ingestion-benchmark-matrix.md`) populated from runs.
