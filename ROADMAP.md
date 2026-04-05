# Roadmap: Prolog Reasoning v2 (2026 & Beyond)

**Last Updated**: April 5, 2026  
**Input**: External critique from Gemini AI + team analysis  
**Vision**: Develop prolog-reasoning as a research platform exploring how deterministic symbolic reasoning supports long-horizon LLM agent memory

---

## Strategic Priorities

### Tier 1: Core Foundations (Q2 2026)

#### 1.1 Temporal Logic Foundation
**Why**: Most "long-horizon" agent memory involves time. "Who was the manager in 2023?" is unanswerable without it.

**Scope**:
- Add `valid_from/2`, `valid_to/2`, `snapshot_at/2` built-in predicates
- Extend benchmark to include temporal queries (ancestor at a point in time)
- Document best practices for time-aware fact storage

**Tasks**:
- [ ] Add temporal built-ins to `src/engine/core.py`
- [ ] Add tests in `tests/test_engine.py`
- [ ] Example: `valid_from(parent(john, alice), 2020-01-01), valid_to(parent(john, alice), 2025-12-31).`
- [ ] Training course: `training/08-temporal-reasoning.md`

**Effort**: 1-2 days  
**Release**: v2.1

---

#### 1.2 Split Core & Optional Dependencies
**Why**: Users wanting just the engine shouldn't bloat their environment with LLM/NLP frameworks.

**Scope**:
- Separate `requirements.txt` into core basics
- Add optional extras: `[llm]`, `[nlp]`, `[dev]`
- Ensure core engine works without any LLM deps

**Tasks**:
- [ ] Refactor `requirements.txt` → `setup.py` with extras_require
- [ ] Verify core runs in minimal environment
- [ ] Update README with installation variants
- [ ] CI/CD test both minimal and full installs

**Effort**: < 1 day  
**Release**: v2.2

---

#### 1.3 Multi-Session Isolation
**Why**: Prevent "knowledge contamination" when serving multiple users/agents on the same instance.

**Scope**:
- Extend `kb_manifest.json` to support session namespaces
- Add session ID to all Prolog predicates as a "tag"
- Lazy-load facts by session; unload on session end

**Tasks**:
- [ ] Extend `src/ir/schema.py` with `session_id` field
- [ ] Update `src/engine/core.py` to accept session context
- [ ] Modify benchmark to include multi-session test
- [ ] Document session lifecycle patterns

**Effort**: 2-3 days  
**Release**: v2.3

---

### Tier 2: Extended Capabilities (Q3 2026)

#### 2.1 Soft-Fail Buffer Zone
**Why**: Real-world data is "fuzzy." Rigid IR validation causes loss of signal.

**Scope**:
- When IR validation fails, store fact as raw text + vector embedding
- Periodic "audit" task attempts to restructure buffered facts later
- Track success rate of deferred structuring (feedback loop)

**Tasks**:
- [ ] Add `UnstructuredFact` type to `src/ir/schema.py`
- [ ] Implement buffer storage in KB manifest
- [ ] Create `src/engine/audit.py` with deferred-fact resolver
- [ ] Add tests: `tests/test_soft_fail.py`
- [ ] Document "graceful degradation" pattern

**Effort**: 3-4 days  
**Release**: v2.4

---

#### 2.2 Fact Contradiction Auditor
**Why**: Detects KB inconsistencies (e.g., "john's father is pete" AND "john's father is paul") and surfaces them for agent resolution.

**Scope**:
- Scan KB for competing facts with same head, different bindings
- Flag contradictions with context (when/where they were asserted)
- Provide LLM-friendly structured output for resolution dialogue

**Tasks**:
- [ ] New module `src/engine/auditor.py`
- [ ] Detection logic: find all facts, group by predicate, detect conflicts
- [ ] Return structured report: `{conflict: ..., fact1: ..., fact2: ..., timestamp_delta: ...}`
- [ ] Add tests: `tests/test_auditor.py`
- [ ] Integration example in `scripts/audit_kb.py`

**Effort**: 2-3 days  
**Release**: v2.5

---

#### 2.3 Improved NL → IR Latency
**Why**: Gemini flagged semantic grounding latency as a blocker for real-time agents.

**Scope**:
- Option A: Cache common intents (fuzzy match recent queries)
- Option B: Add tiny local classifier (BERT-based) for "intent type" detection
- Option C: Hybrid: local classifier for binning, then LLM call only if needed

**Tasks**:
- [ ] Profile current latency: `scripts/profile_nl_parsing.py`
- [ ] Implement intent cache in `src/engine/semantic.py`
- [ ] Measure latency improvement
- [ ] If cache insufficient, evaluate Option B

**Effort**: 2-3 days (cache), 5-7 days (local classifier)  
**Release**: v2.6 (cache) or v2.7 (classifier)

---

### Tier 3: Advanced Features (Q4 2026 / 2027)

#### 3.1 Constraint Graph Visualizer
**Why**: Show users a live graph of what facts/rules exist and how they're related. Powerful for debugging and demo.

