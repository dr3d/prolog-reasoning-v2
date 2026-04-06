# Fact Intake Pipeline

Status: Draft  
Owner: Core symbolic layer  
Date: 2026-04-05

## 1. Why This Exists

Fact intake is the missing middle between natural language and deterministic
symbolic reasoning.

The project already has:

- a deterministic logic layer,
- a semantic grounding path,
- validation,
- explanation,
- and agent-facing integrations.

What it does not yet have as a finished subsystem is a disciplined path for
deciding what language deserves durable symbolic treatment.

That is the fact intake problem.

The hard question is not only:

- "Can the system reason over facts?"

It is also:

- "Which utterances contain a symbolic claim?"
- "Which predicate should that claim map to?"
- "How should the arguments be normalized?"
- "Should the result become a hard fact, a tentative memory, a session note, or nothing at all?"

Without a strong intake pipeline, even a good reasoning engine will eventually
operate over noisy or muddy symbolic state.

## 2. Design Principle

LLMs may propose candidate structure. Deterministic policy decides what becomes
durable symbolic truth.

That means:

- language models or classifiers may interpret
- policy layers may rank or abstain
- symbolic validation and write policy remain authoritative

The intake pipeline exists to keep those roles separate.

## 3. Pipeline Stages

### 3.1 Utterance Classification

First decide what kind of thing the user just said.

Current categories include:

- `query`
- `hard_fact`
- `tentative_fact`
- `correction`
- `preference`
- `session_context`

This is the first gate against garbage ingestion.

If the system gets this wrong, everything after it becomes unstable.

### 3.2 Symbolic Suitability Filter

Not every statement that sounds factual belongs in the symbolic layer.

The system should ask:

- is this explicit enough?
- is it durable enough?
- is it too subjective?
- is it too contextual?
- is it too ambiguous?
- is it a plan or hypothesis rather than a fact?

Example:

- `My manager is Dana.` may be symbolically suitable
- `This feels wrong somehow.` is probably not

### 3.3 Predicate Mapping

Once the system decides a statement is symbolically relevant, it needs to map
surface language to a canonical predicate family.

This should prefer:

- controlled predicate vocabularies
- ranked candidate mappings
- abstention when confidence is too low

The goal is to avoid both:

- predicate explosion
- over-generic sludge predicates

Example:

- `Dana manages me`
- `Dana is my manager`
- `I report to Dana`

may all map toward the same canonical relation family.

### 3.4 Argument Extraction and Normalization

After predicate mapping, the system needs normalized arguments.

This stage should decide:

- what the entities are
- what order they belong in
- whether there is negation
- whether there is uncertainty
- whether a first-person reference needs grounding
- whether time or modality should become metadata

Example:

`My mother was Ann.`

may become:

- predicate candidate: `parent`
- arguments: `["ann", "<speaker>"]`
- needs speaker resolution: `true`
- temporal note: `past_or_unspecified`

### 3.5 Canonical Fact Shaping

The intake pipeline should produce a candidate symbolic record, not just a loose
string.

Suggested shape:

```json
{
  "utterance_type": "assertion",
  "symbolically_suitable": true,
  "assertion_kind": "stable_fact",
  "predicate_candidate": "parent",
  "arguments": ["ann", "<speaker>"],
  "needs_speaker_resolution": true,
  "negated": false,
  "temporal_scope": "past_or_unspecified",
  "confidence": 0.81,
  "action": "stage_for_resolution"
}
```

This record is the handoff point between soft interpretation and hard policy.

### 3.6 Assertion Policy

Even a clean candidate record should not automatically become a hard fact.

The policy layer decides whether to:

- `assert`
- `tentative`
- `confirm`
- `retract`
- `supersede`
- `stage`
- `reject`

That decision should incorporate:

- confidence
- ambiguity
- contradiction risk
- memory class
- context
- provenance

## 4. Memory Classes

The intake pipeline should feed typed memory, not a single undifferentiated KB.

### 4.1 Hard Fact

Use when the claim is:

- explicit
- durable
- grounded enough
- safe to participate in deterministic reasoning

### 4.2 Tentative Fact

Use when the claim matters but should not yet be promoted to truth.

### 4.3 Session Context

Use for temporary working assumptions or current-task state.

### 4.4 Preference / Instruction

Use for behavioral guidance rather than world-state truth.

### 4.5 Reject / Do Not Store

Use when the statement is:

- too vague
- too subjective
- unsupported
- purely hypothetical
- better left in conversation only

## 5. Candidate Record Contract

The intake pipeline should eventually emit a structured record with fields like:

- `utterance_type`
- `symbolically_suitable`
- `assertion_kind`
- `predicate_candidate`
- `predicate_candidates_ranked`
- `arguments`
- `needs_speaker_resolution`
- `negated`
- `temporal_scope`
- `confidence`
- `recommended_action`
- `reasons`

This keeps the intake layer inspectable and benchmarkable.

## 6. Relationship to Current Components

### Current Baseline

- `src/parser/statement_classifier.py`
  - first deterministic routing layer
- `src/parser/semantic.py`
  - grounding layer
- `src/validator/semantic_validator.py`
  - validation layer
- `src/mcp_server.py`
  - exposes `classify_statement` to local models

### Related Specs

- `docs/memory-ingestion-and-revision-notes.md`
  - memory classes and revision behavior
- `docs/write-path-spec.md`
  - safe mutation envelope and journal semantics
- `docs/pre-thinker-control-plane.md`
  - future small-model control plane
- `docs/lmstudio-classifier-matrix.md`
  - evidence that structured classification helps local models

## 7. Implementation Sequence

The next practical order should be:

1. strengthen statement classification
2. add symbolic suitability decisions
3. add predicate candidate mapping
4. add normalized argument extraction
5. emit inspectable candidate fact records
6. connect to write-path policy

Do not jump straight from classifier output to free-form KB writes.

## 8. Future Small-Model Role

The future pre-thinker should not own memory.

Its role should be:

- stateless interpretation
- ranked candidate structure
- ambiguity flags
- abstention when uncertain

It may help with intake, but deterministic policy remains final authority.

The principle is:

- soft logic finds candidate hard logic
- deterministic systems decide what is trusted

## 9. What This Pipeline Is Not

It is not:

- a full ontology system
- a free-form predicate invention engine
- a replacement for symbolic reasoning
- a replacement for write-path policy

It is the bridge between human language and symbolic commitment.

## 10. Summary

The fact intake pipeline is the next serious subsystem because it answers the
question the rest of the project depends on:

How do we turn soft language into clean, durable, symbolic structure without
polluting the knowledge base?

That is the missing middle between:

- LLM interpretation
- deterministic symbolic reasoning

and it is the place where memory curation becomes real.
