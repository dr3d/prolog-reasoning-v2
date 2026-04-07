# Pre-Thinker LoRA Playbook

Status: Draft  
Date: 2026-04-06

This is the practical answer to:

- should we use a stateless small model as a pre-thinker?
- should we fine-tune with LoRA now, or later?

## Short Answer

Use both, in sequence:

1. Run a stateless small pre-thinker first.
2. Log and label real routing decisions.
3. Add LoRA only after the label schema is stable.

LoRA is an optimization step, not the first architecture step.

## Why This Order Works

- The pre-thinker role is narrow and structured (classification/routing).
- Early in development, labels and edge-cases change quickly.
- LoRA before schema stability tends to overfit temporary assumptions.
- A rule baseline plus small-model baseline gives a hard comparison target.

## Contract To Train

Target output contract mirrors `classify_statement`:

- `kind`
- `confidence`
- `needs_speaker_resolution`
- `can_query_now`
- `can_persist_now`
- `suggested_operation`
- `reasons`

This keeps the pre-thinker stateless and advisory:

- it proposes routing
- deterministic policy still decides write/commit behavior

## Clarification Policy Target (Future Lane)

User-facing concept: **Fact Pull**  
Config/policy key: `clarification_eagerness`

Intended behavior for later phases:
- when statement confidence is below commit threshold but ontology/manifest match is high,
- prompt targeted clarification ("did you mean ...?") to improve fact capture quality,
- require explicit confirmation before uncertain persistence.

Training implication:
- evaluate not only classification accuracy,
- also clarification precision (asks when needed) and confirmation safety (no uncertain auto-commit).

## Bootstrap Dataset Pipeline

Generate weak-label synthetic bootstrap data:

```bash
python scripts/generate_prethinker_dataset.py --out-dir data/prethinker --format both
```

This creates:

- `train_flat.jsonl`, `dev_flat.jsonl`, `test_flat.jsonl`
- `train_chat.jsonl`, `dev_chat.jsonl`, `test_chat.jsonl`
- `metadata.json`

`flat` records are best for analysis and evaluator scripts.  
`chat` records are convenient for SFT/LoRA chat fine-tuning pipelines.

You can also bootstrap from captured LM Studio sessions:

```bash
python scripts/bootstrap_prethinker_from_transcripts.py \
  --inputs docs/examples/hospital-cpm-playbook-session.json docs/examples/fantasy-overlord-session.json \
  --out-dir data/prethinker
```

This extracts candidate utterances from real orchestration prompts, labels them
with the deterministic classifier, and writes train/dev/test JSONL in flat/chat
formats.

## Baseline Evaluation (Deterministic Rules)

Run baseline metrics using the current rule classifier:

```bash
python scripts/evaluate_prethinker_classifier.py \
  --input data/prethinker/test_flat.jsonl \
  --report data/prethinker/rule_classifier_eval.json \
  --predictions-jsonl data/prethinker/rule_classifier_predictions.jsonl
```

This gives:

- overall kind accuracy
- per-kind precision/recall/F1
- confusion matrix
- operation/speaker-resolution agreement

Use this as the floor any learned pre-thinker must beat.

## LoRA Decision Gate

LoRA is worth it when all are true:

1. You have at least a few hundred reviewed real turns (not only synthetic).
2. Label schema has stopped changing every few days.
3. You can evaluate on a held-out set from real conversations.
4. You have a rollback path if the tuned model regresses on edge cues.

If those are not true yet, keep using:

- deterministic classifier + explicit rules
- optional untuned small model for side-by-side diagnostics

## Suggested Rollout

Phase A (now):

- keep deterministic classifier as production default
- generate bootstrap data for quick experiments
- capture model predictions and confusion slices

Phase B:

- start collecting reviewed real-turn labels from LM Studio sessions
- promote transcript-bootstrapped weak labels into reviewed labels
- merge real-turn set with synthetic seed set
- train first LoRA candidate for classification only

Phase C:

- A/B compare tuned pre-thinker vs deterministic baseline
- keep deterministic policy as final authority
- expand only if routing metrics and failure behavior improve

## Non-Goals

- no memory inside the pre-thinker
- no direct KB writes from the pre-thinker
- no replacement of deterministic truth checks

The pre-thinker should find hard logic, not become hard logic.
