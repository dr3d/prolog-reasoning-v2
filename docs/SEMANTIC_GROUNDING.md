# Semantic Grounding Layer

## Overview

The Semantic Grounding Layer converts natural language queries into structured Intermediate Representation (IR) that can be processed by the Prolog reasoning engine. This enables agents to query the knowledge base using everyday language instead of Prolog syntax.

## Architecture

```
Natural Language Query
        ↓
   LLM Parser (GPT-4, Claude, etc.)
        ↓
   IR Validation & Correction
        ↓
   Prolog Query Execution
        ↓
   Structured Response
```

## Key Components

### 1. SemanticGrounder Class

**Purpose**: Main interface for converting NL to IR

**Features**:
- LLM-assisted parsing with error correction
- Schema validation against domain knowledge
- Confidence scoring and fallback handling
- Support for multiple query intents

**Usage**:
```python
from parser.semantic import SemanticGrounder

grounder = SemanticGrounder(llm_client=my_llm_api)
parsed = grounder.ground_query("Who is John's parent?")
prolog_query = grounder.to_prolog_query(parsed)
```

### 2. SemanticPrologSkill Class

**Purpose**: End-to-end NL to Prolog execution for agents

**Features**:
- Integrates semantic grounding with Prolog execution
- Provides structured responses for agent consumption
- Includes parsing metadata and confidence scores

**Usage**:
```python
from parser.semantic import SemanticPrologSkill

skill = SemanticPrologSkill()
result = skill.query_nl("Who is John's parent?")
# Returns: success, bindings, explanation, confidence, etc.
```

### 3. Query Intent Classification

The system recognizes different types of user queries:

- **variable_query**: Questions with unknowns (e.g., "Who is John's parent?")
- **fact_check**: Yes/no questions (e.g., "Is Alice allowed to read?")
- **assertion**: Declarative statements (e.g., "John is Alice's parent")
- **list_query**: Requests for multiple results (e.g., "What are John's children?")

## Supported Domains

### Family Relations
- **Predicates**: parent, sibling, ancestor, person
- **Examples**:
  - "Who is John's parent?" → `parent(john, X)`
  - "Are Alice and Bob siblings?" → `sibling(alice, bob)`

### Access Control
- **Predicates**: user, role, permission, allowed
- **Examples**:
  - "Is Alice allowed to read?" → `allowed(alice, read)`
  - "What permissions does Alice have?" → `allowed(alice, X)`

## LLM Integration

### Prompt Engineering

The system uses structured prompts to guide LLM parsing:

```
Convert this natural language query to structured logical representation.

Query: "Who is John's parent?"

Instructions:
1. Identify the intent: fact_check, variable_query, list_query, assertion, or rule
2. Extract the logical predicate and arguments
3. Use variables (X, Y, Z) for unknowns
4. Determine the domain (family, access, general)
5. Provide confidence score (0.0-1.0)

Return only valid JSON:
```

### Error Correction

- **Validation**: IR is validated against domain schemas
- **Retry Logic**: Up to 3 attempts with corrective prompts
- **Fallback**: Graceful degradation with low-confidence results

## Example Usage

### Basic Semantic Grounding

```python
from parser.semantic import SemanticGrounder

grounder = SemanticGrounder()

# Parse natural language
parsed = grounder.ground_query("Who is John's parent?")
print(f"Intent: {parsed.intent.value}")
print(f"Prolog: {grounder.to_prolog_query(parsed)}")
# Output: parent(john, X).
```

### Agent Integration

```python
from parser.semantic import SemanticPrologSkill

skill = SemanticPrologSkill()

# Query with natural language
result = skill.query_nl("Who is John's parent?")
print(f"Success: {result['success']}")
print(f"Answer: {result['explanation']}")
print(f"Bindings: {result['bindings']}")
```

### Response Format

```json
{
  "success": true,
  "bindings": {"X": "alice"},
  "explanation": "✓ Query 'parent(john, X)' succeeded with 1 solution(s).\n  Bindings: X: alice",
  "proof_trace": [...],
  "confidence": 1.0,
  "query": "parent(john, X).",
  "num_solutions": 1,
  "nl_query": "Who is John's parent?",
  "parsed_ir": "{...}",
  "parsing_confidence": 0.9,
  "domain": "family"
}
```

## Integration with Agent Frameworks

### AutoGen

```python
from autogen import AssistantAgent
from parser.semantic import SemanticPrologSkill

class PrologAgent(AssistantAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prolog_skill = SemanticPrologSkill()
    
    def query_knowledge(self, nl_query: str):
        return self.prolog_skill.query_nl(nl_query)
```

### CrewAI

```python
from crewai import Agent, Task
from parser.semantic import SemanticPrologSkill

prolog_skill = SemanticPrologSkill()

agent = Agent(
    role="Knowledgeable Assistant",
    tools=[prolog_skill.query_nl],
    verbose=True
)
```

## Performance & Reliability

### Confidence Scoring
- **High (>0.9)**: Direct pattern matches, clear intent
- **Medium (0.7-0.9)**: Inferred patterns, some ambiguity
- **Low (<0.7)**: Fallback parsing, potential errors

### Error Handling
- **Schema Validation**: Ensures IR conforms to domain rules
- **Type Checking**: Validates argument types and arity
- **Fallback Queries**: Provides answers even with parsing failures

## Future Enhancements

### 1. Multi-turn Conversations
- Context tracking across queries
- Pronoun resolution ("Who is her parent?")
- Follow-up question handling

### 2. Rule Learning
- Inductive learning from examples
- Pattern recognition for new predicates
- Dynamic schema expansion

### 3. Advanced NLP
- Named entity recognition
- Temporal reasoning
- Spatial relationships

### 4. Multi-modal Input
- Voice queries
- Diagram interpretation
- Document analysis

## Testing & Validation

### Unit Tests
```bash
cd src && python -m pytest tests/test_semantic.py -v
```

### Benchmark Evaluation
```bash
python scripts/evaluate_semantic.py
```

### Integration Tests
```bash
python scripts/test_agent_integration.py
```

## Configuration

### Environment Variables
```bash
export OPENAI_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"
```

### Custom LLM Client
```python
def my_llm_client(prompt: str) -> str:
    # Your LLM integration here
    return response

grounder = SemanticGrounder(llm_client=my_llm_client)
```

## Troubleshooting

### Common Issues

1. **Low Confidence Scores**
   - Check query clarity and domain coverage
   - Review LLM prompt and response format
   - Consider adding domain-specific patterns

2. **Schema Validation Errors**
   - Verify predicate definitions in schema
   - Check argument types and counts
   - Update schemas for new domains

3. **LLM API Errors**
   - Verify API keys and endpoints
   - Check rate limits and quotas
   - Implement retry logic with backoff

### Debug Mode

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Research Applications

This semantic grounding layer enables:

- **Explainable AI**: Full reasoning traces from NL queries
- **Knowledge Base Construction**: Automated fact extraction
- **Agent Communication**: Natural interaction with symbolic systems
- **Hybrid Reasoning**: Combining neural and symbolic approaches

The system provides a bridge between human language and formal logic, enabling more intuitive and powerful AI agents.</content>
<parameter name="filePath">d:\_PROJECTS\prolog-reasoning-v2\docs\SEMANTIC_GROUNDING.md