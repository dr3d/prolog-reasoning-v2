# Failure Explanation Layer - Documentation

## Overview

The **Failure Explanation Layer** is a system that translates cryptic Prolog/system errors into friendly, actionable explanations. This is essential for **beginners learning NeSy concepts** and for **debugging production issues**.

Instead of:
```
Error: undefined_entity
```

You get:
```
❌ I don't know who 'charlie' is

📝 System only knows: john, alice, bob

💡 Try: Tell me about charlie first, or use a name I know about
```

## When Failures Happen

The system handles these failure types gracefully:

### 1. **Undefined Entity** (Most Common!)

**What went wrong:** You used a name/entity that the system doesn't know about.

```python
translator = FailureTranslator(kb_entities={"john", "alice", "bob"})

issue = ValidationIssue(
    error_type=ValidationError.UNDEFINED_ENTITY,
    message="Entity 'charlie' not in KB"
)

explanation = translator.explain_validation_error(issue)
print(translator.format_for_human(explanation))
```

**Output:**
```
❌ I don't know who or what 'charlie' is

📝 System only knows: john, alice, bob

💡 Try: Make sure to tell me about charlie first, or use a name I know about


🤔 Did you mean one of these?
   • charlie (similarity: 0%)
```

### 2. **Ungrounded Predicate** (Unfamiliar Relationships)

**What went wrong:** You asked about a relationship type the system doesn't understand.

```python
issue = ValidationIssue(
    error_type=ValidationError.UNGROUNDED_PREDICATE,
    message="Predicate 'can_fly' not grounded in KB"
)

explanation = translator.explain_validation_error(issue)
```

**Output:**
```
⚠️ I'm not sure about the relationship 'can_fly'

📝 I know about these relationships: parent, sibling, ancestor

💡 Try: Ask about relationships the system knows, like "Is Alice the parent of Bob?"
```

### 3. **Query Returns No Results**

**What went wrong:** The system looked for an answer but couldn't find one based on available facts.

```python
explanation = translator.explain_query_failure("Who is Alice's grandparent?")
explanation.format_for_human()
```

**Output:**
```
🔍 I looked for answers but didn't find any

💡 Why this happens:
   - The fact might not be in the knowledge base
   - The question might need different wording
   - You might need to add more facts first

💡 Try:
   - Check if the people/entities exist in the system
   - Try asking about simpler relationships first
   - Tell me about more connections between people
```

### 4. **Timeout/Depth Limit Exceeded**

**What went wrong:** The query was too complex and couldn't be answered in time.

```python
explanation = translator.explain_timeout(
    query="ancestor(X, bob)",
    depth_limit=10
)
```

**Output:**
```
⏰ The query took too long to find an answer

💡 Why this happens:
   - The knowledge base might be very large
   - The rules might have many possible chains
   - The system protects against infinite loops

💡 Try:
   - Ask a more specific question
   - Add constraints to narrow down the search
   - Check if there are circular rule definitions
```

### 5. **Ambiguous Input**

**What went wrong:** The natural language input is unclear or has multiple interpretations.

```python
explanation = translator.explain_ambiguous_input(
    input_str="Bob and Alice",
    options=["Are Bob and Alice siblings?", "Do Bob and Alice have the same parent?"]
)
```

**Output:**
```
🤔 I'm not sure what you're asking

Your input could mean:
1. Are Bob and Alice siblings?
2. Do Bob and Alice have the same parent?

💡 Try: Be more specific about what relationship you're asking about
```

## "Did You Mean?" Suggestions

The system uses **fuzzy string matching** to suggest similar entities when you misspell:

```python
translator.explain_validation_error(issue)
# "Did you mean: 'alice' (similarity: 85%)"? 
```

This helps beginners learn the exact names in the system without frustration.

## Two Output Formats

### 1. **Human Format** 🌟
```python
explanation.format_for_human()
```

