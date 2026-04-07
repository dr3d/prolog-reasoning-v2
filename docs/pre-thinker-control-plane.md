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
- routes turns into ontology context (including context/KB switching),
- runs a pre-handoff clarification lane (clarification eagerness policy),
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
2. Ontological routing (active context and KB-switch candidate)
3. clarification preparation (clarification candidates before model handoff)
4. Correction cue detection
5. Confidence scoring and fallback policy
6. Structured control outputs for downstream components

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
- `kb_switch_candidate`: optional context/KB target
- `manifest_match_score`: float in `[0.0, 1.0]`
- `memory_operation`: `assert | tentative | confirm | retract | supersede | none`
- `clarification_needed`: bool
- `confirmation_required`: bool
- `clarification_prompt`: optional targeted "did you mean...?" prompt
- `correction_cue`: optional label
- `escalation_required`: bool
- `escalation_reason`: optional text
- `trace`: optional short rationale for debugging

This record is consumed by:
- ingestion routing,
- ontology-scoped retrieval policy,
- contradiction and revision workflows,
- and optional larger-model orchestration.

## 5.1 Two Control Lanes

The pre-thinker supports two adjacent but distinct lanes:

1. Ontological routing
- picks active context and suggests context/KB switches.
- scoped search/write decisions are handled by routing policy.

2. clarification eagerness lane
- generates clarification candidates before model handoff.
- asks "did you mean...?" style questions for uncertain but relevant facts.
- does not override deterministic commit gates.

Ownership split:
- routing policy owns the clarification eagerness knob (`clarification_eagerness`),
- pre-thinker emits the signals and candidate prompts.
- operational decision table: `docs/secondary/clarification-eagerness-decision-table.md`

## 5.2 Clarification Eagerness (Policy Knob)

User-facing concept: clarification eagerness
Policy/config key: `clarification_eagerness`

Roadmap note:
- this is a forward-looking control policy, not a mandatory current-runtime behavior.

Purpose:
- increase eagerness to confirm uncertain but relevant facts,
- without lowering deterministic write safety.

Interpretation:
- `0.0`: conservative; clarify only near-commit cases.
- `0.5`: balanced; clarify medium-confidence manifest-matched facts.
- `1.0`: aggressive harvest mode; ask targeted clarification before dropping likely facts.

Important safety rule:
- higher clarification eagerness means more clarification attempts, not more auto-commits.

## 5.3 Clarification Loop

When a turn maps to likely KB terms but confidence is below auto-commit threshold:
1. Generate one targeted clarification question.
2. Ask user to confirm/adjust the candidate fact shape.
3. If confirmed, apply write operation.
4. If corrected, reframe and ask once more.
5. If unresolved after policy limit, keep as tentative or skip persistence.

Recommended caps:
- one question at a time,
- bounded retries per candidate,
- explicit confirmation required for uncertain persistence.

## 6. Interaction With Existing Specs

This design complements two existing notes:
- ontology routing policy in `docs/secondary/ontology-context-routing-spec.md`
- memory ingestion and revision policy in `docs/fact-intake-pipeline.md`

The pre-thinker should be viewed as the decision front-end that feeds those systems.

## 7. Reference Flow

1. User turn arrives.
2. Pre-thinker emits control record.
3. Router resolves active context and optional KB switch.
4. clarification policy decides whether to run clarification before handoff.
5. Ingestion layer applies memory operation.
6. Symbolic layer validates and persists deterministic facts.
7. Large model is called only if policy says escalation is required.
8. Response is assembled with context and revision metadata.

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
