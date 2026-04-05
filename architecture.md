# Prolog Reasoning v2 — Architecture

## 🏗️ System Design

```
┌─────────────────────────────────────────────────────────────┐
│ Natural Language (LLM Input)                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Semantic Parser (LLM) → Structured IR (JSON)               │
│ Handles:                                                    │
│  - NL ambiguity resolution                                 │
│  - Schema validation                                       │
│  - Type checking                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ IR Compiler (Python)                                        │
│ Converts: JSON → Prolog facts/queries                      │
│ Enforces: schema consistency, deduplication               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Prolog Engine (Pure Python)                                 │
│ - Unification                                               │
│ - Backward chaining                                         │
│ - Backtracking                                              │
│ - Built-in predicates (is, findall, etc)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Verifier & Explanation Layer                               │
│ - Check consistency                                         │
│ - Generate proof traces                                    │
│ - Score answer confidence                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Output (JSON)                                               │
│ {                                                           │
│   "answer": true/false/[bindings],                         │
│   "proof": [...proof chain...],                            │
│   "confidence": 0.0-1.0,                                   │
│   "trace": {...execution path...}                          │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Component Breakdown

### 1. **Prolog Engine** (`src/engine/`)
Pure Python Prolog interpreter with:
- Term representation (atoms, compounds, lists)
- Unification algorithm
- Backward-chaining inference
- Backtracking
- Depth limits (prevent infinite loops)
- Built-in predicates

### 2. **Knowledge Base** (`prolog/`)
Organized fact and rule files:
```
prolog/
  core.pl          - Base predicates
  family.pl        - Family/relationship rules
  access.pl        - Permission/role rules
  constraints.pl   - Constraint rules
  ```

### 3. **Semantic Parser** (`src/parser/`)
Converts NL → Structured IR
```python
# Input: "John is Mary's parent"
# Output:
{
  "predicate": "parent",
  "args": ["john", "mary"],
  "type": "fact"
}
```

### 4. **IR Compiler** (`src/compiler/`)
Converts IR → Prolog facts/queries
```python
# Input: IR JSON
# Output: Prolog query/assertion
```

### 5. **Verifier** (`src/verifier/`)
- Logical consistency checks
- Proof trace generation
- Confidence scoring

### 6. **Explanation Layer** (`src/explain/`)
Generates human-readable justifications
```
Query: "Is John Mary's ancestor?"
Proof:
  1. parent(john, alice) [stored fact]
  2. ancestor(X, Y) :- parent(X, Y) [rule]
  3. ancestor(john, alice) [derived]
  ...
  ancestor(john, mary) [ANSWER]
```

## 🧪 Testing & Evaluation (`tests/`, `data/`)

- **Unit tests**: Logic consistency, unification, backtracking
- **Integration tests**: Full pipeline (NL → Prolog → answer)
- **Benchmark dataset**: Family trees, access control, constraints
- **Baseline comparisons**: LLM-only vs Prolog vs hybrid

## 🎯 Key Invariants

1. **Losslessness**: Facts never degrade under recitation
2. **Determinism**: Same query always returns same bindings
3. **Explainability**: Every answer has a proof chain
4. **Schema safety**: IR enforces predicate signatures
5. **Composability**: Rules can be composed (ancestor from parent)

## 📊 Evaluation Plan

Compare across:
- **Correctness**: % of queries answered correctly
- **Consistency**: % of contradictions caught
- **Explanation quality**: Human evaluation of proof traces
- **Grounding accuracy**: % of NL → IR conversions valid
- **Performance**: Query latency, KB size scaling

Baselines:
- Pure LLM (0-shot, few-shot)
- Vector retrieval (embedding similarity)
- Hybrid (Prolog + LLM confidence scores)
