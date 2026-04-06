---
layout: post
title: "Knowledge Bases 101: Facts, Rules, and Queryable Truth"
description: "How to model facts and rules so an agent can reason instead of guess."
level: "Beginner"
domain: "Knowledge Representation"
duration: "25 minutes"
---

# Knowledge Bases 101

This module explains how to structure information so the symbolic layer can do
real work.

## Learning Objectives

By the end of this lesson, you should be able to:

- distinguish base facts from derived facts
- write simple Prolog-style predicates and rules
- avoid common modeling mistakes that cause confusing query behavior
- understand why schema discipline matters for LLM-driven systems

## Facts vs Rules

Facts are explicit assertions:

```prolog
parent(alice, bob).
parent(bob, charlie).
```

Rules define what can be inferred:

```prolog
ancestor(X, Y) :- parent(X, Y).
ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).
```

With this split:

- facts capture observed truth
- rules capture repeatable logic

## Why This Beats Free-Form Notes

Free text can express ideas, but it is hard to validate and reason over.

Structured predicates give you:

- stable query targets
- deterministic derivations
- easier contradiction checks
- clear failure modes when information is missing

## Modeling Discipline

A few habits improve reliability quickly:

1. Keep predicate names consistent (`parent`, not `is_parent_of` and `dad_of` in parallel).
2. Keep argument order consistent (`parent(parent, child)` everywhere).
3. Prefer small, composable predicates over giant overloaded ones.
4. Add rules only when they represent stable domain logic.

## Simple Query Patterns

Given the family facts/rules above:

```prolog
parent(alice, bob).
ancestor(alice, charlie).
ancestor(X, charlie).
```

The first two are yes/no checks.
The third asks for bindings (`X` values that satisfy the query).

In MCP chat mode, use:

- `query_logic` for raw logic queries
- `query_rows` when you want explicit variable bindings as rows

## Common Pitfalls

### Pitfall 1: treating uncertain statements as hard facts

If a user says "maybe alice reports to dana," do not persist as hard fact by default.

Route it as tentative first.

### Pitfall 2: predicate explosion from synonyms

If the same relationship appears as many near-duplicates, reasoning quality drops.

Prefer controlled mapping to a canonical predicate set.

### Pitfall 3: mixing session assumptions with durable truth

"For this session, assume alice is admin" is not the same as a durable world fact.

## Practice Exercise

Create a tiny domain and answer three questions:

1. Add 4-6 facts.
2. Add one rule that derives non-trivial results.
3. Query both base and derived predicates.

You can use family, project dependencies, access control, or game state.

## Key Takeaways

1. Facts are asserted; rules are inferred structure.
2. Good predicate design is a force multiplier for agent reliability.
3. Deterministic reasoning quality depends on disciplined knowledge modeling.
4. Structured logic complements LLM interaction, it does not replace it.

## Next Lesson

- `03-learning-from-failures.md`