Returns a friendly, emoji-rich explanation suitable for:
- Interactive chatbots
- Web interfaces showing error messages
- Learning-focused applications
- User-facing explanations

**Features:**
- Emojis for visual clarity
- Conversational tone
- Actionable "try this" suggestions
- "Did you mean?" recommendations

### 2. **LLM Format** 🤖
```python
explanation.format_for_llm()
```

Returns a structured explanation suitable for:
- Agent/LLM processing
- Automated error correction
- Integration with repair loops
- JSON/structured logging

**Features:**
- Structured dictionary format
- No emojis (cleaner for parsing)
- Categorized suggestions
- Machine-readable failure type

## Integration with SemanticPrologSkill

The Failure Explanation Layer **automatically integrates** with the NL→Prolog pipeline:

```python
from src.parser.semantic import SemanticPrologSkill

skill = SemanticPrologSkill()

result = skill.query_nl("Who is Charlie's parent?")

# If validation fails:
if "failure_explanation" in result:
    print(result["failure_explanation"])  # Human-friendly version
    print(result["why_it_failed"])        # Detailed explanation
    print(result["what_to_try"])          # Actionable suggestion
```

This means **users automatically get explanations without extra code**!

## For Developers: Extending Explanations

### Add new failure types:

```python
# 1. Add to ValidationError enum
class ValidationError(Enum):
    YOUR_ERROR_TYPE = "your_error"

# 2. Add explanation method
def explain_your_error(self, specific_context):
    return FailureExplanation(
        failure_type=FailureType.YOUR_ERROR_TYPE,
        human_explanation="...",
        technical_explanation="...",
        suggestions=["Try X", "Try Y"],
        error_cause="The rule Y was violated"
    )

# 3. Hook it into explain_validation_error() or appropriate method
```

### Customize similarity matching:

```python
# Change threshold for "did you mean" suggestions
min_similarity = 0.7  # 70% match

# Use different distance algorithm
from difflib import SequenceMatcher
ratio = SequenceMatcher(None, user_input, known_entity).ratio()
```

## Testing Explanations

Run the comprehensive test suite:

```bash
# Test failure translator (16 tests)
python -m pytest tests/test_failures.py -v

# Test integration with semantic validator (17 tests)
python -m pytest tests/test_semantic.py -v

# See explanations in action (interactive demo)
python scripts/demonstrate_failures.py
```

## Learning Path for Beginners

1. **First**: Run `python scripts/demonstrate_failures.py`
   - See success and failure scenarios side-by-side
   - Understand what queries work and why

2. **Second**: Read this documentation
   - Learn what each error type means
   - Understand how to fix each kind of failure

3. **Third**: Experiment with the code
   - Modify queries in `demonstrate_failures.py`
   - Try breaking things intentionally
   - Read the explanations to understand what happened

4. **Advanced**: Build your own knowledge base
   - Define facts for your domain
   - Write rules for complex reasoning
   - Use failure explanations to debug your rules

## Quick Reference: Error Types → Actions

| Error Type | Root Cause | What to Try |
|-----------|-----------|------------|
| Undefined Entity | Name not in KB | Add the entity or use known name |
| Ungrounded Predicate | Relationship unknown | Ask about known relationships |
| No Results | No path found | Add more facts or check connections |
| Timeout | Query too complex | Simplify or add constraints |
| Ambiguous Input | Unclear NL | Be more specific |

## Philosophy

> **The best error message is one that teaches.**

The Failure Explanation Layer isn't just about telling you something broke—it's about helping you understand *why* it broke and how to fix it. This is crucial for learning systems like NeSy.

## See Also

- [Semantic Grounding Documentation](legacy/semantic-grounding.md) - NL→Prolog conversion (legacy reference)
- [Semantic Validator Documentation](legacy/semantic-grounding.md) - Pre-execution checking (legacy reference)
- [Agent Integration Documentation](legacy/agent-integration.md) - Using this with LLM agents (legacy reference)
