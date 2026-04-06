# Family Tree Walkthrough

Status: Draft  
Date: 2026-04-05

The point is not to show a giant architecture. The point is to show an agent
using the deterministic layer on purpose because exact relationship reasoning
matters more than fluent guessing.

## What You Will See

The demo loads a tiny family tree and then asks the logic engine questions like:

- Is Ann Clara's ancestor?
- Who are all of Ann's descendants?
- Are Bob and Dana siblings?
- Are Clara and Dana siblings?

This is the kind of problem where a plain LLM may do fine for one turn, but a
deterministic engine gives you:

- stable answers
- explicit rules
- reproducible consequences

## Run It

From the repo root:

```bash
python scripts/demonstrate_family_tree_tool.py
```

## What The Demo Does

It loads these facts:

```prolog
parent(ann, bob).
parent(bob, clara).
parent(ann, dana).
parent(dana, evan).
```

and these rules:

```prolog
ancestor(X, Y) :- parent(X, Y).
ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).
sibling(X, Y) :- parent(P, X), parent(P, Y), X \= Y.
```

Then it asks the engine to compute exact consequences.

## What To Notice

### 1. Overt logic-tool use

The demo is not pretending the model "just knows."

It behaves more like an agent saying:

- this is a relationship problem
- exact consequence matters
- I should use the logic layer

### 2. Rules do the work

The important answer is not stored directly as a sentence.

For example:

- `ancestor(ann, clara)` is derived

That is the whole point of the tool: ask for consequences, not just stored facts.

### 3. Repeatability

If you run the same script again, you get the same answers.

That is the value proposition:

- language models interpret
- logic certifies

## Why This Is A Good First Scenario

It is:

- easy to understand
- easy to run
- hard for fluffy "AI magic" to fake convincingly once the graph gets larger

It is also a clean model for how an agent could use the library:

1. build or load a small world
2. ask explicit symbolic questions
3. return deterministic results with confidence in the reasoning path

## Where To Go Next

After this, the natural next scenarios are:

- access-control checks
- spreadsheet/table derivation from rules
- contradiction detection
- memory curation and candidate fact intake
