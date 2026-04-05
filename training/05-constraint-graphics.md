---
layout: post
title: "Constraint Graphics: Why This Editor Exists"
description: "A short introduction to constraint-based graphics and the ThingLab spirit behind this project."
level: "Beginner"
domain: "Constraint Systems"
duration: "8 minutes"
---

# Constraint Graphics: Why This Editor Exists

**Course Description**  
*A gentle introduction to why graphics is a natural home for neuro-symbolic ideas.*

---

## Learning Objectives

By the end, you will understand:

- why manual layout work is fragile
- why constraints make graphics feel more like a living system than a pile of coordinates
- how this editor acts as an on-ramp to the broader project

---

## The Core Idea

Most editors store the latest position of each object and ask the human to keep everything consistent by hand.

Constraint-based graphics flips that around.

Instead of saying:

- put this rectangle at `x = 420`

You can say:

- keep these two rectangles aligned on the left
- keep this card 32 pixels to the right of that one
- keep this box inside the canvas

Now the relationship survives movement.

That is the emotional heart of systems such as ThingLab. You are not just drawing shapes. You are describing truths about shapes.

---

## Why This Belongs in a NeSy Repo

This repository is about combining explicit structure with useful explanation.

Constraint graphics is a great fit because:

- the rules are visible
- the solver can be deterministic
- failures can be explained in plain language
- the language layer can help express intent without becoming the source of truth

That last point matters. A language model can help you say "make these evenly spaced," but the actual scene should still be validated and solved by an explicit system.

---

## What the MVP Teaches

The browser MVP is deliberately small so the ideas stay legible.

It teaches:

- relationships are first-class objects
- a solver can update geometry predictably
- conflicts are informative, not embarrassing
- the same neuro-symbolic contract used in the larger repo also works in interactive tools

---

## Try It

Open the editor and load `Why constraints?`

Then:

1. Drag `card_a`.
2. Watch `card_b` keep the same left edge.
3. Remove the `align-left` rule.
4. Drag again and feel how quickly the layout becomes manual labor.

---

## Discussion Questions

1. What kinds of layout relationships do you currently preserve by hand?
2. Which rules feel obvious to a human but are missing from today's common design tools?
3. Where should a language model help, and where should it stay out of the way?
