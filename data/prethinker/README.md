# Pre-Thinker Dataset Workspace

This folder holds generated datasets and evaluation reports for pre-thinker
classification experiments.

Included seed examples:

- `sample_flat.jsonl`: one labeled sample per routing class.
- `sample_chat.jsonl`: same examples in chat-style training shape.

Generate bootstrap datasets:

```bash
python scripts/generate_prethinker_dataset.py --out-dir data/prethinker --format both
```

Bootstrap additional weak-label examples from captured transcript JSON:

```bash
python scripts/bootstrap_prethinker_from_transcripts.py \
  --inputs docs/examples/hospital-cpm-playbook-session.json docs/examples/fantasy-overlord-session.json \
  --out-dir data/prethinker
```

Run baseline evaluation with the deterministic classifier:

```bash
python scripts/evaluate_prethinker_classifier.py \
  --input data/prethinker/test_flat.jsonl \
  --report data/prethinker/rule_classifier_eval.json \
  --predictions-jsonl data/prethinker/rule_classifier_predictions.jsonl
```

Notes:

- Generated sets are weak-label synthetic bootstrap data.
- Use them to start quickly, then blend in reviewed real-turn labels.
- Keep the pre-thinker stateless; deterministic policy remains final authority.
