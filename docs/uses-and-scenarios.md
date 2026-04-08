# Uses and Scenarios

Status: Draft  
Owner: Core symbolic layer  
Date: 2026-04-05

## 1. Why This Doc Exists

The easiest way to understand Prolog Reasoning v2 is not as a general-purpose
"AI brain," but as a deterministic logic tool that an agent can load when it
needs exact consequences, explicit rules, or explainable constraint handling.

This doc collects overt logic-tool scenarios:

- the agent knows it needs logic
- the agent calls the tool on purpose
- the symbolic layer does work a plain LLM should not be trusted to improvise

## 2. When An Agent Should Reach For This Tool

An agent should explicitly load or call the logic layer when a task has one or
more of these properties:

- exact relationships matter
- rules chain over multiple steps
- consequences need to be reproducible
- contradictions or impossible states matter
- outputs should be explainable
- the result should be auditable instead of just plausible

Good fit:

- family relationships
- access-control reasoning
- eligibility and policy checks
- spreadsheet/table derivation from rules
- state propagation
- constraint handling

Bad fit:

- open-ended creative writing
- broad brainstorming with no hard rules
- fuzzy subjective judgments with no stable symbolic shape

## 3. Basic Invocation Pattern

The general agent pattern is:

1. Detect a task that needs exact logic.
2. Load or call the symbolic tool.
3. Gather or author the relevant facts/rules.
4. Query for consequences.
5. Return the result with explanation, not just raw confidence.

Current practical surfaces:

- `query_logic`
- `query_rows`
- `list_known_facts`
- `classify_statement`
- `explain_error`
- `show_system_info`

Current limitation:

- the repo does not yet have a finished durable natural-language write path
- so "setting up facts" today usually means:
  - using an existing KB
  - editing a KB file
  - or staging facts in structured form before querying

## 4. Scenario 1: Family Tree Assistant

### Problem

The user wants an agent to build a small family tree and answer relationship
questions reliably.

### Why logic is useful

A plain LLM may answer simple family questions correctly for a while, but:

- multi-step ancestry can drift
- sibling logic is directional and easy to muddle
- explanation matters
- consistency matters across repeated queries

### Overt tool use

The agent explicitly decides:

- "This is relationship logic."
- "I should use the symbolic layer."

### Minimal setup

Today, the agent would likely create or edit facts such as:

```prolog
parent(ann, bob).
parent(bob, clara).
parent(ann, dana).
```

with rules like:

```prolog
ancestor(X, Y) :- parent(X, Y).
ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).
sibling(X, Y) :- parent(P, X), parent(P, Y), X \= Y.
```

### Queries

The agent can then ask:

- `Who is Clara's ancestor?`
- `Is Dana Clara's sibling?`
- `Who are Ann's descendants?`

### What the logic layer adds

- exact closure over ancestry
- stable sibling behavior
- repeatable answers
- explainable reasoning paths

### Realistic current version

Today, this is best modeled as:

- agent authors or selects a family KB
- agent uses `query_logic` or `query_rows`
- agent reports the result and explanation

Try it now:

- `python scripts/demonstrate_family_tree_tool.py`
- walkthrough: `docs/family-tree-walkthrough.md`
- LLM + MCP level: `python scripts/demonstrate_family_tree_agent_mcp.py`
- walkthrough: `docs/family-tree-agent-mcp-walkthrough.md`

### Future version

Later, with fact intake and writes:

- the agent hears "Ann is Bob's mother"
- classifies it as a fact candidate
- maps it to `parent(ann, bob)`
- stages or asserts it
- then uses the logic layer for queries

## 5. Scenario 2: Access Control Agent

### Problem

The user asks:

- "Can Alice write this file?"
- "Who inherits admin permissions?"
- "Why was access denied?"

### Why logic is useful

Permission systems are exactly the sort of place where:

- one mistaken inference matters
- inheritance rules matter
- repeated exactness matters

### Overt tool use

The agent explicitly routes into symbolic mode because:

- roles
- permissions
- derived access

are not good places to rely on language-model guesswork.

### Example facts

```prolog
role(alice, admin).
permission(admin, read).
permission(admin, write).
allowed(User, Action) :- role(User, Role), permission(Role, Action).
```

### Example agent tasks

- determine whether a user is allowed
- list all actions a role implies
- explain why a denial happened
- detect conflicting permission claims

### What the logic layer adds

- exact inheritance
- explicit proof of how access was derived
- clean "no result" cases instead of bluffing

## 6. Scenario 3: Spreadsheet Builder From Rules

### Problem

The user wants a table generated from rules, not guessed row-by-row by an LLM.

Example:

- users
- roles
- inherited permissions
- violation flags

