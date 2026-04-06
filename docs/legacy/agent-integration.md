# Agent Integration Guide

Status: Legacy reference (pre-v2 framing).  
Canonical entry points now: `docs/lm-studio-mcp-guide.md`, `docs/mcp-chat-playbooks.md`, and `docs/fact-intake-pipeline.md`.

## How LLM Agents Use Prolog Reasoning as a Skill

**Key insight**: The KB is *external memory* — not dumped into LLM context. The agent queries it when needed.

## Integration Pattern

### 1. Ambient Awareness (Manifest Injection)

**Before conversation starts**, inject a manifest into the agent's prompt:

```
## Knowledge Base Manifest
Facts: 47  Rules: 8
Predicates: born/2  event/2  lives_in/2  occupation/2  parent/2  role/2  sibling/2
Known entities: alice, ann, blake, dana, scott
Skill: prolog-reasoning
Query command: python src/engine/runner.py "<query>" --kb prolog/core.pl
```

**Result**: Agent knows *what* facts exist, but not the facts themselves.

### 2. Query Decision Logic

Agent follows this behavioral commitment:

> "I will query the knowledge base before answering any factual question about known entities — not from memory."

**Examples**:
- ✅ Query KB: "Where does Scott live?" (entity in manifest)
- ✅ Query KB: "Is Alice an admin?" (role/permission logic)
- ❌ Use memory: "What's the weather like?" (not in KB)

### 3. Query Execution

When agent decides to query:

```bash
# Agent runs this command
python src/engine/runner.py "lives_in(scott, X)." --kb prolog/core.pl

# Gets back:
{
  "success": true,
  "bindings": [{"X": "austin"}],
  "proof": ["lives_in(scott, austin) [stored fact]"]
}
```

### 4. Response Synthesis

Agent combines KB result with its reasoning:

**User**: "Where does Scott live?"

**Agent thinking**:
- Scott is in manifest → query KB
- KB returns: lives_in(scott, austin)
- I know Austin is in Texas → synthesize answer

**Response**: "Scott lives in Austin, Texas."

## Why This Works Better Than Context Dumping

### ❌ Context Dumping (Bad)
```
# Put entire KB in prompt:
parent(john, alice).
parent(alice, bob).
lives_in(scott, austin).
role(alice, admin).
... [47 more facts] ...

Now answer questions about these facts.
```

**Problems**:
- Wastes context window on facts
- Facts compete with conversation
- No inference (can't derive ancestor relationships)
- Facts degrade under summarization

### ✅ External KB (Good)
```
# Manifest only (compact):
Known entities: alice, ann, blake, dana, scott
Predicates: parent/2, lives_in/2, role/2, ancestor/2

# Agent queries as needed
```

**Advantages**:
- Context window free for conversation
- Facts never degrade (lossless)
- Inference works (ancestor derivation)
- Scalable (KB can be huge)

## Agent Skill Implementation

### Skill Definition (JSON)
```json
{
  "name": "prolog-reasoning",
  "description": "Query deterministic knowledge base for facts and inference",
  "commands": [
    {
      "name": "query_kb",
      "description": "Execute Prolog query against knowledge base",
      "parameters": {
        "query": "string - Prolog query like 'parent(john, X).'"
      }
    }
  ],
  "triggers": [
    "factual questions about known entities",
    "relationship queries",
    "permission checks",
    "logical inference needed"
  ]
}
```

### Behavioral Prompts

**System prompt addition**:
```
You have access to a Prolog knowledge base containing facts about people, relationships, roles, and events.

BEFORE answering any factual question about entities in the manifest, query the knowledge base first.

The KB is the source of truth. Do not rely on your training data for these facts.
```

**Example conversation**:

```
User: "Is Alice related to Scott?"

Agent: [thinks: Alice and Scott are known entities → query KB]
Agent: [runs] python src/engine/runner.py "sibling(alice, scott)." --kb prolog/core.pl
KB: {"success": true, "bindings": [{}]}

Agent: "Yes, Alice and Scott are siblings."
```

## Context Management

### What Goes in LLM Context
- **Manifest** (compact summary)
- **Behavioral instructions** (when to query)
- **Conversation history**
- **Current task context**

### What Stays External
- **Actual facts** (stored in .pl files)
- **Proof traces** (generated on demand)
- **Large datasets** (can be terabytes)

## Scaling Benefits

| Approach | Context Usage | Fact Accuracy | Inference Power | Scalability |
|----------|---------------|----------------|-----------------|-------------|
| Context dump | High (wastes window) | Degrades over time | None | Poor |
| External KB | Low (manifest only) | Perfect (lossless) | Full (rules) | Excellent |

## Implementation Steps

1. **Generate manifest** from KB
2. **Inject manifest** into agent prompt
3. **Add behavioral rules** to agent
4. **Implement query interface** (CLI or API)
5. **Test integration** with sample conversations

The KB becomes the agent's "perfect memory" — deterministic, queryable, and inference-capable.
