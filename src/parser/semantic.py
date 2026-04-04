#!/usr/bin/env python3
"""
Semantic Grounding Layer for Prolog Reasoning.

Converts natural language queries to structured IR format using LLM assistance.

Architecture:
    NL Query → LLM Parser → IR Validation → Prolog Query

Example:
    Input: "Who is John's parent?"
    IR: QueryIR(predicate="parent", args=["john", Variable("X")])
    Prolog: "parent(john, X)."
"""

import re
import json
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ir.schema import IR, QueryIR, AssertionIR, RuleIR, IRType, validate_ir, FAMILY_SCHEMA, ACCESS_CONTROL_SCHEMA


class QueryIntent(Enum):
    """Types of user queries we can handle."""
    FACT_CHECK = "fact_check"          # "Is John Alice's parent?"
    VARIABLE_QUERY = "variable_query"  # "Who is John's parent?"
    LIST_QUERY = "list_query"          # "What are John's children?"
    ASSERTION = "assertion"            # "John is Alice's parent"
    RULE_DEFINITION = "rule"           # "An ancestor is a parent or grandparent"


@dataclass
class ParsedQuery:
    """Result of semantic parsing."""
    intent: QueryIntent
    ir: IR
    confidence: float
    raw_query: str
    domain: str = "general"  # "family", "access", "general"


