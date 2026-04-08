# Research Track

This folder holds exploratory framing and evaluation notes that inform direction, but are not required to run the core system.

## Active Track

- `scenarios/README.md`: scenario authoring contract and runner usage.
- `scenarios/scenario-1.md`: first scenario narrative (Chronos-Vault).
- `scenarios/scenario-2.md`: current scenario narrative focused on pre-thinker restructuring pressure.
- `conversation-plan-template.json`: reusable JSON prompt-plan template for `scripts/run_conversaton.py`.
- `conversations/README.md`: output layout for generated run artifacts.
- `model-scenario-matrix.md`: compact multi-model ledger for scenario-based MCP behavior.
- `fact-ingestion-benchmark-matrix-spec.md`: benchmark spec for ingestion scenario scoring and gates.
- `fact-ingestion-dialog-battery.md`: multi-turn ingestion battery ledger.
- `fact-ingestion-dialog-battery.html`: themed HTML render of ingestion battery ledger.
- `fact-extraction-steering-matrix.md`: extraction steering matrix ledger.
- `fact-extraction-steering-matrix.html`: themed HTML render of extraction steering matrix.
- `pre-thinker.md`: forward plan for pre-thinker automation, evaluation loops, and rollout phases.
- `prethinker-lora-playbook.md`: practical pre-thinker vs LoRA sequence and dataset/eval workflow.
- `collaboration-map.md`: contribution lanes and open idea prompts for collaborators.
- `../../scripts/run_prethinker_edge_matrix.py`: edge harness for pre-thinker phrasing and validation runs.
- `../../data/fact_extraction/prethinker_edge_cases_v1.json`: starter edge-case dataset for the harness.

## Archive

- `legacy/README.md`: archived notes, superseded matrixes, and dated run packs.

Render command:

`python scripts/render_research_ledgers_html.py`
