# Prolog Reasoning v2 - Session Tracker

This file is a compact public summary of recent project state.

## Current Snapshot

- Last major track completed: Simulation-oriented MCP demos with visible internals, plus pre-thinker LoRA bootstrap scaffolding
- Current product direction: Core symbolic reliability first, with MVP editor treated as experimental
- Evaluator status: `prolog_baseline` 13/13, `ir_compiled` 13/13, `lm_only` 8/13 (improved from 6/13)
- Latest actions: Added a practical pre-thinker training lane with `scripts/generate_prethinker_dataset.py` (weak-label bootstrap data in flat/chat JSONL shapes), `scripts/evaluate_prethinker_classifier.py` (baseline metrics + confusion matrix), seed samples in `data/prethinker/`, and a new LoRA sequencing guide in `docs/research/prethinker-lora-playbook.md`; added focused classifier unit tests in `tests/test_statement_classifier.py`; wired docs/readme references so the new lane is discoverable.
- Next priority: Collect reviewed real-turn classification labels from live LM Studio sessions, then compare rule baseline vs small-model vs first LoRA run on the same held-out slices before touching write-path authority.

## Usage Notes

1. Keep this file short and current.
2. Keep this file focused on current state, not narrative history.
3. Long-form working notes can stay local and do not need to be published.
