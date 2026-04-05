# Memory Ingestion and Revision Notes

Status: Draft
Date: 2026-04-05
Owner: Core symbolic layer

## 1. Why This Exists

Getting information into a knowledge base is harder than it first appears.

The hard part is not only extracting candidate facts. The hard part is deciding:
- whether something is durable enough to store,
- how certain the system is,
- which memory layer should hold it,
- and what should happen later if the system or user backtracks.

This note captures the current working model so the project can integrate it later without relying on chat memory.

## 2. Core Principle

When in doubt, capture it.
When in doubt about truth, do not promote it.

That means the system should be conservative about what becomes a hard fact, but liberal about preserving potentially useful information in a lower-confidence form.

## 3. Memory Classes

### 3.1 Hard Fact Memory

Use for statements that are:
- explicit,
- stable,
- durable,
- and validated enough to support deterministic reasoning.

Examples:
- "My dog's name is Max."
- "John is allergic to penicillin."
- "The repo uses Python 3.12."

These can participate directly in symbolic reasoning.

### 3.2 Tentative Memory

Use for statements that look important but are not ready to be treated as truth.

Examples:
- "I think Alice reports to Dana."
- "It sounds like the outage started around 2."
- "Maybe this customer is in healthcare."

Tentative memory should preserve information without silently promoting it into hard fact memory.

### 3.3 Session Context Memory

Use for temporary working state.

Examples:
- "Right now I'm debugging the parser."
- "For this example, pretend Alice is the admin."
- "Today I want to focus on roadmap cleanup."

This is not durable fact memory.

### 3.4 Preference / Instruction Memory

Use for user preferences or working constraints.

Examples:
- "Keep responses concise."
- "Do not commit until I review."
- "Use kebab-case filenames."

These affect behavior, not world-state reasoning.

## 4. Statement Classification

The LLM should not be forced into a binary choice between "store as fact" and "ignore".

Instead, each candidate statement should be classified as one of:
- hard fact,
- tentative fact,
- session context,
- preference/instruction,
- hypothesis/planning language.

This keeps ingestion realistic and reduces pressure on one-shot truth judgments.

## 5. Ingestion Pipeline

### Step 1: Candidate Extraction

Detect statements that may matter later.

### Step 2: Statement Typing

Assign one of the memory classes above.

### Step 3: Validation

If the statement is a hard-fact candidate:
- check entity grounding,
- check predicate compatibility,
- check contradictions,
- check active ontology context.

### Step 4: Routing

Store by class:
- hard fact -> symbolic KB
- tentative fact -> tentative memory / audit queue
- session context -> session state
- preference/instruction -> preference memory
- hypothesis -> do not store as fact

### Step 5: Promotion or Rejection

Tentative facts may later be:
- promoted,
- confirmed,
- rejected,
- or superseded.

## 6. Misunderstandings, Corrections, and Backtracking

Three cases need to be treated separately.

### 6.1 Contradiction

A new statement conflicts with an existing stored fact.

Example:
- old: "Alice is my manager."
- new: "Dana is my manager."

This should trigger contradiction handling or a supersession event.

### 6.2 Misunderstanding

The system stored the wrong thing because parsing or inference was wrong.

Example:
- user meant: "Alice reports to Dana."
- stored: "Dana reports to Alice."

This should not silently overwrite history. It should create a correction path.

### 6.3 User Correction / Undo

The user explicitly revises or retracts something.

Examples:
- "Actually, ignore that."
- "No, I meant Bob."
- "Strike the allergy note."

This is a first-class memory operation, not just more text.

## 7. Lightweight Revision Model

Avoid implementing a full truth-maintenance system at first.

Instead, use a lightweight reversible memory journal with events such as:
- `assert`
- `tentative`
- `confirm`
- `retract`
- `supersede`

Under this model:
- the journal records what happened,
- the current KB is a resolved view,
- and history remains inspectable.

This provides operational backtracking without making the whole project depend on heavyweight belief revision.

## 8. Minimal Event Semantics

Each memory event should include:
- event_id
- fact_id
- event_type
- session_id
- context_id
- timestamp
- source
- confidence
- related_fact_id (optional, for supersede/retract)

## 9. Promotion Rules for Tentative Facts

Tentative facts may be promoted when one or more of the following occur:
- explicit user confirmation,
- repeated assertion over time,
- support from validated external structure,
- compatibility with ontology and existing grounded entities,
- no unresolved contradiction with stronger facts.

## 10. Suggested LLM Policy

The LLM should ask these questions for each candidate statement:
- Is this durable?
- Is this certain enough?
- Which memory layer should hold it?
- If uncertain, should I preserve it tentatively instead of promoting it?

This avoids the failure mode of treating all factual-sounding text as settled truth.

## 11. Integration Targets

Potential future integration points:
- `src/parser/semantic.py` for candidate extraction and typing
- `src/agent_skill.py` for routing to memory classes
- `kb_manifest.json` or successor store for event history and metadata
- contradiction auditor for `supersede` and `retract` workflows
- ontology context routing for scoped promotion rules

## 12. Open Questions

1. Should tentative facts be queryable by default, or only surfaced when asked?
2. How much confidence is needed for automatic promotion?
3. Should user correction cues immediately retract old facts, or mark them as disputed first?
4. How should inferred facts behave when the supporting facts are later superseded?
5. How much of this should be explicit to the user versus internal policy?

## 13. Recommended Next Increment

Do not implement full backtracking first.

Implement this sequence instead:
1. tentative memory class
2. explicit `retract` and `supersede` events
3. correction cue detection (`actually`, `I meant`, `ignore that`, `update that`)
4. contradiction audit integration

That would deliver most of the practical value without overcommitting to a heavy revision system.