**Scope**:
- New web interface (React or similar) showing:
  - Fact nodes (colored by predicate)
  - Rule flow edges (implications)
  - Session filters
  - Temporal timeline
- Real-time updates as KB changes
- Export to GraphML/DOT for external tools

**Tasks**:
- [ ] Design schema for fact graph export: `src/engine/graph_export.py`
- [ ] Web UI frontend (separate repo or mvp/graph/)
- [ ] WebSocket stream updates
- [ ] Docs: tutorial + best practices

**Effort**: 1-2 weeks  
**Release**: v3.0

---

#### 3.2 Recursive Fact Refinement 
**Why**: Higher-level version of the auditor—system proactively learns when contradictions arise.

**Scope**:
- When auditor flags a contradiction, trigger a structured dialogue:
  1. LLM sees both facts + context
  2. LLM proposes resolution (which one is stale, or merge them)
  3. System validates proposed change & applies it
  4. Audit log records the refinement
- Accumulate "refinement patterns" to improve future conflict resolution

**Tasks**:
- [ ] Extend auditor with dialogue logic: `src/engine/auditor.py` + methods
- [ ] LLM prompt templates: `src/prompts/fact_refinement.txt`
- [ ] Audit trail storage: extension to `kb_manifest.json`
- [ ] Tests: `tests/test_recursive_refinement.py`
- [ ] Example: `scripts/demo_refinement.py`

**Effort**: 1 week  
**Release**: v3.1

---

#### 3.3 Typed Predicate Templates
**Why**: Dramatically reduce LLM hallucinations by enforcing schema at parse time.

**Scope**:
- Extend IR to support type annotations: `path(A: location, B: location, Cost: int)`
- Semantic parser validates arg types before adding to KB
- Type violations are caught and reported (not silently ignored)
- Show effectiveness on extended benchmark

**Tasks**:
- [ ] Extend `src/ir/schema.py` with `TypedPredicate`
- [ ] Update validator to check types: `src/validator/semantic_validator.py`
- [ ] Benchmark typed vs untyped (research shows 70% hallucination reduction)
- [ ] Documentation + training course

**Effort**: 3-4 days  
**Release**: v2.8

---

### 📚 Tier 4: Nice-to-Have (Future)

#### 4.1 DCG (Definite Clause Grammar) Support
- For parsing domain-specific languages (e.g., contract terms)
- Lower priority unless a customer asks

#### 4.2 Constraint Logic Programming (CLP)
- For scheduling, planning problems
- Leverage existing constraint propagation work

#### 4.3 Module System
- Namespace predicates, avoid collisions in large KBs
- Good for multi-tenant scenarios

#### 4.4 Forward-Chaining Rules
- Complement backward-chaining for reactive systems
- Useful for event-driven agents

---

## Development & Community

Practical actions to support adoption and community.

- [ ] **Update README**: Focus on technical accomplishments over aspirational claims
  - Emphasize **deterministic reasoning** and **integration patterns**

- [ ] **Publish Integration Guide**
  - Document realistic use cases and limitations
  - Include integration examples with MCP, LM Studio

- [ ] **MCP Server Stabilization**
  - Ensure `src/mcp_server.py` is robust
  - Add connection pooling / session management
  - Document Claude Desktop integration

- [ ] **Community Infrastructure** (if opening to contributions)

---

## High-Level Timeline

| Timeline | Major Deliverables | Version |
|---|---|---|
| **Now → May 2026** | Temporal logic, split deps, multi-session isolation | v2.1–2.3 |
| **May → Aug 2026** | Soft-fail buffer, auditor, typed templates | v2.4–2.8 |
| **Aug → Nov 2026** | NL latency improvements, ReadMe refresh | v2.6–2.7 |
| **Q4 2026** | Fact graph visualizer, recursive refinement | v3.0–3.1 |
| **2027+** | DCG, CLP, module system (if demand) | v4.0+ |

---

## Metrics to Track

- **Adoption**: GitHub stars, PyPI downloads, MCP Studio users
- **Quality**: Benchmark accuracy (extended to 100+ test cases)
- **Performance**: Query latency (ms per fact lookup), KB size limits
- **Community**: GitHub issues/discussions, example projects, citations

---

## Open Questions

1. **Hybrid reasoning**: Should we explore Prolog + neuro-symbolic scoring (e.g., confidence weights)?
2. **Temporal scale**: How fine-grained? Seconds? Days? Arbitrary precision?
3. **Auditor frequency**: Real-time checks vs. batch audits? Trade-offs?
4. **Graph UI**: Hosted vs. embedded? Public KB explorer vs. private?

---

## Notes

This roadmap is **input-based** (Gemini critique) and **team-validated**. Tiers 1 & 2 are the moat. Tier 3 is the showpiece. Tier 4 is optionality.

The **core strength** (deterministic reasoning with explicit proof traces) is the primary focus. Additional features should be evaluated against this foundation.
