# Docs Map

This docs tree is intentionally organized by topic and maturity so active guidance stays easy to find.

GitHub Pages base (for shareable rendered HTML):  
`https://dr3d.github.io/prolog-reasoning/`

## Start Here (Core)

- [lm-studio-mcp-guide.md](lm-studio-mcp-guide.md): LM Studio + MCP setup and usage.
- [mcp-chat-playbooks.md](mcp-chat-playbooks.md): copy/paste chat playbooks for deterministic tool use.
- [index.html](https://dr3d.github.io/prolog-reasoning/): default docs landing page with project intro and primary demo links.
- [docs-hub.html](https://dr3d.github.io/prolog-reasoning/docs-hub.html): styled docs hub page.

## Live Demo Artifacts (Core)

- [examples/hospital-cpm-playbook-session.html](https://dr3d.github.io/prolog-reasoning/examples/hospital-cpm-playbook-session.html): Critical Path Method (CPM)-style hospital control-room transcript.
- [examples/fantasy-overlord-session.html](https://dr3d.github.io/prolog-reasoning/examples/fantasy-overlord-session.html): multi-character simulation transcript with Prolog console view.
- [examples/indie-launch-warroom-session.html](https://dr3d.github.io/prolog-reasoning/examples/indie-launch-warroom-session.html): conversational game-launch control-room transcript.
- [examples/indie-launch-warroom-natural-session.html](https://dr3d.github.io/prolog-reasoning/examples/indie-launch-warroom-natural-session.html): natural-language tool-selection robustness capture (honest pass/miss per step).
- [fantasy-overlord-session.md](fantasy-overlord-session.md): markdown version of the fantasy transcript.
- [examples/](examples/): canonical captured transcript JSON/MD/HTML artifacts.

## Conversation Rendering (Core Tooling)

- [../scripts/render_dialog_json_html.py](../scripts/render_dialog_json_html.py): centralized `json -> themed html` renderer with reusable conversation template and CSS skins.
- [../scripts/render_examples_sessions_html.py](../scripts/render_examples_sessions_html.py): one-command re-render for `docs/examples/*-session.json` into canonical HTML.
- [../scripts/render_dialog_helpers.py](../scripts/render_dialog_helpers.py): bridge helper used by capture scripts so they all render via the centralized pipeline.
- [../scripts/templates/dialog-session-page.template.html](../scripts/templates/dialog-session-page.template.html): shared transcript page template (topbar, theme toggle, copy buttons, tool-call expandos).
- [../scripts/templates/dialog-themes/standard.css](../scripts/templates/dialog-themes/standard.css): house transcript skin.
- [../scripts/templates/dialog-themes/telegram.css](../scripts/templates/dialog-themes/telegram.css): Telegram-style skin.
- [../scripts/templates/dialog-themes/imessage.css](../scripts/templates/dialog-themes/imessage.css): iMessage-style skin.

## Walkthroughs (Core)

- [walkthrough-ladder.md](walkthrough-ladder.md): canonical level-by-level demo index.
- [family-tree-walkthrough.md](family-tree-walkthrough.md): deterministic logic tool walkthrough.
- [family-tree-agent-mcp-walkthrough.md](family-tree-agent-mcp-walkthrough.md): LLM + MCP family-tree walkthrough.
- [rule-table-walkthrough.md](rule-table-walkthrough.md): logic-table derivation walkthrough.
- [rule-table-agent-mcp-walkthrough.md](rule-table-agent-mcp-walkthrough.md): LLM + MCP rule-table walkthrough.
- [drug-triage-walkthrough.md](drug-triage-walkthrough.md): deterministic triage logic walkthrough.
- [drug-triage-agent-mcp-walkthrough.md](drug-triage-agent-mcp-walkthrough.md): LLM + MCP triage walkthrough.
- [fantasy-overlord-mcp-walkthrough.md](fantasy-overlord-mcp-walkthrough.md): pause/resume simulation with multi-hop inference.
- [indie-launch-warroom-mcp-walkthrough.md](indie-launch-warroom-mcp-walkthrough.md): launch ops war-room walkthrough with incident/recovery turns.

## Core Design Specs (Core)

- [failure-explanations.md](failure-explanations.md): explainable failure model and taxonomy.
- [fact-intake-pipeline.md](fact-intake-pipeline.md): canonical intake + memory + write-path spec.
- [write-path-spec.md](write-path-spec.md): compatibility pointer to canonical spec.
- [memory-ingestion-and-revision-notes.md](memory-ingestion-and-revision-notes.md): compatibility pointer to canonical spec.
- [pre-thinker-control-plane.md](pre-thinker-control-plane.md): stateless pre-thinker control-plane direction (design-track, not enabled by default runtime).

## Scenario and Positioning (Core)

- [uses-and-scenarios.md](uses-and-scenarios.md): where the logic layer is useful.
- [agent-ingestion-tests.md](agent-ingestion-tests.md): ingestion behavior test prompts.

## Research Track (Exploratory)

- [research/model-scenario-matrix.md](research/model-scenario-matrix.md): compact multi-model ledger for scenario-based MCP behavior and logic-ingestion signals.
- [research/fact-ingestion-benchmark-matrix-spec.md](research/fact-ingestion-benchmark-matrix-spec.md): benchmark matrix spec for fact-recognition scenarios, scoring, and pass/fail gates.
- [research/fact-ingestion-dialog-battery.md](research/fact-ingestion-dialog-battery.md): multi-turn natural-language ingestion battery with deterministic post-run KB checks.
- [research/fact-ingestion-dialog-battery.html](https://dr3d.github.io/prolog-reasoning/research/fact-ingestion-dialog-battery.html): themed HTML render of the ingestion battery ledger.
- [research/fact-extraction-steering-matrix.html](https://dr3d.github.io/prolog-reasoning/research/fact-extraction-steering-matrix.html): themed HTML render of the extraction matrix ledger.
- [research/scenarios/README.md](research/scenarios/README.md): scenario authoring contract and runner usage.
- [research/scenarios/scenario-2.md](research/scenarios/scenario-2.md): current scenario narrative used for recent run batches.
- [research/pre-thinker.md](research/pre-thinker.md): forward plan for automating pre-thinker engineering and evaluation.
- [research/conversation-plan-template.json](research/conversation-plan-template.json): reusable JSON prompt-plan template for scenario runs.
- [research/conversations/README.md](research/conversations/README.md): output layout for generated conversation captures.
- [research/prethinker-lora-playbook.md](research/prethinker-lora-playbook.md): practical pre-thinker vs LoRA sequence and dataset/eval workflow.
- [research/collaboration-map.md](research/collaboration-map.md): contribution lanes and open idea prompts for collaborators.
- [research/legacy/README.md](research/legacy/README.md): archived research notes and dated run packs.
- [../scripts/run_prethinker_edge_matrix.py](../scripts/run_prethinker_edge_matrix.py): automation harness for pre-thinker edge-case runs.
- [../data/fact_extraction/prethinker_edge_cases_v1.json](../data/fact_extraction/prethinker_edge_cases_v1.json): starter edge-case dataset for pre-thinker phrasing checks.

## Secondary Track (Optional)

- [secondary/ontology-context-routing-spec.md](secondary/ontology-context-routing-spec.md): ontology-context routing direction (future/non-critical path, not enabled by default runtime).

## Prototype Track (Optional)

- [prototypes/constraint-editor-mvp-playbook.md](prototypes/constraint-editor-mvp-playbook.md): constraint graphics MVP concept.
- [prototypes/README.md](prototypes/README.md): prototype-track docs index.
- [../prototypes/README.md](../prototypes/README.md): repo-level prototype workspace conventions (status lanes, promotion rules, template).

## Legacy References (Historical)

- [legacy/semantic-grounding.md](legacy/semantic-grounding.md): earlier semantic-grounding narrative.
- [legacy/agent-integration.md](legacy/agent-integration.md): earlier manifest-oriented agent integration notes.

## Session Records

- Long-form session notes stay local-only under `sessions/parts/` and are not published.
- [../sessions.md](../sessions.md): compact public session tracker in repo root.

## Intentional Repo-Root Markdown

These files stay at repo root on purpose because they are top-level project controls or entry points:

- [../README.md](../README.md)
- [../status.md](../status.md)
- [../roadmap.md](../roadmap.md)
- [../architecture.md](../architecture.md)
- [../sessions.md](../sessions.md)
- [../SKILL.md](../SKILL.md)
- [../HERMES-AGENT-INSTALL.md](../HERMES-AGENT-INSTALL.md)
- [../OPENCLAW-AGENT-INSTALL.md](../OPENCLAW-AGENT-INSTALL.md)

## Visual Assets

- [diagrams/](diagrams/): diagram source notes and visual assets.
