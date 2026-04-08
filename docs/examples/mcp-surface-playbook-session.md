# MCP Surface Playbook Session (Captured)

- Captured at: 2026-04-07T15:36:02.313518+00:00
- Model: `qwen3.5-27b@q4_k_m`
- Integration: `mcp/prolog-reasoning`
- Normalization: `Normalized to canonical Prolog-only MCP tool surface on 2026-04-08.`

## Step: preflight

### User Prompt

```text
Use show_system_info and list_known_facts first.
Then give a one-paragraph summary of what this MCP server can do.
```

### Tool Calls

- `show_system_info` `{}`
- `list_known_facts` `{}`

### Assistant Reply



This Prolog Reasoning v2 MCP server is a local-first neuro-symbolic reliability layer designed to augment LLM agents with deterministic symbolic reasoning capabilities. It enables natural language query processing where user intent is expressed conversationally while the underlying Prolog engine validates truth against a structured knowledge base, supporting domains ranging from family relationships and access control permissions to clinical medication triage and project dependency risk analysis. The system features runtime fact assertion and retraction for dynamic chat-driven scenarios, semantic validation before query execution, friendly failure explanations with suggestions, and proof-trace generation—all built on a rich predicate vocabulary that includes both fact-backed examples (like parent, role, permission) and rule-derived predicates (such as ancestor, allowed, blocked_task, safe_candidate). With its core philosophy that "memories are timestamped but facts are not," this server provides a reliable reasoning layer that can handle complex logical queries across multiple domains while maintaining transparency through detailed explanations of what the system knows and how it arrives at conclusions.

## Step: reset

### User Prompt

```text
Use ONLY reset_kb. Confirm success in one sentence.
```

### Tool Calls

- `reset_kb` `{}`

### Assistant Reply



The knowledge base has been successfully reset to its baseline state.

## Step: seed

### User Prompt

```text
Use bulk_assert_facts with these facts, then use assert_fact for one extra fact.
Facts for bulk_assert_facts:
task(alpha).
task(beta).
depends_on(beta, alpha).
supplier_status(alpha_vendor, on_time).
Then call assert_fact with:
completed(alpha).
```

### Tool Calls

- `bulk_assert_facts` `{"facts": ["task(alpha).", "task(beta).", "depends_on(beta, alpha).", "supplier_status(alpha_vendor, on_time)."]}`
- `assert_fact` `{"fact": "completed(alpha)."}`

### Assistant Reply



Perfect! Both operations completed successfully:

**Bulk Assertion (4 facts):**
- ✅ task(alpha).
- ✅ task(beta).
- ✅ depends_on(beta, alpha).
- ✅ supplier_status(alpha_vendor, on_time).

**Individual Assertion (1 fact):**
- ✅ completed(alpha).

All 5 facts have been added to the runtime knowledge base. You can now query these facts using any of the available query functions.

## Step: rows

### User Prompt

```text
Use ONLY query_rows with this query:
depends_on(Task, Prereq).
Return rows and count.
```

### Tool Calls

- `query_rows` `{"query": "depends_on(Task, Prereq)."}`

### Assistant Reply



## Query Results: `depends_on(Task, Prereq)`

**Count:** 1 row(s) found

### Rows:
| Task | Prereq |
|------|--------|
| beta | alpha  |

The knowledge base contains one dependency relationship: **beta depends on alpha**.

## Step: logic

### User Prompt

```text
Use ONLY query_logic with this exact query:
depends_on(beta, alpha).
Return short answer and detailed answer.
```

### Tool Calls

- `query_logic` `{"query": "depends_on(beta, alpha)."}`

### Assistant Reply



**Short Answer:**
SUCCESS - `depends_on(beta, alpha)` is TRUE (1 solution found).

**Detailed Answer:**
The Prolog query `depends_on(beta, alpha).` succeeded with 1 solution. This confirms that in the knowledge base, there is a fact stating that "beta depends on alpha". The query was ground (no variables), and it matched exactly one stored fact in the database. The confidence level is 1.0, indicating this is definitively established as true based on the current facts in the system.

## Step: nl_query

### User Prompt

```text
Use ONLY query_rows with this query:
depends_on(Task, Prereq).
Return rows and count.
```

### Tool Calls

- `query_rows` `{"query": "depends_on(Task, Prereq)."}`

### Assistant Reply



## Query Results: `depends_on(Task, Prereq)`

**Count:** 1 row(s) found

### Rows:
| Task | Prereq |
|------|--------|
| beta | alpha  |

The knowledge base contains one dependency relationship: **beta depends on alpha**.

## Step: classify

### User Prompt

```text
Use ONLY classify_statement on:
Maybe my mother was Ann.
Return classification fields only.
```

### Tool Calls

- `classify_statement` `{"text": "Maybe my mother was Ann."}`

### Assistant Reply



```json
{
  "kind": "tentative_fact",
  "confidence": 0.76,
  "needs_speaker_resolution": true,
  "can_query_now": false,
  "can_persist_now": false,
  "suggested_operation": "store_tentative_fact",
  "reasons": [
    "tentative language detected"
  ],
  "status": "success",
  "text": "Maybe my mother was Ann.",
  "proposal_check": {
    "status": "needs_clarification",
    "issues": [
      "speaker identity is unresolved"
    ],
    "reasoning": [
      "predicate and arity validated against deterministic registry",
      "candidate contains <speaker> and requires explicit grounding before persistence"
    ],
    "candidate": {
      "canonical_predicate": "parent",
      "arguments": [
        "ann",
        "<speaker>"
      ],
      "normalized_fact": "parent(ann, <speaker>).",
      "source": "text:family",
      "raw_predicate": "parent"
    }
  }
}
```

## Step: explain

### User Prompt

```text
Use ONLY explain_error with this error message:
Entity 'charlie' not in KB
Return the explanation and suggestions.
```

### Tool Calls

- `explain_error` `{"error_message": "Entity 'charlie' not in KB"}`

### Assistant Reply



## Error Explanation

**Error Type:** `undefined_entity`

**Explanation:** The query refers to an entity that is not currently known to the knowledge base: `charlie`.

## Suggestions

1. **Check the spelling of the entity name** - Ensure you're using the correct capitalization and spelling
2. **Ask about a known entity** such as john, alice, bob, admin, read, or write
3. **Use 'list_known_facts'** to inspect which entities are currently known in the knowledge base
4. **If the entity should exist**, add facts for it before querying

## Learn More

See the training materials at `training/03-learning-from-failures.md`

## Step: cleanup

### User Prompt

```text
Use ONLY these tools in order:
1) retract_fact completed(alpha).
2) reset_kb
Confirm cleanup complete.
```

### Tool Calls

- `retract_fact` `{"fact": "completed(alpha)."}`
- `reset_kb` `{}`

### Assistant Reply



Cleanup complete. Both operations executed successfully:

1. ✅ Fact `completed(alpha).` retracted from runtime KB
2. ✅ Runtime KB reset to baseline seed state

The knowledge base has been cleaned and restored to its original baseline configuration.
