---
layout: post
title: "Knowledge Bases 101: Facts That Don't Lie"
description: "AI Course Module: Building Reliable Knowledge"
level: "Beginner"
domain: "Knowledge Representation"
duration: "25 minutes"
---
# 📚 Knowledge Bases 101: Facts That Don't Lie

**AI Course Module: Building Reliable Knowledge**  
*Perfect for beginners learning how to teach AI actual facts instead of guesses*

---

## 🎓 Learning Objectives

By the end of this module, you'll understand:
- What a knowledge base really is (and why it matters)
- The difference between "facts" and "guesses"
- How to structure information so AI gets it right
- Why Prolog is perfect for this job

---

## 📖 The Problem: Garbage In, Garbage Out

**You just learned about fixing AI memory, now let's talk about fixing AI accuracy.** 🎯

Here's the thing: **Even with perfect memory, AI can be confidently wrong.**

Imagine a doctor's office with this filing system:
```
Patient: John Smith
- Has allergy (probably penicillin? or was it aspirin?)
- Takes some medication for heart stuff
- Did surgery once... or was that his brother?
```

Yikes! 😨

**This is what happens when AI "guesses" at facts instead of knowing them for certain.**

### The Difference: Guessing vs. Knowing

**Guessing (What LLMs do without help):**
```
LLM thinks: "John might be allergic to penicillin because... 
patterns in my training data suggest... or maybe it was 
allergic to something else... you know what, I'm just going
to take a guess..."
```
Result: ❌ Wrong medicine prescribed, patient in hospital

**Knowing (What Prolog does):**
```prolog
patient(john_smith).
allergic_to(john_smith, penicillin, severe).
```
Prolog: "John IS allergic to penicillin. That's a fact. No guessing."

Result: ✅ Safe, verified, certain

---

## 🏗️ What IS a Knowledge Base?

A **knowledge base** is just organized facts that are:
1. **Concrete** - Not fuzzy, not approximate, not "maybe"
2. **Verified** - Checked to be true
3. **Structured** - Easy for a computer to search
4. **Queryable** - You can ask questions about them

Think of it like this:

| Messy Notes | Knowledge Base |
|-------------|---|
| "John's mom... or wait, Alice? One of them is your parent" | `parent(john, alice).` ✅ Certain |
| "Alice has some allergy, I think?" | `allergy(alice, peanuts, moderate).` ✅ Verified |
| "Bob and Alice are... related somehow?" | `sibling(bob, alice).` ✅ Structured |

---

## 🧬 The Building Blocks: Facts and Rules

### Facts: "This is true"

Facts are statements about the world that don't change:

```prolog
% These are facts - concrete, verified truths
patient(john_smith).
patient(alice_johnson).

allergic_to(john_smith, penicillin, severe).
allergic_to(alice_johnson, peanuts, moderate).

takes_medication(john_smith, metformin, 500, twice_daily).
takes_medication(alice_johnson, lisinopril, 10, once_daily).
```

**These facts answer simple questions:**
- Is John a patient? `patient(john_smith).` → ✅ Yes!
- What's Alice allergic to? `allergic_to(alice_johnson, X).` → `peanuts`

### Rules: "If this, then that"

Rules are like IF statements - they derive new facts from existing ones:

```prolog
% Facts about relationships
parent(alice, bob).
parent(bob, charlie).

% Rule: If X is parent of Y, then X is ancestor of Y
ancestor(X, Y) :- parent(X, Y).

% Rule: If X is parent of Z and Z is ancestor of Y, then X is ancestor of Y
ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).
```

**Now the system can answer complex questions:**
- Is Alice an ancestor of Charlie? `ancestor(alice, charlie).` → ✅ Yes!
  - (You never said "Alice is Charlie's grandparent", but the system figured it out!)

---

## 💡 How This Fixes "False Certainty"

Remember in the first course how AI can be confidently wrong?

**With a knowledge base, we prevent this in 3 ways:**

### 1. **Explicit Validation** ✅

