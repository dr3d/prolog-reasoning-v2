# Pre-Thinker Forward Plan

Status: Active direction  
Date: 2026-04-08

## 1) Why This Exists

This repo is pushing on one specific failure surface in NSAI systems:

`incoming narrative -> candidate memory -> symbolic commit decision`

The pre-thinker is the control layer for that surface.  
Its job is to pre-assess an utterance before any memory write path is attempted.

## 2) Core Goal

Build a small, local pre-thinker that can reliably interpret incoming narrative,
classify intent, and produce structured routing/write signals that survive
deterministic policy gates.

In plain terms:

- not "make a model sound smart"
- make the model useful for safe, high-yield symbolic ingestion
- automate improvement until we know the edge of what works

## 3) What "Success" Means

The pre-thinker is successful when:

1. It emits valid structured outputs for almost all turns.
2. It improves write-path precision and recall versus deterministic baseline.
3. It reduces bad commits without collapsing into over-abstention.
4. It handles narrative ambiguity and correction cues predictably.
5. It remains stateless and advisory (no direct KB authority).

## 4) Current Ground Truth (Now)

Implemented now:

- MCP tool `prethink_utterance` in `src/mcp_server.py`
- MCP tool `prethink_batch` in `src/mcp_server.py`
- Structured assessment validation + fallback to deterministic baseline
- Deterministic write-path projection (`kb_projection.can_write_now`)
- Edge harness:
  - `scripts/run_prethinker_edge_matrix.py`
  - `data/fact_extraction/prethinker_edge_cases_v1.json`

Current architecture posture:

- pre-thinker can be called and evaluated now
- deterministic symbolic layer still decides truth and safety
- no direct durable write permissions are granted to the pre-thinker

## 5) Contract The Pre-Thinker Must Emit

Required assessment fields:

- `kind`
- `confidence`
- `needs_clarification`
- `can_persist_now`
- `suggested_operation`
- `rationale`

Operational projection:

- `kb_projection.should_attempt_write`
- `kb_projection.proposal_status`
- `kb_projection.can_write_now`
- `kb_projection.blocking_reasons`

This gives us a hard eval target:

- Does wording change produce better write-ready outcomes?

## 6) The Real Research Direction (Automated Engineering Loop)

Target loop:

1. Generate or collect phrasing variants for a narrative intent.
2. Run variants through `prethink_batch`.
3. Score:
   - schema validity
   - kind/operation correctness
   - write-readiness (`can_write_now`)
   - false-write risk
4. Promote best-performing prompt/formatting patterns.
5. Add failures back into edge datasets.
6. Repeat continuously.

This is the core idea:

- use local LLM server + deterministic validators + scripted harnesses
- let the system self-pressure-test toward better pre-thinking behavior

## 7) Skill Requirements For The Pre-Thinker

To work on real narrative input, the pre-thinker must handle:

1. Ambiguous speaker grounding (`my mother`, `we`, `our team`)
2. Temporal updates and revisions (`actually`, `correction`, `not anymore`)
3. Hedged uncertainty (`maybe`, `I think`, `someone said`)
4. Latent context dependencies (facts implied by earlier turns)
5. Distinction between:
   - query
   - assertive fact
   - tentative fact
   - correction
   - instruction
   - preference/session context

If it cannot do those reliably, ingestion quality will stall.

## 8) Phased Execution Plan

### Phase A - Stabilize The Evaluation Surface

- Expand `prethinker_edge_cases_v1.json` into broader narrative slices.
- Add explicit expected write-path outcomes per case.
- Keep deterministic baseline and fallback always available.

Exit criteria:

- high structured-output validity
- reproducible score reports across runs

### Phase B - Prompt/Control Optimization

- Compare prompt styles for the same model.
- Compare small-model candidates on the same battery.
- Identify phrasing that increases true positives without raising false commits.

Exit criteria:

- measurable lift over baseline on write-readiness quality metrics

### Phase C - Dataset Growth From Real Runs

- Mine scenario runs for failure clusters.
- Convert high-value failures into edge cases and labeled examples.
- Track drift by timestamped battery snapshots.

Exit criteria:

- failure regression rate trends down over multiple cycles

### Phase D - Candidate Learned Pre-Thinker (Optional)

- Fine-tune/LoRA only after labels stabilize.
- Keep deterministic policy as final authority.
- A/B test learned model vs baseline/fallback stack.

Exit criteria:

- learned system beats baseline on held-out real slices
- no safety regression on commit gating

## 9) Metrics That Matter

Primary:

- assessment schema validity rate
- kind accuracy
- operation accuracy
- write-ready precision
- write-ready recall
- false-write rate (critical)

Secondary:

- fallback rate
- agreement with deterministic baseline
- clarification trigger quality
- latency and cost per turn

## 10) Non-Negotiable Guardrails

1. Pre-thinker is advisory, not authoritative.
2. Deterministic validation gates remain final.
3. Uncertain inputs do not auto-commit.
4. Correction/contradiction signals must never be silently ignored.
5. Every promotion decision must be backed by benchmark evidence.

## 11) Near-Term Build Checklist

1. Add richer edge cases for narrative ambiguity and multi-step correction.
2. Add per-slice scorecards (ambiguity, tentative facts, corrections, queries).
3. Add automated comparison mode for prompt variants.
4. Publish periodic matrix summaries in docs/research.
5. Define promotion thresholds for "best candidate pre-thinker profile."

## 12) North Star

Engineer a pre-thinker that can read messy human narrative and decide, with
measurable reliability, what is ready for symbolic memory and what must be
clarified, deferred, or rejected.

That is the path to trustworthy long-horizon neuro-symbolic memory systems.