class SemanticGrounder:
    """
    Converts natural language to structured IR using LLM assistance.

    Uses prompt engineering to guide LLM toward correct IR format.
    Includes validation and error correction.
    """

    def __init__(self, llm_client=None, max_retries: int = 3):
        """
        Initialize semantic grounder.

        Args:
            llm_client: LLM API client (OpenAI, Anthropic, etc.)
            max_retries: Max attempts for error correction
        """
        self.llm_client = llm_client or self._create_mock_llm()
        self.max_retries = max_retries

        # Schema registry
        self.schemas = {
            "family": FAMILY_SCHEMA,
            "access": ACCESS_CONTROL_SCHEMA,
            "general": {}  # Allow any predicates
        }

    def _create_mock_llm(self):
        """Mock LLM for testing without API keys."""
        def mock_llm(prompt: str) -> str:
            # Extract the actual query from the prompt
            query_start = prompt.find('Query: "') 
            if query_start != -1:
                query_end = prompt.find('"', query_start + 8)
                if query_end != -1:
                    query = prompt[query_start + 8:query_end].lower()
                else:
                    query = prompt.lower()
            else:
                query = prompt.lower()
            
            # Determine if it's a question or assertion
            is_question = "?" in query or query.startswith(("who", "what", "is ", "are ", "does", "can", "may"))
            is_assertion = (" is " in query or " are " in query) and not is_question
            
            if is_assertion:
                # Handle assertions
                return json.dumps({
                    "intent": "assertion",
                    "predicate": "parent",
                    "args": ["john", "alice"],
                    "confidence": 0.95,
                    "domain": "family"
                })
            else:
                # Handle questions/queries
                if "john" in query and "parent" in query:
                    return json.dumps({
                        "intent": "variable_query",
                        "predicate": "parent",
                        "args": ["john", "X"],
                        "confidence": 0.9,
                        "domain": "family"
                    })
                elif "parent" in query and ("who" in query or "what" in query):
                    return json.dumps({
                        "intent": "variable_query", 
                        "predicate": "parent",
                        "args": ["X", "Y"],
                        "confidence": 0.8,
                        "domain": "family"
                    })
                elif "ancestor" in query:
                    if "bob" in query:
                        return json.dumps({
                            "intent": "variable_query",
                            "predicate": "ancestor", 
                            "args": ["X", "bob"],
                            "confidence": 0.85,
                            "domain": "family"
                        })
                    else:
                        return json.dumps({
                            "intent": "fact_check",
                            "predicate": "ancestor",
                            "args": ["john", "alice"],
                            "confidence": 0.85,
                            "domain": "family"
                        })
                elif "allowed" in query or "permission" in query:
                    if "alice" in query and "read" in query:
                        return json.dumps({
                            "intent": "fact_check",
                            "predicate": "allowed",
                            "args": ["alice", "read"],
                            "confidence": 0.95,
                            "domain": "access"
                        })
                    elif "alice" in query:
                        return json.dumps({
                            "intent": "variable_query",
                            "predicate": "allowed",
                            "args": ["alice", "X"],
                            "confidence": 0.9,
                            "domain": "access"
                        })
                    else:
                        return json.dumps({
                            "intent": "variable_query",
                            "predicate": "allowed",
                            "args": ["X", "Y"],
                            "confidence": 0.8,
                            "domain": "access"
                        })
                elif "sibling" in query:
                    return json.dumps({
                        "intent": "fact_check",
                        "predicate": "sibling",
                        "args": ["alice", "bob"],
                        "confidence": 0.8,
                        "domain": "family"
                    })
                else:
                    return json.dumps({
                        "intent": "variable_query",
                        "predicate": "unknown",
                        "args": ["X"],
                        "confidence": 0.1,
                        "domain": "general"
                    })
        return mock_llm

    def ground_query(self, nl_query: str) -> ParsedQuery:
        """
        Convert natural language query to structured IR.

        Args:
            nl_query: Natural language query (e.g., "Who is John's parent?")

        Returns:
            ParsedQuery with IR representation
        """
        for attempt in range(self.max_retries):
            try:
                # Get LLM interpretation
                llm_response = self._query_llm(nl_query)

                # Parse LLM response
                parsed = self._parse_llm_response(llm_response, nl_query)

                # Validate IR
                schema = self.schemas.get(parsed.domain, self.schemas["general"])
                is_valid, errors = validate_ir(parsed.ir, schema)

                if is_valid:
                    return parsed
                else:
                    # Error correction attempt
                    if attempt < self.max_retries - 1:
                        llm_response = self._correct_errors(llm_response, errors, nl_query)
                        continue
                    else:
                        # Return best effort with low confidence
                        parsed.confidence *= 0.5
                        return parsed

            except Exception as e:
                if attempt == self.max_retries - 1:
                    # Return fallback
                    return self._create_fallback_query(nl_query)

        return self._create_fallback_query(nl_query)

    def _query_llm(self, nl_query: str) -> str:
        """Query LLM for semantic interpretation."""
        prompt = self._build_parsing_prompt(nl_query)
        return self.llm_client(prompt)

    def _build_parsing_prompt(self, nl_query: str) -> str:
        """Build prompt for LLM to parse natural language to IR."""

        return f"""Convert this natural language query to structured logical representation.

Query: "{nl_query}"

Instructions:
1. Identify the intent: fact_check, variable_query, list_query, assertion, or rule
2. Extract the logical predicate and arguments
3. Use variables (X, Y, Z) for unknowns
4. Determine the domain (family, access, general)
5. Provide confidence score (0.0-1.0)

Domains:
- Family: parent, sibling, ancestor, person
- Access: user, role, permission, allowed
- General: any predicates

Examples:
Query: "Is John Alice's parent?"
{{
    "intent": "fact_check",
    "predicate": "parent",
    "args": ["john", "alice"],
    "confidence": 0.95,
    "domain": "family"
}}

Query: "Who are John's children?"
{{
    "intent": "variable_query",
    "predicate": "parent",
    "args": ["john", "X"],
    "confidence": 0.9,
    "domain": "family"
}}

Query: "John is Alice's parent"
{{
    "intent": "assertion",
    "predicate": "parent",
    "args": ["john", "alice"],
    "confidence": 0.95,
    "domain": "family"
}}

Return only valid JSON:"""

    def _parse_llm_response(self, response: str, original_query: str) -> ParsedQuery:
        """Parse LLM JSON response into ParsedQuery."""
        try:
            data = json.loads(response.strip())

            # Extract intent
            intent = QueryIntent(data.get("intent", "variable_query"))

            # Build IR based on intent
            if intent == QueryIntent.ASSERTION:
                ir = AssertionIR(
                    predicate=data["predicate"],
                    args=self._normalize_args(data["args"]),
                    confidence=data.get("confidence", 0.5)
                )
            else:  # All query types
                ir = QueryIR(
                    predicate=data["predicate"],
                    args=self._normalize_args(data["args"]),
                    confidence=data.get("confidence", 0.5)
                )

            return ParsedQuery(
                intent=intent,
                ir=ir,
                confidence=data.get("confidence", 0.5),
                raw_query=original_query,
                domain=data.get("domain", "general")
            )

        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid LLM response: {response}") from e

    def _normalize_args(self, args: List[Any]) -> List[Any]:
        """Normalize arguments (handle variables, constants)."""
        normalized = []
        for arg in args:
            if isinstance(arg, str) and arg.isupper() and len(arg) == 1:
                # Variable like "X" -> Variable
                normalized.append(arg)  # Will be handled by IR->Prolog conversion
            else:
                # Constant
                normalized.append(arg.lower() if isinstance(arg, str) else arg)
        return normalized

    def _correct_errors(self, llm_response: str, errors: List[str], original_query: str) -> str:
        """Ask LLM to correct validation errors."""
        correction_prompt = f"""The previous parsing had these errors:
{chr(10).join(errors)}

Original query: "{original_query}"
Previous response: {llm_response}

Please correct the JSON response to fix these errors.
Return only valid JSON:"""

        return self.llm_client(correction_prompt)

    def _create_fallback_query(self, nl_query: str) -> ParsedQuery:
        """Create a fallback query when parsing fails."""
        # Simple keyword-based fallback
        query_lower = nl_query.lower()

        if "parent" in query_lower:
            return ParsedQuery(
                intent=QueryIntent.VARIABLE_QUERY,
                ir=QueryIR(predicate="parent", args=["X", "Y"]),
                confidence=0.1,
                raw_query=nl_query,
                domain="family"
            )
        elif "ancestor" in query_lower:
            return ParsedQuery(
                intent=QueryIntent.VARIABLE_QUERY,
                ir=QueryIR(predicate="ancestor", args=["X", "Y"]),
                confidence=0.1,
                raw_query=nl_query,
                domain="family"
            )
        else:
            return ParsedQuery(
                intent=QueryIntent.VARIABLE_QUERY,
                ir=QueryIR(predicate="unknown", args=["X"]),
                confidence=0.0,
                raw_query=nl_query,
                domain="general"
            )

    def to_prolog_query(self, parsed: ParsedQuery) -> str:
        """Convert parsed query to Prolog syntax."""
        prolog = parsed.ir.to_prolog()
        # Remove "? - " prefix for agent skill compatibility
        if prolog.startswith("?- "):
            return prolog[3:].strip()
        return prolog


