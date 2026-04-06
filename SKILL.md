---
name: prolog-reasoning
description: Use this repository as a deterministic symbolic memory and reasoning skill for agent workflows. Trigger when an external agent such as OpenClaw or Hermes needs to query known facts, explain a symbolic failure, or classify a user statement for memory ingestion and revision.
---

# Prolog Reasoning Skill

## Critical Rule

If the user asks a factual question about anything the symbolic layer may know, query the symbolic layer before answering.

Wrong:

```text
User: "Who is John's parent?"
Agent: "Alice is John's parent."  # answered from model memory or stale context
```

Right:

```text
Agent: use query_prolog("Who is John's parent?")
Agent: answer from the returned result, or say it is not in the KB
```

Do not answer from ambient context when the symbolic layer is supposed to be the source of truth.

Use this skill when the task is about:
- querying deterministic facts instead of trusting model memory,
- deciding whether a user turn is a question, a fact to ingest, a correction, or a preference,
- routing candidate knowledge into the right memory class,
- explaining symbolic failures clearly,
- or integrating the repo as an external reasoning/memory tool for an agent stack.

Do not use this skill for:
- open-ended chat that does not need symbolic truth,
- writing new domain ontologies from scratch unless the user asks,
- or pretending the system already supports durable natural-language fact insertion when it does not.

## What This Repo Is

This project is a local-first neuro-symbolic reliability layer for LLM agents.

Treat it as two connected systems:
- language models interpret turns, classify intent, and explain results,
- the symbolic layer holds explicit facts, rules, and deterministic reasoning.

Core claim:
- memories are contextual and time-bound,
- facts are structured and durable,
- hallucinations happen when those two are confused.

## Current Capability Boundary

The current MCP server is good at:
- `query_prolog`
- `classify_statement`
- `list_known_facts`
- `explain_error`
- `show_system_info`

It is not yet a full write path.

Important current limitation:
- `src/agent_skill.py` contains `add_fact()`, but it is still a stub.
- The MCP layer does not expose a fact-writing tool.
- Natural-language statements like "my mother was ann" should not be treated as already-stored truth.

So:
- questions can be queried,
- candidate facts can be classified,
- but durable storage still needs engineering.

## Quick Decision Tree

1. Is the user asking a factual question?
   - If yes, use `query` mode.
   - If no, continue.
2. Is the user stating something that may matter later?
   - If yes, use `ingest` mode.
   - If no, continue.
3. Is the user correcting or undoing earlier information?
   - If yes, use `revise` mode.
   - If no, continue.
4. Is the user setting working style or behavior?
   - If yes, use `preference` mode.

If the answer could belong in the symbolic layer, do not default to model memory.

## Agent Policy

When a user turn arrives, decide among four modes:

1. `query`
Use when the user is asking about known entities, relationships, permissions, or derived facts.

2. `ingest`
Use when the user is stating something that may belong in memory later.

3. `revise`
Use when the user is correcting, retracting, or superseding earlier information.

4. `preference`
Use when the user is giving instructions about how the assistant should behave.

If a turn mixes these, separate them explicitly before acting.

## Query Workflow

For factual questions:
1. Prefer the symbolic layer over model memory.
2. Use `list_known_facts` if entity or predicate coverage is unclear.
3. Use `query_prolog` for the actual question.
4. If the query fails, distinguish:
   - validation error,
   - no-result,
   - unknown entity,
   - unknown predicate,
   - ambiguous phrasing.
5. Use `explain_error` when the user would benefit from a clearer explanation.

Behavioral commitment:
- If the fact should come from the KB, query it before answering.
- Do not improvise missing facts from model priors.

If your integration has both:
- a compact manifest or summary in context,
- and live MCP access,

use the manifest to orient yourself and the live tools to verify truth.
The summary helps you decide to query; it is not the final source of truth.

## Ingestion Workflow

For statements that look like candidate memory:
1. Extract the candidate statement.
2. Classify it into one of:
   - `hard_fact`
   - `tentative`
   - `session`
   - `preference`
   - `hypothesis`
3. Check whether the statement is explicit, durable, and grounded enough to promote.
4. If grounding is weak, preserve it as tentative rather than hard fact.
5. If the write path is not available, report the intended memory action instead of claiming it was stored.

Use the repo's memory model:
- hard fact: durable world-state truth
- tentative: important but not trusted enough yet
- session: temporary working context
- preference: user instruction or style constraint
- hypothesis: planning or speculation, not memory

## Revision Workflow

Corrections are first-class operations.

Watch for cues like:
- "actually"
- "I meant"
- "ignore that"
- "update that"
- "no, ..."

Map them to one of:
- `confirm`
- `retract`
- `supersede`
- `tentative`
- `none`

Do not silently overwrite history in your explanation.
If the system cannot persist revision events yet, describe the intended revision action explicitly.

## Pronouns And Identity

Be careful with first-person statements like:
- "my mother was ann"
- "my manager is dana"

These require a resolved speaker identity before they can become symbolic facts.

Default policy:
- do not convert `my` into a named entity unless the identity is already established,
- do not query the KB as if the statement were a question,
- explain that the statement is a candidate fact needing speaker grounding and, if applicable, a write path.

Wrong:

```text
User: "My mother was Ann."
Agent: "Your mother was Ann."  # treated as an answered query
```

Better:

```json
{
  "mode": "ingest",
  "statement_type": "hard_fact",
  "memory_operation": "assert",
  "needs_speaker_resolution": true,
  "can_persist_now": false
}
```

## What To Say When Storage Is Not Live

Use wording like:
- "This sounds like a fact to store, not a question to query."
- "I can classify it as a candidate hard fact or tentative fact, but the current MCP skill does not yet persist new facts."
- "The statement also needs speaker grounding before it can become a symbolic fact."

Avoid wording like:
- "I stored that."
- "I can save it for future queries."

unless a real write path has been implemented and verified.

## Where To Read More

Read these only when needed:
- `docs/memory-ingestion-and-revision-notes.md`
  Use for memory classes, tentative promotion, retract/supersede semantics, and event-journal thinking.
- `docs/pre-thinker-control-plane.md`
  Use for statement typing, routing, correction cues, and escalation policy.
- `docs/agent-integration.md`
  Use for the external-memory pattern and manifest/query behavior.
- `docs/agent-ingestion-tests.md`
  Use to evaluate whether an external agent is really separating query, ingestion, correction, and preference handling.
- `docs/lm-studio-mcp-guide.md`
  Use when configuring LM Studio or another MCP client.

## Suggested Output Contract For External Agents

When using this repo as a control plane, prefer returning structured decisions like:

```json
{
  "mode": "ingest",
  "statement_type": "hard_fact",
  "memory_operation": "assert",
  "needs_speaker_resolution": true,
  "can_persist_now": false,
  "reason": "First-person statement with unresolved identity; current MCP layer is query-only."
}
```

For queries, prefer:

```json
{
  "mode": "query",
  "source_of_truth": "symbolic_kb",
  "action": "query_prolog",
  "fallback": "explain_error"
}
```

## Bottom Line

Use the symbolic layer for truth.
Use the language layer for interpretation and routing.
Use tentative memory when truth is not ready.
Do not fake persistence that the system has not actually implemented.
