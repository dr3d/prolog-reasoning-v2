---
layout: post
title: "LLM Memory and Symbolic Reasoning"
description: "Why LLMs drift on facts, and how a deterministic logic layer helps."
level: "Beginner"
domain: "LLM Fundamentals"
duration: "20 minutes"
---

# LLM Memory and Symbolic Reasoning

This module is the front door to the project.

## Learning Objectives

By the end of this lesson, you should be able to explain:

- why LLMs feel smart but still drift on factual state
- why "memory" and "truth" are different problems
- how a symbolic layer helps with stable facts and derived answers
- where this repo fits in a practical local workflow

## The Core Problem

An LLM is excellent at language generation and pattern completion.
It is not a durable fact store.

LLMs can look consistent in short windows, then drift as conversations grow.
That drift often looks like confidence, which is why it is risky.

### Why long-run factual recall breaks down

A pure chat loop fails for durable fact work because:

- context windows are finite, so older details can fall out
- summaries compress detail and can mutate meaning
- retrieval can be approximate and miss key constraints
- model priors can override session-specific facts

In short:

- memories are timestamped artifacts
- facts should be explicit and queryable

## The Split That Helps

The project uses a responsibility split:

- language model: interpret intent and communicate
- symbolic layer: store/query explicit facts and apply deterministic rules

That gives a cleaner contract:

- model fluency for interaction
- logic determinism for truth conditions

## Minimal Example

If your KB includes:

```prolog
parent(alice, bob).
parent(bob, charlie).
ancestor(X, Y) :- parent(X, Y).
ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).
```

Then `ancestor(alice, charlie)` is derived by rule, not guessed.

The answer quality is no longer "what the model felt likely."
It is "what follows from explicit facts and rules."

## How This Repo Exposes It

In chat-integrated mode (MCP), useful tools include:

- `query_prolog` for natural-language question routing
- `query_logic` for literal Prolog query strings
- `query_rows` for table-shaped deterministic outputs
- `list_known_facts` for visibility into entities and predicates
- `classify_statement` for routing hints on non-question utterances

The key is that the logic layer is local and deterministic.
The model can orchestrate, but not silently rewrite truth.

## Try It Quickly

1. Run tests to verify baseline behavior:

```bash
python -m pytest tests -q
```

2. Run a starter demo:

```bash
python scripts/demonstrate_agent.py
```

3. If you are using LM Studio, follow:

- `docs/lm-studio-mcp-guide.md`
- `docs/mcp-chat-playbooks.md`

## Common Misunderstanding

"If the model is better, do I still need symbolic logic?"

Often yes, when you need:

- stable facts across long sessions
- explicit rule application
- explainable failures
- deterministic yes/no behavior for constraints

## Key Takeaways

1. LLM memory and factual truth are different system concerns.
2. A deterministic symbolic layer reduces factual drift.
3. The best pattern is usually hybrid: language + logic.
4. This repo is a practical implementation of that split, local-first.

## Discussion Prompts

1. Which of your current AI tasks need deterministic truth, not plausible prose?
2. Where do you see summary drift in long chats today?
3. Which domain facts in your work should be elevated into explicit predicates?