# =============================================================================
# INTEGRATION WITH AGENT SKILL
# =============================================================================

class SemanticPrologSkill:
    """
    Enhanced agent skill with semantic grounding.

    Accepts natural language queries and converts them to Prolog.
    """

    def __init__(self, kb_path: str = "prolog/core.pl", llm_client=None):
        from agent_skill import PrologSkill

        self.prolog_skill = PrologSkill(kb_path)
        self.grounder = SemanticGrounder(llm_client)

    def query_nl(self, nl_query: str) -> Dict[str, Any]:
        """
        Query using natural language.

        Args:
            nl_query: Natural language query

        Returns:
            Same format as PrologSkill.query()
        """
        # Ground to IR
        parsed = self.grounder.ground_query(nl_query)

        # Convert to Prolog
        prolog_query = self.grounder.to_prolog_query(parsed)

        # Execute
        result = self.prolog_skill.query(prolog_query)

        # Add semantic metadata
        result.update({
            "nl_query": nl_query,
            "parsed_ir": parsed.ir.to_json(),
            "parsing_confidence": parsed.confidence,
            "domain": parsed.domain
        })

        return result


# =============================================================================
# DEMO AND TESTING
# =============================================================================

if __name__ == "__main__":
    # Test semantic grounding
    grounder = SemanticGrounder()

    test_queries = [
        "Who is John's parent?",
        "Is Alice allowed to read?",
        "John is Alice's parent",
        "Who are the ancestors of Bob?"
    ]

    print("=== Semantic Grounding Demo ===\n")

    for query in test_queries:
        print(f"Query: {query}")
        parsed = grounder.ground_query(query)
        prolog = grounder.to_prolog_query(parsed)

        print(f"Intent: {parsed.intent.value}")
        print(f"IR: {parsed.ir.to_json()}")
        print(f"Prolog: {prolog}")
        print(f"Confidence: {parsed.confidence:.2f}")
        print()

    # Test integrated skill
    print("=== Integrated Skill Demo ===\n")

    skill = SemanticPrologSkill()
    result = skill.query_nl("Who is John's parent?")
    print("NL Query Result:")
    
    # Make result JSON serializable
    serializable_result = {}
    for k, v in result.items():
        if k == "bindings" and isinstance(v, dict):
            serializable_result[k] = {str(kk): str(vv) for kk, vv in v.items()}
        else:
            serializable_result[k] = v
    
    print(json.dumps(serializable_result, indent=2))