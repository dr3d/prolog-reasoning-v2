# Roadmap: Prolog Reasoning v2

**Last Updated**: April 7, 2026  
**Vision**: Develop Prolog Reasoning v2 as a lightweight deterministic logic layer for agents, then extend it into a curated symbolic memory pipeline.

---

## Strategic Shape

The project is best understood in three layers:

1. **Deterministic Logic Layer**
   Exact rule application, constraints, derived consequences, and explanations.

2. **Fact Intake / Memory Curation Layer**
   Classify utterances, identify predicates, canonicalize candidate facts, and
   decide what deserves durable storage.

3. **Agent Integration Layer**
   MCP, local LLM workflows, and agent skill packaging.

This roadmap favors the second layer next. Ontology work remains optional and
secondary.

---

## Tier 1: Fact Intake and Memory Curation

### 1.1 Fact Intake Pipeline
**Why**: The hardest problem is no longer query execution. It is deciding what
deserves symbolic treatment in the first place.

**Scope**:
- expand statement classification beyond routing hints
- add symbolic suitability filtering
- add predicate mapping and candidate ranking
- add argument extraction and normalization
- produce inspectable candidate fact records

**Tasks**:
- [x] Add `docs/fact-intake-pipeline.md`
- [ ] Extend `classify_statement` output toward a richer candidate schema
- [ ] Add predicate-candidate mapping layer
- [ ] Add argument normalization / entity shaping rules
- [ ] Add tests for utterance type vs symbolic suitability

**Release**: v2.1

---

### 1.2 Memory Classes and Revision Journal
**Why**: Not every statement should become a hard fact. The system needs typed
memory plus reversible operations.

**Scope**:
- hard fact
- tentative fact
- session context
- preference / instruction
- correction and revision operations

**Tasks**:
- [ ] Add journal schema for `assert`, `tentative`, `confirm`, `retract`, `supersede`
- [ ] Implement tentative memory store
- [ ] Add correction cue routing
- [ ] Define promotion and rejection rules
- [ ] Integrate with the unified intake/write contract in `docs/fact-intake-pipeline.md`

**Release**: v2.2

---

### 1.3 Contradiction and Overwrite Handling
**Why**: A memory system without contradiction handling just becomes a better
organized mess.

**Scope**:
- detect competing facts
- distinguish contradiction from correction
- preserve history
- surface conflicts cleanly to agents

**Tasks**:
- [ ] Add contradiction auditor
- [ ] Add structured conflict reports
- [ ] Connect auditor to `supersede` / `retract`
- [ ] Add tests for conflict vs revision behavior

**Release**: v2.3

---

## Tier 2: Agent-Callable Logic Utility

### 2.1 Logic Coprocessor Positioning
**Why**: The easiest way to understand the library is as a deterministic tool
agents call when precision matters.

**Scope**:
- document best use cases
- clarify bad use cases
- provide invocation patterns

**Tasks**:
- [x] Add `docs/uses-and-scenarios.md`
- [ ] Add examples for:
  - constraints
  - rule-derived spreadsheets/tables
  - policy and permission checks
  - consistency checks
  - relationship propagation

**Release**: v2.4

---

### 2.2 Output and Support Checking
**Why**: Symbolic support is useful not only on input, but also when checking
what a model is about to say.

**Scope**:
- grounded vs inferred vs unsupported output tags
- optional answer-time support checks
- abstention / hedge policy when support is weak

**Tasks**:
- [ ] Design support-check record format
- [ ] Add a first lightweight output-checking prototype
- [ ] Benchmark unsupported-claim detection on local models

**Release**: v2.5

---

## Tier 3: Smarter Control Plane

### 3.1 Stateless Pre-Thinker
**Why**: Rules alone will eventually hit limits on paraphrase, ambiguity, and
predicate mapping. A small model may help as a control-plane analyst.

**Scope**:
- stateless only
- proposes, does not commit
- no independent memory
- structured outputs only

**Tasks**:
- [ ] Benchmark rule-based classifier vs small-model classifier
- [ ] Define control-plane JSON schema
- [ ] Use small model only for:
  - utterance typing
  - symbolic suitability
  - predicate family suggestion
  - ambiguity flags
- [ ] Keep deterministic downstream policy as final authority

**Release**: v2.6+

---

### 3.2 Sidecar Memory Curation
**Why**: A low-friction alternative to ingress governance is to let the main
LLM converse normally and curate memory beside it.

**Scope**:
- post-process turns or summaries
- extract candidate durable facts
- reject transcript sludge
- preserve corrections and provenance

**Tasks**:
- [ ] Compare ingress vs sidecar curation architectures
- [ ] Define memory-curation sidecar protocol
- [ ] Evaluate which turns deserve symbolic promotion

**Release**: exploratory

---

## Tier 4: Secondary / Optional Research

These remain interesting, but they are not the project spine.

### 4.1 Ontology Context Routing
- useful for scoped retrieval later
- not required for the core research claim
- should follow, not precede, strong fact intake

### 4.2 Temporal Logic
- still valuable
- especially once revision and memory classes harden

### 4.3 Constraint and Visual Applications
- graphics editor
- visualizers
- interactive demos

These are application surfaces for the deterministic layer, not the foundation.

---

## Guiding Principle

The project should keep making one distinction sharper:

- language models interpret
- symbolic systems validate, store, and reason

The next phase is about building the missing middle:
the fact intake and memory curation pipeline that decides what the symbolic
layer should trust.
