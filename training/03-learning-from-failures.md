---
layout: post
title: "Learning from Failures: Debugging Symbolic Queries"
description: "How to read validation and query failures and recover quickly."
level: "Beginner"
domain: "Diagnostics and Error Handling"
duration: "20 minutes"
---

# Learning from Failures

Reliable systems do not hide errors. They expose them in ways you can act on.

## Learning Objectives

By the end of this lesson, you should be able to:

- recognize major failure classes in this project
- separate parsing/validation failures from true no-result outcomes
- recover quickly with the right next query
- treat errors as model and KB feedback, not dead ends

## Failure Classes You Will See

## 1. Undefined Entity

Meaning:

- the query references an entity not grounded in the KB

Example:

- "Who is charlie's parent?" when `charlie` is unknown

Typical recovery:

1. run `list_known_facts`
2. correct spelling or entity name
3. add missing fact only if appropriate

## 2. Unknown Predicate

Meaning:

- query uses a relationship name outside supported vocabulary

Example:

- `can_fly(alice)` when that predicate is not modeled

Typical recovery:

1. inspect supported predicates
2. remap question to existing predicate family
3. extend schema and rules only when truly needed

## 3. No Results

Meaning:

- query shape is valid, but no matching fact/rule path succeeds

Example:

- asking for an allergy that is not present in current facts

Typical recovery:

1. ask narrower diagnostic queries
2. verify prerequisite facts exist
3. avoid inventing missing facts in prose

## 4. Ambiguous Input

Meaning:

- natural-language input could map to multiple logical intents

Typical recovery:

1. rephrase with explicit entity + relationship
2. split multi-intent input into separate turns
3. use `classify_statement` when in doubt

## Why This Matters

A common LLM failure is to "helpfully" answer anyway.

This stack is designed to do the opposite:

- fail explicitly
- explain why
- suggest next actions

That behavior is a feature for safety and trust.

## Practical Debug Loop

Use this quick loop in chat or scripts:

1. `show_system_info`
2. `list_known_facts`
3. run a narrow `query_logic` or `query_rows`
4. if failure, call `explain_error`
5. patch the query or facts, then retry

## Example Workflow

User asks:

- "What is Bob allergic to?"

Possible outcomes:

- table/answer exists -> return it
- no result -> explicitly say no supporting fact currently exists

Do not replace "no result" with a guessed allergen.

## Key Takeaways

1. Errors are visibility, not embarrassment.
2. Validation failures and no-result outcomes are different and should be handled differently.
3. Deterministic failure handling is part of anti-hallucination behavior.
4. Good debugging starts with schema and entity visibility, not model confidence.

## Next Lesson

- `04-lm-studio-mcp.md`
