# Development Status

**Last Updated**: April 6, 2026  
**Status**: Core logic layer is solid; fact intake and memory curation are the next serious build.

## Project Spine

The repository now has a clearer center of gravity:

1. **Deterministic logic layer**
   The Prolog engine, constraint propagation, and explanation paths provide
   exact rule application and inspectable reasoning.

2. **Fact intake / memory curation layer**
   This is the next active frontier: statement typing, predicate identification,
   symbolic suitability, tentative memory, correction handling, and revision.

3. **Agent integration layer**
   MCP, LM Studio, Hermes/OpenClaw skills, and demos make the symbolic layer
   callable from real agent workflows.

The graphics editor and ontology-routing ideas remain in the repo, but they are
not the current center of the project.

## Working Now

### Deterministic Logic Layer

- Pure Python Prolog engine in `src/engine/core.py`
  - unification
  - backward chaining
  - backtracking
  - built-ins
- Constraint propagation engine in `src/engine/constraint_propagation.py`
- Proof and explanation support in `src/explain/`
- IR schema and compiler in `src/ir/` and `src/compiler/`

### Intake and Validation

- Semantic grounding in `src/parser/semantic.py`
- Semantic validation in `src/validator/semantic_validator.py`
- Failure explanation layer in `src/explain/failure_translator.py`
- Deterministic statement classifier in `src/parser/statement_classifier.py`
  - `query`
  - `hard_fact`
  - `tentative_fact`
  - `correction`
  - `preference`
  - `session_context`

### Agent Integration

- MCP server in `src/mcp_server.py`
- LM Studio integration guide in `docs/lm-studio-mcp-guide.md`
- Hermes/OpenClaw install playbooks:
  - `HERMES-AGENT-INSTALL.md`
  - `OPENCLAW-AGENT-INSTALL.md`

## Test Status

Current suite:

- Core engine tests
- Semantic validation tests
- Failure explanation tests
- Constraint propagation tests
- MVP validation test
- MCP server tests

**Current total:** `84 passed`

The only recurring warning is the existing `.pytest_cache` permission warning on
Windows.

## What Is Still Simplified

- `src/agent_skill.py` still uses stub KB loading
- the default semantic grounding path still includes a mock LLM mode
- there is no real durable write path yet
- statement classification exists, but predicate mapping and canonical fact
  shaping are still early

That means the repo is already useful as:

- a logic coprocessor for agents
- a deterministic reasoning substrate
- a local MCP-backed symbolic tool

It is not yet complete as:

- a full memory ingestion and revision system
- a durable symbolic memory layer with clean fact injection

## Current Priorities

### 1. Fact Intake Pipeline

This is the main next step.

The system needs a better path from language to assertable symbolic structure:

- utterance classification
- symbolic suitability filtering
- predicate mapping
- entity normalization
- fact canonicalization
- assertion policy

### 2. Memory Curation and Revision

The project needs explicit handling for:

- tentative memory
- correction cues
- `assert` / `tentative` / `confirm` / `retract` / `supersede`
- contradiction surfacing
- provenance and revision journal semantics

### 3. Agent-Callable Logic Utility

The library should become easier to understand as a deterministic tool agents
call for:

- constraints
- rule-derived tables
- consistency checks
- state propagation
- permission and relationship logic

## Secondary / Optional Directions

These are still interesting, but they are not the project spine right now:

- ontology context routing
- pre-thinker control plane
- graphics editor / constraint UI
- richer visualizations

## Recommended Reading Order

If someone wants the current story in the right order:

1. `README.md`
2. `docs/fact-intake-pipeline.md`
3. `docs/research/lmstudio-classifier-matrix.md`
5. `roadmap.md`
6. `sessions.md`

## Summary

The repo is strongest today when understood as:

- a deterministic logic layer for agents
- plus the beginnings of a classifier-driven fact intake pipeline

The biggest research and engineering question is no longer whether symbolic
reasoning works. It is whether the system can reliably turn soft language into
clean, durable, symbolic structure without polluting the KB.
