# Family Memory Ladder Report (Qwen 3.5 9B, Harder Pass)

Date: 2026-04-09  
Model: `qwen/qwen3.5-9b`

## Objective

Run a non-toy pre-think routing experiment that stresses:

- fact seeding and multi-hop ancestry
- explicit corrections
- secondary branch rewiring (correction of a correction path)
- tentative claims that should not be persisted
- lexical distractors (`LIAM-42`, `AVA-7`) that look like entity names
- final consistency checks after noise

The goal was to compare fuzzy recall vs grounded memory behavior, while preserving natural chat output.

## Mode Setup

1. `fuzzy`
- MCP integration disabled
- model relies on context memory only

2. `sharp`
- MCP integration enabled
- direct Prolog fact/query tools encouraged
- no `pre_think`

3. `hybrid`
- MCP integration enabled
- `pre_think` required each turn with:
  - `handoff_mode=rewrite`
  - `kb_ingest_mode=facts`

4. `hybrid_pressure`
- same as `hybrid`
- additional context ballast injected each turn

## Run Notes

- Primary 3-mode run (`fuzzy`, `sharp`, `hybrid`): `20260409-040159`
- Pressure-only run (`hybrid_pressure`): `20260409-043209`
- Reason for split: full 4-mode pass hit wall-clock timeout in this terminal session; pressure mode was then completed independently.

## Consolidated Results

| mode | status | probes pass | probes total | pass rate | tier4+ pass | pre_think calls | prolog tool calls | write tool calls |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| fuzzy | ok | 10 | 12 | 0.833 | 0.778 | 0 | 0 | 0 |
| sharp | ok | 9 | 12 | 0.750 | 0.667 | 0 | 31 | 9 |
| hybrid | ok | 10 | 12 | 0.833 | 0.778 | 24 | 35 | 8 |
| hybrid_pressure | ok | 10 | 12 | 0.833 | 0.778 | 33 | 38 | 8 |

## What Happened

- `hybrid` matched `fuzzy` on top-line score but did it with grounded tool usage and auditable facts.
- `sharp` used many writes/queries but underperformed on this run, with a few blank/empty answers.
- `hybrid_pressure` held score under context ballast, though with higher tool traffic and two transient tool-format retries.
- The biggest late-stage failures were final consistency checks (`q11`, `q12`) where pure fuzzy recall dropped anchor facts.

## Important Scoring Note

Token-based forbidden checks can over-penalize semantically correct answers that mention a forbidden token in a negated context (example: "Theo is no longer in Rhea's lineage"). This affected one probe in `sharp` and one in `hybrid_pressure`.

## Artifacts

Publish-safe summaries:
- [family-memory-ladder-qwen9b-2026-04-09-summary.json](family-memory-ladder-qwen9b-2026-04-09-summary.json)
- [family-memory-ladder-qwen9b-2026-04-09-summary.md](family-memory-ladder-qwen9b-2026-04-09-summary.md)

Local raw transcripts (not published in git):
- `docs/research/conversations/family-memory-ladder/20260409-040159/*`
- `docs/research/conversations/family-memory-ladder/20260409-043209/*`

The `docs/research/conversations/**` tree is intentionally git-ignored for publication hygiene.

## Showcase Rotation Note

Docs hub points at two stable showcase filenames:

- `docs/examples/family-memory-ladder-hybrid-session.html`
- `docs/examples/family-memory-ladder-hybrid-pressure-session.html`

When a better run arrives, replace those two files with newer captures and keep the publish-safe summary files current. This lets links stay stable while content quality improves over time.

## Reproduce

```powershell
# 3-mode main pass
python scripts/run_family_memory_ladder.py --model qwen/qwen3.5-9b --modes fuzzy sharp hybrid --step-retries 3 --request-timeout-seconds 240

# pressure pass
python scripts/run_family_memory_ladder.py --model qwen/qwen3.5-9b --modes hybrid_pressure --step-retries 3 --request-timeout-seconds 240 --pressure-stuffing-chars 1600
```
