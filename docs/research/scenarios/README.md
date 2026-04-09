# Scenario Library

This folder stores narrative scenario source files.

## Scope

- Scenario files are narrative-first and should stay compact.
- Keep reusable process guidance in README/docs, not embedded in each scenario file.

Current scenario files:

- `scenario-1.md` (Chronos-Vault baseline)
- `scenario-2.md` (current pre-thinker restructuring pressure test)

## Scenario File Contract

When creating `scenario-N.md`, use this shape:

1. `Purpose`
2. `Run Mode (Required)`
3. `What This Scenario Exercises`
4. `Conversation Protocol`
5. `Reader Preface`
6. `Story Input (Send Verbatim)`

## Where Prompts and Scoring Live

- Put deep-analysis/stress prompt suites in a run plan (JSON) used by:
  - `scripts/run_conversaton.py --input-mode json_plan`
- Use reusable JSON plan starter:
  - `docs/research/conversation-plan-template.json`
- Keep scoring and matrix summaries in conversation outputs under:
  - `docs/research/conversations/`

## Runner Usage

Primary runner:

- `python scripts/run_conversaton.py --conversation-file docs/research/scenarios/scenario-2.md`

Default behavior:

- Runs a model battery with the local Qwen trio:
  - `qwen3.5-4b`
  - `qwen/qwen3.5-9b`
  - `qwen3.5-27b@q4_k_m`

Single-model override:

- `python scripts/run_conversaton.py --conversation-file docs/research/scenarios/scenario-2.md --model qwen3.5-27b@q4_k_m`

Custom battery override:

- `python scripts/run_conversaton.py --conversation-file docs/research/scenarios/scenario-2.md --models qwen3.5-4b qwen/qwen3.5-9b qwen3.5-27b@q4_k_m`

JSON plan mode example:

```json
{
  "title": "Scenario X Quick Run",
  "run_id": "scenario-x",
  "steps": [
    {"id": "reset", "prompt": "Reset runtime KB now. Use ONLY reset_kb and confirm."},
    {"id": "turn_1", "prompt": "Ingest these facts ..."},
    {"id": "turn_2", "prompt": "Now answer ..."}
  ]
}
```

Then run:

- `python scripts/run_conversaton.py --conversation-file path/to/plan.json --input-mode json_plan`

## Scenario-2 Pre-Think A/B Stress Matrix

Run the exact experiment track:

- baseline with pre-think off
- baseline with pre-think on
- context-stuffed with pre-think off
- context-stuffed with pre-think on

Command:

- `python scripts/run_scenario2_prethink_matrix.py --models qwen3.5-4b qwen/qwen3.5-9b`

Outputs are written under:

- `docs/research/conversations/scenario-2-prethink-matrix/<timestamp>/`

The matrix runner emits:

- per-run transcript (`json`, `md`, `html`)
- `matrix-summary.json`
- `matrix-summary.md`
