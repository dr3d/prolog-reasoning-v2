# LP-LM Comparison Note (2502.09212v1)

Status: Draft  
Date: 2026-04-06

Source reviewed:

- arXiv abstract: `https://arxiv.org/abs/2502.09212`
- arXiv PDF: `https://arxiv.org/pdf/2502.09212.pdf`
- LP-LM code repo (paper-linked): `https://github.com/katherinewu312/lp-lm`
- Title: `LP-LM: No Hallucinations in Question Answering with Logic Programming`

This note compares LP-LM framing against `prolog-reasoning-v2` and pulls out
ideas that are immediately useful for this repo.

## What LP-LM Emphasizes

LP-LM (as described in the paper) centers on:

- grounding question answering in a Prolog knowledge base
- semantic parsing to Prolog terms
- DCG + tabling for efficient parsing/execution
- reducing hallucinations by relying on explicit facts and unification

The paper also explicitly contrasts this approach with RAG-style systems.

## Where This Repo Already Matches

Strong overlap with current `prolog-reasoning-v2`:

- deterministic fact/rule execution (`src/engine/*`, `src/mcp_server.py`)
- local KB-oriented reasoning via MCP tools
- explicit runtime fact operations (`assert_fact`, `retract_fact`, `reset_kb`)
- emphasis on reliability and inspectable results over pure generation

In short: the core "deterministic truth layer" thesis is already aligned.

## Where This Repo Is Ahead

Relative to LP-LM's QA framing, this repo already extends farther into:

- operational state simulation flows (hospital CPM, fantasy session)
- runtime control loops through MCP integrations
- constraint-management direction (not only fact retrieval)
- chat playbook patterns + captured reproducible transcripts

So LP-LM is not a replacement direction; it is mostly validation of the
symbolic grounding choice plus a reminder to keep the parsing layer tight.

## Practical Gaps Worth Importing

Useful LP-LM-inspired gaps to close here:

- stronger formalization of the NL-to-term parsing contract
- more explicit parser-focused evaluation separate from end-to-end demos
- clearer benchmark framing around "hallucination avoidance under known-fact QA"

These are mostly evaluation and interface-discipline improvements, not an
architecture reset.

## Actionable Experiments For This Repo

### 1) Parser Discipline Slice

Add a narrow benchmark track focused on:

- simple, single-fact QA
- multi-hop relation QA
- known-unknown entity/predicate behavior
- adversarial paraphrases that should still map to same logical query

Measure:

- parse success rate
- query correctness rate
- "no fabricated answer" rate when KB lacks support

### 2) Retrieval vs Reasoning Labeling

Split test queries into:

- retrieval-like (`fact-backed`)
- rule-derived (`inferred`)

Then report per-bucket behavior in evaluator outputs.

### 3) Input Distillation Front-End

Paper notes around grammar limits suggest a practical hybrid:

- use deterministic policy for final routing/write authority
- optionally use small-model pre-processing only to distill noisy user phrasing
  into candidate structured intents before Prolog execution

This pairs cleanly with existing pre-thinker work in this repo.

## Suggested Positioning Line

When discussing this repo in LP-LM-adjacent threads:

`LP-LM shows how logic grounding prevents QA hallucinations. This repo takes the same deterministic grounding idea into MCP tooling and stateful control-room workflows, while adding runtime fact ops and constraint-management direction.`

## Bottom Line

What to adopt from LP-LM:

- tighter parser-contract evaluation
- cleaner hallucination-avoidance benchmark language
- explicit separation between language interpretation and symbolic truth checks

What to keep unique here:

- MCP-native operational workflows
- simulation/control-room use cases
- constraint-management path beyond QA-only tasks
