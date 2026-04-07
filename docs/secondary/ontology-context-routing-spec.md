# Ontology Context Routing Spec

Status: Draft
Owner: Core symbolic layer
Date: 2026-04-05

## 1. Goal

Improve retrieval focus and fact placement by modeling the active conversation as a sequence of ontology contexts ("gears").

Instead of searching all knowledge equally on every turn, the system should:
- infer the active ontology context,
- switch context/KB scope when signals indicate drift,
- prioritize retrieval inside that context,
- run a pre-handoff clarification pass (clarification eagerness policy) for uncertain but relevant facts,
- store new facts with explicit context tags,
- and log context transitions for explainability.

## 2. Problem Statement

As fact volume grows, a flat global KB degrades practical relevance even when logic is correct.

Observed failure mode:
- The system remains deterministic but returns low-value facts because retrieval scope is too broad.

Desired behavior:
- Keep deterministic reasoning,
- but narrow search/write scope using active ontology context.

## 3. Terms

- Ontology Context: A domain lens with its own entities, predicates, and optional parent/related contexts.
- Active Context: Highest-confidence context for the current turn.
- Context Transition: Shift from one active context to another between turns.
- Scoped Retrieval: Query policy constrained by active context and fallback strategy.
- Scoped Assertion: Writing a new fact with explicit context metadata.
- clarification eagerness lane: clarification path that tries to confirm uncertain facts before model handoff.

## 4. Design Principles

1. Determinism first: routing should reduce search scope, not add opaque behavior.
2. Explainability: every answer can report context used and fallback path.
3. Reversible policy: global search remains available as fallback.
4. Low coupling: context routing wraps existing engine; it does not replace Prolog semantics.

## 5. Data Model

## 5.1 Ontology Registry

Each context record:
- context_id: string
- name: string
- description: prose profile
- parent_context_id: optional string
- related_context_ids: list[string]
- key_predicates: list[string]
- key_entities: list[string]
- confidence_threshold: float (default 0.55)

Suggested storage:
- `data/ontology_registry.json`

## 5.2 Fact Metadata

Each asserted fact gets metadata:
- fact_id: string
- session_id: string
- context_id: string
- source: enum {user, imported, inferred}
- created_at: timestamp
- confidence: float (optional)

Logical fact content remains unchanged in Prolog terms.

## 5.3 Context Transition Log

Per session transition events:
- turn_index: int
- from_context_id: string
- to_context_id: string
- router_score: float
- trigger: string (keyword, predicate, explicit user signal)

Suggested storage:
- `data/context_transitions.jsonl`

## 6. Routing Algorithm

Input:
- current user turn,
- recent turns window,
- ontology registry,
- previous active context.

Output:
- active_context_id,
- confidence,
- ranked alternatives.

## 6.1 Scoring Signals

- lexical overlap with context description and key terms,
- predicate/entity matches in parsed IR,
- continuity bonus for previous active context,
- explicit user cues ("switch to legal", "back to healthcare").
- manifest alignment score for candidate fact terms.

Optional control-plane inputs from pre-thinker:
- candidate fact confidence,
- `manifest_match_score`,
- ambiguity flags for entity/relation mapping.

Roadmap note:
- these inputs are optional future-lane controls and can remain disabled in current deployments.

## 6.2 Selection Rules

1. Score all contexts.
2. If top score >= threshold, select top.
3. Else keep previous context if previous confidence was stable.
4. Else select `global` context.

## 6.3 Clarification Eagerness Lane (Pre-Handoff Clarification)

This lane is colocated with routing policy, not final generation.

Policy/config key:
- `clarification_eagerness` in `[0.0, 1.0]`

Behavior:
- low: clarify only near-commit uncertain facts.
- medium: clarify medium-confidence manifest-matched facts.
- high: aggressively seek confirmation before dropping likely facts.

Safety invariant:
- this knob increases clarification attempts only.
- it does not permit uncertain auto-commit.

Reference policy table:
- `docs/secondary/clarification-eagerness-decision-table.md`

## 7. Retrieval Policy

Three deterministic modes:

1. strict
- Query active context only.
- Use for high-precision workflows.

2. soft
- Query active context first, then parent/related contexts.
- Stop at first high-confidence result.

3. recovery
- If strict/soft fail, run global fallback and annotate result as fallback.

Default mode: soft.

## 8. Assertion Policy

For each new fact assertion:
1. Resolve active context.
2. Validate predicate compatibility with context profile.
3. If incompatible, either:
   - route to better context, or
   - store as `unstructured` for deferred audit.
4. Persist fact with context metadata.

For uncertain but high-manifest-match candidates:
1. Run clarification pass before persistence.
2. Ask targeted confirmation prompt ("did you mean ...?").
3. Persist only on explicit confirmation.
4. Otherwise keep tentative or skip write.

Policy note:
- higher `clarification_eagerness` increases clarification attempts,
- it does not authorize uncertain auto-commit.

## 9. Explainability Requirements

Every query response should include:
- active_context_id,
- retrieval_mode used,
- fallback_used (bool),
- candidate_contexts (top 3 with scores).

Example:
- context: healthcare
- mode: soft
- fallback_used: false

## 10. Integration Points

1. `src/parser/semantic.py`
- expose parsed entities/predicates for router features.

2. `src/agent_skill.py`
- call router before query/assert.
- include context metadata in structured response.

3. `src/engine/core.py`
- unchanged reasoning semantics; context acts as retrieval/write gate.

4. `kb_manifest.json`
- extend with ontology registry and per-fact context tags.

## 11. Evaluation Plan

## 11.1 Metrics

- context_selection_accuracy: router choice vs labeled context.
- retrieval_precision_at_k under high fact volume.
- wrong-context retrieval rate.
- fallback_rate (soft/recovery).
- response latency delta vs global search baseline.

## 11.2 Benchmarks

Add multi-context benchmark cases:
- mixed-domain conversation turns,
- deliberate context shift turns,
- ambiguous turns requiring fallback.

## 12. Rollout Plan

Phase A (MVP)
- static ontology registry
- lexical + continuity scoring
- soft mode retrieval
- transition log

Phase B
- IR/predicate-aware scoring
- assertion compatibility checks
- context explainability in responses

Phase C
- learned router weights from labeled sessions
- automated context drift detection

## 13. Non-Goals

- No probabilistic logic changes inside Prolog engine.
- No hard dependency on a frontier model for routing.
- No ontology editor UI in this phase.

## 14. Open Questions

1. Should inferred facts inherit source context or use a derived context?
2. How aggressively should context switch on ambiguous turns?
3. Should context thresholds vary by session type?
4. How should cross-context contradictions be surfaced?
