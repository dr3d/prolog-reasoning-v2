# Pre-Thinker Control Plane

Status: Draft
Date: 2026-04-05
Owner: Core symbolic layer

## 1. Why This Exists

The project already separates two roles:
- deterministic symbolic reasoning for truth and consistency,
- language models for interpretation and interaction.

As memory and ontology complexity grow, one large model can become an expensive and unstable place to do all control decisions.

This design introduces a smaller "pre-thinker" model as a control plane for ingestion and routing.

## 2. Core Thesis

Use a small model to decide *how* to think before asking a larger model to decide *what* to say.

In practice:
- the pre-thinker classifies statements,
- routes turns into ontology context,
- detects correction and backtracking cues,
- and decides when to escalate to a larger model.

The symbolic engine remains the source of deterministic truth.

## 3. Problem It Solves

Without a dedicated control layer:
- ingestion decisions are inconsistent,
- factual and tentative signals are mixed,
- ontology context can drift silently,
- large-model calls are used when a cheaper policy decision would be enough.

With a control layer:
- memory decisions become explicit,
- context switching is inspectable,
- escalation is policy-driven,
- and cost/latency become easier to manage.

## 4. Scope of the Pre-Thinker

The pre-thinker is not a replacement for the reasoning engine and not a final-answer generator.

Primary responsibilities:
1. Statement typing
2. Ontology context routing
3. Correction cue detection
4. Confidence scoring and fallback policy
5. Structured control outputs for downstream components

Out of scope:
- proving facts,
- writing final user-facing prose,
- overriding deterministic symbolic results.

## 5. Control Outputs (Contract)

For each user turn, the pre-thinker emits a compact control record.

Suggested fields:
- `turn_id`
- `statement_type`: `hard_fact | tentative | session | preference | hypothesis`
- `context_id`
- `context_confidence`
- `memory_operation`: `assert | tentative | confirm | retract | supersede | none`
- `correction_cue`: optional label
- `escalation_required`: bool
- `escalation_reason`: optional text
- `trace`: optional short rationale for debugging

This record is consumed by:
- ingestion routing,
- ontology-scoped retrieval policy,
- contradiction and revision workflows,
- and optional larger-model orchestration.

## 6. Interaction With Existing Specs

This design complements two existing notes:
- ontology routing policy in `docs/ontology-context-routing-spec.md`
- memory ingestion and revision policy in `docs/memory-ingestion-and-revision-notes.md`

The pre-thinker should be viewed as the decision front-end that feeds those systems.

## 7. Reference Flow

1. User turn arrives.
2. Pre-thinker emits control record.
3. Router selects ontology context and retrieval scope.
4. Ingestion layer applies memory operation.
5. Symbolic layer validates and persists deterministic facts.
6. Large model is called only if policy says escalation is required.
7. Response is assembled with context and revision metadata.

## 8. Model Strategy

The control plane is intentionally small:
- small local model,
- domain-adapted via lightweight fine-tuning or LoRA,
- optimized for classification/routing reliability rather than broad generation quality.

Expected advantages:
- lower cost,
- lower latency,
- more stable policy behavior,
- easier iterative retraining with labeled control decisions.

## 9. Failure Modes To Monitor

1. Wrong statement typing
2. Wrong context routing
3. Missed correction cues
4. Over-escalation (too many large-model calls)
5. Under-escalation (insufficient disambiguation)

Mitigation:
- keep control traces,
- build targeted benchmark slices,
- and gate high-impact operations behind deterministic validation.

## 10. Evaluation Targets

Track at least:
- statement typing accuracy,
- context routing accuracy,
- correction cue recall,
- escalation precision/recall,
- end-to-end latency,
- large-model call rate per turn,
- contradiction handling quality after corrections.

## 11. Incremental Rollout Plan

Phase A: Rule-assisted pre-thinker baseline
- Add typed control schema
- Start with lexical and policy heuristics
- Log control outputs for offline labeling

Phase B: Small-model classifier
- Train on logged and hand-labeled turns
- Deploy for statement typing and correction cues
- Keep deterministic fallback rules active

Phase C: Full control plane
- Add learned context routing confidence
- Add escalation policy tuning
- Integrate quality gates into benchmark suite

## 12. Public Positioning

This is a practical architecture pattern, not model hype:
- symbolic engine for determinism,
- small model for control,
- larger model only when needed.

The goal is to make long-horizon memory systems more auditable, cheaper to run, and easier to correct when conversations evolve.