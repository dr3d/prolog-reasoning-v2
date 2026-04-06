# Write Path Spec

Status: Draft  
Owner: Core symbolic layer  
Date: 2026-04-05

## 1. Goal

Define the first safe mutation path for Prolog Reasoning v2.

This spec exists to answer four questions before LLMs are allowed to mutate durable state:
- what operations are allowed,
- what gets backed up and when,
- how history is recorded,
- and how writes stay scoped instead of collapsing into one flat KB.

## 2. Design Principles

1. Determinism first  
Writes should produce explicit, inspectable state transitions.

2. Backup before mutation  
Recovery must not depend on the agent having behaved well.

3. Journal before cleverness  
Record what happened before optimizing for convenience.

4. Scoped writes, not flat blending  
Every mutation must declare where it belongs.

5. No fake persistence  
The system should never claim something was stored unless the write path actually succeeded.

## 3. First-Class Operations

The initial write path should support exactly these operations:

- `assert`
- `tentative`
- `confirm`
- `retract`
- `supersede`

These map directly to the memory-ingestion and revision model.

### 3.1 assert

Use when:
- the statement is explicit,
- durable,
- sufficiently grounded,
- and ready to participate in deterministic reasoning.

Effect:
- write fact into the resolved hard-fact view,
- record an `assert` journal event.

### 3.2 tentative

Use when:
- the statement may matter later,
- but should not yet be promoted to hard fact.

Effect:
- write into tentative store only,
- do not add to the deterministic hard-fact view,
- record a `tentative` journal event.

### 3.3 confirm

Use when:
- a tentative fact has been explicitly confirmed,
- or promotion policy decides it is ready.

Effect:
- promote tentative fact into hard-fact view,
- keep journal continuity,
- record a `confirm` journal event linked to the earlier tentative record.

### 3.4 retract

Use when:
- the user explicitly undoes a fact,
- or a fact must be removed from active truth without replacement.

Effect:
- remove fact from resolved hard-fact view,
- keep journal history,
- record a `retract` event referencing the earlier fact.

### 3.5 supersede

Use when:
- one fact is replacing another,
- especially for single-valued relationships like manager, role, or current location.

Effect:
- mark old fact as superseded,
- activate new fact,
- record a `supersede` event linking old and new facts.

## 4. Required Mutation Envelope

Every write request must carry:

- `memory_operation`
- `statement_type`
- `context_id`
- `source`
- `session_id`
- `confidence`
- `fact_payload`

Suggested structured request:

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

The write path should reject requests that omit `context_id`.

## 5. Storage Layers

The write path should maintain three distinct artifacts:

1. hard-fact view  
Active deterministic facts available to the symbolic engine.

2. tentative store  
Candidate memory not yet promoted to truth.

3. event journal  
Append-only history of memory operations.

The hard-fact view is the query surface.
The event journal is the audit surface.
The tentative store is the staging surface.

## 6. Backup Policy

Backups should attach to mutation, not to manifest generation or any unrelated maintenance step.

### 6.1 When To Backup

Before every successful mutation attempt that could change durable state:
- `assert`
- `confirm`
- `retract`
- `supersede`

Tentative-only writes may use lighter protection, but it is acceptable to back them up too if implementation simplicity wins.

### 6.2 What To Backup

At minimum:
- current hard-fact view file(s)
- current tentative store file(s), if separate
- current journal file, if mutation rewrites or rotates it

### 6.3 Backup Modes

Use two layers:

1. rolling pre-write snapshot  
- taken immediately before mutation
- keeps the last N write snapshots

2. daily snapshot  
- taken once per day per store
- protects against silent drift over longer sessions

### 6.4 Recovery Goal

Recovery should be boring:
- choose snapshot,
- restore file set,
- rebuild resolved view if needed.

## 7. Journal Semantics

Every journal event should include:

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

Example:

```json
{
  "event_id": "evt_00124",
  "event_type": "supersede",
  "fact_id": "fact_00491",
  "related_fact_id": "fact_00377",
  "context_id": "work-org",
  "session_id": "sess_123",
  "source": "user",
  "timestamp": "2026-04-05T21:30:00Z",
  "confidence": 0.93,
  "payload": {
    "old_fact": "manager(scott, dana).",
    "new_fact": "manager(scott, alice)."
  },
  "result": "applied"
}
```

If a mutation fails validation, the journal should still be allowed to record a rejected attempt, but the hard-fact view must remain unchanged.

## 8. Context And Isolation Rules

This project should not return to a naive flat global/local merge by default.

Every mutation must target an explicit `context_id`.

Minimum rule set:
- `global` is allowed as a context
- project or domain contexts are allowed
- facts without a context must be rejected or routed to `unstructured`

### 8.1 Read Policy

Write scoping and read scoping should align.

If a fact is written under `context_id = healthcare`, retrieval should not silently behave as though it were global unless fallback policy says so.

### 8.2 Same Predicate Across Contexts

The same predicate may exist across multiple contexts.

That is acceptable if:
- context metadata keeps them distinct,
- retrieval policy reports fallback behavior,
- and mutation APIs never imply that all contexts are one shared namespace.

## 9. Validation Gates

Before applying a hard-fact mutation:

1. parse and normalize payload
2. validate statement type vs operation
3. validate entity grounding
4. validate predicate compatibility
5. validate context compatibility
6. run contradiction check if operation is `assert` or `supersede`
7. take backup
8. apply mutation
9. append journal event

If any validation gate fails:
- do not mutate the hard-fact view,
- return a structured failure,
- optionally log a rejected journal event.

## 10. Contradiction Policy

The first write path should not implement full belief revision.

Instead:
- detect obvious contradictions,
- prefer `supersede` for single-valued updates,
- prefer `tentative` when certainty is weak,
- and keep the old fact until an explicit mutation path resolves it.

Example:
- old: `manager(scott, dana).`
- new: `manager(scott, alice).`

Preferred result:
- do not silently append both,
- route through `supersede`,
- keep history visible in the journal.

## 11. Initial API Boundary

The first mutation boundary should be structured, not natural language.

Good first step:
- internal Python API or tool surface accepting structured write requests

Bad first step:
- direct free-form natural-language writes from an LLM with no typed mutation envelope

Suggested module boundary:
- `src/write_path/` or similar

Suggested first functions:
- `prepare_write(request)`
- `backup_stores(context_id)`
- `apply_write(request)`
- `append_journal_event(event)`
- `rebuild_resolved_view(context_id)`

## 12. Out Of Scope For First Increment

- full truth-maintenance system
- automatic ontology creation
- free-form NL ingestion directly to hard facts
- cross-context contradiction resolution
- probabilistic belief merging

## 13. Recommended Implementation Sequence

1. Define journal schema and file layout
2. Add pre-write backup utility
3. Implement structured `assert` and `tentative`
4. Implement `retract` and `supersede`
5. Add correction-cue routing onto those operations
6. Add context-aware rebuild/query surfaces

## 14. Success Criteria

This spec is succeeding when:
- an LLM cannot mutate durable facts without leaving a journal trail,
- destructive mistakes are recoverable from automatic backup,
- every write has a declared context,
- and the system can honestly say whether something was asserted, tentatively preserved, rejected, or superseded.
