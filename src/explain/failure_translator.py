#!/usr/bin/env python3
"""
Failure Explanation Layer for Prolog Reasoning.

Translates Prolog failures and validation errors into natural language
explanations that help LLM agents understand what went wrong and how to fix it.

Examples:
    Input: constraint_violation(no_revisit(location_a))
    Output: "You tried to visit location_a twice. Rules say you can only visit each location once."
    
    Input: undefined_entity(charlie)
    Output: "Charlie isn't known in the system. Did you mean Alice, John, or Bob?"
"""

from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from validator import ValidationError, ValidationIssue


class FailureType(Enum):
    """Types of failures that can occur."""
    VALIDATION_ERROR = "validation_error"      # Pre-execution validation failed
    QUERY_FAILED = "query_failed"              # Query returned no solutions
    CONSTRAINT_VIOLATED = "constraint_violated" # Constraint enforcement failed
    UNDEFINED_ENTITY = "undefined_entity"      # Entity not in KB
    UNGROUNDED_PREDICATE = "ungrounded_predicate"
    AMBIGUOUS_INPUT = "ambiguous_input"        # Can't determine intended meaning
    SYNTAX_ERROR = "syntax_error"              # Malformed input
    TIMEOUT = "timeout"                        # Query exceeded depth limit
    MISSING_FACT = "missing_fact"              # Required fact not provided


@dataclass
class FailureExplanation:
    """Explains why something failed."""
    failure_type: FailureType
    core_message: str                # What went wrong (simple)
    detailed_explanation: str        # Why it matters (technical)
    suggestion: str                  # How to fix it (actionable)
    confidence: float = 1.0         # How confident we are (0.0-1.0)


