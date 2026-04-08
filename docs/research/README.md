# Research Track

This folder holds exploratory framing and evaluation notes that inform direction, but are not required to run the core system.

- `lmstudio-classifier-matrix.md`: local model behavior comparisons for classifier/control-plane prompts.
- `model-scenario-matrix.md`: compact multi-model run ledger for scenario-based MCP tool/ingestion behavior.
- `fact-ingestion-benchmark-matrix-spec.md`: canonical benchmark spec for scenario matrix design, scoring, gates, and artifacts.
- `fact-ingestion-dialog-battery.md`: multi-turn natural-language ingestion battery with post-run deterministic KB checks.
- `fact-ingestion-dialog-battery.html`: themed HTML render of the ingestion battery ledger.
- `fact-extraction-steering-matrix.html`: themed HTML render of the extraction matrix ledger.
- `prethinker-lora-playbook.md`: practical plan for when to use stateless pre-thinker baselines vs LoRA fine-tuning.
- `collaboration-map.md`: contribution lanes and open idea prompts for new collaborators.
- `stretch-logic-scenarios.md`: trimmed appendix of advanced scenario ideas (canonical practical scenarios live in `docs/uses-and-scenarios.md`).
- `neuro-symbolic-2026-landscape.md`: landscape-style synthesis and cautions.
- `neuro-symbolic-2026-stack-pitch.md`: implementation-oriented positioning narrative.
- `lp-lm-comparison.md`: takeaways from LP-LM (2502.09212v1) mapped to this repo's roadmap and MCP workflow.

Render command:

`python scripts/render_research_ledgers_html.py`