### Why logic is useful

A spreadsheet is often a visible surface for:

- facts
- rule application
- derived columns
- exceptions

A plain LLM may produce a plausible-looking sheet that is not closed under the
rules.

### Overt tool use

The agent explicitly decides:

- "I need deterministic row derivation."
- "I will use the logic layer to compute the columns."

### Example workflow

1. Agent loads facts about users, roles, permissions.
2. Agent queries for all derived permissions.
3. Agent materializes rows such as:
   - user
   - role
   - derived_permission
   - violation_flag
4. Agent emits CSV or markdown table.

### What the logic layer adds

- deterministic derived columns
- easy explanation of each row
- less spreadsheet hallucination

Try it now:

- `python scripts/demonstrate_rule_table_tool.py`
- walkthrough: `docs/rule-table-walkthrough.md`
- LLM + MCP level: `python scripts/demonstrate_rule_table_agent_mcp.py`
- walkthrough: `docs/rule-table-agent-mcp-walkthrough.md`

## 7. Scenario 4: Constraint or State Propagation Assistant

### Problem

The user gives a set of explicit conditions that must hold together.

Examples:

- layout constraints
- dependency rules
- state propagation
- allowed / disallowed combinations

### Why logic is useful

This is where agents often sound confident while silently missing one
constraint.

### Overt tool use

The agent explicitly switches to symbolic support because:

- there are explicit conditions
- closure matters
- inconsistency matters

### Example tasks

- propagate consequences from a few seed facts
- identify contradiction
- enumerate valid states
- explain why a requested configuration fails

### What the logic layer adds

- closure over explicit rules
- contradiction detection
- auditable state transitions

## 8. Scenario 5: Soft Inferencer With Hard Consequences

### Problem

The main agent or LLM is good at interpreting messy language, but not at
certifying exact consequences.

### Pattern

The soft system proposes:

- candidate facts
- candidate relationships
- candidate constraints

The logic layer then decides:

- what follows
- what conflicts
- what is unsupported
- what is impossible

### Why this matters

This is one of the strongest uses of the library:

- soft systems explore
- hard logic certifies

That makes the library a logic coprocessor rather than a competing agent brain.

## 9. Scenario 6: Memory Curation Sidecar

### Problem

The user wants an agent with better memory, but does not want raw conversation
transcript to become durable truth.

### Overt tool use

The agent or sidecar deliberately uses the symbolic pipeline to:

- classify candidate memory
- separate hard facts from tentative claims
- preserve corrections
- avoid treating fading conversational memory as truth

### Current realistic use

Today, the tool can already help with:

- `classify_statement`
- identifying candidate facts vs preferences vs corrections

The future version adds:

- predicate mapping
- canonical fact shaping
- assert / tentative / supersede decisions

### Why logic is useful

Without curation, memory becomes sludge.

With curation, durable symbolic memory becomes:

- inspectable
- revisable
- less fuzzy

## 10. What We Mean By "Overt Logic Tool Use"

This doc is not about hidden symbolic help.

It is about an agent knowing:

- "This is a logic problem."
- "I should call the deterministic layer."

That can mean:

- explicit MCP tool calls
- explicit skill loading
- loading a logic-backed KB before answering
- materializing derived outputs from rule queries

The important thing is that logic is not accidental. It is chosen because the
task needs it.

## 11. Summary

The strongest current story for the project is:

- a deterministic logic layer for agents
- overtly invoked when exact consequences matter

The strongest next story is:

- use the same layer to curate memory so facts do not remain trapped in fuzzy
  conversational drift

That gives the repo two compatible utilities:

1. a practical logic coprocessor
2. a trust layer for symbolic memory

For harder moonshot-style domains, see:

- `docs/research/legacy/stretch-logic-scenarios.md`

## 12. Scenario 7: Drug Interaction Triage

### Problem

The agent must choose among candidate medications for a patient with:

- existing medications
- allergy constraints
- renal-risk constraints

### Why logic is useful

A language model can sound plausible here while silently missing a dangerous
constraint interaction.

This scenario needs:

- exact rule closure
- explicit reason codes
- reproducible recommendation output

### Overt tool use

The agent intentionally switches into deterministic mode:

- query risk status with symbolic predicates
- classify each candidate as `contraindicated`, `caution`, or `safe`
- summarize recommendations from derived results

Try it now:

- deterministic layer only: `python scripts/demonstrate_drug_triage_tool.py`
- walkthrough: `docs/drug-triage-walkthrough.md`
- LLM + MCP layer: `python scripts/demonstrate_drug_triage_agent_mcp.py`
- walkthrough: `docs/drug-triage-agent-mcp-walkthrough.md`