class FailureTranslator:
    """
    Translates system failures into human-readable explanations.
    
    Helps LLM agents understand and recover from errors.
    """
    
    def __init__(self, kb_entities: Optional[Set[str]] = None):
        """
        Initialize failure translator.
        
        Args:
            kb_entities: Known entities for did-you-mean suggestions
        """
        self.kb_entities = kb_entities or set()
    
    def explain_validation_error(self, issue: ValidationIssue) -> FailureExplanation:
        """
        Explain a validation error in human terms.
        
        Args:
            issue: ValidationIssue from semantic validator
            
        Returns:
            FailureExplanation with friendly message
        """
        if issue.error_type == ValidationError.UNDEFINED_ENTITY:
            return self._explain_undefined_entity(issue)
        elif issue.error_type == ValidationError.UNGROUNDED_PREDICATE:
            return self._explain_ungrounded_predicate(issue)
        elif issue.error_type == ValidationError.INCONSISTENT_FACTS:
            return self._explain_inconsistent_facts(issue)
        elif issue.error_type == ValidationError.MISSING_CONSTRAINT:
            return self._explain_missing_constraint(issue)
        else:
            return self._explain_generic_error(issue)
    
    def explain_query_failure(self, query: str, context: Optional[Dict[str, Any]] = None) -> FailureExplanation:
        """
        Explain why a query returned no solutions.
        
        Args:
            query: The Prolog query that failed
            context: Additional context (facts in KB, domain, etc.)
            
        Returns:
            FailureExplanation suggesting what might be wrong
        """
        return FailureExplanation(
            failure_type=FailureType.QUERY_FAILED,
            core_message=f"No answer found for: {query}",
            detailed_explanation=self._analyze_query_failure(query, context),
            suggestion=self._suggest_query_fix(query, context),
            confidence=0.7
        )
    
    def explain_timeout(self, query: str, depth_limit: int) -> FailureExplanation:
        """
        Explain that a query exceeded resource limits.
        
        Args:
            query: The query that timed out
            depth_limit: The depth limit that was exceeded
            
        Returns:
            FailureExplanation with suggestions
        """
        return FailureExplanation(
            failure_type=FailureType.TIMEOUT,
            core_message=f"Query took too long or got too complex",
            detailed_explanation=f"The reasoning depth exceeded {depth_limit} steps, which usually means either:\n"
                                f"  1. You're asking about very distant relationships (too many hops)\n"
                                f"  2. There's a circular reasoning loop\n"
                                f"  3. The KB is too large for this query",
            suggestion="Try asking about closer relationships, or check if there are circular dependencies in your rules",
            confidence=1.0
        )
    
    def explain_ambiguous_input(self, input_str: str, parsed_options: List[str]) -> FailureExplanation:
        """
        Explain that input was ambiguous.
        
        Args:
            input_str: The ambiguous input
            parsed_options: Possible interpretations
            
        Returns:
            FailureExplanation asking for clarification
        """
        options_str = "\n  - ".join(parsed_options)
        return FailureExplanation(
            failure_type=FailureType.AMBIGUOUS_INPUT,
            core_message=f"I'm not sure what you mean",
            detailed_explanation=f'"{input_str}" could mean:\n  - {options_str}',
            suggestion="Can you be more specific? Use names from the system (like 'Alice' instead of 'she')",
            confidence=0.5
        )
    
    def _explain_undefined_entity(self, issue: ValidationIssue) -> FailureExplanation:
        """Explain an undefined entity error."""
        # Extract entity name from message
        entity = self._extract_entity_name(issue.message)
        
        # Find similar entities for did-you-mean
        similar = self._find_similar_entities(entity, self.kb_entities)
        
        suggestion = f"Make sure to tell me about {entity} first, or use a name I know about"
        if similar:
            suggestion = f"Did you mean {' or '.join(similar)}? Or tell me about {entity} first"
        
        return FailureExplanation(
            failure_type=FailureType.UNDEFINED_ENTITY,
            core_message=f"I don't know who or what '{entity}' is",
            detailed_explanation=f"The system only knows about: {', '.join(sorted(self.kb_entities))}",
            suggestion=suggestion,
            confidence=0.9
        )
    
    def _explain_ungrounded_predicate(self, issue: ValidationIssue) -> FailureExplanation:
        """Explain an ungrounded predicate warning."""
        return FailureExplanation(
            failure_type=FailureType.UNGROUNDED_PREDICATE,
            core_message="I'm not sure what relationship you're asking about",
            detailed_explanation=f"The predicate seems new or unclear: {issue.message}",
            suggestion="Be explicit about what you want to know (parent, sibling, allowed, etc.)",
            confidence=0.7
        )
    
    def _explain_inconsistent_facts(self, issue: ValidationIssue) -> FailureExplanation:
        """Explain an inconsistency error."""
        return FailureExplanation(
            failure_type=FailureType.INCONSISTENT_FACTS,
            core_message="There's a contradiction in what you told me",
            detailed_explanation=f"{issue.message}",
            suggestion="Review your facts - you might have said something contradictory",
            confidence=0.8
        )
    
    def _explain_missing_constraint(self, issue: ValidationIssue) -> FailureExplanation:
        """Explain a missing constraint error."""
        return FailureExplanation(
            failure_type=FailureType.MISSING_CONSTRAINT,
            core_message="Some important rules might be missing",
            detailed_explanation=f"{issue.message}. This means the logic might not match your intent.",
            suggestion="Double-check that you've explained all the rules and constraints",
            confidence=0.6
        )
    
    def _explain_generic_error(self, issue: ValidationIssue) -> FailureExplanation:
        """Explain a generic/unknown error."""
        return FailureExplanation(
            failure_type=FailureType.SYNTAX_ERROR,
            core_message=f"Something went wrong: {issue.message}",
            detailed_explanation="The system encountered an unexpected issue",
            suggestion=issue.suggestion or "Try rephrasing your question or checking the facts",
            confidence=0.5
        )
    
    def _analyze_query_failure(self, query: str, context: Optional[Dict[str, Any]]) -> str:
        """Analyze why a query might have failed."""
        if context is None:
            context = {}
        
        # Check if it's a simple fact query
        if "(" in query and ")" in query:
            predicate = query.split("(")[0].strip()
            return (f"The system couldn't find any '{predicate}' relationships that match. "
                   f"Either the relationship doesn't exist, or you asked about the wrong entities.")
        
        return "The reasoning didn't find a path to an answer with the facts you provided."
    
    def _suggest_query_fix(self, query: str, context: Optional[Dict[str, Any]]) -> str:
        """Suggest how to fix a failing query."""
        suggestions = [
            "Check that all the names used exist in the system",
            "Make sure you've told the system all necessary facts",
            "Try a simpler question first",
        ]
        return ". ".join(suggestions) + "."
    
    def _extract_entity_name(self, message: str) -> str:
        """Extract entity name from error message."""
        # Simple extraction: look for quoted strings or patterns
        import re
        match = re.search(r"'([^']+)'", message)
        if match:
            return match.group(1)
        # Fallback: look for capitalized words
        words = message.split()
        for word in words:
            if word and word[0].isupper():
                return word
        return "[unknown]"
    
    def _find_similar_entities(self, entity: str, known_entities: Set[str]) -> List[str]:
        """Find entities similar to the given one for did-you-mean."""
        if not known_entities:
            return []
        
        entity_lower = entity.lower()
        similar = []
        
        # Exact match (caseless)
        for known in known_entities:
            if known.lower() == entity_lower:
                return [known]
        
        # Substring matches
        for known in known_entities:
            if entity_lower in known.lower() or known.lower() in entity_lower:
                similar.append(known)
        
        # Levenshtein-style simple distance (first letter match)
        if not similar:
            for known in known_entities:
                if known and entity and known[0].lower() == entity[0].lower():
                    similar.append(known)
        
        return similar[:3]  # Return top 3 suggestions
    
    def format_for_llm(self, explanation: FailureExplanation) -> str:
        """
        Format explanation for consumption by LLM agent.
        
        Args:
            explanation: FailureExplanation to format
            
        Returns:
            Formatted string suitable for LLM parsing
        """
        return f"""
FAILURE: {explanation.failure_type.value}

What went wrong:
{explanation.core_message}

Why:
{explanation.detailed_explanation}

Suggestion:
{explanation.suggestion}

Confidence: {explanation.confidence:.2f}
"""
    
    def format_for_human(self, explanation: FailureExplanation) -> str:
        """
        Format explanation for human readability.
        
        Args:
            explanation: FailureExplanation to format
            
        Returns:
            Formatted string readable by humans
        """
        return f"""
❌ {explanation.core_message}

📝 Why: {explanation.detailed_explanation}

💡 Try: {explanation.suggestion}
"""