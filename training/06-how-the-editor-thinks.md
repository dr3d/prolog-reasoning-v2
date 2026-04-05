---
layout: post
title: "How This Editor Thinks"
description: "A plain-language walkthrough of the deterministic solve loop used in the constraint editor MVP."
level: "Beginner"
domain: "Reasoning Systems"
duration: "8 minutes"
---

# How This Editor Thinks

**Course Description**  
*Understand the solve loop without needing a math-heavy background.*

---

## Learning Objectives

By the end, you will understand:

- what happens after every drag or resize
- why deterministic update order matters
- how this mirrors the broader propagation ideas in the repo

---

## The Four-Step Loop

Every edit follows the same shape:

1. Copy the current scene.
2. Apply constraints in a fixed order.
3. If the scene settles into a valid state, keep it.
4. If a contradiction appears, restore the previous valid scene and explain why.

This sounds simple because it is meant to be simple.

The educational value comes from the fact that users can build an intuition for what the solver is doing.

---

## Why Fixed Order Matters

When systems become mysterious, users stop trusting them.

This MVP uses a deterministic order so that:

- the same edit behaves the same way every time
- there is a clear mental model for source and follower rectangles
- conflicts can be described in terms of competing rules, not random behavior

This is not the most general possible solver. It is a readable one.

---

## Source and Follower

For pairwise constraints, rectangle `A` is the source and rectangle `B` is the follower.

Examples:

- `align-left(A, B)` means move `B` until its left edge matches `A`
- `equal-width(A, B)` means update `B` until its width matches `A`
- `horizontal-gap(A, B, 24)` means place `B` after `A` with a 24 pixel gap

That directional choice is part of how the MVP stays low friction.

---

## Where NeSy Shows Up

The bigger repo already emphasizes explicit representations, propagation, and explanations. The editor applies that same pattern to geometry:

- structured objects instead of free-form prose
- rule application instead of hidden magic
- named contradictions instead of silent failure

The editor is not pretending to be a giant general solver. It is a small, honest environment where you can watch symbolic structure affect a visual scene.

---

## Try It

Load `How this editor thinks`

Then:

1. Resize `story_a`.
2. Watch the equal-width rules propagate.
3. Watch the horizontal-gap rules reposition the following rectangles.
4. Remove one rule and see how the scene regains more freedom.

---

## Discussion Questions

1. What tradeoff are we making by choosing a simple directional solver?
2. When would you want more expressive math, and when is clarity more important?
3. How does this loop compare to how an LLM usually edits content?
