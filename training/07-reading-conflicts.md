---
layout: post
title: "Reading Conflicts Without Fear"
description: "A short lesson on why contradictions are useful feedback in neuro-symbolic systems."
level: "Beginner"
domain: "Diagnostics"
duration: "7 minutes"
---

# Reading Conflicts Without Fear

**Course Description**  
*Learn to treat a contradiction as a teaching moment instead of a dead end.*

---

## Learning Objectives

By the end, you will understand:

- what a conflict actually means
- why rollback is a feature, not a punishment
- how explicit diagnostics connect this editor to the rest of the project

---

## A Conflict Is Two Truths That Cannot Coexist

In this editor, a conflict does not mean the app crashed.

It means the current set of requests contains at least one impossible combination.

Example:

- `align-left(rule_a, rule_b)`
- `horizontal-gap(rule_a, rule_b, 36)`

Those two rules disagree because `rule_b` cannot both share `rule_a`'s left edge and sit 36 pixels to the right of it.

---

## Why Rollback Matters

When a scene becomes impossible, the editor restores the last valid state.

That does two important things:

- it protects the canvas from drifting into nonsense
- it turns failure into feedback you can act on

The goal is not to shame the user. The goal is to preserve trust.

---

## Why This Is Educational

Many AI systems fail in vague ways:

- the output just looks wrong
- the model changes its story
- the user is left guessing

Explicit conflict reporting is better.

It says:

- which rule was involved
- which objects were involved
- why the request could not be satisfied

That is the same design ethic the larger repo is chasing for reasoning systems more broadly.

---

## Try It

Load `How to read a conflict`

Then:

1. Read the conflict card.
2. Remove the `align-left` rule.
3. Watch the conflict disappear.
4. Add the rule back and remove the `horizontal-gap` rule instead.

Both paths teach the same lesson: when structure is explicit, repair is easier.

---

## Discussion Questions

1. What makes an error feel helpful instead of hostile?
2. How would you want an LLM to explain a contradiction in plain language?
3. Where else in software would rollback plus explanation improve trust?
