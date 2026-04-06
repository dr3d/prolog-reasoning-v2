# Fact Intake, Memory, and Write Path Spec

Status: Draft  
Owner: Core symbolic layer  
Date: 2026-04-06

This is the canonical spec for:

- fact intake
- memory class routing
- revision operations
- safe write-path policy

It replaces the previous split narrative across:

- `docs/memory-ingestion-and-revision-notes.md`
- `docs/write-path-spec.md`

Those files are now compatibility stubs that point here.

## 1. Why This Exists

The hardest problem is no longer query execution. The hardest problem is deciding what language should become symbolic state.

Without a disciplined intake/write path:

- good reasoning runs on muddy facts
- memory silently drifts
- corrections become ambiguous
- agents claim persistence that never happened

## 2. Design Principle

Soft interpretation may propose structure. Deterministic policy decides what is stored and reasoned over.

Role split:

- language model or classifier: interpret, rank, abstain
- deterministic policy: validate, route, write, journal
- symbolic engine: reason over resolved hard facts

## 3. End-to-End Pipeline

1. Utterance classification
2. Symbolic suitability filtering
3. Predicate mapping and candidate ranking
4. Argument extraction and normalization
5. Candidate record emission
6. Memory operation decision
7. Validation gates
8. Backup + mutation + journal append

### 3.1 Utterance Classification

Current classes:

- `query`
- `hard_fact`
- `tentative_fact`
- `correction`
- `preference`
- `session_context`

### 3.2 Symbolic Suitability

A factual-sounding statement is not automatically fit for symbolic storage. Suitability checks should reject vague, subjective, or underspecified claims.

### 3.3 Predicate Mapping

Map language into a controlled predicate vocabulary with ranked candidates and abstention on low confidence.

### 3.4 Argument Normalization

Normalize:

- entity identity
- argument order
- negation
- uncertainty
- speaker references
- temporal hints as metadata

### 3.5 Candidate Record Contract

```json
{
  "utterance_type": "assertion",
  "symbolically_suitable": true,
  "assertion_kind": "stable_fact",
  "predicate_candidate": "parent",
  "predicate_candidates_ranked": ["parent", "guardian_of"],
  "arguments": ["ann", "<speaker>"],
  "needs_speaker_resolution": true,
  "negated": false,
  "temporal_scope": "past_or_unspecified",
  "confidence": 0.81,
  "recommended_action": "stage_for_resolution",
  "reasons": ["first_person_reference_unresolved"]
}
```

## 4. Memory Classes

Use typed memory, not one flat store.

### 4.1 Hard Fact

For explicit, durable, validated claims that should drive deterministic inference.

### 4.2 Tentative Fact

For potentially useful claims not ready for truth promotion.

### 4.3 Session Context

For temporary working assumptions and task-local state.

### 4.4 Preference / Instruction

For behavioral guidance, not world-state truth.

### 4.5 Reject / No Store

For unsuitable statements (too vague, purely hypothetical, unsupported).

## 5. First-Class Memory Operations

Supported operations:

- `assert`
- `tentative`
- `confirm`
- `retract`
- `supersede`

Operation semantics:

- `assert`: add to resolved hard-fact view + journal
- `tentative`: store in tentative layer only + journal
- `confirm`: promote tentative fact to hard-fact view + journal link
- `retract`: remove from resolved view + journal history retained
- `supersede`: replace old fact with new fact + linked journal record

## 6. Write Request Envelope (Required)

```json
{
  "memory_operation": "assert",
  "statement_type": "hard_fact",
  "context_id": "global",
  "source": "user",
  "session_id": "sess_123",
  "confidence": 0.94,
  "fact_payload": {
    "format": "prolog",
    "value": "parent(ann, scott)."
  }
}
```

`context_id` is required. Writes without context should be rejected.

## 7. Storage Surfaces

Maintain three distinct stores:

1. hard-fact resolved view (query surface)
2. tentative store (staging surface)
3. append-only event journal (audit surface)

## 8. Backup and Journal Policy

### 8.1 Backups

Backup before durable mutations:

- `assert`
- `confirm`
- `retract`
- `supersede`

### 8.2 Journal Event Minimum

- `event_id`
- `event_type`
- `fact_id`
- `related_fact_id` optional
- `context_id`
- `session_id`
- `source`
- `timestamp`
- `confidence`
- `payload`
- `result`

Rejected writes may be journaled as rejected attempts; resolved hard facts must remain unchanged on rejection.

## 9. Validation Gates

Before mutation:

1. parse and normalize payload
2. validate statement type vs operation
3. validate entity grounding
4. validate predicate compatibility
5. validate context compatibility
6. run contradiction checks (for `assert` and `supersede`)
7. take backup
8. apply mutation
9. append journal event

## 10. Contradiction and Revision Rules

Treat these separately:

- contradiction (new claim conflicts with stored fact)
- misunderstanding (prior parse was wrong)
- user correction/undo (explicit revision cue)

First increment policy:

- prefer `supersede` for single-valued relationships
- prefer `tentative` when certainty is weak
- do not silently append mutually incompatible hard facts

## 11. API Boundary

First write path should be structured, not free-form natural language.

Suggested module:

- `src/write_path/`

Suggested functions:

- `prepare_write(request)`
- `backup_stores(context_id)`
- `apply_write(request)`
- `append_journal_event(event)`
- `rebuild_resolved_view(context_id)`

## 12. Relation to Pre-Thinker

The pre-thinker, if used, is stateless and advisory:

- suggests candidate structure
- flags ambiguity
- proposes routing

Deterministic validation and write policy remain final authority.

## 13. Incremental Rollout

1. strengthen statement classification and suitability checks
2. emit candidate records with ranked predicates
3. implement tentative store and journal
4. implement `retract` and `supersede`
5. add contradiction audit integration
6. add promotion rules for tentative facts

## 14. Out of Scope (First Increment)

- full truth-maintenance system
- free-form NL writes straight into hard facts
- automatic ontology creation
- probabilistic belief merging

## 15. Summary

The system already reasons deterministically. This spec defines how information earns the right to be reasoned over.