Before AI adds anything to the knowledge base, we check:
- "Is this entity real?" (Does John actually exist?)
- "Is this relationship valid?" (Can someone be allergic to "flying"? No!)
- "Does this contradict something?" (John can't be 5 years old AND 80 years old)

```python
# Without validation (BAD):
LLM says: "User john is allergic to flying"
System: "OK, added to database" ❌
# <- WRONG! "Flying" isn't real, "allergic_to_flying" is nonsense

# With validation (GOOD):
LLM says: "User john is allergic to flying"
System: "⚠️ I don't know what 'flying' is. Valid allergies are: peanuts, penicillin, etc."
LLM: "Oh! I meant peanuts"
System: "✅ Verified and added" ✅
```

### 2. **Confidence Tracking** 📊

Every fact knows how confident we should be:

```prolog
% Strong facts (verified by human)
patient(john_smith, confidence=100).

% Weaker facts (LLM parsed, needs verification)
allergic_to(john_smith, shellfish, confidence=60).
```

The system uses confidence scores to decide:
- High confidence (100%): Trust it completely
- Medium confidence (60%): Use it, but mention uncertainty
- Low confidence (30%): Suggest verification before using

### 3. **Proof Traces** 🔍

When the system answers a question, it shows WHY:

```
Question: "Is John an ancestor of David?"

Answer: ✅ YES

Proof:
  1. parent(john, alice) — VERIFIED FACT
  2. parent(alice, bob) — VERIFIED FACT
  3. parent(bob, david) — VERIFIED FACT
  4. Therefore: ancestor(john, david) ✅

Confidence: 100% (all facts verified)
```

No guessing. No "probably". Just facts and reasoning.

---

## 🎮 Try It: Build Your First Knowledge Base

Let's build a simple family tree:

```prolog
% Facts: Who are the family members?
family(john).
family(alice).
family(bob).
family(charlie).

% Facts: Who is whose parent?
parent(john, alice).
parent(alice, bob).
parent(bob, charlie).

% Rule: If X is a parent of Y, then Y is a child of X
child(Y, X) :- parent(X, Y).

% Rule: If X is parent of Y and Y is parent of Z, X is grandparent of Z
grandparent(X, Z) :- parent(X, Y), parent(Y, Z).

% Rule: Siblings share a parent
sibling(X, Y) :- parent(Z, X), parent(Z, Y), X \= Y.
```

Now you can ask questions:
- `parent(john, alice).` → ✅ Yes
- `child(bob, alice).` → ✅ Yes (derived from rule!)
- `grandparent(john, bob).` → ✅ Yes (derived from rule!)
- `sibling(alice, bob).` → ❌ No (they don't share a parent)

**Cool, right?** You wrote facts once, and the rules let you ask infinite questions!

---

## 🚨 What We're Preventing

### The "False Certainty" Problem

**Without a Knowledge Base (OLD WAY):**
```
LLM: "John is probably allergic to something...
      let me guess... penicillin?"
System: "Sure, sounds good"
Doctor: Uses penicillin
John: 🏥 ALLERGIC REACTION
```

**With a Knowledge Base (NEW WAY):**
```
LLM: "John is allergic to penicillin"
Validation: "Is 'john' a patient? YES ✅
            Is 'penicillin' a real allergy? YES ✅
            Does this contradict anything? NO ✅"
System: ✅ VERIFIED - add to database
Doctor: Checks database → "John is allergic to penicillin" ✅
John: 😊 Safe treatment
```

---

## 🔗 How This Connects to the Pipeline

Remember from Course 1 how memory gets fixed?

**Course 1 (Memory):**
```
External Knowledge Base stores facts
LLM queries the KB instead of guessing
AI gets accurate answers
```

**Course 2 (This one - Knowledge Bases):**
```
External Knowledge Base stores VERIFIED facts
Only TRUE information can enter
Validation prevents "confident mistakes"
AI gets accurate answers AND knows why
```

**Together:** Safe, reliable, explainable AI! 🎯

---

## 📝 Key Takeaways

✅ **Facts are better than guesses**
- One fact: `parent(alice, bob).`
- One guess: "Alice might be Bob's... parent? Maybe?"

✅ **Rules extend facts without guessing**
- You don't tell it "Alice is Bob's grandparent"
- You write rules and let it derive that truth

✅ **Validation prevents wrong facts from entering**
- Before a fact goes in the database, we verify it
- This eliminates "false certainty"

✅ **Prolog is perfect for this**
- Simple, clear syntax: `facts` and `rules`
- Automatic proof generation
- No approximation or fuzziness

---

## 🎓 Next Steps

1. **Run the example:** `python scripts/demonstrate_semantic.py`
2. **Try the validation demo:** `python scripts/demonstrate_failures.py`
3. **Read deeper:** Check out `docs/semantic-grounding.md`
4. **Course 3 (coming soon):** Learn how to handle mistakes when they happen

---

## 🤔 Try This at Home

Create a knowledge base about something you know:
- **Your pets:** Names, species, tricks, favorite food
- **Your friends:** Names, hobbies, relationships
- **A hobby:** Rules about how it works

Then ask it questions and see if it can derive answers!

Example for pets:
```prolog
pet(fluffy, cat).
pet(rex, dog).

owner(fluffy, alice).
owner(rex, bob).

likes(fluffy, fish).
likes(rex, steak).

% Rule: If X is a pet and Y is the owner, Y has a pet
has_pet(Owner, Pet) :- pet(Pet, _), owner(Pet, Owner).
```

Try it! 🐱🐕

---

**Questions?** Check `docs/` folder for technical details or start `Course 3` on failure handling!
